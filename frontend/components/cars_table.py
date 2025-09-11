"""
מסך בעברית (PySide6) עם נתונים מה-API:
- Header עליון: 'שלום מנהל המערכת' + סטטוס שרת + כמות רכבים זמינים + כפתור ☰ לפתיחת פאנל צד
- פאנל צד (Drawer) עם 'סטטיסטיקות' ו'יועץ AI' (נפתח/נסגר בלחיצה)
- HERO עם תמונת הרקע שסיפקת ושורת חיפוש
- מתחת: רשימת כרטיסי רכבים (שמאל) + פאנל פילטרים (ימין, רוחב קבוע, כולל כפתור 'איפוס')
- כפתור 'הזמן רכב' בכל כרטיס פותח דיאלוג הזמנה
- שורת סיכום בתחתית הרשימה: סה״כ רכבים זמינים (לפי הסינון)
- נתונים נטענים מה-API (ללא דמו). אפשר סינון בצד השרת או בצד הלקוח (דגל SERVER_FILTERING).
"""

import os
import requests
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox,
    QGroupBox, QGridLayout, QFrame, QMessageBox, QDialog, QDateEdit,
    QFormLayout, QDialogButtonBox, QApplication, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QDate, Signal, QSize, QPropertyAnimation
from PySide6.QtGui import QFont, QPixmap, QPainter

# ===== הגדרות API =====
API_BASE_URL = "http://localhost:8000"
API_CARS_URL = f"{API_BASE_URL}/api/cars"
SERVER_FILTERING = True  # True = סינון בצד השרת דרך פרמטרים; False = סינון בצד הלקוח

# תמונת הרקע של ה-HERO (מהודעתך)
HERO_IMAGE_URL = ("https://lh3.googleusercontent.com/aida-public/"
                  "AB6AXuA2xhXWzHKPKdydixhYmU3tlLkQ0SVhA5in4m8ahsJGtcmkGEIoLBc0HK5F5iWyOYikqEDLTXx7rMCHqkty7gjX4N3yJrLivkyGl1DO_sWOHmGWa_bP24ZN6tTGPMMkG56WQSvmCUBiM78eqTAo7NNUl3WuW2CRDRx9ZlsE-atCPHlbqICdEV0sKc7Or_Igb1GxkhVT03a_OrZZ-usetWeWEqK_tT5_e3vGu_9Kid-pFYJHzyKzjNKcaC8WcvO1E9XBZpemeblimol7")


# ============================
# עזרי רשת
# ============================

def http_get_json(url: str, params: Optional[dict] = None, timeout: int = 8):
    try:
        r = requests.get(url, params=params or {}, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"GET {url} failed: {e}")
    return None


# ============================
# דיאלוג הזמנה
# ============================

class BookingDialog(QDialog):
    def __init__(self, car_data: Dict, parent=None):
        super().__init__(parent)
        self.car_data = car_data
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("הזמנת רכב - חשבונית")
        self.setMinimumSize(600, 680)
        self.setModal(True)

        layout = QVBoxLayout(self)

        title = QLabel("חשבונית הזמנת רכב")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1F3A8A; padding: 14px; background: #F1F5F9; border-radius: 12px;")
        layout.addWidget(title)

        # פרטי הרכב
        car_group = QGroupBox("פרטי הרכב")
        car_layout = QGridLayout(car_group)

        def add_row(r, lbl, val):
            l = QLabel(lbl); l.setAlignment(Qt.AlignRight); l.setFont(QFont("Arial", 10, QFont.Bold))
            v = QLabel(val); v.setAlignment(Qt.AlignLeft);  v.setFont(QFont("Arial", 10))
            car_layout.addWidget(l, r, 0); car_layout.addWidget(v, r, 1)

        r = 0
        add_row(r, "יצרן:", str(self.car_data.get("make", ""))); r += 1
        add_row(r, "דגם:", str(self.car_data.get("model", ""))); r += 1
        add_row(r, "מחיר יומי:", f"{self.car_data.get('daily_rate', 0)} ₪"); r += 1
        if self.car_data.get("supplier"):
            add_row(r, "ספק:", str(self.car_data.get("supplier", ""))); r += 1

        layout.addWidget(car_group)

        # פרטי לקוח
        cust_group = QGroupBox("פרטי הלקוח")
        cust_form = QFormLayout(cust_group)
        cust_form.setFormAlignment(Qt.AlignRight)
        cust_form.setLabelAlignment(Qt.AlignRight)

        self.first_name = QLineEdit()
        self.last_name  = QLineEdit()
        self.email      = QLineEdit()
        self.phone      = QLineEdit()
        cust_form.addRow("שם פרטי:", self.first_name)
        cust_form.addRow("שם משפחה:", self.last_name)
        cust_form.addRow("אימייל:", self.email)
        cust_form.addRow("טלפון:", self.phone)
        layout.addWidget(cust_group)

        # תאריכים
        dates_group = QGroupBox("תאריכי השכרה")
        dates_form  = QFormLayout(dates_group)
        dates_form.setFormAlignment(Qt.AlignRight)
        dates_form.setLabelAlignment(Qt.AlignRight)

        self.start_date = QDateEdit(); self.start_date.setCalendarPopup(True); self.start_date.setDate(QDate.currentDate())
        self.end_date   = QDateEdit(); self.end_date.setCalendarPopup(True);   self.end_date.setDate(QDate.currentDate().addDays(3))

        dates_form.addRow("תאריך תחילה:", self.start_date)
        dates_form.addRow("תאריך סיום:",   self.end_date)
        layout.addWidget(dates_group)

        # כפתורים
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("אשר הזמנה")
        buttons.button(QDialogButtonBox.Cancel).setText("ביטול")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


# ============================
# עזר לטעינת תמונות
# ============================

def load_pixmap_from_url(url: str) -> QPixmap:
    try:
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            pm = QPixmap()
            if pm.loadFromData(r.content):
                return pm
    except Exception:
        pass
    return QPixmap()

def load_car_pixmap(car: Dict, desired: QSize) -> QPixmap:
    url = car.get("image_url")
    if url:
        pm = load_pixmap_from_url(url)
        if not pm.isNull():
            return pm.scaled(desired, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    make  = str(car.get("make", "")).lower().replace(" ", "_")
    model = str(car.get("model","")).lower().replace(" ", "_")
    path = os.path.join("images", f"{make}_{model}.jpg")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(desired, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    ph = QPixmap(desired); ph.fill(Qt.lightGray); return ph


# ============================
# תפריט צד (Drawer)
# ============================

class SideDrawer(QFrame):
    navigate_stats = Signal()
    navigate_ai    = Signal()

    def __init__(self, width: int = 260):
        super().__init__()
        self._target_width = width
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self.setStyleSheet("""
            QFrame { background:#FFFFFF; border:1px solid #E6EAF0; border-radius:12px; }
        """)
        v = QVBoxLayout(self)
        v.setContentsMargins(12,12,12,12); v.setSpacing(8)

        title = QLabel("ניווט")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignRight)
        v.addWidget(title)

        def nav_btn(text):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{ text-align:right; padding:10px 12px; border:none; border-radius:8px;} QPushButton:hover{background:#F1F5F9;}")
            return b

        btn_stats = nav_btn("סטטיסטיקות")
        btn_ai    = nav_btn("יועץ AI")
        btn_stats.clicked.connect(self.navigate_stats.emit)
        btn_ai.clicked.connect(self.navigate_ai.emit)
        v.addWidget(btn_stats)
        v.addWidget(btn_ai)
        v.addStretch(1)

        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(220)

    def toggle(self):
        if self.maximumWidth() == 0: self.open()
        else: self.close()

    def open(self):
        self.anim.stop(); self.anim.setStartValue(self.maximumWidth()); self.anim.setEndValue(self._target_width); self.anim.start()

    def close(self):
        self.anim.stop(); self.anim.setStartValue(self.maximumWidth()); self.anim.setEndValue(0); self.anim.start()


# ============================
# Header עליון
# ============================

class TopBar(QFrame):
    toggle_drawer_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#TopBar { background:#FFFFFF; border-bottom:1px solid #E6EAF0; }
            QLabel.counter { color:#0F172A; font-weight:600; }
        """)
        self.setObjectName("TopBar")
        h = QHBoxLayout(self)
        h.setContentsMargins(16,8,16,8)
        h.setSpacing(10)

        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(36, 32)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setStyleSheet("QPushButton { border:1px solid #E6EAF0; border-radius:8px; background:#FFFFFF; } QPushButton:hover{background:#F8FAFC;}")
        self.menu_btn.clicked.connect(self.toggle_drawer_requested.emit)
        h.addWidget(self.menu_btn, 0, Qt.AlignLeft)

        h.addStretch(1)

        self.hello_lbl = QLabel("שלום מנהל המערכת")
        self.hello_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        h.addWidget(self.hello_lbl, 0, Qt.AlignRight)

        sep = QLabel("•"); sep.setStyleSheet("color:#94A3B8;"); h.addWidget(sep, 0, Qt.AlignRight)

        self.status_dot = QLabel(); self.status_dot.setFixedSize(10,10); self.status_dot.setStyleSheet("background:#EF4444; border-radius:5px;")
        self.status_text = QLabel("שרת: מנותק"); self.status_text.setStyleSheet("color:#334155;")
        h.addWidget(self.status_text, 0, Qt.AlignRight)
        h.addWidget(self.status_dot, 0, Qt.AlignRight)

        sep2 = QLabel("•"); sep2.setStyleSheet("color:#94A3B8;"); h.addWidget(sep2, 0, Qt.AlignRight)

        self.cars_count_lbl = QLabel("רכבים זמינים: 0")
        self.cars_count_lbl.setObjectName("counter")
        self.cars_count_lbl.setStyleSheet("color:#0F172A; font-weight:600;")
        h.addWidget(self.cars_count_lbl, 0, Qt.AlignRight)

    def update_status(self, server_connected: bool, available_count: int):
        if server_connected:
            self.status_dot.setStyleSheet("background:#22C55E; border-radius:5px;")
            self.status_text.setText("שרת: מחובר")
        else:
            self.status_dot.setStyleSheet("background:#EF4444; border-radius:5px;")
            self.status_text.setText("שרת: מנותק")
        self.cars_count_lbl.setText(f"רכבים זמינים: {available_count}")


# ============================
# HERO
# ============================

class HeroSection(QFrame):
    search_submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.bg_pixmap = QPixmap()
        self.setup_ui()
        self.load_background()

    def setup_ui(self):
        self.setMinimumHeight(300)
        self.setStyleSheet("QFrame { border-radius: 16px; }")

        self.overlay = QVBoxLayout(self)
        self.overlay.setContentsMargins(24, 24, 24, 24)
        self.overlay.addStretch(1)

        title = QLabel("מצא את הרכב המושלם שלך")
        title.setFont(QFont("Arial", 28, QFont.Black))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignHCenter)
        self.overlay.addWidget(title)

        subtitle = QLabel("חפש רכבים לפי עיר, דגם או סוג — קומפקט, משפחתי, שטח ועוד")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: white;")
        subtitle.setAlignment(Qt.AlignHCenter)
        self.overlay.addWidget(subtitle)

        bar = QHBoxLayout()
        bar.setSpacing(0); bar.setContentsMargins(0, 16, 0, 24)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("חיפוש רכבים לפי עיר, דגם או סוג…")
        self.search_edit.setMinimumHeight(44)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-right: none;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                padding: 0 14px;
                font-size: 14px;
                min-width: 380px;
            }
        """)
        btn = QPushButton("חיפוש")
        btn.setMinimumHeight(44); btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; padding: 0 18px;
                border-top-right-radius: 12px; border-bottom-right-radius: 12px; font-weight: 700;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn.clicked.connect(lambda: self.search_submitted.emit(self.search_edit.text().strip()))
        bar.addStretch(1); bar.addWidget(self.search_edit, 0); bar.addWidget(btn, 0); bar.addStretch(1)

        self.overlay.addLayout(bar)
        self.overlay.addStretch(2)

    def load_background(self):
        pm = load_pixmap_from_url(HERO_IMAGE_URL)
        if pm.isNull():
            self.setStyleSheet(self.styleSheet() + "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #64748B, stop:1 #475569); }")
        else:
            self.bg_pixmap = pm
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter = QPainter(self); painter.drawPixmap(0, 0, scaled); painter.end()


# ============================
# כרטיס רכב
# ============================

class CarCardWidget(QFrame):
    booked = Signal(dict)

    def __init__(self, car: Dict, parent=None):
        super().__init__(parent)
        self.car = car
        self.setObjectName("CarCard")
        self.setStyleSheet("""
            QFrame#CarCard { background: #FFFFFF; border: 1px solid #E6EAF0; border-radius: 12px; }
            QFrame#CarCard:hover { border-color: #D0D7E2; }
            QLabel.subtle { color:#667085; }
        """)
        self.build()

    def build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(14)

        img = QLabel(); img.setFixedSize(360, 180)
        pm = load_car_pixmap(self.car, img.size()); img.setPixmap(pm)
        img.setStyleSheet("border-radius: 10px; background:#F4F6F7;")
        img.setScaledContents(False)
        root.addWidget(img, 0)

        center = QVBoxLayout()
        title = QLabel(self.title_text()); title.setFont(QFont("Arial", 12, QFont.Bold))
        sub   = QLabel(self.subtitle_text()); sub.setObjectName("subtle")
        specs = QLabel(self.specs_text());    specs.setObjectName("subtle")
        center.addWidget(title); center.addWidget(sub); center.addWidget(specs); center.addStretch(1)
        root.addLayout(center, 1)

        right = QVBoxLayout()
        price_row = QHBoxLayout()
        price = QLabel(self.price_text()); price.setFont(QFont("Arial", 16, QFont.Bold))
        per = QLabel("/יום")
        price_row.addWidget(price); price_row.addWidget(per); price_row.addStretch(1)
        right.addLayout(price_row)

        btn = QPushButton("הזמן רכב")
        btn.setCursor(Qt.PointingHandCursor); btn.setFixedWidth(140)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; padding: 10px 14px;
                border-radius: 10px; font-weight: 700;
            }
            QPushButton:hover { background-color: #DC2626; }
            QPushButton:disabled { background-color: #CCCCCC; color:#666666; }
        """)
        btn.setEnabled(self.car.get("available", True))
        btn.clicked.connect(lambda: self.booked.emit(self.car))
        right.addStretch(1); right.addWidget(btn, 0, Qt.AlignRight)
        root.addLayout(right)

    def title_text(self) -> str:
        t = str(self.car.get("car_type", "")); return t.capitalize() if t else "רכב"
    def subtitle_text(self) -> str:
        return f"{self.car.get('make','')} {self.car.get('model','')} או דומה"
    def specs_text(self) -> str:
        return f"{self.car.get('seats', '?')} מושבים | אוטומט"
    def price_text(self) -> str:
        return f"{self.car.get('daily_rate', 0)} ₪"


# ============================
# רשימת כרטיסים + שורת סיכום
# ============================

class CarsCardsList(QWidget):
    car_booked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.data: List[Dict] = []
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(14)

        self.cards_container = QVBoxLayout()
        self.cards_container.setSpacing(14)
        self.vbox.addLayout(self.cards_container)

        self.total_label = QLabel("")
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("background:#F1F5F9; border-radius:10px; padding:8px 12px; color:#0F172A; font-weight:600;")
        self.vbox.addWidget(self.total_label)

    def set_cars(self, cars: List[Dict]):
        self.data = cars
        for i in reversed(range(self.cards_container.count())):
            item = self.cards_container.itemAt(i)
            w = item.widget()
            if w: w.setParent(None)
        for car in cars:
            card = CarCardWidget(car)
            card.booked.connect(self.car_booked.emit)
            self.cards_container.addWidget(card)

        available = sum(1 for c in cars if c.get("available", True))
        total = len(cars)
        self.total_label.setText(f"סה״כ רכבים זמינים: {available} (מתוך {total})")


# ============================
# פאנל פילטרים – רוחב קבוע + איפוס
# ============================

class FiltersPanel(QWidget):
    filters_changed = Signal()
    search_clicked = Signal(str)
    reset_clicked  = Signal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setFixedWidth(320)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

        card = QFrame(self)
        card.setStyleSheet("""
            QFrame { background:#FFFFFF; border:1px solid #E6EAF0; border-radius:12px; }
            QLabel  { font-size: 12.5px; color:#334155; margin: 2px 2px 6px 2px; }
            QLineEdit, QComboBox, QDateEdit {
                background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px;
                min-height: 40px; padding: 0 10px; font-size: 13px;
            }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.addWidget(card)

        form = QVBoxLayout(card)
        form.setContentsMargins(16,16,16,16)
        form.setSpacing(16)

        self.free_search = QLineEdit(); self.free_search.setPlaceholderText("עיר / דגם / סוג…")
        self.free_search.returnPressed.connect(lambda: self.search_clicked.emit(self.free_search.text().strip()))
        form.addWidget(QLabel("חיפוש חופשי"))
        form.addWidget(self.free_search)

        self.size_combo = QComboBox(); self.size_combo.addItems(["הכל", "Small", "Medium", "Large"])
        form.addWidget(QLabel("גודל הרכב")); form.addWidget(self.size_combo)

        self.supplier_combo = QComboBox(); self.supplier_combo.addItems(["הכל", "Hertz", "Avis", "Budget", "Enterprise"])
        form.addWidget(QLabel("ספק")); form.addWidget(self.supplier_combo)

        self.price_combo = QComboBox(); self.price_combo.addItems(["כל מחיר", "עד 200₪", "200-300₪", "300-400₪", "מעל 400₪"])
        form.addWidget(QLabel("טווח מחיר")); form.addWidget(self.price_combo)

        self.start_date = QDateEdit(); self.start_date.setCalendarPopup(True); self.start_date.setDate(QDate.currentDate())
        self.end_date   = QDateEdit(); self.end_date.setCalendarPopup(True);   self.end_date.setDate(QDate.currentDate().addDays(3))
        form.addWidget(QLabel("תאריך התחלה")); form.addWidget(self.start_date)
        form.addWidget(QLabel("תאריך סיום"));   form.addWidget(self.end_date)

        btn_row = QHBoxLayout()
        btn_search = QPushButton("חפש")
        btn_search.setCursor(Qt.PointingHandCursor)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color:#EF4444; color:white; padding:10px;
                border-radius:10px; font-weight:700; font-size:14px;
            }
            QPushButton:hover { background-color:#DC2626; }
        """)
        btn_search.clicked.connect(lambda: self.search_clicked.emit(self.free_search.text().strip()))
        btn_row.addWidget(btn_search)

        btn_reset = QPushButton("איפוס")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setStyleSheet("""
            QPushButton {
                background-color:#FFFFFF; color:#0F172A; padding:10px;
                border:1px solid #E2E8F0; border-radius:10px; font-weight:600; font-size:14px;
            }
            QPushButton:hover { background-color:#F8FAFC; }
        """)
        btn_reset.clicked.connect(self.reset_filters)
        btn_row.addWidget(btn_reset)

        form.addLayout(btn_row)

        self.size_combo.currentIndexChanged.connect(self.filters_changed.emit)
        self.supplier_combo.currentIndexChanged.connect(self.filters_changed.emit)
        self.price_combo.currentIndexChanged.connect(self.filters_changed.emit)

    def reset_filters(self):
        self.free_search.clear()
        self.size_combo.setCurrentIndex(0)
        self.supplier_combo.setCurrentIndex(0)
        self.price_combo.setCurrentIndex(0)
        self.start_date.setDate(QDate.currentDate())
        self.end_date.setDate(QDate.currentDate().addDays(3))
        self.reset_clicked.emit()
        self.search_clicked.emit("")


# ============================
# מסך ראשי
# ============================

class CarsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.all_cars_data: List[Dict] = []
        self.server_connected: bool = False
        self.setup_ui()
        self.load_all_from_api()   # טוען רשימה התחלתית מה-API
        self.apply_filters()       # מציג לפי מצב ראשוני

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_all_from_api)
        self.refresh_timer.start(30000)

    # ---------- UI ----------
    def setup_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        self.topbar = TopBar()
        self.topbar.toggle_drawer_requested.connect(self.on_toggle_drawer)
        root.addWidget(self.topbar)

        self.page_scroll = QScrollArea(); self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setStyleSheet("QScrollArea { border: none; }")
        root.addWidget(self.page_scroll)

        outer = QWidget(); self.page_scroll.setWidget(outer)
        outer_h = QHBoxLayout(outer); outer_h.setContentsMargins(16,16,16,16); outer_h.setSpacing(16)

        self.drawer = SideDrawer(width=260)
        self.drawer.navigate_stats.connect(lambda: QMessageBox.information(self, "סטטיסטיקות", "כאן יוצגו סטטיסטיקות (TODO)."))
        self.drawer.navigate_ai.connect(lambda: QMessageBox.information(self, "יועץ AI", "כאן יופיע יועץ ה-AI (TODO)."))
        outer_h.addWidget(self.drawer, 0, Qt.AlignTop)

        main_col = QWidget(); main_v = QVBoxLayout(main_col); main_v.setContentsMargins(0,0,0,0); main_v.setSpacing(16)

        self.hero = HeroSection()
        self.hero.search_submitted.connect(self.on_top_search)
        main_v.addWidget(self.hero)

        content = QHBoxLayout(); content.setSpacing(16)

        left = QVBoxLayout()
        self.cards_list = CarsCardsList()
        self.cards_list.car_booked.connect(self.on_car_booked)
        left.addWidget(self.cards_list, 0)
        left_wrap = QWidget(); left_wrap.setLayout(left)
        content.addWidget(left_wrap, 1)

        self.filters = FiltersPanel()
        self.filters.search_clicked.connect(self.on_side_search)
        self.filters.reset_clicked.connect(self.apply_filters)
        self.filters.filters_changed.connect(self.apply_filters)
        content.addWidget(self.filters, 0, Qt.AlignTop | Qt.AlignRight)

        main_v.addLayout(content)
        outer_h.addWidget(main_col, 1)

    def on_toggle_drawer(self):
        self.drawer.toggle()

    # ---------- API ----------
    def load_all_from_api(self):
        """טעינת כל הרכבים מה-API (ללא סינון) כדי שנוכל לדעת את המצב הכללי.
           אם לא קיים endpoint כזה – עדיין ננסה לעבוד בסינון שרת עם פרמטרים ב-apply_filters()."""
        data = http_get_json(API_CARS_URL)
        if isinstance(data, list):
            self.all_cars_data = data
            self.server_connected = True
        else:
            # אם אין /api/cars ללא פרמטרים – לא נכשל, רק נסמן מצב שרת בהתאם
            self.server_connected = data is not None
        # רענון הסטטוס והספירה בטופ-בר (על בסיס מה שמוצג כרגע)
        current = getattr(self, "_last_shown_cars", [])
        available = sum(1 for c in current if c.get("available", True))
        self.topbar.update_status(self.server_connected, available)

    def _build_server_params_from_filters(self) -> dict:
        """ממפה את פילטרי ה-UI לפרמטרים לבקשת GET מהשרת.
           שמנו גם אלטרנטיבות שמות (size/car_type, price_min/max) כדי להגדיל סיכוי תאימות."""
        params = {}
        q = self.filters.free_search.text().strip()
        if q:
            params["q"] = q

        # גודל
        size_map = {"Small": "small", "Medium": "medium", "Large": "large"}
        size_ui = self.filters.size_combo.currentText()
        if size_ui in size_map:
            params["size"] = size_map[size_ui]
            params["car_type"] = size_map[size_ui]  # אלטרנטיבי

        # ספק
        supplier = self.filters.supplier_combo.currentText()
        if supplier and supplier != "הכל":
            params["supplier"] = supplier

        # טווח מחיר
        price = self.filters.price_combo.currentText()
        if price == "עד 200₪":
            params["price_max"] = 200
        elif price == "200-300₪":
            params["price_min"] = 201; params["price_max"] = 300
        elif price == "300-400₪":
            params["price_min"] = 301; params["price_max"] = 400
        elif price == "מעל 400₪":
            params["price_min"] = 401

        # תאריכים (אם השרת תומך)
        sd = self.filters.start_date.date().toString("yyyy-MM-dd")
        ed = self.filters.end_date.date().toString("yyyy-MM-dd")
        params["start_date"] = sd
        params["end_date"] = ed

        return params

    # ---------- סינון והצגה ----------
    def on_top_search(self, text: str):
        self.filters.free_search.setText(text)
        self.apply_filters()

    def on_side_search(self, text: str):
        self.apply_filters()

    def apply_filters(self):
        """אם SERVER_FILTERING=True – שולחים פרמטרים לשרת ומציגים את התוצאה.
           אחרת – מסננים את self.all_cars_data בצד הלקוח."""
        cars: List[Dict] = []

        if SERVER_FILTERING:
            params = self._build_server_params_from_filters()
            data = http_get_json(API_CARS_URL, params=params)
            if isinstance(data, list):
                cars = data
                self.server_connected = True
            else:
                # אם שרת לא מחזיר רשימה — ננסה נפילה חיננית לסינון לקוח
                self.server_connected = data is not None
                cars = self._client_side_filter(self.all_cars_data)
        else:
            cars = self._client_side_filter(self.all_cars_data)

        # הצגה
        self.cards_list.set_cars(cars)
        self._last_shown_cars = cars  # לשימושי טופ-בר
        available = sum(1 for c in cars if c.get("available", True))
        self.topbar.update_status(self.server_connected, available)

    def _client_side_filter(self, cars_in: List[Dict]) -> List[Dict]:
        cars = list(cars_in)

        q = self.filters.free_search.text().strip().lower()
        if q:
            cars = [c for c in cars if any(q in str(c.get(k, "")).lower() for k in ("make","model","car_type","supplier","location"))]

        size = self.filters.size_combo.currentText()
        if size != "הכל":
            norm = {"Small":"small","Medium":"medium","Large":"large",
                    "compact":"small","family":"medium","suv":"large","luxury":"large"}
            cars = [c for c in cars if norm.get(str(c.get("car_type","")).lower(), str(c.get("car_type","")).lower()) == norm[size]]

        supplier = self.filters.supplier_combo.currentText()
        if supplier != "הכל":
            cars = [c for c in cars if c.get("supplier") == supplier]

        price = self.filters.price_combo.currentText()
        if price != "כל מחיר":
            out = []
            for c in cars:
                v = c.get("daily_rate", 0)
                if ("עד 200" in price and v <= 200) or \
                   ("200-300" in price and 200 < v <= 300) or \
                   ("300-400" in price and 300 < v <= 400) or \
                   ("מעל 400" in price and v > 400):
                    out.append(c)
            cars = out

        # (תאריכים – אופציונלי בצד הלקוח: כאן לא סיננו לפי תאריכים כי זה תלוי לוגיקה עסקית)
        return cars

    # ---------- הזמנה ----------
    def on_car_booked(self, car: Dict):
        dlg = BookingDialog(car, self)
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "הזמנה", "ההזמנה נשלחה בהצלחה!")


# ========== הרצה ==========
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("השכרת רכבים")
    w = CarsWidget()
    w.resize(1280, 840)
    w.show()
    sys.exit(app.exec())
