"""
Admin Endpoints - מערכת ניהול לרכבים ולקוחות
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import json

try:
    from database.postgres_connection import db
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

router = APIRouter(prefix="/api/admin", tags=["Admin Management"])

# מודלים לניהול
class CarCreate(BaseModel):
    make: str
    model: str
    year: int
    car_type: str  # economy, family, luxury, etc.
    transmission: str  # manual, automatic
    daily_rate: float
    location: str
    fuel_type: str
    seats: int
    image_url: Optional[str] = None
    features: Optional[List[str]] = []

class CarUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    car_type: Optional[str] = None
    transmission: Optional[str] = None
    daily_rate: Optional[float] = None
    available: Optional[bool] = None
    location: Optional[str] = None
    fuel_type: Optional[str] = None
    seats: Optional[int] = None
    image_url: Optional[str] = None
    features: Optional[List[str]] = None

class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    license_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None

# Admin Endpoints for Cars
@router.post("/cars")
async def create_car(car: CarCreate):
    """הוספת רכב חדש"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        car_id = db.add_car(car.dict())
        return {
            "message": "רכב נוסף בהצלחה",
            "car_id": car_id,
            "car_details": f"{car.make} {car.model} {car.year}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בהוספת רכב: {str(e)}")

@router.put("/cars/{car_id}")
async def update_car(car_id: int, car_update: CarUpdate):
    """עדכון רכב קיים"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        # בדוק שהרכב קיים
        existing_car = db.get_car_by_id(str(car_id))
        if not existing_car:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        
        # עדכן רק את השדות שנשלחו
        update_data = car_update.dict(exclude_unset=True)
        if update_data:
            db.update_car(car_id, update_data)
        
        return {"message": "רכב עודכן בהצלחה", "car_id": car_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בעדכון רכב: {str(e)}")

@router.delete("/cars/{car_id}")
async def delete_car(car_id: int):
    """מחיקת רכב"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        # בדוק שהרכב קיים
        existing_car = db.get_car_by_id(str(car_id))
        if not existing_car:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        
        # במקום מחיקה, סמן כלא זמין
        db.update_car(car_id, {"available": False})
        
        return {"message": "רכב הוסר מהמערכת", "car_id": car_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה במחיקת רכב: {str(e)}")

# Admin Endpoints for Customers
@router.post("/customers")
async def create_customer(customer: CustomerCreate):
    """הוספת לקוח חדש"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        customer_id = db.add_customer(customer.dict())
        return {
            "message": "לקוח נוסף בהצלחה",
            "customer_id": customer_id,
            "customer_name": f"{customer.first_name} {customer.last_name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בהוספת לקוח: {str(e)}")

@router.get("/customers")
async def get_all_customers():
    """קבלת כל הלקוחות"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        customers = db.get_all_customers()
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת לקוחות: {str(e)}")

# Data Management
@router.post("/init-sample-data")
async def initialize_sample_data():
    """אתחול נתוני דוגמה"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        # בדוק אם כבר יש נתונים
        cars = db.get_all_cars()
        if len(cars) > 0:
            return {"message": "נתונים כבר קיימים במערכת", "cars_count": len(cars)}
        
        # הוסף רכבים לדוגמה
        sample_cars = [
            {
                "make": "טויוטה", "model": "קורולה", "year": 2023, "car_type": "economy",
                "transmission": "automatic", "daily_rate": 150.0, "location": "תל אביב",
                "fuel_type": "gasoline", "seats": 5, "features": ["מזגן", "Bluetooth", "GPS"]
            },
            {
                "make": "הונדה", "model": "CR-V", "year": 2022, "car_type": "family",
                "transmission": "automatic", "daily_rate": 280.0, "location": "חיפה",
                "fuel_type": "gasoline", "seats": 7, "features": ["מזגן", "7 מקומות", "מצלמת רוורס"]
            },
            {
                "make": "BMW", "model": "X3", "year": 2023, "car_type": "luxury",
                "transmission": "automatic", "daily_rate": 450.0, "location": "ירושלים",
                "fuel_type": "gasoline", "seats": 5, "features": ["עור", "מולטימדיה", "מושבים מחוממים"]
            }
        ]
        
        cars_added = 0
        for car_data in sample_cars:
            car_id = db.add_car(car_data)
            if car_id:
                cars_added += 1
        
        return {
            "message": f"נוספו {cars_added} רכבים לדוגמה",
            "cars_added": cars_added
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה באתחול נתונים: {str(e)}")

@router.get("/stats")
async def get_admin_stats():
    """סטטיסטיקות מערכת"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        cars = db.get_all_cars()
        customers = db.get_all_customers() if hasattr(db, 'get_all_customers') else []
        bookings = db.get_all_bookings() if hasattr(db, 'get_all_bookings') else []
        
        return {
            "total_cars": len(cars),
            "available_cars": len([c for c in cars if c.get('available', True)]),
            "total_customers": len(customers),
            "total_bookings": len(bookings),
            "cars_by_type": db.get_cars_by_type_stats(),
            "database_type": "PostgreSQL"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת סטטיסטיקות: {str(e)}")

@router.delete("/clear-all-data")
async def clear_all_data():
    """ניקוי כל הנתונים (זהירות!)"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="בסיס הנתונים לא זמין")
    
    try:
        db.clear_all_data()
        return {"message": "כל הנתונים נוקו מהמערכת"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בניקוי נתונים: {str(e)}")