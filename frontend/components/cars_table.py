"""
רכיב הצגת רכבים עם פאנל פרטים וחשבונית - גרסה סופית
עם פילטרים קומפקטיים וטבלה גדולה
"""

import requests
import json
from datetime import datetime, date
from typing import Dict, Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QLineEdit, QComboBox, QGroupBox, QGridLayout,
    QTextEdit, QFrame, QScrollArea, QMessageBox, QDialog, QDateEdit,
    QSpinBox, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QDate
from PySide6.QtGui import QFont, QPixmap

API_BASE_URL = "http://localhost:8000"

class BookingDialog(QDialog):
    """דיאלוג הזמנת רכב עם חשבונית"""
    
    def __init__(self, car_data: Dict, parent=None):
        super().__init__(parent)
        self.car_data = car_data
        self.booking_data = {}
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("הזמנת רכב - חשבונית")
        self.setGeometry(200, 200, 600, 700)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # כותרת
        title = QLabel("חשבונית הזמנת רכב")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2E86C1; padding: 15px; background: #F8F9FA; border-radius: 8px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # פרטי הרכב
        car_group = QGroupBox("פרטי הרכב")
        car_layout = QGridLayout()
        
        car_layout.addWidget(QLabel("יצרן:"), 0, 0)
        car_layout.addWidget(QLabel(str(self.car_data.get("make", ""))), 0, 1)
        
        car_layout.addWidget(QLabel("דגם:"), 1, 0)
        car_layout.addWidget(QLabel(str(self.car_data.get("model", ""))), 1, 1)
        
        car_layout.addWidget(QLabel("שנה:"), 2, 0)
        car_layout.addWidget(QLabel(str(self.car_data.get("year", ""))), 2, 1)
        
        car_layout.addWidget(QLabel("מחיר יומי:"), 3, 0)
        daily_rate = self.car_data.get("daily_rate", 0)
        car_layout.addWidget(QLabel(f"{daily_rate} ₪"), 3, 1)
        
        car_group.setLayout(car_layout)
        layout.addWidget(car_group)
        
        # פרטי ההזמנה
        booking_group = QGroupBox("פרטי ההזמנה")
        booking_layout = QFormLayout()
        
        # תאריכים
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setMinimumDate(QDate.currentDate())
        booking_layout.addRow("תאריך תחילה:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate().addDays(1))
        self.end_date.setMinimumDate(QDate.currentDate().addDays(1))
        booking_layout.addRow("תאריך סיום:", self.end_date)
        
        # מיקומים
        self.pickup_location = QLineEdit()
        self.pickup_location.setText(str(self.car_data.get("location", "")))
        booking_layout.addRow("מיקום איסוף:", self.pickup_location)
        
        self.return_location = QLineEdit()
        self.return_location.setText(str(self.car_data.get("location", "")))
        booking_layout.addRow("מיקום החזרה:", self.return_location)
        
        # ביטוח
        self.insurance_type = QComboBox()
        self.insurance_type.addItems(["בסיסי (חובה)", "מורחב (+50₪/יום)", "מקיף (+100₪/יום)"])
        booking_layout.addRow("סוג ביטוח:", self.insurance_type)
        
        # הערות
        self.special_requests = QTextEdit()
        self.special_requests.setMaximumHeight(80)
        self.special_requests.setPlaceholderText("הערות מיוחדות (אופציונלי)")
        booking_layout.addRow("הערות:", self.special_requests)
        
        booking_group.setLayout(booking_layout)
        layout.addWidget(booking_group)
        
        # פרטי לקוח
        customer_group = QGroupBox("פרטי הלקוח")
        customer_layout = QFormLayout()
        
        self.first_name = QLineEdit()
        customer_layout.addRow("שם פרטי:", self.first_name)
        
        self.last_name = QLineEdit()
        customer_layout.addRow("שם משפחה:", self.last_name)
        
        self.email = QLineEdit()
        customer_layout.addRow("אימייל:", self.email)
        
        self.phone = QLineEdit()
        customer_layout.addRow("טלפון:", self.phone)
        
        self.license_number = QLineEdit()
        customer_layout.addRow("מספר רישיון:", self.license_number)
        
        customer_group.setLayout(customer_layout)
        layout.addWidget(customer_group)
        
        # חישוב מחיר
        self.price_label = QLabel()
        self.price_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E86C1; padding: 10px; background: #E8F4FD; border-radius: 5px;")
        layout.addWidget(self.price_label)
        
        # כפתורים
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("אשר הזמנה")
        buttons.button(QDialogButtonBox.Cancel).setText("ביטול")
        buttons.accepted.connect(self.confirm_booking)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # חיבור לעדכון מחיר
        self.start_date.dateChanged.connect(self.update_price)
        self.end_date.dateChanged.connect(self.update_price)
        self.insurance_type.currentTextChanged.connect(self.update_price)
        
        # חישוב מחיר ראשוני
        self.update_price()
    
    def update_price(self):
        """עדכון חישוב המחיר"""
        try:
            start = self.start_date.date().toPython()
            end = self.end_date.date().toPython()
            days = (end - start).days
            
            if days <= 0:
                self.price_label.setText("תאריכים לא תקינים")
                return
            
            daily_rate = float(self.car_data.get("daily_rate", 0))
            base_price = daily_rate * days
            
            # ביטוח
            insurance_cost = 0
            insurance_text = self.insurance_type.currentText()
            if "מורחב" in insurance_text:
                insurance_cost = 50 * days
            elif "מקיף" in insurance_text:
                insurance_cost = 100 * days
            
            total_price = base_price + insurance_cost
            
            price_text = f"""
            <b>פירוט החשבונית:</b><br>
            השכרה: {days} ימים × {daily_rate}₪ = {base_price}₪<br>
            ביטוח: {insurance_cost}₪<br>
            <b>סה"כ לתשלום: {total_price}₪</b>
            """
            
            self.price_label.setText(price_text)
            
        except Exception as e:
            self.price_label.setText(f"שגיאה בחישוב: {e}")
    
    def confirm_booking(self):
        """אישור ההזמנה"""
        # בדיקת שדות חובה
        if not all([self.first_name.text(), self.last_name.text(), 
                   self.email.text(), self.phone.text(), self.license_number.text()]):
            QMessageBox.warning(self, "שדות חסרים", "אנא מלא את כל השדות החובה")
            return
        
        # הכנת נתוני ההזמנה
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        days = (end - start).days
        daily_rate = float(self.car_data.get("daily_rate", 0))
        
        # חישוב ביטוח
        insurance_cost = 0
        insurance_text = self.insurance_type.currentText()
        if "מורחב" in insurance_text:
            insurance_cost = 50 * days
        elif "מקיף" in insurance_text:
            insurance_cost = 100 * days
        
        total_price = (daily_rate * days) + insurance_cost
        
        self.booking_data = {
            "car_id": self.car_data.get("id"),
            "customer": {
                "first_name": self.first_name.text(),
                "last_name": self.last_name.text(),
                "email": self.email.text(),
                "phone": self.phone.text(),
                "license_number": self.license_number.text()
            },
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "pickup_location": self.pickup_location.text(),
            "return_location": self.return_location.text(),
            "insurance_type": insurance_text.split()[0].lower(),
            "days": days,
            "total_price": total_price,
            "special_requests": self.special_requests.toPlainText()
        }
        
        # שליחת ההזמנה לשרת
        try:
            response = requests.post(f"{API_BASE_URL}/api/bookings", json=self.booking_data)
            if response.status_code == 200:
                QMessageBox.information(self, "הזמנה אושרה", 
                                      f"ההזמנה אושרה בהצלחה!\nמספר הזמנה: {response.json().get('booking_id', 'לא ידוע')}")
                self.accept()
            else:
                QMessageBox.warning(self, "שגיאה", f"שגיאה ביצירת הזמנה: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "שגיאת תקשורת", f"לא ניתן ליצור הזמנה: {str(e)}")

class CarDetailsWidget(QWidget):
    """פאנל פרטי רכב"""
    
    book_car = Signal(dict)  # Signal להזמנת רכב
    
    def __init__(self):
        super().__init__()
        self.current_car = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setMaximumWidth(350)  # רוחב מותאם
        layout = QVBoxLayout()
        
        # כותרת
        title = QLabel("פרטי הרכב")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2E86C1; padding: 8px; background: #F8F9FA; border-radius: 5px;")
        layout.addWidget(title)
        
        # פאנל פרטים
        self.details_frame = QFrame()
        self.details_frame.setStyleSheet("background: white; border: 1px solid #BDC3C7; border-radius: 5px; padding: 12px;")
        details_layout = QVBoxLayout()
        
        # תמונת רכב
        self.car_image = QLabel()
        self.car_image.setFixedHeight(100)
        self.car_image.setAlignment(Qt.AlignCenter)
        self.car_image.setStyleSheet("background: #ECF0F1; border: 1px solid #BDC3C7; border-radius: 5px; color: #7F8C8D; font-size: 11px;")
        self.car_image.setText("תמונת רכב")
        details_layout.addWidget(self.car_image)
        
        # פרטים טכניים
        self.info_layout = QGridLayout()
        details_layout.addLayout(self.info_layout)
        
        # תכונות
        features_label = QLabel("תכונות:")
        features_label.setFont(QFont("Arial", 10, QFont.Bold))
        details_layout.addWidget(features_label)
        
        self.features_text = QTextEdit()
        self.features_text.setMaximumHeight(70)
        self.features_text.setReadOnly(True)
        details_layout.addWidget(self.features_text)
        
        # כפתור הזמנה
        self.book_button = QPushButton("הזמן רכב זה")
        self.book_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.book_button.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1E8449;
            }
        """)
        self.book_button.clicked.connect(self.on_book_clicked)
        self.book_button.setEnabled(False)
        details_layout.addWidget(self.book_button)
        
        self.details_frame.setLayout(details_layout)
        layout.addWidget(self.details_frame)
        
        # הודעה ראשונית
        self.empty_label = QLabel("בחר רכב מהטבלה לצפייה בפרטים")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #7F8C8D; font-style: italic; padding: 30px; font-size: 11px;")
        layout.addWidget(self.empty_label)
        
        self.setLayout(layout)
        self.hide_details()
    
    def show_car_details(self, car_data: Dict):
        """הצגת פרטי רכב"""
        self.current_car = car_data
        
        # עדכון תמונת רכב
        car_name = f"{car_data.get('make', '')} {car_data.get('model', '')}"
        self.car_image.setText(f"תמונת רכב\n{car_name}")
        
        # מחיקת פרטים ישנים
        for i in reversed(range(self.info_layout.count())):
            self.info_layout.itemAt(i).widget().setParent(None)
        
        # הוספת פרטים חדשים
        details = [
            ("יצרן:", str(car_data.get("make", "לא ידוע"))),
            ("דגם:", str(car_data.get("model", "לא ידוע"))),
            ("שנה:", str(car_data.get("year", "לא ידוע"))),
            ("סוג:", str(car_data.get("car_type", "לא ידוע"))),
            ("תיבת הילוכים:", str(car_data.get("transmission", "לא ידוע"))),
            ("דלק:", str(car_data.get("fuel_type", "לא ידוע"))),
            ("מקומות:", str(car_data.get("seats", "לא ידוע"))),
            ("מיקום:", str(car_data.get("location", "לא ידוע"))),
            ("מחיר יומי:", f"{car_data.get('daily_rate', 0)} ₪"),
            ("זמינות:", "זמין" if car_data.get("available", True) else "תפוס")
        ]
        
        for i, (label, value) in enumerate(details):
            label_widget = QLabel(label)
            label_widget.setFont(QFont("Arial", 8, QFont.Bold))
            value_widget = QLabel(value)
            value_widget.setFont(QFont("Arial", 8))
            
            self.info_layout.addWidget(label_widget, i, 0)
            self.info_layout.addWidget(value_widget, i, 1)
        
        # תכונות
        features = car_data.get("features", [])
        if isinstance(features, list):
            features_text = "\n".join([f"• {feature}" for feature in features])
        else:
            features_text = str(features) if features else "אין מידע על תכונות"
        
        self.features_text.setText(features_text)
        
        # עדכון כפתור הזמנה
        is_available = car_data.get("available", True)
        self.book_button.setEnabled(is_available)
        self.book_button.setText("הזמן רכב זה" if is_available else "רכב לא זמין")
        
        # הצגת הפאנל
        self.show_details()
    
    def show_details(self):
        """הצגת פאנל הפרטים"""
        self.empty_label.hide()
        self.details_frame.show()
    
    def hide_details(self):
        """הסתרת פאנל הפרטים"""
        self.details_frame.hide()
        self.empty_label.show()
    
    def on_book_clicked(self):
        """טיפול בלחיצה על כפתור הזמנה"""
        if self.current_car:
            booking_dialog = BookingDialog(self.current_car, self)
            if booking_dialog.exec() == QDialog.Accepted:
                QMessageBox.information(self, "הזמנה", "ההזמנה נשלחה בהצלחה!")

class CarsWidget(QWidget):
    """רכיב ראשי להצגת רכבים עם פאנל פרטים"""
    
    def __init__(self):
        super().__init__()
        self.cars_data = []
        self.setup_ui()
        self.load_cars()
        
        # Timer לרענון נתונים
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_cars)
        self.refresh_timer.start(30000)  # רענון כל 30 שניות
    
    def setup_ui(self):
        layout = QHBoxLayout()
        
        # צד שמאל - טבלת רכבים
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # פילטרים קומפקטיים בשורה אחת
        filters_layout = QHBoxLayout()
        
        # חיפוש
        search_label = QLabel("חיפוש:")
        search_label.setMaximumWidth(50)
        filters_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("יצרן, דגם, מיקום...")
        self.search_input.setMaximumWidth(150)
        self.search_input.textChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.search_input)
        
        filters_layout.addSpacing(10)
        
        # סוג רכב
        type_label = QLabel("סוג:")
        type_label.setMaximumWidth(30)
        filters_layout.addWidget(type_label)
        
        self.car_type_filter = QComboBox()
        self.car_type_filter.addItems(["הכל", "economy", "family", "luxury", "compact"])
        self.car_type_filter.setMaximumWidth(90)
        self.car_type_filter.currentTextChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.car_type_filter)
        
        filters_layout.addSpacing(10)
        
        # מיקום
        location_label = QLabel("מיקום:")
        location_label.setMaximumWidth(40)
        filters_layout.addWidget(location_label)
        
        self.location_filter = QComboBox()
        self.location_filter.addItem("הכל")
        self.location_filter.setMaximumWidth(90)
        self.location_filter.currentTextChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.location_filter)
        
        filters_layout.addSpacing(10)
        
        # כפתור רענון
        refresh_btn = QPushButton("רענן")
        refresh_btn.setMaximumWidth(50)
        refresh_btn.setMaximumHeight(25)
        refresh_btn.clicked.connect(self.load_cars)
        filters_layout.addWidget(refresh_btn)
        
        # ממלא מקום
        filters_layout.addStretch()
        
        left_layout.addLayout(filters_layout)
        
        # טבלת רכבים
        self.cars_table = QTableWidget()
        self.cars_table.setColumnCount(7)
        self.cars_table.setHorizontalHeaderLabels([
            "יצרן", "דגם", "שנה", "סוג", "מחיר יומי", "מיקום", "זמינות"
        ])
        self.cars_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cars_table.setAlternatingRowColors(True)
        self.cars_table.itemSelectionChanged.connect(self.on_car_selected)
        left_layout.addWidget(self.cars_table)
        
        # סטטיסטיקות
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("background: #E8F4FD; padding: 6px; border-radius: 5px; color: #2E86C1; font-size: 10px;")
        left_layout.addWidget(self.stats_label)
        
        left_panel.setLayout(left_layout)
        layout.addWidget(left_panel, 4)  # 4/5 מהמקום לטבלה
        
        # צד ימין - פרטי רכב
        self.car_details = CarDetailsWidget()
        layout.addWidget(self.car_details, 1)  # 1/5 מהמקום לפרטים
        
        self.setLayout(layout)
    
    def load_cars(self):
        """טעינת רכבים מהשרת"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/cars")
            if response.status_code == 200:
                self.cars_data = response.json()
                self.update_location_filter()
                self.populate_table()
                self.update_stats()
            else:
                QMessageBox.warning(self, "שגיאה", "לא ניתן לטעון רכבים מהשרת")
        except Exception as e:
            QMessageBox.critical(self, "שגיאת תקשורת", f"שגיאה בטעינת נתונים: {str(e)}")
    
    def update_location_filter(self):
        """עדכון רשימת המיקומים בפילטר"""
        current_location = self.location_filter.currentText()
        self.location_filter.clear()
        self.location_filter.addItem("הכל")
        
        locations = set()
        for car in self.cars_data:
            location = car.get("location", "")
            if location and location != "string":
                locations.add(location)
        
        for location in sorted(locations):
            self.location_filter.addItem(location)
        
        # שמירת הבחירה הקודמת
        index = self.location_filter.findText(current_location)
        if index >= 0:
            self.location_filter.setCurrentIndex(index)
    
    def populate_table(self):
        """מילוי הטבלה ברכבים"""
        filtered_cars = self.get_filtered_cars()
        
        self.cars_table.setRowCount(len(filtered_cars))
        
        for row, car in enumerate(filtered_cars):
            # סינון רכבים עם נתונים לא תקינים
            if car.get("make") == "string" or car.get("model") == "string":
                continue
                
            items = [
                str(car.get("make", "לא ידוע")),
                str(car.get("model", "לא ידוע")),
                str(car.get("year", "לא ידוע")),
                str(car.get("car_type", "לא ידוע")),
                f"{car.get('daily_rate', 0)} ₪",
                str(car.get("location", "לא ידוע")),
                "זמין" if car.get("available", True) else "תפוס"
            ]
            
            for col, item_text in enumerate(items):
                item = QTableWidgetItem(item_text)
                
                # צביעת שורות לא זמינות
                if not car.get("available", True):
                    item.setBackground(Qt.lightGray)
                
                # הוספת ID הרכב לשורה הראשונה
                if col == 0:
                    item.setData(Qt.UserRole, car)
                
                self.cars_table.setItem(row, col, item)
        
        # התאמת גודל עמודות
        self.cars_table.resizeColumnsToContents()
    
    def get_filtered_cars(self):
        """קבלת רכבים מסוננים לפי הפילטרים"""
        filtered = [car for car in self.cars_data if car.get("make") != "string"]
        
        # פילטר חיפוש טקסט
        search_text = self.search_input.text().lower()
        if search_text:
            filtered = [
                car for car in filtered
                if search_text in str(car.get("make", "")).lower() or
                   search_text in str(car.get("model", "")).lower() or
                   search_text in str(car.get("location", "")).lower()
            ]
        
        # פילטר סוג רכב
        car_type = self.car_type_filter.currentText()
        if car_type != "הכל":
            filtered = [car for car in filtered if car.get("car_type") == car_type]
        
        # פילטר מיקום
        location = self.location_filter.currentText()
        if location != "הכל":
            filtered = [car for car in filtered if car.get("location") == location]
        
        return filtered
    
    def filter_cars(self):
        """הפעלת סינון ועדכון הטבלה"""
        self.populate_table()
        self.update_stats()
    
    def update_stats(self):
        """עדכון סטטיסטיקות"""
        filtered_cars = self.get_filtered_cars()
        total = len(filtered_cars)
        available = len([car for car in filtered_cars if car.get("available", True)])
        
        if total > 0:
            avg_price = sum(car.get("daily_rate", 0) for car in filtered_cars) / total
            stats_text = f"סה\"כ רכבים: {total} | זמינים: {available} | מחיר ממוצע: {avg_price:.0f}₪"
        else:
            stats_text = "לא נמצאו רכבים התואמים לחיפוש"
        
        self.stats_label.setText(stats_text)
    
    def on_car_selected(self):
        """טיפול בבחירת רכב מהטבלה"""
        current_row = self.cars_table.currentRow()
        if current_row >= 0:
            first_item = self.cars_table.item(current_row, 0)
            if first_item:
                car_data = first_item.data(Qt.UserRole)
                if car_data:
                    self.car_details.show_car_details(car_data)