"""
רכיב צ'אט מלא עם יועץ AI + RAG – גרסה מעוצבת בהתאמה למערכת
- RTL מלא, כרטיסים לבנים עם גבול #E6EAF0 ורדיוס 12
- צבע ראשי אדום #EF4444 לכפתורים/אינטראקציות
- טאב־בר מעודן, “שבבי” טיפים (Pills), בועות צ’אט נקיות
- אוטנטיקציה דרך session_manager, תמיכה ב-chat / recommend / quick-tips
"""

import json
from datetime import datetime
from typing import Dict, Optional

import requests
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QSplitter, QGroupBox, QComboBox, QSpinBox, QLabel, QScrollArea, QFrame,
    QMessageBox, QProgressBar, QTabWidget, QSizePolicy, QGridLayout
)

# אימות (נלקח מהפרויקט שלך)
from ui.login_dialog import session_manager

API_BASE_URL = "http://localhost:8000"

# ===== Theme (מתואם לשאר המערכת) =====
PRIMARY        = "#EF4444"
PRIMARY_HOVER  = "#DC2626"
BORDER         = "#E6EAF0"
CARD_BG        = "#FFFFFF"
SURFACE        = "#F8FAFC"
TEXT_PRIMARY   = "#0F172A"
TEXT_MUTED     = "#667085"
ACCENT_BLUE    = "#1E3A8A"
SUCCESS_BG     = "#E8F5E9"
SUCCESS_BORDER = "#4CAF50"
WARNING        = "#F59E0B"
DANGER         = "#EF4444"
OK_GREEN       = "#22C55E"

# ===== Helpers =====
def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))

# ---------- THREAD לקבלת תשובות AI ----------
class AIResponseThread(QThread):
    response_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, message: str, endpoint: str = "chat", data: Dict = None, timeout: int = 60):
        super().__init__()
        self.message = message
        self.endpoint = endpoint
        self.data = data or {}
        self.timeout = timeout

    def run(self):
        try:
            token = session_manager.get_token()
            headers = {
                "Authorization": f"Bearer {token}" if token else "",
                "Content-Type": "application/json"
            }

            if self.endpoint == "chat":
                payload = {"message": self.message, "context": self.data}
                url = f"{API_BASE_URL}/api/ai/chat"
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

            elif self.endpoint == "recommend":
                payload = self.data
                url = f"{API_BASE_URL}/api/ai/recommend-car"
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

            elif self.endpoint.startswith("tips"):
                category = self.endpoint.replace("tips_", "")
                url = f"{API_BASE_URL}/api/ai/quick-tips?category={category}"
                response = requests.get(url, headers=headers, timeout=self.timeout // 2)

            else:
                url = f"{API_BASE_URL}/api/ai/quick-tips"
                response = requests.get(url, headers=headers, timeout=self.timeout // 2)

            if response.status_code == 200:
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                text = data.get("response") or data.get("message") or json.dumps(data, ensure_ascii=False)
                self.response_received.emit(text)

            elif response.status_code == 401:
                self.error_occurred.emit("לא מורשה - אנא התחבר מחדש למערכת")
            elif response.status_code == 404:
                self.error_occurred.emit("שירות AI לא נמצא - וודא שהשרת רץ עם AI endpoints")
            else:
                self.error_occurred.emit(f"שגיאת שרת: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            self.error_occurred.emit("הבקשה לקחה זמן רב מדי. יועץ ה-AI עדיין חושב…")
        except Exception as e:
            self.error_occurred.emit(f"שגיאה בתקשורת: {str(e)}")

# ---------- WIDGET פעולות מהירות ----------
class QuickActionsWidget(QWidget):
    action_requested = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setup_ui()

    def _chip(self, label: str, action: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:#FFFFFF; color:{TEXT_PRIMARY};
                border:1px solid {BORDER}; border-radius:999px;
                padding:6px 12px; font-size:12.5px; font-weight:600;
            }}
            QPushButton:hover {{ background:{SURFACE}; border-color:{PRIMARY}; color:{PRIMARY}; }}
        """)
        btn.clicked.connect(lambda _=None, a=action: self.action_requested.emit("tips", a))
        return btn

    def setup_ui(self):
        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;}}")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)

        title = QLabel("🚀 פעולות מהירות")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet(f"color:{ACCENT_BLUE};")
        v.addWidget(title, 0, Qt.AlignRight)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        tips = [
            ("👨‍👩‍👧‍👦 רכב משפחתי", "family"),
            ("💰 חיסכון וכלכלה", "budget"),
            ("🛡️ ביטוח", "insurance"),
            ("🚦 נהיגה בטוחה", "driving"),
            ("💎 רכבי יוקרה", "luxury"),
            ("🚚 רכבים מסחריים", "commercial"),
        ]
        for i, (label, key) in enumerate(tips):
            grid.addWidget(self._chip(label, key), i // 3, i % 3, Qt.AlignRight)
        v.addLayout(grid)

        # חוצץ
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet(f"color:{BORDER};")
        v.addWidget(sep)

        # טופס המלצה קצר
        form_row = QHBoxLayout()
        form_row.setSpacing(8)

        self.budget_spin = QSpinBox(); self.budget_spin.setRange(50, 1000); self.budget_spin.setValue(200); self.budget_spin.setSuffix(" ₪")
        self.passengers_spin = QSpinBox(); self.passengers_spin.setRange(1, 8); self.passengers_spin.setValue(2)
        self.purpose_combo = QComboBox(); self.purpose_combo.addItems(["עירונית", "משפחתית", "עסקית", "חופשה", "הובלה"])
        self.duration_spin = QSpinBox(); self.duration_spin.setRange(1, 30); self.duration_spin.setValue(3)

        # סגנון שדות
        field_css = f"QComboBox, QSpinBox {{ background:#FFFFFF; border:1px solid {BORDER}; border-radius:10px; min-height:36px; padding:0 10px; }}"
        self.budget_spin.setStyleSheet(field_css)
        self.passengers_spin.setStyleSheet(field_css)
        self.purpose_combo.setStyleSheet(field_css)
        self.duration_spin.setStyleSheet(field_css)

        def add_labeled(lbl, w):
            box = QVBoxLayout(); box.setSpacing(4)
            t = QLabel(lbl); t.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12.5px;")
            box.addWidget(t, 0, Qt.AlignRight); box.addWidget(w)
            wrapper = QFrame(); wrapper.setLayout(box); return wrapper

        form_row.addWidget(add_labeled("תקציב יומי", self.budget_spin))
        form_row.addWidget(add_labeled("נוסעים", self.passengers_spin))
        form_row.addWidget(add_labeled("מטרה", self.purpose_combo))
        form_row.addWidget(add_labeled("ימים", self.duration_spin))

        v.addLayout(form_row)

        btn = QPushButton("🤖 קבל המלצה חכמה")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:white; border:none; border-radius:10px;
                padding:10px 14px; font-weight:700;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
        """)
        btn.clicked.connect(self.request_ai_recommendation)
        v.addWidget(btn, 0, Qt.AlignLeft)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(card)

    def request_ai_recommendation(self):
        purpose_map = {"עירונית": "city", "משפחתית": "family", "עסקית": "business", "חופשה": "vacation", "הובלה": "commercial"}
        recommendation_data = {
            "budget": self.budget_spin.value(),
            "passengers": self.passengers_spin.value(),
            "purpose": purpose_map[self.purpose_combo.currentText()],
            "duration": self.duration_spin.value(),
            "preferences": []
        }
        details = (f"מחפש רכב עבור {recommendation_data['passengers']} נוסעים, "
                   f"תקציב {recommendation_data['budget']} ₪ ליום, "
                   f"למטרת {self.purpose_combo.currentText()}, למשך {recommendation_data['duration']} ימים")
        self.action_requested.emit("user_message", details)
        self.action_requested.emit("recommend", json.dumps(recommendation_data, ensure_ascii=False))

# ---------- WIDGET הצגת צ'אט ----------
class ChatDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setup_ui()

    def setup_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(380)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;
                padding:12px; font-size:14px; color:{TEXT_PRIMARY};
            }}
        """)
        v.addWidget(self.chat_display)

        welcome = (
            "🤖 **יועץ השכרת רכבים**\n\n"
            "ברוך הבא! אני עובד בשילוב RAG + Ollama כדי לתת תשובות מדויקות.\n\n"
            "מה אפשר לשאול?\n"
            "• המלצות רכבים מותאמות\n"
            "• טיפים לביטוח וחיסכון\n"
            "• עצות למשפחות/עסקים/שטח\n"
        )
        self.add_message("יועץ AI", welcome, "assistant")

    def add_message(self, sender: str, message: str, sender_type: str = "user"):
        ts = datetime.now().strftime("%H:%M")
        text = html_escape(message).replace("\n", "<br>")
        if sender_type == "assistant":
            accent = ACCENT_BLUE; icon = "🤖"
        else:
            accent = PRIMARY; icon = "👤"

        html = f"""
        <div style="margin:10px 0; padding:12px; background:#FFFFFF; border:1px solid {BORDER}; border-radius:12px; direction:rtl;">
            <div style="color:{TEXT_MUTED}; font-size:12px; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                <span style="font-size:16px">{icon}</span>
                <span style="color:{TEXT_PRIMARY}; font-weight:700">{html_escape(sender)}</span>
                <span>• {ts}</span>
            </div>
            <div style="border-right:4px solid {accent}; padding-right:10px; color:{TEXT_PRIMARY}; line-height:1.6; font-size:14px;">
                {text}
            </div>
        </div>
        """
        self.chat_display.insertHtml(html)
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

# ---------- WIDGET סטטוס RAG ----------
class RAGStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setup_ui()
        self.check_status()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_status)
        self.timer.start(30000)

    def setup_ui(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.dot = QLabel(); self.dot.setFixedSize(10, 10); self.dot.setStyleSheet(f"background:{DANGER}; border-radius:5px;")
        self.label = QLabel("שרת AI: מנותק"); self.label.setStyleSheet(f"color:{TEXT_PRIMARY}; font-weight:600;")
        h.addWidget(self.label, 0, Qt.AlignRight)
        h.addWidget(self.dot, 0, Qt.AlignRight)
        h.addStretch(1)

    def check_status(self):
        try:
            r = requests.get(f"{API_BASE_URL}/api/ai/health", timeout=6)
            ok = r.status_code == 200 and (r.json() or {}).get("status") == "available"
            self.dot.setStyleSheet(f"background:{OK_GREEN if ok else DANGER}; border-radius:5px;")
            self.label.setText(f"שרת AI: {'מחובר' if ok else 'מנותק'}")
        except Exception:
            self.dot.setStyleSheet(f"background:{DANGER}; border-radius:5px;")
            self.label.setText("שרת AI: מנותק")

# ---------- WIDGET ראשי של יועץ AI ----------
class AIChatWidget(QTabWidget):
    """הווידג'ט הראשי לצ'אט עם AI עם טאבים – עיצוב אחיד"""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.current_thread: Optional[AIResponseThread] = None
        self.setup_ui()

    def setup_ui(self):
        # סגנון טאב־בר
        self.setDocumentMode(True)
        self.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background:{SURFACE}; color:{TEXT_PRIMARY};
                border:1px solid {BORDER}; padding:8px 12px; border-radius:10px; margin:4px;
                font-weight:600;
            }}
            QTabBar::tab:selected {{ background:{CARD_BG}; border-color:{PRIMARY}; color:{PRIMARY}; }}
            QTabBar::tab:hover {{ background:{CARD_BG}; }}
        """)

        # --- Tab: Chat ---
        chat_tab = QWidget()
        chat_v = QVBoxLayout(chat_tab)
        chat_v.setContentsMargins(0, 0, 0, 0)
        chat_v.setSpacing(12)

        # Header card: כותרת + סטטוס
        header = QFrame()
        header.setStyleSheet(f"QFrame{{background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;}}")
        hh = QHBoxLayout(header); hh.setContentsMargins(14, 12, 14, 12)

        title = QLabel("🤖 יועץ השכרת רכבים (RAG + Ollama)")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet(f"color:{ACCENT_BLUE};")
        hh.addWidget(title, 0, Qt.AlignRight)

        hh.addStretch(1)
        self.status = RAGStatusWidget()
        hh.addWidget(self.status, 0)

        chat_v.addWidget(header)

        # Quick actions (card)
        self.quick_actions = QuickActionsWidget()
        self.quick_actions.action_requested.connect(self.handle_quick_action)
        chat_v.addWidget(self.quick_actions)

        # Chat display (card)
        self.chat_display = ChatDisplayWidget()
        chat_v.addWidget(self.chat_display)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("כתוב כאן את השאלה שלך…")
        self.message_input.setStyleSheet(f"""
            QLineEdit {{
                background:#FFFFFF; border:1px solid {BORDER}; border-radius:999px;
                padding:12px 16px; font-size:14px;
            }}
            QLineEdit:focus {{ border-color:{PRIMARY}; }}
        """)
        self.message_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("שלח")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.setFixedWidth(110)
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:white; border:none; border-radius:999px;
                padding:12px 16px; font-weight:700;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background:#CCCCCC; color:#666666; }}
        """)
        self.send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.message_input, 1)
        input_row.addWidget(self.send_button, 0, Qt.AlignLeft)
        chat_v.addLayout(input_row)

        # Progress (card-like)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background:{CARD_BG}; border:1px solid {BORDER}; border-radius:10px;
                text-align:center; color:{ACCENT_BLUE}; font-weight:600;
            }}
            QProgressBar::chunk {{ background:{PRIMARY}; border-radius:8px; }}
        """)
        chat_v.addWidget(self.progress_bar)

        self.addTab(chat_tab, "💬 צ'אט AI")

        # --- Tab: Info ---
        info_tab = self.create_info_tab()
        self.addTab(info_tab, "ℹ️ מידע על המערכת")

    def create_info_tab(self):
        info = QWidget()
        v = QVBoxLayout(info)
        v.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;}}")
        inner = QVBoxLayout(card); inner.setContentsMargins(14, 14, 14, 14)

        text = QTextEdit(); text.setReadOnly(True)
        text.setStyleSheet(f"QTextEdit{{background:{CARD_BG}; border:none; color:{TEXT_PRIMARY};}}")
        text.setMarkdown("""
# 🤖 מידע על יועץ השכרת רכבים

## 🧠 טכנולוגיות
- **RAG**: איחזור ידע משולב יצירה
- **Ollama**: מנוע שפה מקומי
- **ChromaDB**: חיפוש וקטורי סמנטי

## 📚 מסד הידע
- רכבים, ביטוח, תקנות, חיסכון, בטיחות ועוד

## 🎯 יכולות
- המלצות מותאמות, ניתוח צרכים, תמיכה 24/7
        """)
        inner.addWidget(text)
        v.addWidget(card)
        return info

    # ---------- Actions & Flow ----------
    def handle_quick_action(self, action_type: str, data: str):
        if action_type == "user_message":
            user = (session_manager.get_user_info() or {}).get("first_name", "משתמש")
            self.chat_display.add_message(user, data, "user")
            return

        self.set_loading(True, "יועץ ה-AI חושב…")

        if action_type == "tips":
            self.current_thread = AIResponseThread("", f"tips_{data}", timeout=40)
        elif action_type == "recommend":
            try:
                payload = json.loads(data)
            except Exception:
                self.show_error("שגיאה בנתוני ההמלצה")
                return
            self.current_thread = AIResponseThread("", "recommend", payload, timeout=60)
        else:
            self.show_error("פעולה לא מוכרת")
            return

        self.current_thread.response_received.connect(self.display_response)
        self.current_thread.error_occurred.connect(self.show_error)
        self.current_thread.finished.connect(self._cleanup_thread)
        self.current_thread.start()

    def send_message(self):
        msg = self.message_input.text().strip()
        if not msg:
            return

        user = (session_manager.get_user_info() or {}).get("first_name", "משתמש")
        self.chat_display.add_message(user, msg, "user")
        self.message_input.clear()

        self.set_loading(True, "יועץ ה-AI עובד על התשובה…")

        self.current_thread = AIResponseThread(msg, "chat", {}, timeout=90)
        self.current_thread.response_received.connect(self.display_response)
        self.current_thread.error_occurred.connect(self.show_error)
        self.current_thread.finished.connect(self._cleanup_thread)
        self.current_thread.start()

    def display_response(self, response: str):
        self.chat_display.add_message("יועץ AI", response, "assistant")
        self.set_loading(False)

    def show_error(self, error_message: str):
        self.chat_display.add_message("מערכת", f"מצטער, נתקלתי בבעיה: {error_message}\nאנא נסה שוב.", "assistant")
        self.set_loading(False)

    def set_loading(self, loading: bool, message: str = ""):
        if loading:
            self.progress_bar.setVisible(True)
            self.send_button.setText(message or "מבצע…")
            self.send_button.setEnabled(False)
            self.message_input.setEnabled(False)
        else:
            self.progress_bar.setVisible(False)
            self.send_button.setText("שלח")
            self.send_button.setEnabled(True)
            self.message_input.setEnabled(True)

    def _cleanup_thread(self):
        self.current_thread = None

# ===== הרצה לבדיקה מקומית (אופציונלי) =====
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = AIChatWidget()
    w.resize(980, 720)
    w.show()
    sys.exit(app.exec())
