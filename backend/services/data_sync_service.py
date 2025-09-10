"""
Data Sync Service - סנכרון נתונים מ-APIs חיצוניים לבסיס הנתונים
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import threading

# ייבוא מודולי המערכת
try:
    from database.db_connection import SessionLocal
    from database.models import Car
    from services.trawex_api import search_external_cars
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    print(f"Database לא זמין: {e}")

class DataSyncService:
    """שירות סנכרון נתונים מ-APIs חיצוניים"""
    
    def __init__(self):
        self.is_running = False
        self.last_sync = None
        self.sync_interval_hours = 6  # סנכרון כל 6 שעות
        
    def sync_external_cars_to_db(self) -> Dict:
        """סנכרון רכבים חיצוניים לבסיס הנתונים"""
        if not DATABASE_AVAILABLE:
            return {"success": False, "error": "Database לא זמין"}
        
        try:
            print("מתחיל סנכרון רכבים חיצוניים...")
            
            # קבלת רכבים מהAPI החיצוני
            locations = ["Tel Aviv", "Jerusalem", "Haifa", "Ben Gurion Airport", "Eilat"]
            all_external_cars = []
            
            for location in locations:
                try:
                    cars = search_external_cars(
                        pickup_location=location,
                        pickup_date="2024-12-01",
                        return_date="2024-12-05"
                    )
                    all_external_cars.extend(cars)
                    print(f"נמצאו {len(cars)} רכבים ב-{location}")
                    time.sleep(1)  # הפסקה בין בקשות
                except Exception as e:
                    print(f"שגיאה בחיפוש ב-{location}: {e}")
                    continue
            
            if not all_external_cars:
                return {"success": False, "error": "לא נמצאו רכבים חיצוניים"}
            
            # סנכרון לבסיס הנתונים
            db = SessionLocal()
            synced_count = 0
            updated_count = 0
            
            try:
                # מחיקת רכבים חיצוניים ישנים (בני יותר מיום)
                yesterday = datetime.now() - timedelta(days=1)
                old_external_cars = db.query(Car).filter(
                    Car.external_api == "trawex",
                    Car.updated_at < yesterday
                ).all()
                
                for old_car in old_external_cars:
                    db.delete(old_car)
                
                # הוספת/עדכון רכבים חיצוניים
                for car_data in all_external_cars:
                    try:
                        # בדיקה אם הרכב כבר קיים
                        existing_car = db.query(Car).filter(
                            Car.make == car_data.get("make"),
                            Car.model == car_data.get("model"),
                            Car.supplier == car_data.get("supplier"),
                            Car.external_api == "trawex"
                        ).first()
                        
                        if existing_car:
                            # עדכון רכב קיים
                            existing_car.daily_rate = car_data.get("daily_rate", 0)
                            existing_car.available = car_data.get("available", True)
                            existing_car.location = car_data.get("location", "Unknown")
                            existing_car.updated_at = datetime.now()
                            updated_count += 1
                        else:
                            # הוספת רכב חדש
                            new_car = Car(
                                make=car_data.get("make", "Unknown"),
                                model=car_data.get("model", "Unknown"),
                                year=car_data.get("year", 2023),
                                car_type=car_data.get("car_type", "economy"),
                                transmission=car_data.get("transmission", "automatic"),
                                daily_rate=car_data.get("daily_rate", 0),
                                location=car_data.get("location", "Unknown"),
                                fuel_type=car_data.get("fuel_type", "gasoline"),
                                available=car_data.get("available", True),
                                supplier=car_data.get("supplier", "External"),
                                external_api="trawex",
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            db.add(new_car)
                            synced_count += 1
                            
                    except Exception as e:
                        print(f"שגיאה בעדכון רכב {car_data.get('make')} {car_data.get('model')}: {e}")
                        continue
                
                db.commit()
                self.last_sync = datetime.now()
                
                result = {
                    "success": True,
                    "synced_cars": synced_count,
                    "updated_cars": updated_count,
                    "total_processed": len(all_external_cars),
                    "sync_time": self.last_sync.isoformat()
                }
                
                print(f"סנכרון הושלם: {synced_count} רכבים חדשים, {updated_count} רכבים עודכנו")
                return result
                
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
                
        except Exception as e:
            print(f"שגיאה בסנכרון: {e}")
            return {"success": False, "error": str(e)}
    
    def schedule_periodic_sync(self):
        """הגדרת סנכרון תקופתי"""
        schedule.clear()
        
        # סנכרון כל 6 שעות
        schedule.every(self.sync_interval_hours).hours.do(self.sync_external_cars_to_db)
        
        # סנכרון יומי בחצות
        schedule.every().day.at("00:00").do(self.sync_external_cars_to_db)
        
        print(f"סנכרון תקופתי מוגדר לכל {self.sync_interval_hours} שעות")
    
    def start_background_sync(self):
        """הפעלת סנכרון ברקע"""
        if self.is_running:
            print("סנכרון כבר רץ")
            return
        
        self.is_running = True
        self.schedule_periodic_sync()
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # בדיקה כל דקה
        
        # הפעלת הthread ברקע
        sync_thread = threading.Thread(target=run_scheduler, daemon=True)
        sync_thread.start()
        
        print("סנכרון ברקע הופעל")
        
        # סנכרון ראשוני מיידי
        threading.Thread(target=self.sync_external_cars_to_db, daemon=True).start()
    
    def stop_background_sync(self):
        """עצירת סנכרון ברקע"""
        self.is_running = False
        schedule.clear()
        print("סנכרון ברקע הופסק")
    
    def get_sync_status(self) -> Dict:
        """מצב הסנכרון"""
        return {
            "is_running": self.is_running,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "next_sync": schedule.next_run().isoformat() if schedule.next_run() else None,
            "sync_interval_hours": self.sync_interval_hours
        }
    
    def manual_sync(self) -> Dict:
        """סנכרון ידני"""
        print("מבצע סנכרון ידני...")
        return self.sync_external_cars_to_db()

# יצירת instance גלובלי
data_sync_service = DataSyncService()

# פונקציות עזר
def start_data_sync():
    """הפעלת סנכרון נתונים"""
    if DATABASE_AVAILABLE:
        data_sync_service.start_background_sync()
    else:
        print("סנכרון נתונים לא זמין - Database לא מחובר")

def manual_sync_data():
    """סנכרון ידני"""
    return data_sync_service.manual_sync()

def get_sync_status():
    """מצב הסנכרון"""
    return data_sync_service.get_sync_status()

def stop_data_sync():
    """עצירת סנכרון"""
    data_sync_service.stop_background_sync()

if __name__ == "__main__":
    # בדיקה מהירה
    print("בדיקת Data Sync Service:")
    
    if DATABASE_AVAILABLE:
        result = manual_sync_data()
        print(f"תוצאת סנכרון: {result}")
    else:
        print("Database לא זמין - לא ניתן לבצע סנכרון")