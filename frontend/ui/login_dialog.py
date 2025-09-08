"""
מסך כניסה למערכת השכרת רכבים
"""

import sys
import requests
import json
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QPushButton, QLineEdit, QCheckBox, QFrame, QTextEdit,
    QProgressBar, QTabWidget, QWidget, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QPixmap, QPalette, QColor

# ====================
# API Client for Authentication
# ====================

class AuthAPI:
    """ממשק לשירותי האוטנטיקציה"""
    
    BASE_URL = "http://localhost:8000"
    
    @staticmethod
    def login(email: str, password: str) -> Dict[str, Any]:
        """כניסה למערכת"""
        try:
            response = requests.post(
                f"{AuthAPI.BASE_URL}/api/auth/login",
                json={"email": email, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("detail", "שגיאה לא ידועה")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "לא ניתן להתחבר לשרת"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "פג הזמן לחיבור"}
        except Exception as e:
            return {"success": False, "error": f"שגיאה: {str(e)}"}
    
    @staticmethod
    def register(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """רישום משתמש חדש"""
        try:
            response = requests.post(
                f"{AuthAPI.BASE_URL}/api/auth/register",
                json=user_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("detail", "שגיאה ברישום")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"שגיאה: {str(e)}"}
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """אימות תקינות token"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{AuthAPI.BASE_URL}/api/auth/validate-token",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Token לא תקין"}
                
        except Exception as e:
            return {"success": False, "error": f"שגיאה באימות: {str(e)}"}

# ====================
# Session Manager
# ====================

class SessionManager:
    """ניהול הפעלת המשתמש"""
    
    def __init__(self):
        self.token = None
        self.user_data = None
        self.is_logged_in = False
    
    def login(self, token: str, user_data: Dict[str, Any]):
        """רישום כניסה"""
        self.token = token
        self.user_data = user_data
        self.is_logged_in = True
    
    def logout(self):
        """יציאה מהמערכת"""
        self.token = None
        self.user_data = None
        self.is_logged_in = False
    
    def get_auth_header(self) -> Dict[str, str]:
        """קבלת header לאוטנטיקציה"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def get_user_name(self) -> str:
        """קבלת שם המשתמש"""
        if self.user_data:
            return f"{self.user_data.get('first_name', '')} {self.user_data.get('last_name', '')}".strip()
        return "משתמש"
    
    def get_user_role(self) -> str:
        """קבלת תפקיד המשתמש"""
        if self.user_data:
            return self.user_data.get('role', 'customer')
        return 'customer'
    
    def is_admin(self) -> bool:
        """בדיקה אם המשתמש אדמין"""
        return self.get_user_role() == 'admin'

# Session גלובלי
session_manager = SessionManager()

# ====================
# Login Dialog
# ====================

class LoginDialog(QDialog):
    """מסך כניסה למערכת"""
    
    login_successful = Signal(dict)  # Signal לכניסה מוצלחת
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("כניסה למערכת השכרת רכבים")
        self.setFixedSize(450, 600)
        self.setModal(True)
        
        # משתנים
        self.is_loading = False
        
        self.setup_ui()
        self.setup_styles()
        
        # מילוי אוטומטי לפיתוח
        self.fill_demo_data()
    
    def setup_ui(self):
        """הגדרת ממשק המשתמש"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # כותרת
        title_label = QLabel("🚗 מערכת השכרת רכבים")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # תת כותרת
        subtitle_label = QLabel("התחבר לחשבון שלך")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)
        
        # טאבים - כניסה ורישום
        self.tabs = QTabWidget()
        
        # טאב כניסה
        login_tab = self.create_login_tab()
        self.tabs.addTab(login_tab, "כניסה")
        
        # טאב רישום
        register_tab = self.create_register_tab()
        self.tabs.addTab(register_tab, "רישום")
        
        layout.addWidget(self.tabs)
        
        # אזור הודעות
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.hide()
        layout.addWidget(self.message_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # מצב אינסופי
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # כפתורי פעולה
        buttons_layout = QHBoxLayout()
        
        self.login_button = QPushButton("התחבר")
        self.login_button.setMinimumHeight(40)
        self.login_button.clicked.connect(self.handle_login)
        
        self.register_button = QPushButton("הירשם")
        self.register_button.setMinimumHeight(40)
        self.register_button.clicked.connect(self.handle_register)
        
        self.cancel_button = QPushButton("ביטול")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.register_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        # כפתור עזרה/מידע
        info_layout = QHBoxLayout()
        #demo_button = QPushButton("מלא נתונים לדוגמא")
        #demo_button.clicked.connect(self.fill_demo_data)
        #info_layout.addWidget(demo_button)
        
        server_status_button = QPushButton("בדוק חיבור לשרת")
        server_status_button.clicked.connect(self.check_server_status)
        info_layout.addWidget(server_status_button)
        
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
    
    def create_login_tab(self):
        """יצירת טאב כניסה"""
        widget = QWidget()
        form_layout = QFormLayout()
        
        # שדות כניסה
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        form_layout.addRow("אימייל:", self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("הכנס סיסמא")
        form_layout.addRow("סיסמא:", self.password_input)
        
        # זכור אותי
        self.remember_checkbox = QCheckBox("זכור אותי")
        form_layout.addRow("", self.remember_checkbox)
        
        widget.setLayout(form_layout)
        return widget
    
    def create_register_tab(self):
        """יצירת טאב רישום"""
        widget = QWidget()
        form_layout = QFormLayout()
        
        # שדות רישום
        self.reg_email_input = QLineEdit()
        self.reg_email_input.setPlaceholderText("example@email.com")
        form_layout.addRow("אימייל:", self.reg_email_input)
        
        self.reg_first_name_input = QLineEdit()
        self.reg_first_name_input.setPlaceholderText("שם פרטי")
        form_layout.addRow("שם פרטי:", self.reg_first_name_input)
        
        self.reg_last_name_input = QLineEdit()
        self.reg_last_name_input.setPlaceholderText("שם משפחה")
        form_layout.addRow("שם משפחה:", self.reg_last_name_input)
        
        self.reg_phone_input = QLineEdit()
        self.reg_phone_input.setPlaceholderText("050-1234567")
        form_layout.addRow("טלפון:", self.reg_phone_input)
        
        self.reg_password_input = QLineEdit()
        self.reg_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("סיסמא:", self.reg_password_input)
        
        self.reg_confirm_password_input = QLineEdit()
        self.reg_confirm_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("אימות סיסמא:", self.reg_confirm_password_input)
        
        # תפקיד
        self.role_combo = QComboBox()
        self.role_combo.addItems(["customer", "employee", "manager"])
        form_layout.addRow("תפקיד:", self.role_combo)
        
        widget.setLayout(form_layout)
        return widget
    
    def setup_styles(self):
        """עיצוב הממשק"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 12px;
                background-color: white;
            }
            
            QLineEdit:focus {
                border-color: #2E86C1;
            }
            
            QPushButton {
                background-color: #2E86C1;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #2874A6;
            }
            
            QPushButton:pressed {
                background-color: #1B4F72;
            }
            
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                background-color: white;
                border-radius: 5px;
            }
            
            QTabBar::tab {
                background-color: #ecf0f1;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            
            QTabBar::tab:selected {
                background-color: #2E86C1;
                color: white;
            }
            
            QLabel {
                color: #2c3e50;
            }
        """)
    
    def fill_demo_data(self):
        """מילוי נתונים לדוגמא"""
        current_tab = self.tabs.currentIndex()
        
        if current_tab == 0:  # טאב כניסה
            self.email_input.setText("admin@carrental.com")
            self.password_input.setText("admin123")
        else:  # טאב רישום
            self.reg_email_input.setText("user@test.com")
            self.reg_first_name_input.setText("משה")
            self.reg_last_name_input.setText("כהן")
            self.reg_phone_input.setText("050-1234567")
            self.reg_password_input.setText("123456")
            self.reg_confirm_password_input.setText("123456")
    
    def check_server_status(self):
        """בדיקת מצב השרת"""
        self.show_message("בודק חיבור לשרת...", "info")
        
        try:
            response = requests.get(f"{AuthAPI.BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                self.show_message("✅ החיבור לשרת תקין", "success")
            else:
                self.show_message("⚠️ השרת לא מגיב כראוי", "warning")
        except Exception as e:
            self.show_message(f"❌ לא ניתן להתחבר לשרת: {str(e)}", "error")
    
    def handle_login(self):
        """טיפול בכניסה"""
        if self.is_loading:
            return
        
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            self.show_message("אנא מלא את כל השדות", "error")
            return
        
        self.start_loading("מתחבר...")
        
        # כניסה ברקע
        QTimer.singleShot(100, lambda: self._perform_login(email, password))
    
    def handle_register(self):
        """טיפול ברישום"""
        if self.is_loading:
            return
        
        # איסוף נתונים
        user_data = {
            "email": self.reg_email_input.text().strip(),
            "first_name": self.reg_first_name_input.text().strip(),
            "last_name": self.reg_last_name_input.text().strip(),
            "phone": self.reg_phone_input.text().strip(),
            "password": self.reg_password_input.text().strip(),
            "confirm_password": self.reg_confirm_password_input.text().strip(),
            "role": self.role_combo.currentText()
        }
        
        # בדיקות בסיסיות
        if not all([user_data["email"], user_data["first_name"], 
                   user_data["last_name"], user_data["password"]]):
            self.show_message("אנא מלא את כל השדות החובה", "error")
            return
        
        if user_data["password"] != user_data["confirm_password"]:
            self.show_message("סיסמאות לא תואמות", "error")
            return
        
        self.start_loading("נרשם...")
        
        # רישום ברקע
        QTimer.singleShot(100, lambda: self._perform_register(user_data))
    
    def _perform_login(self, email: str, password: str):
        """ביצוע כניסה בפועל"""
        result = AuthAPI.login(email, password)
        
        if result["success"]:
            token_data = result["data"]
            
            # שמירה בסשן
            session_manager.login(
                token_data["access_token"],
                token_data["user"]
            )
            
            self.show_message(f"🎉 ברוך הבא, {session_manager.get_user_name()}!", "success")
            
            # סגירת החלון אחרי רגע
            QTimer.singleShot(1500, self.accept_login)
            
        else:
            self.show_message(f"❌ {result['error']}", "error")
        
        self.stop_loading()
    
    def _perform_register(self, user_data: dict):
        """ביצוע רישום בפועל"""
        result = AuthAPI.register(user_data)
        
        if result["success"]:
            self.show_message("✅ נרשמת בהצלחה! כעת תוכל להתחבר", "success")
            # מעבר לטאב כניסה
            self.tabs.setCurrentIndex(0)
            self.email_input.setText(user_data["email"])
            
        else:
            self.show_message(f"❌ {result['error']}", "error")
        
        self.stop_loading()
    
    def accept_login(self):
        """אישור כניסה וסגירת החלון"""
        self.login_successful.emit(session_manager.user_data)
        self.accept()
    
    def start_loading(self, message: str):
        """התחלת מצב טעינה"""
        self.is_loading = True
        self.progress_bar.show()
        self.show_message(message, "info")
        
        # נכבה כפתורים
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)
    
    def stop_loading(self):
        """סיום מצב טעינה"""
        self.is_loading = False
        self.progress_bar.hide()
        
        # נדליק כפתורים
        self.login_button.setEnabled(True)
        self.register_button.setEnabled(True)
    
    def show_message(self, message: str, msg_type: str = "info"):
        """הצגת הודעה למשתמש"""
        self.message_label.setText(message)
        self.message_label.show()
        
        # צביעה לפי סוג הודעה
        if msg_type == "error":
            self.message_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        elif msg_type == "success":
            self.message_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        elif msg_type == "warning":
            self.message_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        else:
            self.message_label.setStyleSheet("color: #3498db; font-weight: bold;")
        
        # הסתרת ההודעה אחרי 5 שניות
        if msg_type in ["success", "error"]:
            QTimer.singleShot(5000, self.message_label.hide)