"""
ממשק גרפי ראשי למערכת השכרת רכבים
מממש תבניות MVP ו-Microfrontends
כולל גרפים עם QtCharts ויועץ AI עם RAG
"""

import sys
import requests
import json
import os
from datetime import datetime, date
from typing import List, Optional

# הוספת נתיב לחיפוש מודולים
sys.path.append(os.path.dirname(__file__))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QDateEdit, QSpinBox, QMessageBox, QFrame, QScrollArea,
    QGroupBox, QGridLayout, QSplashScreen, QStatusBar, QDialog
)
from PySide6.QtCore import Qt, QThread, QTimer, QDate, Signal
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap, QPainter

# הוספת imports למערכת אוטנטיקציה
from ui.login_dialog import LoginDialog, session_manager

# הוספת import ליועץ AI
try:
    from components.ai_chat_widget import AIChatWidget
    AI_CHAT_AVAILABLE = True
    print("יועץ AI זמין")
except ImportError as e:
    AI_CHAT_AVAILABLE = False
    print(f"יועץ AI לא זמין: {e}")

# ====================
# הגדרות גלובליות
# ====================

API_BASE_URL = "http://localhost:8000"

class CarRentalStyles:
    """עיצוב אחיד לכל האפליקציה"""
    
    PRIMARY_COLOR = "#2E86C1"      # כחול עיקרי
    SECONDARY_COLOR = "#F8C471"    # כתום משני
    SUCCESS_COLOR = "#58D68D"      # ירוק הצלחה
    WARNING_COLOR = "#F1948A"      # אדום אזהרה
    BACKGROUND_COLOR = "#F8F9FA"   # רקע בהיר
    TEXT_COLOR = "#2C3E50"         # טקסט כהה
    
    @staticmethod
    def get_main_style():
        return """
        QMainWindow {
            background-color: #F8F9FA;
            color: #2C3E50;
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
        
        QLineEdit, QComboBox, QDateEdit, QSpinBox {
            padding: 8px;
            border: 2px solid #BDC3C7;
            border-radius: 4px;
            font-size: 12px;
        }
        
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {
            border-color: #2E86C1;
        }
        
        QTableWidget {
            gridline-color: #BDC3C7;
            background-color: white;
            alternate-background-color: #F8F9FA;
        }
        
        QTableWidget::item:selected {
            background-color: #2E86C1;
            color: white;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #BDC3C7;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QTabWidget::pane {
            border: 1px solid #BDC3C7;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #ECF0F1;
            padding: 10px 20px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #2E86C1;
            color: white;
        }
        """

# ====================
# API Client
# ====================

class CarRentalAPI:
    """ממשק לתקשורת עם שרת ה-FastAPI"""
    
    @staticmethod
    def get_all_cars():
        """קבלת כל הרכבים"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/queries/cars")
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"שגיאה בקבלת רכבים: {e}")
            return []
    
    @staticmethod
    def search_cars(query_data):
        """חיפוש רכבים"""
        try:
            response = requests.post(f"{API_BASE_URL}/api/queries/cars/search", json=query_data)
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"שגיאה בחיפוש: {e}")
            return []
    
    @staticmethod
    def get_car_stats():
        """קבלת סטטיסטיקות"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/queries/stats/cars-by-type")
            return response.json() if response.status_code == 200 else {"data": []}
        except Exception as e:
            print(f"שגיאה בקבלת סטטיסטיקות: {e}")
            return {"data": []}

# ====================
# רכיבי UI (Microfrontends)
# ====================

class SearchWidget(QGroupBox):
    """רכיב חיפוש רכבים"""
    
    search_requested = Signal(dict)  # Signal לבקשת חיפוש
    
    def __init__(self):
        super().__init__("חיפוש רכבים")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QGridLayout()
        
        # שדות חיפוש
        layout.addWidget(QLabel("מיקום:"), 0, 0)
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("תל אביב, חיפה, ירושלים...")
        layout.addWidget(self.location_input, 0, 1)
        
        layout.addWidget(QLabel("מחיר מקסימלי ליום:"), 0, 2)
        self.max_price_input = QSpinBox()
        self.max_price_input.setRange(0, 1000)
        self.max_price_input.setSuffix(" ₪")
        self.max_price_input.setValue(500)
        layout.addWidget(self.max_price_input, 0, 3)
        
        layout.addWidget(QLabel("סוג רכב:"), 1, 0)
        self.car_type_combo = QComboBox()
        self.car_type_combo.addItems(["הכל", "economy", "compact", "midsize", "fullsize", "luxury", "suv"])
        layout.addWidget(self.car_type_combo, 1, 1)
        
        layout.addWidget(QLabel("תיבת הילוכים:"), 1, 2)
        self.transmission_combo = QComboBox()
        self.transmission_combo.addItems(["הכל", "automatic", "manual"])
        layout.addWidget(self.transmission_combo, 1, 3)
        
        # כפתור חיפוש
        self.search_button = QPushButton("חפש רכבים")
        self.search_button.clicked.connect(self.perform_search)
        layout.addWidget(self.search_button, 2, 0, 1, 4)
        
        self.setLayout(layout)
    
    def perform_search(self):
        """ביצוע חיפוש"""
        query = {}
        
        if self.location_input.text().strip():
            query["location"] = self.location_input.text().strip()
        
        if self.max_price_input.value() > 0:
            query["max_price"] = self.max_price_input.value()
        
        if self.car_type_combo.currentText() != "הכל":
            query["car_type"] = self.car_type_combo.currentText()
        
        if self.transmission_combo.currentText() != "הכל":
            query["transmission"] = self.transmission_combo.currentText()
        
        self.search_requested.emit(query)

class CarsTableWidget(QGroupBox):
    """טבלת תצוגת רכבים"""
    
    car_selected = Signal(dict)  # Signal לבחירת רכב
    
    def __init__(self):
        super().__init__("רכבים זמינים")
        self.cars_data = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # טבלה
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "יצרן", "דגם", "שנה", "סוג", "תיבת הילוכים", "מחיר ליום", "מיקום"
        ])
        
        # הגדרת רוחב עמודות
        self.table.setColumnWidth(0, 100)  # יצרן
        self.table.setColumnWidth(1, 120)  # דגם
        self.table.setColumnWidth(2, 80)   # שנה
        self.table.setColumnWidth(3, 100)  # סוג
        self.table.setColumnWidth(4, 120)  # תיבת הילוכים
        self.table.setColumnWidth(5, 100)  # מחיר
        self.table.setColumnWidth(6, 120)  # מיקום
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemClicked.connect(self.on_car_selected)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def update_cars(self, cars):
        """עדכון רשימת הרכבים"""
        self.cars_data = cars
        self.table.setRowCount(len(cars))
        
        for row, car in enumerate(cars):
            self.table.setItem(row, 0, QTableWidgetItem(car["make"]))
            self.table.setItem(row, 1, QTableWidgetItem(car["model"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(car["year"])))
            self.table.setItem(row, 3, QTableWidgetItem(car["car_type"]))
            self.table.setItem(row, 4, QTableWidgetItem(car["transmission"]))
            self.table.setItem(row, 5, QTableWidgetItem(f"{car['daily_rate']:.0f} ₪"))
            self.table.setItem(row, 6, QTableWidgetItem(car["location"]))
    
    def on_car_selected(self, item):
        """טיפול בבחירת רכב"""
        row = item.row()
        if 0 <= row < len(self.cars_data):
            self.car_selected.emit(self.cars_data[row])

class CarDetailsWidget(QGroupBox):
    """פרטי הרכב הנבחר"""
    
    def __init__(self):
        super().__init__("פרטי רכב")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        layout.addWidget(self.details_text)
        
        # כפתור הזמנה
        self.book_button = QPushButton("הזמן רכב זה")
        self.book_button.setEnabled(False)
        layout.addWidget(self.book_button)
        
        self.setLayout(layout)
    
    def update_car_details(self, car):
        """עדכון פרטי הרכב"""
        details = f"""
<h3>{car['make']} {car['model']} ({car['year']})</h3>
<p><b>סוג רכב:</b> {car['car_type']}</p>
<p><b>תיבת הילוכים:</b> {car['transmission']}</p>
<p><b>דלק:</b> {car['fuel_type']}</p>
<p><b>מספר מקומות:</b> {car['seats']}</p>
<p><b>מיקום:</b> {car['location']}</p>
<p><b>מחיר ליום:</b> <span style="color: #2E86C1; font-weight: bold;">{car['daily_rate']:.0f} ₪</span></p>
<p><b>זמינות:</b> {"זמין" if car['available'] else "לא זמין"}</p>
        """
        
        self.details_text.setHtml(details)
        self.book_button.setEnabled(car['available'])

# ====================
# גרפים - QtCharts (מתוקן)
# ====================

try:
    from PySide6.QtCharts import (
        QChart, QChartView, QPieSeries, QBarSeries, QBarSet,
        QBarCategoryAxis, QValueAxis
    )
    CHARTS_AVAILABLE = True
    print("QtCharts זמין - גרפים יעבדו")
except ImportError:
    CHARTS_AVAILABLE = False
    print("QtCharts לא זמין - התקן: pip install PySide6-Addons")

class SimpleChartsWidget(QTabWidget):
    """גרפים פשוטים ובטוחים"""
    
    def __init__(self):
        super().__init__()
        self.charts_created = False
        self.setup_ui()
        
        if CHARTS_AVAILABLE:
            # Timer לרענון נתונים - רק אם הגרפים זמינים
            self.timer = QTimer()
            self.timer.timeout.connect(self.safe_refresh_all_charts)
            self.timer.start(60000)  # רענון כל דקה (פחות אגרסיבי)
    
    def setup_ui(self):
        if not CHARTS_AVAILABLE:
            # אם אין QtCharts, הצג הודעת התקנה
            error_widget = QWidget()
            error_layout = QVBoxLayout()
            error_label = QLabel("""
            QtCharts לא זמין!
            
            להתקנה, הרץ בטרמינל:
            pip install PySide6-Addons
            
            או:
            pip uninstall PySide6 PySide6-Addons
            pip install PySide6>=6.6.0 PySide6-Addons>=6.6.0
            
            לאחר מכן הפעל מחדש את האפליקציה.
            """)
            error_label.setStyleSheet("""
                color: #e74c3c;
                padding: 30px;
                font-size: 14px;
                background-color: #fdf2f2;
                border: 2px solid #e74c3c;
                border-radius: 8px;
            """)
            error_layout.addWidget(error_label)
            error_widget.setLayout(error_layout)
            self.addTab(error_widget, "התקנה נדרשת")
            return
        
        try:
            # טאב גרף עוגה
            self.pie_tab = self.create_pie_chart_tab()
            self.addTab(self.pie_tab, "סוגי רכבים")
            
            # טאב גרף עמודות
            self.bar_tab = self.create_bar_chart_tab()
            self.addTab(self.bar_tab, "מיקומים")
            
            # טאב סטטיסטיקות טקסט
            self.stats_tab = self.create_stats_tab()
            self.addTab(self.stats_tab, "סטטיסטיקות")
            
            self.charts_created = True
            
            # טעינה ראשונית
            QTimer.singleShot(1000, self.safe_refresh_all_charts)  # רענון ראשוני אחרי שנייה
            
        except Exception as e:
            print(f"שגיאה ביצירת גרפים: {e}")
            self.show_error_tab(f"שגיאה ביצירת גרפים: {e}")
    
    def show_error_tab(self, error_msg):
        """הצגת טאב שגיאה"""
        error_widget = QWidget()
        error_layout = QVBoxLayout()
        error_label = QLabel(f"שגיאה: {error_msg}")
        error_label.setStyleSheet("color: red; padding: 20px;")
        error_layout.addWidget(error_label)
        error_widget.setLayout(error_layout)
        self.addTab(error_widget, "שגיאה")
    
    def create_pie_chart_tab(self):
        """יצירת טאב גרף עוגה"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        try:
            # יצירת גרף עוגה
            self.pie_series = QPieSeries()
            self.pie_chart = QChart()
            self.pie_chart.addSeries(self.pie_series)
            self.pie_chart.setTitle("התפלגות רכבים לפי סוג")
            self.pie_chart.legend().show()
            
            self.pie_chart_view = QChartView(self.pie_chart)
            self.pie_chart_view.setRenderHint(QPainter.Antialiasing)
            layout.addWidget(self.pie_chart_view)
            
            # כפתור רענון
            refresh_btn = QPushButton("רענן נתונים")
            refresh_btn.clicked.connect(self.safe_refresh_pie_chart)
            layout.addWidget(refresh_btn)
            
        except Exception as e:
            print(f"שגיאה ביצירת גרף עוגה: {e}")
            error_label = QLabel(f"שגיאה: {e}")
            layout.addWidget(error_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_bar_chart_tab(self):
        """יצירת טאב גרף עמודות"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        try:
            # יצירת גרף עמודות
            self.bar_series = QBarSeries()
            self.bar_chart = QChart()
            self.bar_chart.addSeries(self.bar_series)
            self.bar_chart.setTitle("רכבים לפי סוג")
            
            self.bar_chart_view = QChartView(self.bar_chart)
            self.bar_chart_view.setRenderHint(QPainter.Antialiasing)
            layout.addWidget(self.bar_chart_view)
            
            # כפתור רענון
            refresh_btn = QPushButton("רענן נתונים")
            refresh_btn.clicked.connect(self.safe_refresh_bar_chart)
            layout.addWidget(refresh_btn)
            
        except Exception as e:
            print(f"שגיאה ביצירת גרף עמודות: {e}")
            error_label = QLabel(f"שגיאה: {e}")
            layout.addWidget(error_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_stats_tab(self):
        """יצירת טאב סטטיסטיקות טקסט"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        # כפתור רענון
        refresh_btn = QPushButton("רענן סטטיסטיקות")
        refresh_btn.clicked.connect(self.safe_refresh_stats)
        layout.addWidget(refresh_btn)
        
        widget.setLayout(layout)
        return widget
    
    def safe_refresh_pie_chart(self):
        """רענון בטוח של גרף העוגה"""
        if not CHARTS_AVAILABLE or not self.charts_created:
            return
            
        try:
            data = CarRentalAPI.get_car_stats()
            
            # מחק נתונים ישנים בצורה בטוחה
            if hasattr(self, 'pie_series') and self.pie_series:
                self.pie_series.clear()
            
            colors = [QColor("#3498db"), QColor("#e74c3c"), QColor("#2ecc71"), 
                     QColor("#f39c12"), QColor("#9b59b6"), QColor("#1abc9c")]
            
            data_items = data.get("data", [])
            if not data_items:
                return
            
            for i, item in enumerate(data_items):
                try:
                    slice_obj = self.pie_series.append(f"{item['type']}: {item['count']}", item["count"])
                    if i < len(colors):
                        slice_obj.setColor(colors[i])
                    
                    # הדגש את החלק הגדול ביותר
                    max_count = max([x["count"] for x in data_items])
                    if item["count"] == max_count:
                        slice_obj.setExploded(True)
                        slice_obj.setLabelVisible(True)
                except Exception as slice_error:
                    print(f"שגיאה בהוספת slice: {slice_error}")
                    continue
            
            if hasattr(self, 'pie_chart') and self.pie_chart:
                self.pie_chart.setTitle(f"התפלגות רכבים לפי סוג (סה\"כ: {data.get('total_cars', 0)})")
            
        except Exception as e:
            print(f"שגיאה ברענון גרף העוגה: {e}")
    
    def safe_refresh_bar_chart(self):
        """רענון בטוח של גרף העמודות"""
        if not CHARTS_AVAILABLE or not self.charts_created:
            return
            
        try:
            data = CarRentalAPI.get_car_stats()
            data_items = data.get("data", [])
            
            if not data_items:
                return
            
            # נקה את הגרף בצורה בטוחה
            if hasattr(self, 'bar_chart') and self.bar_chart:
                # הסר צירים ישנים
                for axis in self.bar_chart.axes():
                    try:
                        self.bar_chart.removeAxis(axis)
                    except:
                        pass
                
                # הסר series ישנים
                try:
                    self.bar_chart.removeAllSeries()
                except:
                    pass
            
            # צור series חדש
            self.bar_series = QBarSeries()
            bar_set = QBarSet("מספר רכבים")
            categories = []
            
            for item in data_items:
                try:
                    bar_set.append(item["count"])
                    categories.append(item["type"])
                except Exception as item_error:
                    print(f"שגיאה בהוספת פריט: {item_error}")
                    continue
            
            bar_set.setColor(QColor("#3498db"))
            self.bar_series.append(bar_set)
            
            # הוסף series לגרף
            if hasattr(self, 'bar_chart') and self.bar_chart:
                self.bar_chart.addSeries(self.bar_series)
                
                # צור צירים חדשים
                axis_x = QBarCategoryAxis()
                axis_x.setCategories(categories)
                axis_y = QValueAxis()
                
                max_count = max([item["count"] for item in data_items]) if data_items else 1
                axis_y.setRange(0, max_count + 1)
                
                # הוסף צירים
                self.bar_chart.addAxis(axis_x, Qt.AlignBottom)
                self.bar_chart.addAxis(axis_y, Qt.AlignLeft)
                
                # חבר series לצירים
                self.bar_series.attachAxis(axis_x)
                self.bar_series.attachAxis(axis_y)
                
                self.bar_chart.setTitle("רכבים לפי סוג")
            
        except Exception as e:
            print(f"שגיאה ברענון גרף העמודות: {e}")
    
    def safe_refresh_stats(self):
        """רענון בטוח של סטטיסטיקות טקסט"""
        try:
            cars = CarRentalAPI.get_all_cars()
            stats_data = CarRentalAPI.get_car_stats()
            
            # חישוב סטטיסטיקות
            total_cars = len(cars)
            available_cars = len([car for car in cars if car.get("available", True)])
            
            # מחיר ממוצע
            if cars:
                avg_price = sum(car.get("daily_rate", 0) for car in cars) / len(cars)
            else:
                avg_price = 0
            
            # מיקומים
            locations = set(car.get("location", "") for car in cars)
            
            stats_html = f"""
            <h2 style="color: #2E86C1;">סטטיסטיקות מערכת השכרת רכבים</h2>
            
            <h3>נתונים כלליים:</h3>
            <ul>
                <li><b>סה"כ רכבים במערכת:</b> {total_cars}</li>
                <li><b>רכבים זמינים:</b> {available_cars}</li>
                <li><b>רכבים תפוסים:</b> {total_cars - available_cars}</li>
                <li><b>מחיר ממוצע ליום:</b> {avg_price:.0f} ₪</li>
                <li><b>מספר מיקומים:</b> {len(locations)}</li>
            </ul>
            
            <h3>התפלגות לפי סוג:</h3>
            <ul>
            """
            
            for item in stats_data.get("data", []):
                percentage = (item["count"] / total_cars * 100) if total_cars > 0 else 0
                stats_html += f"<li><b>{item['type']}:</b> {item['count']} רכבים ({percentage:.1f}%)</li>"
            
            stats_html += """
            </ul>
            
            <h3>מיקומים:</h3>
            <ul>
            """
            
            for location in sorted(locations):
                location_cars = [car for car in cars if car.get("location") == location]
                stats_html += f"<li><b>{location}:</b> {len(location_cars)} רכבים</li>"
            
            stats_html += "</ul>"
            
            if hasattr(self, 'stats_text') and self.stats_text:
                self.stats_text.setHtml(stats_html)
            
        except Exception as e:
            print(f"שגיאה ברענון סטטיסטיקות: {e}")
            if hasattr(self, 'stats_text') and self.stats_text:
                self.stats_text.setPlainText(f"שגיאה בטעינת סטטיסטיקות: {e}")
    
    def safe_refresh_all_charts(self):
        """רענון בטוח של כל הגרפים"""
        if not CHARTS_AVAILABLE or not self.charts_created:
            return
        
        try:
            self.safe_refresh_pie_chart()
            self.safe_refresh_bar_chart()
            self.safe_refresh_stats()
            print("רענון גרפים הושלם")
        except Exception as e:
            print(f"שגיאה ברענון כללי: {e}")

# ====================
# חלון ראשי
# ====================

class MainWindow(QMainWindow):
    """חלון ראשי של האפליקציה"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        self.setWindowTitle("מערכת השכרת רכבים - Car Rental System")
        self.setGeometry(100, 100, 1400, 900)
        
        # Widget מרכזי
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout ראשי
        main_layout = QVBoxLayout()
        
        # כותרת
        title_label = QLabel("מערכת השכרת רכבים")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2E86C1; margin: 20px;")
        main_layout.addWidget(title_label)
        
        # יצירת טאבים ראשיים
        main_tabs = QTabWidget()
        
        # טאב רכבים (קיים)
        cars_tab = self.create_cars_tab()
        main_tabs.addTab(cars_tab, "🚗 חיפוש רכבים")
        
        # טאב גרפים
        charts_tab = SimpleChartsWidget()
        main_tabs.addTab(charts_tab, "📊 סטטיסטיקות וגרפים")
        
        # טאב יועץ AI מתקדם (חדש!)
        if AI_CHAT_AVAILABLE:
            try:
                ai_chat_tab = AIChatWidget()
                main_tabs.addTab(ai_chat_tab, "🤖 יועץ AI מתקדם")
                print("✅ טאב יועץ AI נוסף בהצלחה")
            except Exception as e:
                print(f"⚠️ שגיאה בטעינת יועץ AI: {e}")
                # צור טאב שגיאה
                error_tab = QWidget()
                error_layout = QVBoxLayout()
                error_label = QLabel(f"""
                יועץ ה-AI זמנית לא זמין
                
                שגיאה: {str(e)}
                
                וודא שהשרת רץ והקבצים קיימים:
                - backend/api/ai_endpoints.py
                - ai-service/rag_service.py
                - frontend/components/ai_chat_widget.py
                """)
                error_label.setStyleSheet("color: #e67e22; padding: 20px; background: #fef9e7; border: 2px solid #f39c12; border-radius: 8px;")
                error_layout.addWidget(error_label)
                error_tab.setLayout(error_layout)
                main_tabs.addTab(error_tab, "⚠️ יועץ AI")
        else:
            # צור טאב הודעה על היעדר יועץ AI
            placeholder_tab = QWidget()
            placeholder_layout = QVBoxLayout()
            placeholder_label = QLabel("""
            🤖 יועץ AI לא זמין
            
            כדי להפעיל את יועץ ה-AI, צור את הקבצים הבאים:
            
            1. frontend/components/ai_chat_widget.py
            2. backend/api/ai_endpoints.py  
            3. ai-service/rag_service.py
            
            ווודא ש-Docker עם Ollama + ChromaDB רצים.
            
            לאחר מכן הפעל מחדש את האפליקציה.
            """)
            placeholder_label.setStyleSheet("color: #7f8c8d; padding: 30px; font-size: 14px;")
            placeholder_layout.addWidget(placeholder_label)
            placeholder_tab.setLayout(placeholder_layout)
            main_tabs.addTab(placeholder_tab, "🤖 יועץ AI")
        
        main_layout.addWidget(main_tabs)
        
        central_widget.setLayout(main_layout)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("מוכן לחיפוש רכבים")
    
    def create_cars_tab(self):
        """יצירת טאב חיפוש הרכבים"""
        cars_widget = QWidget()
        layout = QVBoxLayout()
        
        # רכיב חיפוש
        self.search_widget = SearchWidget()
        self.search_widget.search_requested.connect(self.perform_search)
        layout.addWidget(self.search_widget)
        
        # Layout תחתון (טבלה + פרטים)
        bottom_layout = QHBoxLayout()
        
        # טבלת רכבים
        self.cars_table = CarsTableWidget()
        self.cars_table.car_selected.connect(self.on_car_selected)
        bottom_layout.addWidget(self.cars_table, 2)
        
        # פרטי רכב
        self.car_details = CarDetailsWidget()
        bottom_layout.addWidget(self.car_details, 1)
        
        layout.addLayout(bottom_layout)
        cars_widget.setLayout(layout)
        
        return cars_widget
    
    def load_initial_data(self):
        """טעינת נתונים ראשוניים"""
        self.status_bar.showMessage("טוען רכבים...")
        cars = CarRentalAPI.get_all_cars()
        self.cars_table.update_cars(cars)
        self.status_bar.showMessage(f"נטענו {len(cars)} רכבים")
    
    def perform_search(self, query):
        """ביצוע חיפוש"""
        self.status_bar.showMessage("מחפש...")
        cars = CarRentalAPI.search_cars(query)
        self.cars_table.update_cars(cars)
        self.status_bar.showMessage(f"נמצאו {len(cars)} רכבים")
    
    def on_car_selected(self, car):
        """טיפול בבחירת רכב"""
        self.car_details.update_car_details(car)
        self.status_bar.showMessage(f"נבחר: {car['make']} {car['model']}")

# ====================
# פונקציה ראשית
# ====================

def main():
    """הפעלת האפליקציה עם מערכת אוטנטיקציה"""
    app = QApplication(sys.argv)
    
    # עיצוב כללי
    app.setStyleSheet(CarRentalStyles.get_main_style())
    
    # מסך כניסה
    login_dialog = LoginDialog()
    
    if login_dialog.exec() == QDialog.Accepted:
        # המשתמש התחבר בהצלחה
        print(f"משתמש התחבר: {session_manager.get_user_name()}")
        print(f"תפקיד: {session_manager.get_user_role()}")
        
        # יצירת חלון ראשי
        window = MainWindow()
        window.show()
        
        # הצגת הודעת ברכה בstatus bar
        welcome_msg = f"שלום {session_manager.get_user_name()}"
        if session_manager.is_admin():
            welcome_msg += " (אדמין)"
        window.status_bar.showMessage(welcome_msg)
        
        print("מערכת השכרת רכבים הופעלה בהצלחה!")
        if not CHARTS_AVAILABLE:
            print("⚠️  QtCharts לא זמין - התקן: pip install PySide6-Addons")
        else:
            print("📊 גרפים זמינים ופעילים")
        
        if not AI_CHAT_AVAILABLE:
            print("⚠️  יועץ AI לא זמין - צור קבצי AI")
        else:
            print("🤖 יועץ AI זמין ופעיל")
        
        # הפעלת לולאת האירועים
        sys.exit(app.exec())
    else:
        # המשתמש ביטל את הכניסה
        print("הכניסה בוטלה")
        sys.exit(0)

if __name__ == "__main__":
    main()