"""
רכיב הצגת רכבים עם טבלה משולבת אחת
"""

import requests
import json
from datetime import datetime, date
from typing import Dict, Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QLineEdit, QComboBox, QGroupBox, QGridLayout,
    QTextEdit, QFrame, QMessageBox, QDialog, QDateEdit, QSpinBox, 
    QFormLayout, QDialogButtonBox, QTabWidget, QProgressBar, QSplitter
)
from PySide6.QtCore import Qt, QTimer, Signal, QDate, QThread
from PySide6.QtGui import QFont, QColor

API_BASE_URL = "http://localhost:8000"

# ===========================================
# דיאלוג הזמנה
# ===========================================

class BookingDialog(QDialog):
    def __init__(self, car_data: Dict, parent=None):
        super().__init__(parent)
        self.car_data = car_data
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("הזמנת רכב - חשבונית")
        self.setGeometry(200, 200, 600, 700)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        title = QLabel("חשבונית הזמנת רכב")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2E86C1; padding: 15px; background: #F8F9FA; border-radius: 8px;")
        layout.addWidget(title)
        
        # פרטי הרכב
        car_group = QGroupBox("פרטי הרכב")
        car_layout = QGridLayout()
        
        car_layout.addWidget(QLabel("יצרן:"), 0, 0)
        car_layout.addWidget(QLabel(str(self.car_data.get("make", ""))), 0, 1)
        car_layout.addWidget(QLabel("דגם:"), 1, 0)
        car_layout.addWidget(QLabel(str(self.car_data.get("model", ""))), 1, 1)
        car_layout.addWidget(QLabel("מחיר יומי:"), 2, 0)
        car_layout.addWidget(QLabel(f"{self.car_data.get('daily_rate', 0)} ₪"), 2, 1)
        
        # הוספת ספק אם קיים
        if self.car_data.get('supplier'):
            car_layout.addWidget(QLabel("ספק:"), 3, 0)
            car_layout.addWidget(QLabel(str(self.car_data.get("supplier", ""))), 3, 1)
        
        car_group.setLayout(car_layout)
        layout.addWidget(car_group)
        
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
        
        customer_group.setLayout(customer_layout)
        layout.addWidget(customer_group)
        
        # תאריכים
        dates_group = QGroupBox("תאריכי השכרה")
        dates_layout = QFormLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        dates_layout.addRow("תאריך תחילה:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate().addDays(3))
        dates_layout.addRow("תאריך סיום:", self.end_date)
        
        dates_group.setLayout(dates_layout)
        layout.addWidget(dates_group)
        
        # כפתורים
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("אשר הזמנה")
        buttons.button(QDialogButtonBox.Cancel).setText("ביטול")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)

# ===========================================
# פאנל פרטי רכב
# ===========================================

class CarDetailsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_car = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setMaximumWidth(320)
        layout = QVBoxLayout()
        
        title = QLabel("פרטי הרכב")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2E86C1; padding: 8px; background: #F8F9FA; border-radius: 5px;")
        layout.addWidget(title)
        
        self.details_frame = QFrame()
        self.details_frame.setStyleSheet("background: white; border: 1px solid #BDC3C7; border-radius: 5px; padding: 12px;")
        details_layout = QVBoxLayout()
        
        # תמונת רכב
        self.car_image = QLabel()
        self.car_image.setFixedHeight(80)
        self.car_image.setAlignment(Qt.AlignCenter)
        self.car_image.setStyleSheet("background: #ECF0F1; border: 1px solid #BDC3C7; border-radius: 5px; color: #7F8C8D; font-size: 10px;")
        self.car_image.setText("תמונת רכב")
        details_layout.addWidget(self.car_image)
        
        # פרטים טכניים
        self.info_layout = QGridLayout()
        details_layout.addLayout(self.info_layout)
        
        # תכונות
        features_label = QLabel("תכונות:")
        features_label.setFont(QFont("Arial", 9, QFont.Bold))
        details_layout.addWidget(features_label)
        
        self.features_text = QTextEdit()
        self.features_text.setMaximumHeight(60)
        self.features_text.setReadOnly(True)
        self.features_text.setStyleSheet("font-size: 9px;")
        details_layout.addWidget(self.features_text)
        
        # כפתור הזמנה
        self.book_button = QPushButton("הזמן רכב זה")
        self.book_button.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        self.book_button.clicked.connect(self.on_book_clicked)
        self.book_button.setEnabled(False)
        details_layout.addWidget(self.book_button)
        
        self.details_frame.setLayout(details_layout)
        layout.addWidget(self.details_frame)
        
        # הודעה ראשונית
        self.empty_label = QLabel("בחר רכב מהטבלה לצפייה בפרטים")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #7F8C8D; font-style: italic; padding: 30px; font-size: 10px;")
        layout.addWidget(self.empty_label)
        
        self.setLayout(layout)
        self.hide_details()
    
    def show_car_details(self, car_data: Dict):
        self.current_car = car_data
        
        # עדכון תמונת רכב
        car_name = f"{car_data.get('make', '')} {car_data.get('model', '')}"
        source = car_data.get('source', 'מקומי')
        self.car_image.setText(f"תמונת רכב\n{car_name}\n({source})")
        
        # מחיקת פרטים ישנים
        for i in reversed(range(self.info_layout.count())):
            self.info_layout.itemAt(i).widget().setParent(None)
        
        # הוספת פרטים חדשים
        details = []
        
        # הוספת ספק אם זה רכב חיצוני
        if car_data.get('supplier'):
            details.append(("ספק:", str(car_data.get("supplier", ""))))
        
        details.extend([
            ("יצרן:", str(car_data.get("make", "לא ידוע"))),
            ("דגם:", str(car_data.get("model", "לא ידוע"))),
            ("שנה:", str(car_data.get("year", "לא ידוע"))),
            ("סוג:", str(car_data.get("car_type", "לא ידוע"))),
            ("מחיר יומי:", f"{car_data.get('daily_rate', 0)} ₪"),
            ("נוסעים:", str(car_data.get("seats", "לא ידוע"))),
        ])
        
        # הוספת מיקום (רק לרכבים מקומיים)
        if car_data.get('location') and not car_data.get('supplier'):
            details.append(("מיקום:", str(car_data.get("location", "לא ידוע"))))
        
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
            features_text = "\n".join([f"• {feature}" for feature in features[:4]])
        else:
            features_text = str(features) if features else "אין מידע על תכונות"
        
        self.features_text.setText(features_text)
        
        # עדכון כפתור הזמנה
        is_available = car_data.get("available", True)
        self.book_button.setEnabled(is_available)
        self.book_button.setText("הזמן רכב זה" if is_available else "רכב לא זמין")
        
        self.show_details()
    
    def show_details(self):
        self.empty_label.hide()
        self.details_frame.show()
    
    def hide_details(self):
        self.details_frame.hide()
        self.empty_label.show()
    
    def on_book_clicked(self):
        if self.current_car:
            booking_dialog = BookingDialog(self.current_car, self)
            if booking_dialog.exec() == QDialog.Accepted:
                QMessageBox.information(self, "הזמנה", "ההזמנה נשלחה בהצלחה!")

# ===========================================
# רכיב ראשי עם טבלה משולבת
# ===========================================

class CarsWidget(QWidget):
    """רכיב ראשי עם טבלה משולבת לרכבים מקומיים וחיצוניים"""
    
    def __init__(self):
        super().__init__()
        self.local_cars_data = []
        self.external_cars_data = []
        self.all_cars_data = []
        self.setup_ui()
        self.load_all_cars()
        
        # Timer לרענון נתונים
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_all_cars)
        self.refresh_timer.start(30000)
    
    def setup_ui(self):
        main_layout = QHBoxLayout()
        
        # צד שמאל - טבלה משולבת
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # כותרת כללית
        main_title = QLabel("מערכת השכרת רכבים - טבלה משולבת")
        main_title.setFont(QFont("Arial", 16, QFont.Bold))
        main_title.setAlignment(Qt.AlignCenter)
        main_title.setStyleSheet("color: #2E86C1; padding: 10px; background: #F8F9FA; border-radius: 8px; margin-bottom: 5px;")
        left_layout.addWidget(main_title)
        
        # פילטרים משולבים
        filters_layout = QHBoxLayout()
        
        filters_layout.addWidget(QLabel("חיפוש:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("יצרן, דגם, ספק...")
        self.search_input.setMaximumWidth(120)
        self.search_input.textChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.search_input)
        
        filters_layout.addWidget(QLabel("מקור:"))
        self.source_filter = QComboBox()
        self.source_filter.addItems(["הכל", "מקומי", "חיצוני"])
        self.source_filter.setMaximumWidth(80)
        self.source_filter.currentTextChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.source_filter)
        
        filters_layout.addWidget(QLabel("סוג:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["הכל", "economy", "compact", "family", "luxury", "suv"])
        self.type_filter.setMaximumWidth(80)
        self.type_filter.currentTextChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.type_filter)
        
        filters_layout.addWidget(QLabel("ספק:"))
        self.supplier_filter = QComboBox()
        self.supplier_filter.addItems(["הכל", "Hertz", "Avis", "Budget", "Enterprise", "Sixt"])
        self.supplier_filter.setMaximumWidth(80)
        self.supplier_filter.currentTextChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.supplier_filter)
        
        filters_layout.addWidget(QLabel("מחיר:"))
        self.price_filter = QComboBox()
        self.price_filter.addItems(["הכל", "עד 200₪", "200-300₪", "300-400₪", "מעל 400₪"])
        self.price_filter.setMaximumWidth(90)
        self.price_filter.currentTextChanged.connect(self.filter_cars)
        filters_layout.addWidget(self.price_filter)
        
        refresh_btn = QPushButton("רענן")
        refresh_btn.setMaximumWidth(50)
        refresh_btn.setStyleSheet("background-color: #28A745; color: white; padding: 6px; border-radius: 4px; font-weight: bold;")
        refresh_btn.clicked.connect(self.load_all_cars)
        filters_layout.addWidget(refresh_btn)
        
        filters_layout.addStretch()
        left_layout.addLayout(filters_layout)
        
        # טבלה משולבת
        self.cars_table = QTableWidget()
        self.cars_table.setColumnCount(8)
        self.cars_table.setHorizontalHeaderLabels([
            "מקור", "ספק/מיקום", "יצרן", "דגם", "שנה", "סוג", "מחיר יומי", "נוסעים"
        ])
        self.cars_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cars_table.setAlternatingRowColors(True)
        self.cars_table.itemSelectionChanged.connect(self.on_car_selected)
        left_layout.addWidget(self.cars_table)
        
        # סטטיסטיקות משולבות
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("background: #E8F4FD; padding: 6px; border-radius: 5px; color: #2E86C1; font-size: 10px;")
        left_layout.addWidget(self.stats_label)
        
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, 5)  # 5/6 מהמסך לטבלה
        
        # צד ימין - פרטי רכב
        self.car_details = CarDetailsWidget()
        main_layout.addWidget(self.car_details, 1)  # 1/6 מהמסך לפרטים
        
        self.setLayout(main_layout)
    
    def load_all_cars(self):
        """טעינת כל הרכבים - מקומיים וחיצוניים"""
        self.load_local_cars()
        self.load_external_cars()
        self.merge_cars_data()
        self.populate_table()
        self.update_stats()
    
    def load_local_cars(self):
        """טעינת רכבים מקומיים"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/cars", timeout=5)
            if response.status_code == 200:
                self.local_cars_data = response.json()
                # הוספת מקור לכל רכב מקומי
                for car in self.local_cars_data:
                    car["source"] = "מקומי"
                    car["supplier"] = None  # אין ספק לרכבים מקומיים
        except Exception as e:
            print(f"שגיאה בטעינת רכבים מקומיים: {e}")
            self.local_cars_data = []
    
    def load_external_cars(self):
        """טעינת רכבים חיצוניים (דמו)"""
        self.external_cars_data = [
            {"supplier": "Hertz", "make": "Toyota", "model": "Corolla", "year": 2023, "car_type": "economy", "daily_rate": 180, "seats": 5, "features": ["GPS", "A/C", "Bluetooth"], "source": "חיצוני", "available": True},
            {"supplier": "Hertz", "make": "Nissan", "model": "Altima", "year": 2023, "car_type": "family", "daily_rate": 220, "seats": 5, "features": ["GPS", "A/C", "Premium Audio"], "source": "חיצוני", "available": True},
            {"supplier": "Avis", "make": "Honda", "model": "Civic", "year": 2022, "car_type": "compact", "daily_rate": 165, "seats": 5, "features": ["A/C", "Bluetooth", "Backup Camera"], "source": "חיצוני", "available": True},
            {"supplier": "Avis", "make": "BMW", "model": "X3", "year": 2023, "car_type": "luxury", "daily_rate": 450, "seats": 5, "features": ["GPS", "Leather", "Premium Sound"], "source": "חיצוני", "available": True},
            {"supplier": "Budget", "make": "Ford", "model": "Escape", "year": 2022, "car_type": "suv", "daily_rate": 290, "seats": 7, "features": ["GPS", "AWD", "Roof Rack"], "source": "חיצוני", "available": True},
            {"supplier": "Budget", "make": "Hyundai", "model": "Elantra", "year": 2023, "car_type": "economy", "daily_rate": 155, "seats": 5, "features": ["A/C", "Bluetooth"], "source": "חיצוני", "available": True},
            {"supplier": "Enterprise", "make": "Mercedes", "model": "C-Class", "year": 2023, "car_type": "luxury", "daily_rate": 520, "seats": 5, "features": ["GPS", "Leather", "Premium Sound"], "source": "חיצוני", "available": True},
            {"supplier": "Enterprise", "make": "Jeep", "model": "Wrangler", "year": 2022, "car_type": "suv", "daily_rate": 380, "seats": 5, "features": ["4WD", "Convertible", "GPS"], "source": "חיצוני", "available": True},
        ]
    
    def merge_cars_data(self):
        """מיזוג נתוני רכבים מקומיים וחיצוניים"""
        self.all_cars_data = []
        
        # הוספת רכבים מקומיים (מסנן רכבים פגומים)
        for car in self.local_cars_data:
            if car.get("make") != "string":
                self.all_cars_data.append(car)
        
        # הוספת רכבים חיצוניים
        self.all_cars_data.extend(self.external_cars_data)
    
    def populate_table(self):
        """מילוי הטבלה המשולבת"""
        filtered_cars = self.get_filtered_cars()
        self.cars_table.setRowCount(len(filtered_cars))
        
        for row, car in enumerate(filtered_cars):
            # קביעת ספק/מיקום
            supplier_location = car.get("supplier", "") if car.get("supplier") else car.get("location", "לא ידוע")
            
            items = [
                car.get("source", "לא ידוע"),
                supplier_location,
                str(car.get("make", "לא ידוע")),
                str(car.get("model", "לא ידוע")),
                str(car.get("year", "לא ידוע")),
                str(car.get("car_type", "לא ידוע")),
                f"{car.get('daily_rate', 0)} ₪",
                str(car.get("seats", "לא ידוע"))
            ]
            
            for col, item_text in enumerate(items):
                item = QTableWidgetItem(str(item_text))
                
                # צביעה לפי מקור
                if car.get("source") == "מקומי":
                    item.setBackground(QColor(240, 248, 255))  # כחול בהיר
                else:
                    # צביעה לפי ספק לרכבים חיצוניים
                    if car.get("supplier") == "Hertz":
                        item.setBackground(QColor(255, 255, 224))  # צהוב בהיר
                    elif car.get("supplier") == "Avis":
                        item.setBackground(QColor(230, 240, 255))  # כחול בהיר
                    elif car.get("supplier") == "Budget":
                        item.setBackground(QColor(240, 255, 240))  # ירוק בהיר
                    elif car.get("supplier") == "Enterprise":
                        item.setBackground(QColor(255, 240, 245))  # ורוד בהיר
                    else:
                        item.setBackground(QColor(248, 248, 248))  # אפור בהיר
                
                # סימון רכבים לא זמינים
                if not car.get("available", True):
                    item.setBackground(QColor(211, 211, 211))  # אפור
                
                if col == 0:
                    item.setData(Qt.UserRole, car)
                
                self.cars_table.setItem(row, col, item)
        
        self.cars_table.resizeColumnsToContents()
    
    def get_filtered_cars(self):
        """סינון רכבים לפי הפילטרים"""
        filtered = self.all_cars_data.copy()
        
        # פילטר חיפוש
        search_text = self.search_input.text().lower()
        if search_text:
            filtered = [
                car for car in filtered
                if search_text in str(car.get("make", "")).lower() or
                   search_text in str(car.get("model", "")).lower() or
                   search_text in str(car.get("supplier", "")).lower() or
                   search_text in str(car.get("location", "")).lower()
            ]
        
        # פילטר מקור
        source = self.source_filter.currentText()
        if source != "הכל":
            filtered = [car for car in filtered if car.get("source") == source]
        
        # פילטר סוג
        car_type = self.type_filter.currentText()
        if car_type != "הכל":
            filtered = [car for car in filtered if car.get("car_type") == car_type]
        
        # פילטר ספק
        supplier = self.supplier_filter.currentText()
        if supplier != "הכל":
            filtered = [car for car in filtered if car.get("supplier") == supplier]
        
        # פילטר מחיר
        price_range = self.price_filter.currentText()
        if price_range != "הכל":
            if "עד 200" in price_range:
                filtered = [car for car in filtered if car.get("daily_rate", 0) <= 200]
            elif "200-300" in price_range:
                filtered = [car for car in filtered if 200 < car.get("daily_rate", 0) <= 300]
            elif "300-400" in price_range:
                filtered = [car for car in filtered if 300 < car.get("daily_rate", 0) <= 400]
            elif "מעל 400" in price_range:
                filtered = [car for car in filtered if car.get("daily_rate", 0) > 400]
        
        return filtered
    
    def filter_cars(self):
        """הפעלת סינון"""
        self.populate_table()
        self.update_stats()
    
    def update_stats(self):
        """עדכון סטטיסטיקות"""
        filtered_cars = self.get_filtered_cars()
        total = len(filtered_cars)
        
        local_count = len([car for car in filtered_cars if car.get("source") == "מקומי"])
        external_count = len([car for car in filtered_cars if car.get("source") == "חיצוני"])
        available_count = len([car for car in filtered_cars if car.get("available", True)])
        
        if total > 0:
            avg_price = sum(car.get("daily_rate", 0) for car in filtered_cars) / total
            min_price = min(car.get("daily_rate", 0) for car in filtered_cars)
            max_price = max(car.get("daily_rate", 0) for car in filtered_cars)
            
            stats_text = f'סה"כ: {total} רכבים | מקומי: {local_count} | חיצוני: {external_count} | זמינים: {available_count} | מחיר: {min_price}-{max_price}₪ (ממוצע: {avg_price:.0f}₪)'
        else:
            stats_text = "לא נמצאו רכבים התואמים לחיפוש"
        
        self.stats_label.setText(stats_text)
    
    def on_car_selected(self):
        """בחירת רכב מהטבלה"""
        current_row = self.cars_table.currentRow()
        if current_row >= 0:
            first_item = self.cars_table.item(current_row, 0)
            if first_item:
                car_data = first_item.data(Qt.UserRole)
                if car_data:
                    self.car_details.show_car_details(car_data)