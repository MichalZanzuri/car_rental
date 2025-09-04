"""
API endpoints לאוטנטיקציה וניהול משתמשים
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import sys
import os

# הוספת נתיב לחיפוש מודולים
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth_service import auth_service, get_current_user, require_admin, require_manager_or_admin
from models.user_models import (
    UserCreate, UserLogin, UserResponse, TokenResponse, 
    UserUpdate, UserRole, User
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ====================
# Authentication Endpoints
# ====================

@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    """רישום משתמש חדש"""
    try:
        new_user = auth_service.register_user(user_data)
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה ברישום: {str(e)}")

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """כניסה למערכת"""
    try:
        return auth_service.authenticate_user(login_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בכניסה: {str(e)}")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """קבלת פרטי המשתמש הנוכחי"""
    return current_user.to_response()

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """יציאה מהמערכת"""
    # כרגע פשוט מחזירים הודעה - בעתיד נוכל לשמור blacklist של tokens
    return {
        "message": "התנתקת בהצלחה",
        "user": current_user.get_display_name()
    }

@router.put("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user)
):
    """שינוי סיסמא"""
    # אימות הסיסמא הישנה
    if not User.verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="הסיסמא הנוכחית שגויה")
    
    # בדיקת תקינות הסיסמא החדשה
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="סיסמא חייבת להיות לפחות 6 תווים")
    
    # כאן נוסיף event לשינוי סיסמא
    # לצורך הדוגמא, נחזיר הצלחה
    return {"message": "הסיסמא שונתה בהצלחה"}

# ====================
# User Management Endpoints (Admin Only)
# ====================

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(admin_user: User = Depends(require_admin)):
    """קבלת כל המשתמשים (אדמין בלבד)"""
    try:
        return auth_service.get_all_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת משתמשים: {str(e)}")

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    admin_user: User = Depends(require_admin)
):
    """עדכון תפקיד משתמש (אדמין בלבד)"""
    try:
        updated_user = auth_service.update_user_role(user_id, new_role, admin_user.user_id)
        return {
            "message": "תפקיד המשתמש עודכן בהצלחה",
            "user": updated_user
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בעדכון תפקיד: {str(e)}")

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    admin_user: User = Depends(require_manager_or_admin)
):
    """קבלת פרטי משתמש לפי ID (מנהל או אדמין)"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")
    
    return user.to_response()

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: User = Depends(require_admin)
):
    """מחיקת משתמש (אדמין בלבד)"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")
    
    if user.user_id == admin_user.user_id:
        raise HTTPException(status_code=400, detail="אי אפשר למחוק את עצמך")
    
    # כאן נוסיף event למחיקת משתמש
    return {"message": f"המשתמש {user.get_display_name()} נמחק בהצלחה"}

# ====================
# Validation Endpoints
# ====================

@router.get("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """בדיקת תקינות token"""
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role.value,
        "name": current_user.get_display_name()
    }

@router.get("/check-email/{email}")
async def check_email_availability(email: str):
    """בדיקת זמינות אימייל"""
    existing_user = auth_service.get_user_by_email(email)
    return {
        "available": existing_user is None,
        "message": "האימייל זמין" if existing_user is None else "האימייל כבר קיים במערכת"
    }

# ====================
# Statistics Endpoints
# ====================

@router.get("/stats")
async def get_auth_stats(admin_user: User = Depends(require_admin)):
    """סטטיסטיקות אוטנטיקציה (אדמין בלבד)"""
    try:
        all_users = auth_service.get_all_users()
        
        stats = {
            "total_users": len(all_users),
            "active_users": len([u for u in all_users if u.status.value == "active"]),
            "users_by_role": {},
            "recent_registrations": 0
        }
        
        # סטטיסטיקות לפי תפקיד
        for user in all_users:
            role = user.role.value
            stats["users_by_role"][role] = stats["users_by_role"].get(role, 0) + 1
        
        # רישומים אחרונים (השבוע האחרון)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        
        stats["recent_registrations"] = len([
            u for u in all_users 
            if u.created_at and datetime.fromisoformat(u.created_at.replace("Z", "+00:00").replace("+00:00", "")) > week_ago
        ])
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת סטטיסטיקות: {str(e)}")

# ====================
# Development/Testing Endpoints
# ====================

@router.post("/create-admin")
async def create_admin_user():
    """יצירת משתמש אדמין ראשוני (לפיתוח בלבד)"""
    try:
        # בדיקה שאין כבר אדמין
        all_users = auth_service.get_all_users()
        admin_exists = any(user.role.value == "admin" for user in all_users)
        
        if admin_exists:
            raise HTTPException(status_code=400, detail="כבר קיים משתמש אדמין במערכת")
        
        admin_data = UserCreate(
            email="admin@carrental.com",
            password="admin123",
            confirm_password="admin123",
            first_name="מנהל",
            last_name="מערכת",
            phone="050-1234567",
            role=UserRole.ADMIN
        )
        
        new_admin = auth_service.register_user(admin_data)
        return {
            "message": "משתמש אדמין נוצר בהצלחה",
            "user": new_admin,
            "login_details": {
                "email": "admin@carrental.com",
                "password": "admin123"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה ביצירת אדמין: {str(e)}")