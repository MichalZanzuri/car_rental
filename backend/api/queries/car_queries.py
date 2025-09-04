"""
CQRS Queries - שאילתות לקבלת נתונים מהמערכת
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# הוספת נתיב לחיפוש מודולים
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.event_store import event_service

router = APIRouter(prefix="/api/queries", tags=["Queries"])

# ====================
# Query Models
# ====================

class CarSearchQuery(BaseModel):
    location: Optional[str] = None
    car_type: Optional[str] = None  
    max_price: Optional[float] = None
    transmission: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class Car(BaseModel):
    id: str
    make: str
    model: str
    year: int
    car_type: str
    transmission: str
    daily_rate: float
    available: bool
    location: str
    fuel_type: str
    seats: int
    image_url: Optional[str] = None

# ====================
# Query Handlers
# ====================

@router.get("/cars", response_model=List[Car])
async def get_all_cars():
    """קבלת כל הרכבים במערכת"""
    try:
        cars_data = event_service.get_all_cars()
        cars = []
        for car_data in cars_data:
            car = Car(**car_data)
            cars.append(car)
        return cars
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת רכבים: {str(e)}")

@router.get("/cars/{car_id}", response_model=Car)
async def get_car_by_id(car_id: str):
    """קבלת פרטי רכב לפי ID"""
    try:
        car_data = event_service.get_car_by_id(car_id)
        if not car_data:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        return Car(**car_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.post("/cars/search", response_model=List[Car])
async def search_cars(query: CarSearchQuery):
    """חיפוש רכבים לפי קריטריונים"""
    try:
        all_cars = event_service.get_all_cars()
        results = []
        
        for car_data in all_cars:
            car = Car(**car_data)
            
            # סינון לפי זמינות
            if not car.available:
                continue
            
            # סינון לפי מיקום
            if query.location and query.location.lower() not in car.location.lower():
                continue
            
            # סינון לפי סוג רכב
            if query.car_type and car.car_type != query.car_type:
                continue
            
            # סינון לפי מחיר מקסימלי
            if query.max_price and car.daily_rate > query.max_price:
                continue
            
            # סינון לפי תיבת הילוכים
            if query.transmission and car.transmission != query.transmission:
                continue
            
            results.append(car)
        
        # רישום פעולת חיפוש
        query_dict = query.dict(exclude_unset=True)
        event_service.log_search(query_dict, len(results))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בחיפוש: {str(e)}")

@router.get("/cars-by-location/{location}")
async def get_cars_by_location(location: str):
    """קבלת רכבים לפי מיקום"""
    try:
        all_cars = event_service.get_all_cars()
        location_cars = [
            Car(**car_data) for car_data in all_cars 
            if location.lower() in car_data["location"].lower() and car_data["available"]
        ]
        return location_cars
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.get("/available-cars")
async def get_available_cars():
    """קבלת כל הרכבים הזמינים"""
    try:
        all_cars = event_service.get_all_cars()
        available_cars = [
            Car(**car_data) for car_data in all_cars 
            if car_data["available"]
        ]
        return available_cars
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.get("/stats/cars-by-type")
async def get_cars_stats():
    """סטטיסטיקות רכבים לפי סוג - לגרפים"""
    try:
        cars = event_service.get_all_cars()
        from collections import Counter
        
        type_counts = Counter([car["car_type"] for car in cars])
        
        return {
            "data": [
                {"type": car_type, "count": count} 
                for car_type, count in type_counts.items()
            ],
            "total_cars": len(cars)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.get("/stats/search-analytics")
async def get_search_analytics():
    """סטטיסטיקות חיפושים - לגרפים"""
    try:
        return event_service.get_search_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.get("/stats/cars-by-location")
async def get_cars_by_location_stats():
    """סטטיסטיקות רכבים לפי מיקום"""
    try:
        cars = event_service.get_all_cars()
        from collections import Counter
        
        location_counts = Counter([car["location"] for car in cars])
        
        return {
            "data": [
                {"location": location, "count": count} 
                for location, count in location_counts.items()
            ],
            "total_locations": len(location_counts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.get("/stats/price-ranges")
async def get_price_ranges():
    """סטטיסטיקות רכבים לפי טווחי מחיר"""
    try:
        cars = event_service.get_all_cars()
        
        price_ranges = {
            "0-150": 0,
            "150-250": 0,
            "250-350": 0,
            "350-450": 0,
            "450+": 0
        }
        
        for car in cars:
            price = car["daily_rate"]
            if price < 150:
                price_ranges["0-150"] += 1
            elif price < 250:
                price_ranges["150-250"] += 1
            elif price < 350:
                price_ranges["250-350"] += 1
            elif price < 450:
                price_ranges["350-450"] += 1
            else:
                price_ranges["450+"] += 1
        
        return {
            "data": [
                {"range": range_name, "count": count}
                for range_name, count in price_ranges.items()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")