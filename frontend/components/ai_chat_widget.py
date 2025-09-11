"""
צ'אט AI – בועות בגודל תוכן, ספינר עיגול קטן מעל הצ'אט בלבד,
טאבים כשני כפתורים בכותרת, שורת הקלדה קטנה יותר, סטטוס תחתון ללא מסגרת פנימית.
"""

import requests, json
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QSpinBox, QGridLayout, QFrame, QSizePolicy,
    QScrollArea, QBoxLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QTextCursor, QTextDocument

# ===== Theme =====
PRIMARY        = "#EF4444"
PRIMARY_HOVER  = "#DC2626"
BORDER         = "#E6EAF0"
CARD_BG        = "#FFFFFF"
SURFACE        = "#F8FAFC"
TEXT_PRIMARY   = "#0F172A"
TEXT_MUTED     = "#667085"
ACCENT_BLUE    = "#1E3A8A"
OK_GREEN       = "#22C55E"
DANGER         = "#EF4444"
SUCCESS_BG     = "#E8F5E9"
SUCCESS_BORDER = "#4CAF50"

# WhatsApp-like
CHAT_BG        = "#ECE5DD"
BUBBLE_IN_BG   = "#FFFFFF"   # assistant
BUBBLE_OUT_BG  = "#F3FFE5"   # user (בהיר יותר)
BUBBLE_IN_BR   = "#E0E0E0"
BUBBLE_OUT_BR  = "#D6F4BF"

API_BASE_URL = "http://localhost:8000"


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- Spinner Overlay: עיגול קטן מעל הצ'אט בלבד ----------
class SmallRingSpinner(QWidget):
    """עיגול טעינה קטן שמופיע בתוך אזור הצ'אט בלבד (ללא כיסוי כל המסך)."""
    def __init__(self, parent=None, diameter: int = 36, thickness: int = 4):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setWindowFlags(Qt.SubWindow)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._running = False
        self.diameter = diameter
        self.thickness = thickness
        self.hide()

    def start(self):
        if not self.parent():
            return
        self._running = True
        self.setGeometry(self.parent().rect())  # מכסה רק את אזור הצ'אט
        self._timer.start(16)
        self.show()
        self.raise_()

    def stop(self):
        self._running = False
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.parent():
            self.setGeometry(self.parent().rect())

    def paintEvent(self, e):
        if not self._running:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # ללא השחרה – רק עיגול קטן במרכז אזור הצ'אט
        r = self.diameter
        cx, cy = self.width() // 2, self.height() // 2
        rect = QRect(cx - r // 2, cy - r // 2, r, r)

        pen_bg = QPen(QColor(0, 0, 0, 40))
        pen_bg.setWidth(self.thickness)
        pen_bg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_bg)
        p.drawEllipse(rect)

        pen = QPen(QColor(DANGER))
        pen.setWidth(self.thickness)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        start_angle = int(self._angle * 16)
        span = int(270 * 16)
        p.drawArc(rect, start_angle, span)


# ---------- QTextEdit גדל אוטו לשורת שליחה ----------
class GrowingTextEdit(QTextEdit):
    returnPressed = Signal()

    def __init__(self, min_h=36, max_h=120, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._min_h = min_h
        self._max_h = max_h
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self._adjust_height)
        self._adjust_height()

    def _adjust_height(self):
        doc: QTextDocument = self.document()
        doc.setTextWidth(self.viewport().width())
        h = int(doc.size().height() + 10)
        self.setFixedHeight(max(self._min_h, min(self._max_h, h)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._adjust_height()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not (e.modifiers() & Qt.ShiftModifier):
            self.returnPressed.emit()
            e.accept()
            return
        super().keyPressEvent(e)


# ---------- Thread ----------
class AIResponseThread(QThread):
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, url: str, payload: Dict, timeout: int = 120):
        super().__init__()
        self.url = url
        self.payload = payload or {}
        self.timeout = timeout

    def run(self):
        try:
            r = requests.post(self.url, json=self.payload, timeout=self.timeout)
            if r.status_code == 200:
                try:
                    data = r.json()
                except Exception:
                    data = {}
                self.response_ready.emit(str(data.get("response", data.get("message", "✓ בוצע"))))
            else:
                self.error_occurred.emit(f"שגיאת שרת: {r.status_code}")
        except requests.exceptions.Timeout:
            self.error_occurred.emit("Ollama לוקח זמן רב לעבד. נסה שוב בעוד כמה רגעים.")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"שגיאת חיבור: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"שגיאה: {str(e)}")


# ---------- ווידג'ט ראשי ----------
class AIChatWidget(QWidget):
    """צ'אט בסגנון וואטסאפ עם ספינר עיגול קטן רק על אזור הצ'אט, טאבים בכותרת, ושורת הקלדה קטנה"""

    def __init__(self):
        super().__init__()
        self.base_url = API_BASE_URL
        self.current_thread: Optional[AIResponseThread] = None

        self.setLayoutDirection(Qt.RightToLeft)
        self.setup_ui()
        self.check_ai_status()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)  # מתחיל קצת יותר למעלה

        # ===== כותרת + "טאבים" כשני כפתורים =====
        header = QFrame()
        header.setStyleSheet(f"QFrame{{background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;}}")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(10)

        title = QLabel("🤖 AI OLLAMA")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet(f"color:{ACCENT_BLUE};")

        # כפתורי טאב
        self.btn_chat = QPushButton("💬 צ'אט AI"); self.btn_chat.setCheckable(True); self.btn_chat.setChecked(True)
        self.btn_rec  = QPushButton("🚗 המלצות חמות"); self.btn_rec.setCheckable(True)

        for b in (self.btn_chat, self.btn_rec):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:{SURFACE}; color:{TEXT_PRIMARY};
                    border:1px solid {BORDER}; border-radius:10px;
                    padding:8px 12px; font-weight:700;
                }}
                QPushButton:hover {{ background:{CARD_BG}; }}
                QPushButton:checked {{ background:{CARD_BG}; border-color:{PRIMARY}; color:{PRIMARY}; }}
            """)

        hl.addWidget(title, 0, Qt.AlignRight)
        hl.addStretch(1)
        hl.addWidget(self.btn_rec, 0, Qt.AlignLeft)
        hl.addWidget(self.btn_chat, 0, Qt.AlignLeft)
        root.addWidget(header)

        # ===== סטאק של דפים (במקום QTabWidget) =====
        self.stack = QStackedWidget()
        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;}}")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(10, 10, 10, 10)
        card_l.setSpacing(8)

        # --- דף צ'אט ---
        chat_page = QWidget()
        chat_outer = QVBoxLayout(chat_page)
        chat_outer.setContentsMargins(8, 8, 8, 8)
        chat_outer.setSpacing(8)

        main_row = QHBoxLayout()
        main_row.setDirection(QBoxLayout.RightToLeft)

        # פאנל טיפים (ימין)
        tips_panel = QFrame()
        tips_panel.setFixedWidth(300)  # מעט קטן יותר
        tips_panel.setStyleSheet(f"QFrame{{background:{SURFACE}; border:1px solid {BORDER}; border-radius:12px;}}")
        tips_v = QVBoxLayout(tips_panel)
        tips_v.setContentsMargins(12, 12, 12, 12)
        tips_v.setSpacing(10)
        tips_title = QLabel("טיפים מהירים")
        tips_title.setAlignment(Qt.AlignHCenter)
        tips_title.setFont(QFont("Arial", 15, QFont.DemiBold))
        tips_v.addWidget(tips_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        tips_container = QWidget()
        tips_list = QVBoxLayout(tips_container)
        tips_list.setContentsMargins(0, 0, 0, 0)
        tips_list.setSpacing(10)

        quick_tips = [
            ("💡 טיפי קיץ", "בקיץ מומלץ לבחור רכב עם מיזוג אוויר חזק"),
            ("🚗 רכב משפחתי", "איזה רכב מתאים למשפחה עם ילדים?"),
            ("💰 חיסכון", "איך לחסוך כסף בהשכרה?"),
            ("🛡️ ביטוח", "מה ההבדל בין סוגי הביטוח?"),
            ("🏢 רכב עסקי", "רכב מתאים לנסיעות עסקיות?"),
        ]
        for label, q in quick_tips:
            b = QPushButton(label)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(52)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:#FFFFFF; color:{TEXT_PRIMARY};
                    border:1px solid {BORDER}; border-radius:12px;
                    padding:10px 12px; font-size:14px; font-weight:700; text-align:center;
                }}
                QPushButton:hover {{ background:{CARD_BG}; border-color:{PRIMARY}; color:{PRIMARY}; }}
            """)
            b.clicked.connect(lambda _, m=q: self._quick(m))
            tips_list.addWidget(b)
        tips_list.addStretch(1)
        scroll.setWidget(tips_container)
        tips_v.addWidget(scroll)

        # אזור צ'אט (שמאל)
        chat_area = QFrame()
        chat_area.setStyleSheet("QFrame{background:transparent; border:none;}")
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(6)

        # תצוגת צ'אט – גדל, מתחיל גבוה
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background:{CHAT_BG};
                border:none;
                padding:14px;
                font-size:14px; color:{TEXT_PRIMARY};
            }}
        """)
        chat_layout.addWidget(self.chat_display, 1)

        # שורת שליחה – קטנה יותר
        send_container = QFrame()
        send_container.setStyleSheet(f"QFrame{{background:#FFFFFF; border:1px solid {BORDER}; border-radius:14px;}}")
        s = QHBoxLayout(send_container)
        s.setContentsMargins(8, 6, 8, 6)
        s.setSpacing(6)

        self.message_input = GrowingTextEdit(min_h=34, max_h=110)
        self.message_input.setPlaceholderText("כתוב כאן את ההודעה… (Enter=שליחה, Shift+Enter=שורה חדשה)")
        self.message_input.setStyleSheet("QTextEdit{background:transparent; border:none; font-size:14px;}")
        self.message_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("שלח")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.setFixedWidth(96)
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:white; border:none; border-radius:14px;
                padding:8px 12px; font-weight:700;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background:#CCCCCC; color:#666666; }}
        """)
        self.send_button.clicked.connect(self.send_message)

        s.addWidget(self.message_input, 1)
        s.addWidget(self.send_button, 0, Qt.AlignLeft)
        chat_layout.addWidget(send_container)

        # ספינר קטן – רק מעל הצ'אט
        self.chat_spinner = SmallRingSpinner(self.chat_display, diameter=34, thickness=4)

        # הרכבה
        main_row.addWidget(tips_panel, 0)
        main_row.addWidget(chat_area, 1)
        chat_outer.addLayout(main_row)
        # ברכת פתיחה
        self.add_message("יועץ AI", "שלום! איך אפשר לעזור?\nשאל שאלות על רכבים, ביטוח וחיסכון.", "assistant")

        # --- דף המלצות ---
        rec_page = QWidget()
        rec_l = QVBoxLayout(rec_page)
        rec_l.setContentsMargins(8, 8, 8, 8)
        rec_l.setSpacing(8)

        card_rec = QFrame()
        card_rec.setStyleSheet(f"QFrame{{background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;}}")
        grid = QGridLayout(card_rec)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("סוג רכב:"), 0, 1, Qt.AlignRight)
        self.category_combo = QComboBox(); self.category_combo.addItems(
            ["רכב קומפקטי","רכב משפחתי","רכב עסקי","רכב יוקרה","רכב שטח"]
        ); grid.addWidget(self.category_combo, 0, 0)

        grid.addWidget(QLabel("נוסעים:"), 1, 1, Qt.AlignRight)
        self.passengers_spin = QSpinBox(); self.passengers_spin.setRange(1, 8); self.passengers_spin.setValue(2)
        grid.addWidget(self.passengers_spin, 1, 0)

        grid.addWidget(QLabel("תקציב יומי (₪):"), 2, 1, Qt.AlignRight)
        self.budget_combo = QComboBox(); self.budget_combo.addItems(
            ["עד 100 ₪","100-200 ₪","200-300 ₪","300-500 ₪","500+ ₪"]
        ); grid.addWidget(self.budget_combo, 2, 0)

        rec_l.addWidget(card_rec)

        btn = QPushButton("קבל המלצה")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton{{background:{PRIMARY};color:white;border:none;border-radius:12px;padding:10px 14px;font-weight:700;}}"
                          f"QPushButton:hover{{background:{PRIMARY_HOVER};}}")
        btn.clicked.connect(self.get_car_recommendation)
        rec_l.addWidget(btn, 0, Qt.AlignLeft)

        self.recommendation_display = QTextEdit()
        self.recommendation_display.setReadOnly(True)
        self.recommendation_display.setStyleSheet(
            f"QTextEdit{{background:#FFFFFF;border:1px solid {BORDER};border-radius:12px;padding:12px;}}"
        )
        rec_l.addWidget(self.recommendation_display, 1)

        # הוספה לסטאק
        card_l.addWidget(chat_page)  # נעטוף ב-card כדי לקבל מסגרת אחידה
        self.stack.addWidget(card)   # index 0 = chat (בתוך card)
        self.stack.addWidget(rec_page)  # index 1 = recommendations

        root.addWidget(self.stack)

        # ===== סטטוס תחתון ירוק – בלי ריבוע פנימי =====
        self.footer = QFrame()
        self.footer.setStyleSheet(f"QFrame{{background:{SUCCESS_BG}; border:1px solid {SUCCESS_BORDER}; border-radius:0;}}")
        fb = QHBoxLayout(self.footer)
        fb.setContentsMargins(12, 8, 12, 8)
        fb.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(10, 10); dot.setStyleSheet(f"background:{OK_GREEN}; border-radius:5px;")
        self.footer_label = QLabel("🟢 שרת AI פעיל")
        # ללא רקע/מסגרת פנימית
        self.footer_label.setStyleSheet("color:#1B5E20; font-weight:700; background:transparent; border:none;")
        fb.addWidget(self.footer_label, 0, Qt.AlignRight)
        fb.addWidget(dot, 0, Qt.AlignRight)
        fb.addStretch(1)
        root.addWidget(self.footer)

        # חיבור הכפתורים לסטאק
        self.btn_chat.clicked.connect(lambda: self._switch_page(0))
        self.btn_rec.clicked.connect(lambda: self._switch_page(1))

    # ===== עזרי עמודים =====
    def _switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx == 0:
            self.btn_chat.setChecked(True); self.btn_rec.setChecked(False)
        else:
            self.btn_chat.setChecked(False); self.btn_rec.setChecked(True)

    # ===== סטטוס שרת =====
    def check_ai_status(self):
        try:
            r = requests.get(f"{self.base_url}/api/ai/health", timeout=8)
            ok = r.status_code == 200 and (r.json() or {}).get("status") == "available"
            if ok:
                model = r.json().get("active_model", "לא ידוע")
                self.footer_label.setText(f"🟢 שרת AI פעיל • מודל: {model}")
            else:
                self.footer.setStyleSheet("QFrame{background:#FDECEC; border:1px solid #FCA5A5; border-radius:0;}")
                self.footer_label.setText("🔴 שרת AI לא זמין")
                self.footer_label.setStyleSheet("color:#7F1D1D; font-weight:700; background:transparent; border:none;")
        except Exception:
            self.footer.setStyleSheet("QFrame{background:#FDECEC; border:1px solid #FCA5A5; border-radius:0;}")
            self.footer_label.setText("🔴 בעיית חיבור לשרת")
            self.footer_label.setStyleSheet("color:#7F1D1D; font-weight:700; background:transparent; border:none;")

    # ===== בועות צ'אט =====
    def add_message(self, sender: str, message: str, sender_type: str = "user"):
        ts = datetime.now().strftime("%H:%M")
        safe = esc(message).replace("\n", "<br>")
        is_user = sender_type == "user"

        bg   = BUBBLE_OUT_BG if is_user else BUBBLE_IN_BG
        br   = BUBBLE_OUT_BR if is_user else BUBBLE_IN_BR
        align = "right" if is_user else "left"
        margin_style = "margin:6px 10px 6px 30%;" if is_user else "margin:6px 30% 6px 10px;"

        html = f"""
        <table align="{align}" style="{margin_style}">
          <tr>
            <td style="
                background:{bg};
                border:1px solid {br};
                border-radius:18px;
                padding:10px 12px;
                max-width: 55ch;
                word-wrap: break-word;">
                <div style="color:{TEXT_PRIMARY}; font-size:14px; line-height:1.55;">{safe}</div>
                <div style="margin-top:4px; font-size:11px; color:{TEXT_MUTED}; direction:ltr; text-align:right;">
                    {ts} {"✓✓" if is_user else ""}
                </div>
            </td>
          </tr>
        </table>
        """
        self.chat_display.moveCursor(QTextCursor.End)
        self.chat_display.insertHtml(html)
        self.chat_display.moveCursor(QTextCursor.End)

    def _quick(self, text: str):
        # שלח טיפ מהיר
        self.message_input.setPlainText(text)
        self.send_message()

    # ===== פעולות =====
    def send_message(self):
        msg = self.message_input.toPlainText().strip()
        if not msg:
            return
        self.add_message("משתמש", msg, "user")
        self.message_input.clear()

        # ספינר קטן רק מעל הצ'אט
        self.chat_spinner.start()
        self.send_button.setEnabled(False)

        payload = {"message": msg}
        self.current_thread = AIResponseThread(f"{self.base_url}/api/ai/chat", payload, 120)
        self.current_thread.response_ready.connect(self._on_ai)
        self.current_thread.error_occurred.connect(self._on_err)
        self.current_thread.finished.connect(self._cleanup)
        self.current_thread.start()

    def get_car_recommendation(self):
        self.chat_spinner.start()
        payload = {
            "category": getattr(self, "category_combo", None).currentText() if hasattr(self, "category_combo") else "",
            "passengers": getattr(self, "passengers_spin", None).value() if hasattr(self, "passengers_spin") else 1,
            "budget": getattr(self, "budget_combo", None).currentText() if hasattr(self, "budget_combo") else "",
        }
        self.current_thread = AIResponseThread(f"{self.base_url}/api/ai/recommend-car", payload, 90)
        self.current_thread.response_ready.connect(self._on_ai)
        self.current_thread.error_occurred.connect(self._on_err)
        self.current_thread.finished.connect(self._cleanup)
        self.current_thread.start()

    # ===== תוצאות =====
    def _on_ai(self, text: str):
        self.add_message("יועץ AI", text, "assistant")

    def _on_err(self, err: str):
        self.add_message("מערכת", f"בעיה בקבלת תשובת AI: {esc(err)}", "assistant")

    def _cleanup(self):
        self.chat_spinner.stop()
        self.send_button.setEnabled(True)
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit(); self.current_thread.wait()
        self.current_thread = None


# ---------- Run ----------
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("צ'אט AI – ספינר קטן מעל הצ'אט")
    w = AIChatWidget()
    w.resize(1180, 740)
    w.show()
    sys.exit(app.exec())
