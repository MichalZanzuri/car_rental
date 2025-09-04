"""
שירות אוטנטיקציה וניהול משתמשים
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# הוספת נתיב לחיפוש מודולים
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.event_store import event_service, Event, EventType
from models.user_models import User, UserCreate, UserLogin, TokenResponse, UserResponse, UserRole

# הגדרות JWT
SECRET_KEY = "your-secret-key-change-this-in-production-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 שעות

security = HTTPBearer()

class AuthService:
    """שירות אוטנטיקציה"""
    
    def __init__(self):
        self.event_service = event_service
    
    def create_access_token(self, user_data: dict, expires_delta: Optional[timedelta] = None):
        """יצירת JWT token"""
        to_encode = user_data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """אימות JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token לא תקין",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def register_user(self, user_data: UserCreate) -> UserResponse:
        """רישום משתמש חדש"""
        
        # בדיקה שהאימייל לא קיים
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="משתמש עם האימייל הזה כבר קיים במערכת"
            )
        
        # יצירת ID חדש למשתמש
        user_id = f"user-{uuid.uuid4()}"
        
        # הצפנת סיסמא
        password_hash = User.hash_password(user_data.password)
        
        # הכנת נתוני האירוע
        registration_data = {
            "email": user_data.email.lower(),
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone": user_data.phone,
            "password_hash": password_hash,
            "role": user_data.role.value,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
        # יצירת אירוע רישום
        event = Event(
            event_type=EventType.USER_REGISTERED,
            aggregate_id=user_id,
            data=registration_data,
            user_id="system"
        )
        
        # שמירת האירוע
        if self.event_service.event_store.append_event(event):
            # החזרת המשתמש החדש
            user = self._rebuild_user_from_events(user_id)
            if user:
                return user.to_response()
        
        raise HTTPException(
            status_code=500,
            detail="שגיאה ברישום המשתמש"
        )
    
    def authenticate_user(self, login_data: UserLogin) -> TokenResponse:
        """אימות משתמש וכניסה למערכת"""
        
        # חיפוש המשתמש לפי אימייל
        user = self.get_user_by_email(login_data.email)
        if not user:
            self._log_failed_login(login_data.email, "user_not_found")
            raise HTTPException(
                status_code=401,
                detail="אימייל או סיסמא שגויים"
            )
        
        # בדיקה שהמשתמש יכול להתחבר
        if not user.can_login():
            self._log_failed_login(login_data.email, "user_locked")
            if user.is_locked():
                raise HTTPException(
                    status_code=423,
                    detail="החשבון נעול זמנית. נסה שוב מאוחר יותר"
                )
            else:
                raise HTTPException(
                    status_code=403,
                    detail="החשבון לא פעיל"
                )
        
        # אימות סיסמא
        if not User.verify_password(login_data.password, user.password_hash):
            self._log_failed_login(login_data.email, "wrong_password")
            raise HTTPException(
                status_code=401,
                detail="אימייל או סיסמא שגויים"
            )
        
        # רישום כניסה מוצלחת
        self._log_successful_login(user.user_id)
        
        # יצירת token
        token_data = {
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role.value,
            "name": user.get_display_name()
        }
        
        access_token = self.create_access_token(token_data)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user.to_response(),
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """חיפוש משתמש לפי אימייל"""
        # קבלת כל אירועי הרישום
        user_events = self.event_service.event_store.get_all_events(EventType.USER_REGISTERED)
        
        for event in user_events:
            if event.data.get("email", "").lower() == email.lower():
                user = self._rebuild_user_from_events(event.aggregate_id)
                if user and not user.deleted:
                    return user
        
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """חיפוש משתמש לפי ID"""
        return self._rebuild_user_from_events(user_id)
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """קבלת המשתמש הנוכחי מה-token"""
        token = credentials.credentials
        payload = self.verify_token(token)
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token לא תקין"
            )
        
        user = self.get_user_by_id(user_id)
        if not user or not user.can_login():
            raise HTTPException(
                status_code=401,
                detail="המשתמש לא קיים או לא פעיל"
            )
        
        return user
    
    def require_role(self, required_role: UserRole):
        """דקורטור לבדיקת הרשאות"""
        def role_checker(current_user: User = Depends(self.get_current_user)) -> User:
            if current_user.role.value != required_role.value:
                # אדמין יכול לעשות הכל
                if current_user.role != UserRole.ADMIN:
                    raise HTTPException(
                        status_code=403,
                        detail="אין הרשאה לפעולה זו"
                    )
            return current_user
        
        return role_checker
    
    def get_all_users(self) -> list[UserResponse]:
        """קבלת כל המשתמשים (לאדמין)"""
        users = []
        user_events = self.event_service.event_store.get_all_events(EventType.USER_REGISTERED)
        
        user_ids = set(event.aggregate_id for event in user_events)
        
        for user_id in user_ids:
            user = self._rebuild_user_from_events(user_id)
            if user and not user.deleted:
                users.append(user.to_response())
        
        return users
    
    def update_user_role(self, user_id: str, new_role: UserRole, admin_user_id: str) -> UserResponse:
        """עדכון תפקיד משתמש (לאדמין)"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="משתמש לא נמצא")
        
        update_data = {
            "role": new_role.value,
            "updated_at": datetime.now().isoformat(),
            "updated_by": admin_user_id
        }
        
        event = Event(
            event_type="user_updated",
            aggregate_id=user_id,
            data=update_data,
            user_id=admin_user_id
        )
        
        if self.event_service.event_store.append_event(event):
            updated_user = self._rebuild_user_from_events(user_id)
            return updated_user.to_response()
        
        raise HTTPException(status_code=500, detail="שגיאה בעדכון המשתמש")
    
    def _rebuild_user_from_events(self, user_id: str) -> Optional[User]:
        """בנייה מחדש של משתמש מהאירועים"""
        events = self.event_service.event_store.get_events(user_id)
        if not events:
            return None
        
        user = User(user_id)
        for event in events:
            user.apply_event(event)
        
        return user
    
    def _log_successful_login(self, user_id: str):
        """רישום כניסה מוצלחת"""
        login_data = {
            "login_time": datetime.now().isoformat(),
            "success": True,
            "ip_address": None,  # נוכל להוסיף בעתיד
            "user_agent": None
        }
        
        event = Event(
            event_type=EventType.USER_LOGIN,
            aggregate_id=user_id,
            data=login_data,
            user_id=user_id
        )
        
        self.event_service.event_store.append_event(event)
    
    def _log_failed_login(self, email: str, reason: str):
        """רישום כניסה כושלת"""
        login_data = {
            "login_time": datetime.now().isoformat(),
            "success": False,
            "email": email,
            "reason": reason,
            "ip_address": None,
            "user_agent": None
        }
        
        # אם יש משתמש עם האימייל הזה, נרשום את האירוע עליו
        user = self.get_user_by_email(email)
        if user:
            event = Event(
                event_type=EventType.USER_LOGIN,
                aggregate_id=user.user_id,
                data=login_data,
                user_id="anonymous"
            )
            self.event_service.event_store.append_event(event)

# יצירת instance גלובלי
auth_service = AuthService()

# פונקציות עזר לשימוש ב-FastAPI
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """קבלת המשתמש הנוכחי"""
    return auth_service.get_current_user(credentials)

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """בדיקת הרשאות אדמין"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="נדרשות הרשאות אדמין"
        )
    return current_user

def require_manager_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """בדיקת הרשאות מנהל או אדמין"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=403,
            detail="נדרשות הרשאות מנהל"
        )
    return current_user