"""
מסך ראשי בעברית:
- Hero עליון עם תמונת רקע, כותרת, ותיבת חיפוש
- מתחתיו: רשימת כרטיסי רכבים (שמאל) + ריבוע פילטרים (ימין)
- כפתור 'הזמן רכב' בכל כרטיס פותח דיאלוג חשבונית/הזמנה
- תמונות רכבים: image_url בדאטה, או קובץ מקומי images/<make>_<model>.jpg, אחרת פלייסהולדר
"""

import os
import requests
from typing import Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox,
    QGroupBox, QGridLayout, QTextEdit, QFrame, QMessageBox, QDialog, QDateEdit,
    QFormLayout, QDialogButtonBox, QScrollArea, QSizePolicy, QApplication, QSpacerItem
)
from PySide6.QtCore import Qt, QTimer, QDate, Signal, QSize, QByteArray
from PySide6.QtGui import QFont, QPixmap

API_BASE_URL = "http://localhost:8000"
HERO_IMAGE_PATH = "assets/hero.jpg"  # שים כאן את תמונת הרקע שלך (לדוגמה: /path/to/drivego_hero.jpg)


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
        self.setMinimumSize(600, 700)
        self.setModal(True)

        layout = QVBoxLayout(self)

        title = QLabel("חשבונית הזמנת רכב")
        title.setFont(QFont("Rubik", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1F3A8A; padding: 14px; background: #F1F5F9; border-radius: 12px;")
        layout.addWidget(title)

        # פרטי הרכב
        car_group = QGroupBox("פרטי הרכב")
        car_layout = QGridLayout(car_group)

        def add_row(r, lbl, val):
            l = QLabel(lbl); l.setAlignment(Qt.AlignRight); l.setFont(QFont("Rubik", 10, QFont.Bold))
            v = QLabel(val); v.setAlignment(Qt.AlignLeft); v.setFont(QFont("Rubik", 10))
            car_layout.addWidget(l, r, 0)
            car_layout.addWidget(v, r, 1)

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
        self.last_name = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        cust_form.addRow("שם פרטי:", self.first_name)
        cust_form.addRow("שם משפחה:", self.last_name)
        cust_form.addRow("אימייל:", self.email)
        cust_form.addRow("טלפון:", self.phone)
        layout.addWidget(cust_group)

        # תאריכים
        dates_group = QGroupBox("תאריכי השכרה")
        dates_form = QFormLayout(dates_group)
        dates_form.setFormAlignment(Qt.AlignRight)
        dates_form.setLabelAlignment(Qt.AlignRight)

        self.start_date = QDateEdit(); self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.end_date = QDateEdit(); self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate().addDays(3))

        dates_form.addRow("תאריך תחילה:", self.start_date)
        dates_form.addRow("תאריך סיום:", self.end_date)
        layout.addWidget(dates_group)

        # כפתורים
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("אשר הזמנה")
        buttons.button(QDialogButtonBox.Cancel).setText("ביטול")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


# ============================
# Hero עליון עם רקע וחיפוש
# ============================

class HeroSection(QFrame):
    search_submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setMinimumHeight(340)
        # אם יש תמונה – נשים כרקע; אחרת צבע דיפולט
        if os.path.exists(HERO_IMAGE_PATH):
            self.setStyleSheet(f"""
                QFrame {{
                    border-radius: 16px;
                    background-image: url('{HERO_IMAGE_PATH}');
                    background-position: center;
                    background-repeat: no-repeat;
                    background-origin: content;
                    background-clip: border;
                }}
            """)
        else:
            self.setStyleSheet("QFrame { border-radius: 16px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #CBD5E1, stop:1 #94A3B8); }")

        overlay = QVBoxLayout(self)
        overlay.setContentsMargins(24, 24, 24, 24)
        overlay.addStretch(1)

        title = QLabel("מצא את הרכב המושלם שלך")
        title.setFont(QFont("Rubik", 28, QFont.Black))
        title.setStyleSheet("color: white; text-shadow: 0 2px 8px rgba(0,0,0,0.35);")
        title.setAlignment(Qt.AlignHCenter)
        overlay.addWidget(title)

        subtitle = QLabel("חפש רכבים לפי עיר, דגם או סוג — קומפקט, משפחתי, שטח ועוד")
        subtitle.setFont(QFont("Rubik", 12))
        subtitle.setStyleSheet("color: white;")
        subtitle.setAlignment(Qt.AlignHCenter)
        overlay.addWidget(subtitle)

        # תיבת חיפוש מרכזית
        bar = QHBoxLayout()
        bar.setSpacing(0)
        bar.setContentsMargins(0, 16, 0, 24)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("חיפוש רכבים לפי עיר, דגם או סוג...")
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
        search_btn = QPushButton("חיפוש")
        search_btn.setMinimumHeight(44)
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 0 18px;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        search_btn.clicked.connect(lambda: self.search_submitted.emit(self.search_edit.text().strip()))
        bar.addStretch(1)
        bar.addWidget(self.search_edit, 0)
        bar.addWidget(search_btn, 0)
        bar.addStretch(1)
        overlay.addLayout(bar)

        overlay.addStretch(2)


# ============================
# כרטיס רכב
# ============================

def load_pixmap_for_car(car: Dict, desired_size: QSize) -> QPixmap:
    """
    טעינת תמונה לרכב לפי סדר עדיפויות:
      1) image_url בשדה הדאטה
      2) קובץ מקומי images/<make>_<model>.jpg (למשל images/toyota_corolla.jpg)
      3) החזרה של פלייסהולדר
    """
    # 1) URL
    url = car.get("image_url")
    if url:
        try:
            r = requests.get(url, timeout=6)
            if r.status_code == 200:
                pm = QPixmap()
                if pm.loadFromData(QByteArray(r.content)):
                    return pm.scaled(desired_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            pass

    # 2) local file
    make = str(car.get("make", "")).lower().replace(" ", "_")
    model = str(car.get("model", "")).lower().replace(" ", "_")
    local_path = os.path.join("images", f"{make}_{model}.jpg")
    if os.path.exists(local_path):
        pm = QPixmap(local_path)
        if not pm.isNull():
            return pm.scaled(desired_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # 3) placeholder
    ph = QPixmap(desired_size)
    ph.fill(Qt.lightGray)
    return ph


class CarCardWidget(QFrame):
    booked = Signal(dict)

    def __init__(self, car: Dict, parent=None):
        super().__init__(parent)
        self.car = car
        self.setObjectName("CarCard")
        self.setStyleSheet("""
            QFrame#CarCard {
                background: #FFFFFF;
                border: 1px solid #E6EAF0;
                border-radius: 12px;
            }
            QFrame#CarCard:hover { border-color: #D0D7E2; }
            QLabel.card-sub { color:#667085; }
        """)
        self.build()

    def build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(14)

        # תמונה
        img_label = QLabel()
        img_label.setFixedSize(360, 180)
        pm = load_pixmap_for_car(self.car, img_label.size())
        img_label.setPixmap(pm)
        img_label.setScaledContents(False)
        img_label.setStyleSheet("border-radius: 10px; background:#F4F6F7;")
        root.addWidget(img_label, 0)

        # מרכז – טקסט
        center = QVBoxLayout()
        title = QLabel(self.title_text()); title.setFont(QFont("Rubik", 12, QFont.Bold))
        sub = QLabel(self.subtitle_text()); sub.setObjectName("card-sub")
        specs = QLabel(self.specs_text()); specs.setObjectName("card-sub")
        center.addWidget(title)
        center.addWidget(sub)
        center.addWidget(specs)
        center.addStretch(1)
        root.addLayout(center, 1)

        # ימין – מחיר + הזמנה
        right = QVBoxLayout()
        price_row = QHBoxLayout()
        price = QLabel(self.price_text()); price.setFont(QFont("Rubik", 16, QFont.Bold))
        per = QLabel("/יום")
        price_row.addWidget(price); price_row.addWidget(per); price_row.addStretch(1)
        right.addLayout(price_row)

        btn = QPushButton("הזמן רכב")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedWidth(140)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 10px 14px;
                border-radius: 10px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #DC2626; }
            QPushButton:disabled { background-color: #CCCCCC; color:#666666; }
        """)
        btn.setEnabled(self.car.get("available", True))
        btn.clicked.connect(lambda: self.booked.emit(self.car))
        right.addStretch(1)
        right.addWidget(btn, 0, Qt.AlignRight)
        root.addLayout(right)

    def title_text(self) -> str:
        t = str(self.car.get("car_type", ""))
        return t.capitalize() if t else "רכב"

    def subtitle_text(self) -> str:
        return f"{self.car.get('make','')} {self.car.get('model','')} או דומה"

    def specs_text(self) -> str:
        seats = self.car.get('seats', '?')
        trans = "אוטומט"
        return f"{seats} מושבים | {trans}"

    def price_text(self) -> str:
        p = self.car.get('daily_rate', 0)
        return f"{p} ₪"


class CarsCardsList(QWidget):
    car_booked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.data: List[Dict] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")

        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(14)
        self.vbox.addStretch(1)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def set_cars(self, cars: List[Dict]):
        self.data = cars
        # נקה (השאר stretch)
        for i in reversed(range(self.vbox.count()-1)):
            w = self.vbox.itemAt(i).widget()
            if w:
                w.setParent(None)
        # הוסף כרטיסים
        for car in cars:
            card = CarCardWidget(car)
            card.booked.connect(self.car_booked.emit)
            self.vbox.insertWidget(self.vbox.count()-1, card)


# ============================
# פאנל פילטרים (ימין)
# ============================

class FiltersPanel(QWidget):
    filters_changed = Signal()
    search_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setMinimumWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = QLabel("סינון חיפוש")
        header.setFont(QFont("Rubik", 16, QFont.Bold))
        header.setStyleSheet("color:#0F172A;")
        root.addWidget(header)

        form_card = QFrame()
        form_card.setStyleSheet("""
            QFrame { background: #FFFFFF; border: 1px solid #E6EAF0; border-radius: 12px; }
            QLabel  { font-size: 12px; color:#334155; }
            QLineEdit, QComboBox, QDateEdit {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                min-height: 34px;
                padding: 0 10px;
            }
        """)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        # שדות
        self.free_search = QLineEdit(); self.free_search.setPlaceholderText("עיר / דגם / סוג...")
        self.free_search.returnPressed.connect(lambda: self.search_clicked.emit(self.free_search.text().strip()))
        form_layout.addWidget(QLabel("חיפוש חופשי"))
        form_layout.addWidget(self.free_search)

        self.size_combo = QComboBox()
        self.size_combo.addItems(["הכל", "Small", "Medium", "Large"])
        form_layout.addWidget(QLabel("גודל הרכב"))
        form_layout.addWidget(self.size_combo)

        self.supplier_combo = QComboBox()
        self.supplier_combo.addItems(["הכל", "Hertz", "Avis", "Budget", "Enterprise"])
        form_layout.addWidget(QLabel("ספק"))
        form_layout.addWidget(self.supplier_combo)

        self.price_combo = QComboBox()
        self.price_combo.addItems(["כל מחיר", "עד 200₪", "200-300₪", "300-400₪", "מעל 400₪"])
        form_layout.addWidget(QLabel("טווח מחיר"))
        form_layout.addWidget(self.price_combo)

        btn = QPushButton("חפש")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn.clicked.connect(lambda: self.search_clicked.emit(self.free_search.text().strip()))
        form_layout.addWidget(btn)

        root.addWidget(form_card)
        root.addStretch(1)

        # חיבור שינויי פילטרים
        self.size_combo.currentIndexChanged.connect(self.filters_changed.emit)
        self.supplier_combo.currentIndexChanged.connect(self.filters_changed.emit)
        self.price_combo.currentIndexChanged.connect(self.filters_changed.emit)


# ============================
# מסך ראשי
# ============================

class CarsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.local_cars_data: List[Dict] = []
        self.external_cars_data: List[Dict] = []
        self.all_cars_data: List[Dict] = []
        self.setup_ui()
        self.load_all_cars()

        # רענון נתונים כל 30 שניות
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_all_cars)
        self.refresh_timer.start(30000)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # 1) Hero
        self.hero = HeroSection()
        self.hero.search_submitted.connect(self.on_top_search)
        root.addWidget(self.hero)

        # 2) אזור התוכן – כרטיסים + פילטרים
        content = QHBoxLayout()
        content.setSpacing(16)

        # שמאל: רשימת כרטיסים
        left = QVBoxLayout()
        header = QLabel("רכבים זמינים")
        header.setFont(QFont("Rubik", 18, QFont.Bold))
        header.setStyleSheet("color:#0F172A;")
        left.addWidget(header)

        self.cards_list = CarsCardsList()
        self.cards_list.car_booked.connect(self.on_car_booked)
        left.addWidget(self.cards_list, 1)
        left_wrap = QWidget(); left_wrap.setLayout(left)
        content.addWidget(left_wrap, 5)

        # ימין: פילטרים
        self.filters = FiltersPanel()
        self.filters.search_clicked.connect(self.on_side_search)
        self.filters.filters_changed.connect(self.apply_filters)
        content.addWidget(self.filters, 3)

        root.addLayout(content)

    # ---------- Data ----------
    def load_all_cars(self):
        self.load_local_cars()
        self.load_external_cars()
        self.merge_cars_data()
        self.apply_filters()

    def load_local_cars(self):
        try:
            resp = requests.get(f"{API_BASE_URL}/api/cars", timeout=5)
            if resp.status_code == 200:
                self.local_cars_data = resp.json()
                for car in self.local_cars_data:
                    car["source"] = "מקומי"
                    car.setdefault("car_type", "medium")
                    car.setdefault("available", True)
        except Exception as e:
            print(f"שגיאה בטעינת רכבים מקומיים: {e}")
            self.local_cars_data = []

    def load_external_cars(self):
        # כולל image_url לכל רכב (מקורות חופשיים). אפשר להחליף ל-URL משלך או לקבצים מקומיים.
        self.external_cars_data = [
            {"supplier":"Hertz","make":"Toyota","model":"Corolla","year":2023,"car_type":"compact","daily_rate":180,"seats":5,"features":["GPS","A/C","Bluetooth"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1619767886558-efdc259cde1b?q=80&w=1200&auto=format&fit=crop"},
            {"supplier":"Hertz","make":"Nissan","model":"Versa","year":2023,"car_type":"compact","daily_rate":190,"seats":5,"features":["GPS","A/C"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1549921296-3f21b18fd8e3?q=80&w=1200&auto=format&fit=crop"},
            {"supplier":"Avis","make":"Honda","model":"Civic","year":2022,"car_type":"small","daily_rate":165,"seats":5,"features":["A/C","Bluetooth","Camera"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1549923746-c502d488b3ea?q=80&w=1200&auto=format&fit=crop"},
            {"supplier":"Avis","make":"BMW","model":"X3","year":2023,"car_type":"large","daily_rate":450,"seats":5,"features":["GPS","Leather"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1619767886558-efdc259cde1b?q=80&w=1200&auto=format&fit=crop"},  # אפשר להחליף לתמונה ספציפית ל-BMW X3
            {"supplier":"Budget","make":"Ford","model":"Escape","year":2022,"car_type":"medium","daily_rate":290,"seats":7,"features":["GPS","AWD","Rack"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1616789914313-66db8f5f85bb?q=80&w=1200&auto=format&fit=crop"},
            {"supplier":"Budget","make":"Hyundai","model":"Elantra","year":2023,"car_type":"small","daily_rate":155,"seats":5,"features":["A/C","Bluetooth"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1617814076560-0d5c9b7a99cc?q=80&w=1200&auto=format&fit=crop"},
            {"supplier":"Enterprise","make":"Mercedes","model":"C-Class","year":2023,"car_type":"large","daily_rate":520,"seats":5,"features":["GPS","Leather"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1200&auto=format&fit=crop"},
            {"supplier":"Enterprise","make":"Jeep","model":"Wrangler","year":2022,"car_type":"large","daily_rate":380,"seats":5,"features":["4WD","Convertible","GPS"],"source":"חיצוני","available":True,
             "image_url":"https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1200&auto=format&fit=crop"},  # החלף לפי הצורך
        ]

    def merge_cars_data(self):
        self.all_cars_data = []
        for car in self.local_cars_data:
            if car.get("make") != "string":
                self.all_cars_data.append(car)
        self.all_cars_data.extend(self.external_cars_data)

    # ---------- Filters & Search ----------
    def on_top_search(self, text: str):
        # ממלא גם את החיפוש החופשי בצד
        self.filters.free_search.setText(text)
        self.apply_filters()

    def on_side_search(self, text: str):
        self.apply_filters()

    def apply_filters(self):
        cars = list(self.all_cars_data)

        # חיפוש חופשי
        q = self.filters.free_search.text().strip().lower()
        if q:
            cars = [c for c in cars if any(
                q in str(c.get(k, "")).lower()
                for k in ("make", "model", "car_type", "supplier", "location")
            )]

        # גודל
        size = self.filters.size_combo.currentText()
        if size != "הכל":
            norm = {"Small":"small","Medium":"medium","Large":"large","compact":"small","family":"medium","suv":"large","luxury":"large"}
            cars = [c for c in cars if norm.get(str(c.get("car_type","")).lower(), str(c.get("car_type","")).lower()) == norm[size]]

        # ספק
        supplier = self.filters.supplier_combo.currentText()
        if supplier != "הכל":
            cars = [c for c in cars if c.get("supplier") == supplier]

        # מחיר
        price = self.filters.price_combo.currentText()
        if price != "כל מחיר":
            def in_range(v):
                v = c.get("daily_rate", 0)
                if "עד 200" in price: return v <= 200
                if "200-300" in price: return 200 < v <= 300
                if "300-400" in price: return 300 < v <= 400
                if "מעל 400" in price: return v > 400
                return True
            filtered = []
            for c in cars:
                v = c.get("daily_rate", 0)
                if ("עד 200" in price and v <= 200) or \
                   ("200-300" in price and 200 < v <= 300) or \
                   ("300-400" in price and 300 < v <= 400) or \
                   ("מעל 400" in price and v > 400):
                    filtered.append(c)
            cars = filtered

        self.cards_list.set_cars(cars)

    # ---------- Booking ----------
    def on_car_booked(self, car: Dict):
        dlg = BookingDialog(car, self)
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "הזמנה", "ההזמנה נשלחה בהצלחה!")


# ========== דוגמה להרצה מקומית ==========
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("השכרת רכבים")
    w = CarsWidget()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
