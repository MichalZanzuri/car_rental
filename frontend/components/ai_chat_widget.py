"""
רכיב צ'אט פשוט וחלק עם יועץ AI - ללא authentication
"""
import requests
import json
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
    QLabel, QComboBox, QSpinBox, QTabWidget, QGridLayout, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


class AIResponseThread(QThread):
    """Thread לטיפול בתשובות AI"""
    response_ready = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, url: str, payload: Dict, timeout: int = 120):
        super().__init__()
        self.url = url
        self.payload = payload
        self.timeout = timeout
    
    def run(self):
        try:
            response = requests.post(self.url, json=self.payload, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if 'response' in data:
                    self.response_ready.emit(data['response'])
                elif 'message' in data:
                    self.response_ready.emit(data['message'])
                else:
                    self.response_ready.emit(str(data))
            else:
                self.error_occurred.emit(f"שגיאת שרת: {response.status_code}")
        except requests.exceptions.Timeout:
            self.error_occurred.emit("Ollama לוקח זמן רב לעבד. נסה שוב בעוד כמה רגעים.")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"שגיאת חיבור: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"שגיאה: {str(e)}")


class AIChatWidget(QWidget):
    """רכיב צ'אט פשוט עם יועץ AI"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://localhost:8000"
        self.current_thread = None
        self.setup_ui()
        self.check_ai_status()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # כותרת
        title = QLabel("🤖 יועץ AI מתקדם - Ollama + Gemma 2B")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #2E86AB;
                background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
                padding: 15px;
                border-radius: 10px;
                border: 2px solid #1976D2;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # סטטוס AI
        self.status_label = QLabel("🔄 בודק סטטוס יועץ AI...")
        self.status_label.setStyleSheet("""
            QLabel {
                background: #FFF3E0;
                color: #F57C00;
                padding: 10px;
                border-radius: 5px;
                border-left: 4px solid #FF9800;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        # טאבים
        tabs = QTabWidget()
        
        # טאב צ'אט
        chat_tab = QWidget()
        chat_layout = QVBoxLayout(chat_tab)
        
        # כפתורי טיפים מהירים
        tips_frame = QFrame()
        tips_frame.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
                border-radius: 10px;
                padding: 10px;
                margin: 5px 0;
            }
        """)
        tips_layout = QGridLayout(tips_frame)
        
        quick_tips = [
            ("💡 טיפי הקיץ", "בקיץ מומלץ לבחור רכב עם מיזוג אוויר חזק"),
            ("🚗 רכב משפחתי", "איזה רכב הכי מתאים למשפחה עם ילדים?"),
            ("💰 חיסכון כסף", "איך אפשר לחסוך כסף בהשכרת רכב?"),
            ("🛡️ ביטוח רכב", "מה ההבדל בין סוגי הביטוח השונים?"),
            ("🏢 רכב עסקי", "איזה רכב מתאים לנסיעות עסקיות?"),
            ("🌟 רכבי יוקרה", "מתי כדאי לשכור רכב יוקרה?")
        ]
        
        for i, (title_text, question) in enumerate(quick_tips):
            btn = QPushButton(title_text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: linear-gradient(135deg, #{"E3F2FD" if i % 2 == 0 else "E8F5E9"} 0%, #{"BBDEFB" if i % 2 == 0 else "C8E6C9"} 100%);
                    color: #{"1976D2" if i % 2 == 0 else "388E3C"};
                    border: 2px solid #{"2196F3" if i % 2 == 0 else "4CAF50"};
                    padding: 8px 12px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: linear-gradient(135deg, #{"BBDEFB" if i % 2 == 0 else "C8E6C9"} 0%, #{"90CAF9" if i % 2 == 0 else "A5D6A7"} 100%);
                }}
            """)
            btn.clicked.connect(lambda checked, q=question: self.send_quick_tip(q))
            tips_layout.addWidget(btn, i // 3, i % 3)
        
        chat_layout.addWidget(QLabel("⚡ טיפים מהירים:"))
        chat_layout.addWidget(tips_frame)
        
        # אזור צ'אט
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: #FAFAFA;
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                padding: 15px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        chat_layout.addWidget(self.chat_display)
        
        # קלט הודעה
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("💬 שאל את יועץ ה-AI כל שאלה על השכרת רכבים...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #2196F3;
                border-radius: 25px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #1976D2;
                background: #F3F8FF;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("📤 שלח")
        self.send_button.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 25px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
            }
            QPushButton:disabled {
                background: #CCCCCC;
                color: #666666;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        chat_layout.addLayout(input_layout)
        
        # פרוגרס בר
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                color: #1976D2;
            }
            QProgressBar::chunk {
                background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
                border-radius: 3px;
            }
        """)
        chat_layout.addWidget(self.progress_bar)
        
        tabs.addTab(chat_tab, "💬 צ'אט AI")
        
        # טאב המלצות
        recommend_tab = self.create_recommend_tab()
        tabs.addTab(recommend_tab, "🚗 המלצות חכמות")
        
        layout.addWidget(tabs)
        
        # הודעת ברכה
        self.add_message("🤖 יועץ AI", """
        שלום! אני יועץ הרכבים האישי שלך, מופעל על ידי Ollama + Gemma 2B.
        
        🎯 אני יכול לעזור לך עם:
        • המלצות רכבים מותאמות אישית
        • ייעוץ ביטוח מקצועי
        • טיפי חיסכון וכסף
        • עצות לנהיגה בעונות השנה
        • בחירת רכבים עסקיים ומשפחתיים
        
        ⏱️ זמני תגובה: 30-90 שניות (Ollama מעבד בקפידה)
        
        איך אני יכול לעזור לך היום?
        """, "assistant")
    
    def create_recommend_tab(self):
        """יצירת טאב המלצות רכבים"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # כותרת
        title = QLabel("🚗 כלי המלצות רכבים חכם")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976D2; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # טופס המלצות
        form_layout = QVBoxLayout()
        
        # קטגוריית רכב
        layout_category = QHBoxLayout()
        layout_category.addWidget(QLabel("סוג רכב:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "🚗 רכב קומפקטי",
            "👨‍👩‍👧‍👦 רכב משפחתי", 
            "🏢 רכב עסקי",
            "🌟 רכב יוקרה",
            "🚙 רכב שטח",
            "🚐 מיניבוס"
        ])
        layout_category.addWidget(self.category_combo)
        form_layout.addLayout(layout_category)
        
        # מספר נוסעים
        layout_passengers = QHBoxLayout()
        layout_passengers.addWidget(QLabel("מספר נוסעים:"))
        self.passengers_spin = QSpinBox()
        self.passengers_spin.setRange(1, 8)
        self.passengers_spin.setValue(2)
        layout_passengers.addWidget(self.passengers_spin)
        form_layout.addLayout(layout_passengers)
        
        # תקציב
        layout_budget = QHBoxLayout()
        layout_budget.addWidget(QLabel("תקציב יומי (₪):"))
        self.budget_combo = QComboBox()
        self.budget_combo.addItems([
            "עד 100 ₪",
            "100-200 ₪", 
            "200-300 ₪",
            "300-500 ₪",
            "500+ ₪"
        ])
        layout_budget.addWidget(self.budget_combo)
        form_layout.addLayout(layout_budget)
        
        layout.addLayout(form_layout)
        
        # כפתור המלצה
        recommend_btn = QPushButton("🎯 קבל המלצת רכב מותאמת")
        recommend_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #388E3C 0%, #2E7D32 100%);
            }
        """)
        recommend_btn.clicked.connect(self.get_car_recommendation)
        layout.addWidget(recommend_btn)
        
        # תוצאות המלצה
        self.recommendation_display = QTextEdit()
        self.recommendation_display.setReadOnly(True)
        self.recommendation_display.setStyleSheet("""
            QTextEdit {
                background: #F8F9FA;
                border: 2px solid #28A745;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.recommendation_display)
        
        return widget
    
    def check_ai_status(self):
        """בדיקת סטטוס יועץ AI"""
        try:
            response = requests.get(f"{self.base_url}/api/ai/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'available':
                    self.status_label.setText("🟢 יועץ AI + Ollama פעיל ומוכן!")
                    self.status_label.setStyleSheet("""
                        QLabel {
                            background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
                            color: #2E7D32;
                            padding: 10px;
                            border-radius: 5px;
                            border-left: 4px solid #4CAF50;
                            font-weight: bold;
                        }
                    """)
                    
                    # מידע על המודל
                    model_info = data.get('active_model', 'לא ידוע')
                    models_list = data.get('ollama_models', [])
                    models_str = ', '.join(models_list[:3])
                    
                    tooltip_text = f"""מודל פעיל: {model_info}
מודלים זמינים: {models_str}
סטטוס: {data.get('message', '')}"""
                    self.status_label.setToolTip(tooltip_text)
                else:
                    self.status_label.setText("🟡 יועץ AI זמין חלקית")
            else:
                self.status_label.setText("🔴 יועץ AI לא זמין")
        except Exception as e:
            self.status_label.setText(f"❌ שגיאה: {str(e)}")
    
    def add_message(self, sender: str, message: str, sender_type: str = "user"):
        """הוספת הודעה לצ'אט"""
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
                {message.replace(chr(10), '<br>')}
            </div>
        </div>
        '''
        
        self.chat_display.insertHtml(formatted_message)
        
        # גלילה למטה
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def send_quick_tip(self, question: str):
        """שליחת טיפ מהיר"""
        self.message_input.setText(question)
        self.send_message()
    
    def send_message(self):
        """שליחת הודעה ליועץ AI - ללא authentication"""
        message = self.message_input.text().strip()
        if not message:
            return
        
        # הוספת הודעת המשתמש
        self.add_message("👤 משתמש", message, "user")
        self.message_input.clear()
        
        # הצגת התקדמות
        self.show_progress("🧠 Ollama חושב ומעבד את השאלה...")
        self.send_button.setEnabled(False)
        
        # הכנת הבקשה - ללא authentication
        payload = {"message": message}
        
        # שליחה באופן אסינכרוני
        self.current_thread = AIResponseThread(
            f"{self.base_url}/api/ai/chat", 
            payload,
            120  # timeout של 2 דקות
        )
        self.current_thread.response_ready.connect(self.handle_ai_response)
        self.current_thread.error_occurred.connect(self.handle_ai_error)
        self.current_thread.finished.connect(self.cleanup_request)
        self.current_thread.start()
    
    def get_car_recommendation(self):
        """קבלת המלצת רכב מותאמת"""
        # הכנת הפרמטרים
        category = self.category_combo.currentText()
        passengers = self.passengers_spin.value()
        budget = self.budget_combo.currentText()
        
        self.show_progress("🎯 מחפש המלצות רכבים מותאמות...")
        
        payload = {
            "category": category,
            "passengers": passengers,
            "budget": budget
        }
        
        self.current_thread = AIResponseThread(
            f"{self.base_url}/api/ai/recommend-car", 
            payload,
            90
        )
        self.current_thread.response_ready.connect(self.handle_recommendation_response)
        self.current_thread.error_occurred.connect(self.handle_ai_error)
        self.current_thread.finished.connect(self.cleanup_request)
        self.current_thread.start()
    
    def show_progress(self, message: str):
        """הצגת התקדמות"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # אינדטרמיניסטי
        self.progress_bar.setFormat(f"⏳ {message}")
    
    def hide_progress(self):
        """הסתרת התקדמות"""
        self.progress_bar.setVisible(False)
    
    def handle_ai_response(self, response: str):
        """טיפול בתשובת AI"""
        self.add_message("🤖 יועץ Ollama", response, "assistant")
    
    def handle_recommendation_response(self, response: str):
        """טיפול בתשובת המלצה"""
        formatted_response = f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); 
                    border-radius: 10px; border: 2px solid #4CAF50;">
            <h3 style="color: #2E7D32; margin-bottom: 15px;">🎯 המלצת רכב מותאמת אישית</h3>
            <div style="color: #1B5E20; line-height: 1.8; font-size: 14px;">
                {response.replace(chr(10), '<br>')}
            </div>
        </div>
        """
        self.recommendation_display.setHtml(formatted_response)
    
    def handle_ai_error(self, error: str):
        """טיפול בשגיאות AI"""
        self.add_message("❌ מערכת", f"בעיה בקבלת תשובת AI: {error}", "assistant")
    
    def cleanup_request(self):
        """ניקוי אחרי בקשה"""
        self.hide_progress()
        self.send_button.setEnabled(True)
        
        # תיקון שגיאת QThread
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit()
            self.current_thread.wait()
        
        self.current_thread = None