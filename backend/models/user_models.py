"""
מודלי משתמשים ואוטנטיקציה
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import hashlib
import secrets
from passlib.context import CryptContext

# הגדרת הצפנת סיסמאות
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CUSTOMER = "customer"
    EMPLOYEE = "employee"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

# ====================
# Pydantic Models
# ====================

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('שם חייב להיות לפחות 2 תווים')
        return v.strip()
    
    @validator('phone')
    def validate_phone(cls, v):
        if v:
            # בדיקת פורמט טלפון ישראלי בסיסי
            cleaned = v.replace('-', '').replace(' ', '')
            if not cleaned.isdigit() or len(cleaned) < 9:
                raise ValueError('מספר טלפון לא תקין')
        return v

class UserCreate(UserBase):
    password: str
    confirm_password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('סיסמא חייבת להיות לפחות 6 תווים')
        
        # בדיקות נוספות לביטחון
        if not any(c.isdigit() for c in v):
            raise ValueError('סיסמא חייבת להכיל לפחות ספרה אחת')
        
        if not any(c.isalpha() for c in v):
            raise ValueError('סיסמא חייבת להכיל לפחות אות אחת')
        
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('סיסמאות לא תואמות')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None

class UserResponse(UserBase):
    user_id: str
    status: UserStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int = 3600  # שעה

# ====================
# User Domain Model
# ====================

class User:
    """מודל משתמש עבור Event Sourcing"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.email = ""
        self.first_name = ""
        self.last_name = ""
        self.phone = None
        self.password_hash = ""
        self.role = UserRole.CUSTOMER
        self.status = UserStatus.ACTIVE
        self.created_at = None
        self.updated_at = None
        self.last_login = None
        self.failed_login_attempts = 0
        self.locked_until = None
        self.deleted = False
    
    @staticmethod
    def hash_password(password: str) -> str:
        """הצפנת סיסמא"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """אימות סיסמא"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def apply_event(self, event):
        """יישום אירוע על המשתמש"""
        from database.event_store import EventType
        
        if event.event_type == EventType.USER_REGISTERED:
            self._apply_user_registered(event.data)
        elif event.event_type == EventType.USER_LOGIN:
            self._apply_user_login(event.data)
        elif event.event_type == "user_updated":
            self._apply_user_updated(event.data)
        elif event.event_type == "user_password_changed":
            self._apply_password_changed(event.data)
        elif event.event_type == "user_locked":
            self._apply_user_locked(event.data)
        elif event.event_type == "user_deleted":
            self._apply_user_deleted(event.data)
    
    def _apply_user_registered(self, data):
        """יישום אירוע רישום משתמש"""
        self.email = data.get("email", "")
        self.first_name = data.get("first_name", "")
        self.last_name = data.get("last_name", "")
        self.phone = data.get("phone")
        self.password_hash = data.get("password_hash", "")
        self.role = UserRole(data.get("role", UserRole.CUSTOMER))
        self.status = UserStatus(data.get("status", UserStatus.ACTIVE))
        self.created_at = data.get("created_at")
        self.failed_login_attempts = 0
    
    def _apply_user_login(self, data):
        """יישום אירוע כניסה"""
        self.last_login = data.get("login_time")
        if data.get("success", False):
            self.failed_login_attempts = 0
            self.locked_until = None
        else:
            self.failed_login_attempts += 1
            # נעילת חשבון אחרי 5 ניסיונות כושלים
            if self.failed_login_attempts >= 5:
                from datetime import timedelta
                self.locked_until = datetime.now() + timedelta(minutes=30)
    
    def _apply_user_updated(self, data):
        """יישום אירוע עדכון פרטי משתמש"""
        if "first_name" in data:
            self.first_name = data["first_name"]
        if "last_name" in data:
            self.last_name = data["last_name"]
        if "phone" in data:
            self.phone = data["phone"]
        if "role" in data:
            self.role = UserRole(data["role"])
        if "status" in data:
            self.status = UserStatus(data["status"])
        self.updated_at = data.get("updated_at")
    
    def _apply_password_changed(self, data):
        """יישום אירוע שינוי סיסמא"""
        self.password_hash = data.get("new_password_hash", self.password_hash)
        self.updated_at = data.get("changed_at")
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def _apply_user_locked(self, data):
        """יישום אירוע נעילת משתמש"""
        self.status = UserStatus.SUSPENDED
        self.locked_until = data.get("locked_until")
    
    def _apply_user_deleted(self, data):
        """יישום אירוע מחיקת משתמש"""
        self.deleted = True
        self.status = UserStatus.INACTIVE
    
    def is_locked(self) -> bool:
        """בדיקה אם המשתמש נעול"""
        if self.locked_until:
            return datetime.now() < self.locked_until
        return False
    
    def can_login(self) -> bool:
        """בדיקה אם המשתמש יכול להתחבר"""
        return (
            not self.deleted and
            self.status == UserStatus.ACTIVE and
            not self.is_locked()
        )
    
    def get_display_name(self) -> str:
        """שם להצגה"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def to_dict(self) -> dict:
        """המרה למילון"""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "display_name": self.get_display_name()
        }
    
    def to_response(self) -> UserResponse:
        """המרה למודל תגובה"""
        return UserResponse(
            user_id=self.user_id,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            phone=self.phone,
            role=self.role,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_login=self.last_login
        )

# ====================
# עזרים נוספים
# ====================

def generate_user_id() -> str:
    """יצירת ID ייחודי למשתמש"""
    import uuid
    return f"user-{uuid.uuid4()}"

def generate_session_token() -> str:
    """יצירת token לסשן"""
    return secrets.token_urlsafe(32)

def is_valid_email(email: str) -> bool:
    """בדיקת תקינות אימייל"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None