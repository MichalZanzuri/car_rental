"""
רכיב צ'אט מלא עם יועץ AI + RAG למערכת השכרת רכבים
גרסה מתוקנת עם אוטנטיקציה
"""
import requests
import json
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QPushButton, QSplitter, QGroupBox,
    QComboBox, QSpinBox, QLabel, QScrollArea,
    QFrame, QMessageBox, QProgressBar, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

# Import session manager for authentication
from ui.login_dialog import session_manager

API_BASE_URL = "http://localhost:8000"

# ---------- THREAD לקבלת תשובות AI ----------
class AIResponseThread(QThread):
    response_received = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, message: str, endpoint: str = "chat", data: Dict = None):
        super().__init__()
        self.message = message
        self.endpoint = endpoint
        self.data = data or {}
        
    def run(self):
        try:
            # הכנת headers עם authentication
            headers = {
                "Authorization": f"Bearer {session_manager.get_token()}",
                "Content-Type": "application/json"
            }
            
            if self.endpoint == "chat":
                payload = {"message": self.message, "context": self.data}
                url = f"{API_BASE_URL}/api/ai/chat"
                response = requests.post(url, headers=headers, json=payload, timeout=60)
            elif self.endpoint == "recommend":
                payload = self.data
                url = f"{API_BASE_URL}/api/ai/recommend-car"
                response = requests.post(url, headers=headers, json=payload, timeout=60)
            elif self.endpoint.startswith("tips"):
                category = self.endpoint.replace("tips_", "")
                url = f"{API_BASE_URL}/api/ai/quick-tips?category={category}"
                response = requests.get(url, headers=headers, timeout=30)
            else:
                url = f"{API_BASE_URL}/api/ai/quick-tips"
                response = requests.get(url, headers=headers, timeout=30)
                
            if response.status_code == 200:
                data = response.json()
                self.response_received.emit(data.get("response", "אין תשובה"))
            elif response.status_code == 401:
                self.error_occurred.emit("לא מורשה - אנא התחבר מחדש למערכת")
            elif response.status_code == 404:
                self.error_occurred.emit("שירות AI לא נמצא - וודא שהשרת רץ עם AI endpoints")
            else:
                self.error_occurred.emit(f"שגיאת שרת: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            self.error_occurred.emit("הבקשה לקחה זמן רב מדי. יועץ הAI עדיין חושב...")
        except Exception as e:
            self.error_occurred.emit(f"שגיאה בתקשורת: {str(e)}")

# ---------- WIDGET פעולות מהירות ----------
class QuickActionsWidget(QWidget):
    action_requested = Signal(str, str)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("🚀 פעולות מהירות עם יועץ AI חכם")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: #2E86AB; margin: 5px;")
        layout.addWidget(title)
        
        # טיפים מהירים
        tips_group = QGroupBox("💡 טיפים מהירים")
        tips_layout = QVBoxLayout()
        
        row1_layout = QHBoxLayout()
        tips_row1 = [("👨‍👩‍👧‍👦", "רכב משפחתי", "family"),
                     ("💰", "חיסכון וכלכלה", "budget"),
                     ("🛡️", "ביטוח", "insurance")]
        for icon, text, action in tips_row1:
            btn = QPushButton(f"{icon} {text}")
            btn.clicked.connect(lambda checked, a=action: self.action_requested.emit("tips", a))
            btn.setStyleSheet("padding: 8px; margin: 2px;")
            row1_layout.addWidget(btn)
        
        row2_layout = QHBoxLayout()
        tips_row2 = [("🚦", "נהיגה בטוחה", "driving"),
                     ("💎", "רכבי יוקרה", "luxury"),
                     ("🚚", "רכבים מסחריים", "commercial")]
        for icon, text, action in tips_row2:
            btn = QPushButton(f"{icon} {text}")
            btn.clicked.connect(lambda checked, a=action: self.action_requested.emit("tips", a))
            btn.setStyleSheet("padding: 8px; margin: 2px;")
            row2_layout.addWidget(btn)
        
        tips_layout.addLayout(row1_layout)
        tips_layout.addLayout(row2_layout)
        tips_group.setLayout(tips_layout)
        layout.addWidget(tips_group)
        
        # המלצות רכבים
        recommendation_group = QGroupBox("🔍 מוצא רכב מותאם עם AI")
        rec_layout = QVBoxLayout()
        
        input_layout = QHBoxLayout()
        self.budget_spin = QSpinBox()
        self.budget_spin.setRange(50, 1000)
        self.budget_spin.setValue(200)
        self.budget_spin.setSuffix(" ש״ח")
        
        self.passengers_spin = QSpinBox()
        self.passengers_spin.setRange(1, 8)
        self.passengers_spin.setValue(2)
        
        self.purpose_combo = QComboBox()
        self.purpose_combo.addItems(["עירונית", "משפחתית", "עסקית", "חופשה", "הובלה"])
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 30)
        self.duration_spin.setValue(3)
        
        input_layout.addWidget(QLabel("תקציב יומי:"))
        input_layout.addWidget(self.budget_spin)
        input_layout.addWidget(QLabel("נוסעים:"))
        input_layout.addWidget(self.passengers_spin)
        input_layout.addWidget(QLabel("מטרה:"))
        input_layout.addWidget(self.purpose_combo)
        input_layout.addWidget(QLabel("ימים:"))
        input_layout.addWidget(self.duration_spin)
        
        recommend_btn = QPushButton("🤖 קבל המלצה חכמה מהAI")
        recommend_btn.clicked.connect(self.request_ai_recommendation)
        recommend_btn.setStyleSheet("background-color: #3498db; color: white; padding: 10px; font-weight: bold;")
        
        rec_layout.addLayout(input_layout)
        rec_layout.addWidget(recommend_btn)
        recommendation_group.setLayout(rec_layout)
        layout.addWidget(recommendation_group)
        
        self.setLayout(layout)
        
    def request_ai_recommendation(self):
        purpose_map = {"עירונית": "city", "משפחתית": "family", "עסקית": "business",
                       "חופשה": "vacation", "הובלה": "commercial"}
        
        recommendation_data = {
            "budget": self.budget_spin.value(),
            "passengers": self.passengers_spin.value(),
            "purpose": purpose_map[self.purpose_combo.currentText()],
            "duration": self.duration_spin.value(),
            "preferences": []
        }
        
        details = f"מחפש רכב עבור {recommendation_data['passengers']} נוסעים, " \
                  f"תקציב {recommendation_data['budget']} ש״ח ליום, " \
                  f"למטרת {self.purpose_combo.currentText()}, למשך {recommendation_data['duration']} ימים"
        
        self.action_requested.emit("user_message", details)
        self.action_requested.emit("recommend", json.dumps(recommendation_data))

# ---------- WIDGET הצגת צ'אט ----------
class ChatDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(400)
        self.chat_display.setFont(QFont("Arial", 11))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.chat_display)
        self.setLayout(layout)
        
        welcome_message = """
🤖 **יועץ השכרת רכבים החכם בעולם!**

ברוך הבא למערכת יועץ AI המתקדמת ביותר לשכירת רכבים! 

**אני משתמש בטכנולוגיית RAG מתקדמת עם:**
• מסד ידע עצום על רכבים וביטוח
• למידת מכונה עם Ollama AI
• חיפוש וקטורי חכם עם ChromaDB

**אני יכול לעזור לך עם:**
• 🚗 המלצות מותאמות אישית על רכבים
• 💰 טיפים לחיסכון וביטוח
• 👨‍👩‍👧‍👦 בחירת רכב משפחתי מושלם
• 🚦 עצות נהיגה בטוחה
• 📋 מידע על תקנות ודרישות
• ❓ כל שאלה אחרת על השכרת רכבים

**שאל אותי כל שאלה - אני הולך לתת לך תשובה מקצועית ומדויקת!**
        """
        self.add_message("🤖 יועץ AI מתקדם", welcome_message, "assistant")
        
    def add_message(self, sender: str, message: str, sender_type: str = "user"):
        timestamp = datetime.now().strftime("%H:%M")
        if sender_type == "assistant":
            color, bg_color, border_color, icon = "#2E86AB", "#E3F2FD", "#1976D2", "🤖"
        else:
            color, bg_color, border_color, icon = "#27AE60", "#E8F5E8", "#4CAF50", "👤"
        formatted_message = f'''
        <div style="margin: 15px 0; padding: 15px; background: linear-gradient(135deg, {bg_color} 0%, #ffffff 100%); 
                    border-radius: 12px; border-left: 5px solid {border_color}; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <div style="color: {color}; font-weight: bold; margin-bottom: 8px; display: flex; align-items: center;">
                <span style="font-size: 16px; margin-right: 8px;">{icon}</span>
                {sender} - {timestamp}
            </div>
            <div style="color: #2C3E50; line-height: 1.6; font-size: 14px;">
                {message.replace('\n', '<br>')}
            </div>
        </div>
        '''
        self.chat_display.insertHtml(formatted_message)
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.End)
        self.chat_display.setTextCursor(cursor)

# ---------- WIDGET סטטוס RAG ----------
class RAGStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.check_status()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_status)
        self.timer.start(30000)
        
    def setup_ui(self):
        layout = QHBoxLayout()
        self.status_label = QLabel("בודק סטטוס יועץ AI...")
        self.status_label.setStyleSheet("color: #7F8C8D; font-size: 12px;")
        layout.addWidget(self.status_label)
        layout.addStretch()
        self.setLayout(layout)
        
    def check_status(self):
        try:
            # בדיקת סטטוס בלי authentication - זה endpoint פתוח
            response = requests.get(f"{API_BASE_URL}/api/ai/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                if status == "available":
                    self.status_label.setText("🟢 יועץ AI + RAG פעיל ומוכן!")
                    self.status_label.setStyleSheet("color: #27AE60; font-weight: bold;")
                elif status == "partial":
                    self.status_label.setText("🟡 יועץ AI פעיל חלקית")
                    self.status_label.setStyleSheet("color: #F39C12; font-weight: bold;")
                else:
                    self.status_label.setText("🔴 יועץ AI לא זמין")
                    self.status_label.setStyleSheet("color: #E74C3C; font-weight: bold;")
            else:
                self.status_label.setText("⚠️ בעיה בחיבור לשרת")
                self.status_label.setStyleSheet("color: #E67E22;")
        except:
            self.status_label.setText("❌ לא ניתן להתחבר לשרת AI")
            self.status_label.setStyleSheet("color: #E74C3C; font-weight: bold;")

# ---------- WIDGET ראשי של יועץ AI ----------
class AIChatWidget(QTabWidget):
    """הווידג'ט הראשי לצ'אט עם AI עם טאבים"""
    
    def __init__(self):
        super().__init__()
        self.current_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        # טאב ראשי - צ'אט
        chat_tab = QWidget()
        chat_layout = QVBoxLayout()
        
        # כותרת
        title_label = QLabel("🤖 יועץ השכרת רכבים עם בינה מלאכותית")
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2E86AB; margin: 10px; padding: 10px; background: #F0F8FF; border-radius: 8px;")
        chat_layout.addWidget(title_label)
        
        # סטטוס RAG
        self.status_widget = RAGStatusWidget()
        chat_layout.addWidget(self.status_widget)
        
        # חלק עליון - פעולות מהירות
        self.quick_actions = QuickActionsWidget()
        self.quick_actions.action_requested.connect(self.handle_quick_action)
        chat_layout.addWidget(self.quick_actions)
        
        # קו הפרדה
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #BDC3C7;")
        chat_layout.addWidget(line)
        
        # אזור הצ'אט
        self.chat_display = ChatDisplayWidget()
        chat_layout.addWidget(self.chat_display)
        
        # אזור הקלדה
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("כתוב כאן את השאלה שלך ליועץ הAI החכם...")
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input.setStyleSheet("padding: 10px; font-size: 14px; border-radius: 5px; border: 2px solid #BDC3C7;")
        
        self.send_button = QPushButton("🚀 שאל את יועץ הAI")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet("background-color: #3498db; color: white; padding: 10px 20px; font-weight: bold; border-radius: 5px;")
        
        # מחוון טעינה
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #3498db; }")
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        chat_layout.addWidget(self.progress_bar)
        
        chat_tab.setLayout(chat_layout)
        
        # הוספת הטאב
        self.addTab(chat_tab, "💬 צ'אט עם יועץ AI")
        
        # טאב מידע על RAG
        info_tab = self.create_info_tab()
        self.addTab(info_tab, "ℹ️ מידע על המערכת")
        
    def create_info_tab(self):
        """יצירת טאב מידע על המערכת"""
        info_widget = QWidget()
        layout = QVBoxLayout()
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        
        content = """
# 🤖 מידע על יועץ השכרת רכבים החכם

## 🧠 טכנולוגיות מתקדמות
המערכת מבוססת על הטכנולוגיות המתקדמות ביותר:

### 🔍 RAG (Retrieval Augmented Generation)
- חיפוש וקטורי חכם במסד הידע
- שילוב מידע רלוונטי עם יכולות AI
- תשובות מדויקות ומעודכנות

### 🦙 Ollama AI Engine  
- מודל שפה מקומי ומהיר
- מותאם למידע על רכבים וביטוח
- פועל ללא תלות באינטרנט

### 📊 ChromaDB Vector Database
- מסד נתונים וקטורי מתקדם
- חיפוש דמיון סמנטי
- אחסון יעיל של מסד הידע

## 📚 מסד הידע כולל:
- מידע מפורט על כל סוגי הרכבים
- הוראות ביטוח ותקנות
- טיפי נהיגה בטוחה
- עצות חיסכון וכלכלה
- מידע מקצועי עדכני

## 🎯 יכולות המערכת:
- המלצות מותאמות אישית
- ניתוח צרכים מתקדם
- עצות מקצועיות מדויקות
- למידה מתמשכת
- תמיכה 24/7

---
**המערכת פותחה במיוחד עבור פרויקט הנדסת מערכות חלונות**
        """
        
        info_text.setMarkdown(content)
        info_text.setStyleSheet("background-color: #f8f9fa; font-family: Arial;")
        
        layout.addWidget(info_text)
        info_widget.setLayout(layout)
        
        return info_widget
        
    def handle_quick_action(self, action_type: str, data: str):
        """טיפול בפעולות מהירות"""
        if action_type == "user_message":
            # הצג הודעת משתמש
            user_info = session_manager.get_user_info()
            user_name = user_info.get("first_name", "משתמש") if user_info else "משתמש"
            self.chat_display.add_message(user_name, data, "user")
            return
            
        self.set_loading(True, "יועץ ה-AI חושב...")
        
        if action_type == "tips":
            self.current_thread = AIResponseThread("", f"tips_{data}")
        elif action_type == "recommend":
            try:
                rec_data = json.loads(data)
                self.current_thread = AIResponseThread("", "recommend", rec_data)
            except:
                self.show_error("שגיאה בנתוני ההמלצה")
                return
        
        self.current_thread.response_received.connect(self.display_response)
        self.current_thread.error_occurred.connect(self.show_error)
        self.current_thread.start()
        
    def send_message(self):
        """שלח הודעה לAI"""
        message = self.message_input.text().strip()
        if not message:
            return
            
        # הצג הודעת המשתמש
        user_info = session_manager.get_user_info()
        user_name = user_info.get("first_name", "משתמש") if user_info else "משתמש"
        
        self.chat_display.add_message(user_name, message, "user")
        self.message_input.clear()
        self.set_loading(True, "יועץ ה-AI עובד על התשובה...")
        
        # שלח לAI
        self.current_thread = AIResponseThread(message, "chat")
        self.current_thread.response_received.connect(self.display_response)
        self.current_thread.error_occurred.connect(self.show_error)
        self.current_thread.start()
        
    def display_response(self, response: str):
        """הצג תשובת AI"""
        self.chat_display.add_message("🤖 יועץ AI מתקדם", response, "assistant")
        self.set_loading(False)
        
    def show_error(self, error_message: str):
        """הצג שגיאה"""
        self.chat_display.add_message("⚠️ שגיאה", f"מצטער, נתקלתי בבעיה: {error_message}\n\nאנא נסה שוב או פנה לתמיכה טכנית.", "assistant")
        self.set_loading(False)
        
    def set_loading(self, loading: bool, message: str = ""):
        """הגדר מצב טעינה"""
        if loading:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # אנימציה אינסופית
            self.send_button.setText(message)
            self.send_button.setEnabled(False)
            self.message_input.setEnabled(False)
        else:
            self.progress_bar.setVisible(False)
            self.send_button.setText("🚀 שאל את יועץ הAI")
            self.send_button.setEnabled(True)
            self.message_input.setEnabled(True)