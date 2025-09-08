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

# הוספת import לרכיב הרכבים החדש
try:
    from components.cars_table import CarsWidget
    CARS_WIDGET_AVAILABLE = True
    print("רכיב רכבים זמין")
except ImportError as e:
    CARS_WIDGET_AVAILABLE = False
    print(f"רכיב רכבים לא זמין: {e}")

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
            response = requests.get(f"{API_BASE_URL}/api/cars")
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"שגיאה בקבלת רכבים: {e}")
            return []
    
    @staticmethod
    def search_cars(query_data):
        """חיפוש רכבים"""
        try:
            response = requests.post(f"{API_BASE_URL}/api/cars/search", json=query_data)
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"שגיאה בחיפוש: {e}")
            return []
    
    @staticmethod
    def get_car_stats():
        """קבלת סטטיסטיקות"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/stats/cars-by-type")
            return response.json() if response.status_code == 200 else {"data": []}
        except Exception as e:
            print(f"שגיאה בקבלת סטטיסטיקות: {e}")
            return {"data": []}

# ====================
# רכיבי UI - Fallback Components
# ====================

class SimpleCarsWidget(QGroupBox):
    """רכיב פשוט להצגת רכבים - fallback אם הרכיב החדש לא זמין"""
    
    def __init__(self):
        super().__init__("רכבים זמינים")
        self.setup_ui()
        self.load_cars()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # הודעה
        info_label = QLabel("רכיב הרכבים המתקדם לא זמין. משתמש ברכיב פשוט.")
        info_label.setStyleSheet("color: #e67e22; padding: 10px; background: #fef9e7; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # טבלה פשוטה
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["יצרן", "דגם", "שנה", "מחיר יומי"])
        layout.addWidget(self.table)
        
        # כפתור רענון
        refresh_btn = QPushButton("רענן נתונים")
        refresh_btn.clicked.connect(self.load_cars)
        layout.addWidget(refresh_btn)
        
        self.setLayout(layout)
    
    def load_cars(self):
        """טעינת רכבים"""
        try:
            cars = CarRentalAPI.get_all_cars()
            self.table.setRowCount(len(cars))
            
            for row, car in enumerate(cars):
                self.table.setItem(row, 0, QTableWidgetItem(str(car.get("make", "לא ידוע"))))
                self.table.setItem(row, 1, QTableWidgetItem(str(car.get("model", "לא ידוע"))))
                self.table.setItem(row, 2, QTableWidgetItem(str(car.get("year", "לא ידוע"))))
                self.table.setItem(row, 3, QTableWidgetItem(f"{car.get('daily_rate', 0)} ₪"))
            
        except Exception as e:
            QMessageBox.warning(self, "שגיאה", f"לא ניתן לטעון רכבים: {str(e)}")

# ====================
# גרפים - QtCharts
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
            self.timer.start(60000)  # רענון כל דקה
    
    def setup_ui(self):
        if not CHARTS_AVAILABLE:
            error_widget = QWidget()
            error_layout = QVBoxLayout()
            error_label = QLabel("QtCharts לא זמין! התקן: pip install PySide6-Addons")
            error_label.setStyleSheet("color: #e74c3c; padding: 30px; font-size: 14px; background-color: #fdf2f2; border: 2px solid #e74c3c; border-radius: 8px;")
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
            QTimer.singleShot(1000, self.safe_refresh_all_charts)
            
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
            self.pie_series = QPieSeries()
            self.pie_chart = QChart()
            self.pie_chart.addSeries(self.pie_series)
            self.pie_chart.setTitle("התפלגות רכבים לפי סוג")
            
            self.pie_chart_view = QChartView(self.pie_chart)
            self.pie_chart_view.setRenderHint(QPainter.Antialiasing)
            layout.addWidget(self.pie_chart_view)
            
            refresh_btn = QPushButton("רענן נתונים")
            refresh_btn.clicked.connect(self.safe_refresh_pie_chart)
            layout.addWidget(refresh_btn)
            
        except Exception as e:
            error_label = QLabel(f"שגיאה: {e}")
            layout.addWidget(error_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_bar_chart_tab(self):
        """יצירת טאב גרף עמודות"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        try:
            self.bar_series = QBarSeries()
            self.bar_chart = QChart()
            self.bar_chart.addSeries(self.bar_series)
            self.bar_chart.setTitle("רכבים לפי סוג")
            
            self.bar_chart_view = QChartView(self.bar_chart)
            self.bar_chart_view.setRenderHint(QPainter.Antialiasing)
            layout.addWidget(self.bar_chart_view)
            
            refresh_btn = QPushButton("רענן נתונים")
            refresh_btn.clicked.connect(self.safe_refresh_bar_chart)
            layout.addWidget(refresh_btn)
            
        except Exception as e:
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
                except Exception:
                    continue
            
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
            
            if hasattr(self, 'bar_chart') and self.bar_chart:
                self.bar_chart.removeAllSeries()
            
            self.bar_series = QBarSeries()
            bar_set = QBarSet("מספר רכבים")
            categories = []
            
            for item in data_items:
                bar_set.append(item["count"])
                categories.append(item["type"])
            
            self.bar_series.append(bar_set)
            
            if hasattr(self, 'bar_chart'):
                self.bar_chart.addSeries(self.bar_series)
            
        except Exception as e:
            print(f"שגיאה ברענון גרף העמודות: {e}")
    
    def safe_refresh_stats(self):
        """רענון בטוח של סטטיסטיקות טקסט"""
        try:
            cars = CarRentalAPI.get_all_cars()
            stats_data = CarRentalAPI.get_car_stats()
            
            total_cars = len(cars)
            available_cars = len([car for car in cars if car.get("available", True)])
            
            avg_price = sum(car.get("daily_rate", 0) for car in cars) / len(cars) if cars else 0
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
            """
            
            if hasattr(self, 'stats_text') and self.stats_text:
                self.stats_text.setHtml(stats_html)
            
        except Exception as e:
            print(f"שגיאה ברענון סטטיסטיקות: {e}")
    
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
        
        # טאב רכבים
        if CARS_WIDGET_AVAILABLE:
            cars_tab = CarsWidget()
        else:
            cars_tab = SimpleCarsWidget()
        main_tabs.addTab(cars_tab, "🚗 חיפוש רכבים")
        
        # טאב גרפים
        charts_tab = SimpleChartsWidget()
        main_tabs.addTab(charts_tab, "📊 סטטיסטיקות וגרפים")
        
        # טאב יועץ AI מתקדם
        if AI_CHAT_AVAILABLE:
            try:
                ai_chat_tab = AIChatWidget()
                main_tabs.addTab(ai_chat_tab, "🤖 יועץ AI מתקדם")
                print("✅ טאב יועץ AI נוסף בהצלחה")
            except Exception as e:
                print(f"⚠️ שגיאה בטעינת יועץ AI: {e}")
                error_tab = QWidget()
                error_layout = QVBoxLayout()
                error_label = QLabel(f"יועץ ה-AI זמנית לא זמין. שגיאה: {str(e)}")
                error_label.setStyleSheet("color: #e67e22; padding: 20px; background: #fef9e7; border: 2px solid #f39c12; border-radius: 8px;")
                error_layout.addWidget(error_label)
                error_tab.setLayout(error_layout)
                main_tabs.addTab(error_tab, "⚠️ יועץ AI")
        else:
            placeholder_tab = QWidget()
            placeholder_layout = QVBoxLayout()
            placeholder_label = QLabel("🤖 יועץ AI לא זמין")
            placeholder_layout.addWidget(placeholder_label)
            placeholder_tab.setLayout(placeholder_layout)
            main_tabs.addTab(placeholder_tab, "🤖 יועץ AI")
        
        main_layout.addWidget(main_tabs)
        central_widget.setLayout(main_layout)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("מוכן לחיפוש רכבים")

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
        window.status_bar.showMessage(f"שלום {session_manager.get_user_name()}")
        
        sys.exit(app.exec())
    else:
        # המשתמש לא התחבר או ביטל
        sys.exit(0)

if __name__ == "__main__":
    main()