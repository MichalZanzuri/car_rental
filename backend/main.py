"""
שרת FastAPI עיקרי למערכת השכרת רכבים
מממש תבנית CQRS ו-Gateway
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, date
import uvicorn

# יבוא הrouters
from api.commands.car_commands import router as commands_router
from api.queries.car_queries import router as queries_router
from api.auth_endpoints import router as auth_router

# יצירת אפליקציית FastAPI
app = FastAPI(
    title="Car Rental System API",
    description="מערכת ניהול השכרת רכבים",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# הוספת הrouters
app.include_router(commands_router)
app.include_router(queries_router)
app.include_router(auth_router)

# הוספת AI router (אחרי יצירת app)
try:
    from api.ai_endpoints import router as ai_router
    app.include_router(ai_router)
    print("✅ AI Router נטען בהצלחה")
except ImportError as e:
    print(f"⚠️ AI Router לא זמין: {e}")

# הגדרת CORS (כדי שה-Frontend יוכל להתחבר)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # בפרודקשיון נשנה את זה
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================
# מודלי נתונים (Pydantic)
# ====================

from pydantic import BaseModel
from enum import Enum

class CarType(str, Enum):
    ECONOMY = "economy"
    COMPACT = "compact" 
    MIDSIZE = "midsize"
    FULLSIZE = "fullsize"
    LUXURY = "luxury"
    SUV = "suv"

class TransmissionType(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"

class Car(BaseModel):
    id: int
    make: str  # יצרן
    model: str  # דגם
    year: int
    car_type: CarType
    transmission: TransmissionType
    daily_rate: float  # מחיר יומי
    available: bool
    location: str
    fuel_type: str
    seats: int
    image_url: Optional[str] = None

class CarSearchQuery(BaseModel):
    location: Optional[str] = None
    car_type: Optional[CarType] = None  
    max_price: Optional[float] = None
    transmission: Optional[TransmissionType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class BookingRequest(BaseModel):
    car_id: int
    customer_name: str
    customer_email: str
    start_date: date
    end_date: date
    pickup_location: str

# ====================
# Event Sourcing Integration
# ====================

from database.event_store import event_service

# ====================
# API Endpoints (CQRS Pattern)
# ====================

@app.get("/")
async def root():
    """נקודת קצה ראשית - בדיקת תקינות השרת"""
    return {
        "message": "🚗 מערכת השכרת רכבים פעילה!",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """בדיקת בריאות השרת"""
    return {"status": "healthy", "service": "car-rental-api"}

# Query Endpoints (CQRS - Query Side)

@app.get("/api/cars", response_model=List[Car])
async def get_all_cars():
    """החזרת כל הרכבים במערכת"""
    cars_data = event_service.get_all_cars()
    cars = []
    for car_data in cars_data:
        # המרה למבנה Pydantic
        car = Car(**car_data)
        cars.append(car)
    return cars

@app.get("/api/cars/{car_id}", response_model=Car)
async def get_car_by_id(car_id: str):
    """קבלת פרטי רכב לפי ID"""
    car_data = event_service.get_car_by_id(car_id)
    if not car_data:
        raise HTTPException(status_code=404, detail="רכב לא נמצא")
    return Car(**car_data)

@app.post("/api/cars/search", response_model=List[Car])
async def search_cars(query: CarSearchQuery):
    """חיפוש רכבים לפי קריטריונים"""
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

@app.get("/api/stats/cars-by-type")
async def get_cars_stats():
    """סטטיסטיקות רכבים לפי סוג - לגרפים"""
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

@app.get("/api/stats/search-analytics")
async def get_search_analytics():
    """סטטיסטיקות חיפושים - לגרפים"""
    return event_service.get_search_statistics()

# Command Endpoints (CQRS - Command Side)

@app.post("/api/bookings")
async def create_booking(booking: BookingRequest):
    """יצירת הזמנה חדשה"""
    # בדיקת קיום הרכב
    car_data = event_service.get_car_by_id(str(booking.car_id))
    if not car_data:
        raise HTTPException(status_code=404, detail="רכב לא נמצא")
    
    car = Car(**car_data)
    if not car.available:
        raise HTTPException(status_code=400, detail="רכב לא זמין להזמנה")
    
    # חישוב מחיר כולל
    days = (booking.end_date - booking.start_date).days
    if days <= 0:
        raise HTTPException(status_code=400, detail="תאריכים לא תקינים")
    
    total_price = car.daily_rate * days
    
    # יצירת הזמנה במערכת Event Sourcing
    booking_id = event_service.create_booking({
        "car_id": booking.car_id,
        "customer_name": booking.customer_name,
        "customer_email": booking.customer_email,
        "start_date": booking.start_date.isoformat(),
        "end_date": booking.end_date.isoformat(),
        "pickup_location": booking.pickup_location,
        "total_price": total_price,
        "days": days
    })
    
    return {
        "booking_id": booking_id,
        "status": "confirmed",
        "car": car.make + " " + car.model,
        "customer": booking.customer_name,
        "dates": f"{booking.start_date} - {booking.end_date}",
        "days": days,
        "daily_rate": car.daily_rate,
        "total_price": total_price,
        "message": "🎉 ההזמנה אושרה בהצלחה!"
    }

if __name__ == "__main__":
    print("🚗 מפעיל שרת השכרת רכבים...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # התחדשות אוטומטית בפיתוח
        log_level="info"
    )