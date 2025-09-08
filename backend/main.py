"""
שרת FastAPI עיקרי למערכת השכרת רכבים
מממש תבנית CQRS ו-Gateway עם PostgreSQL
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, date
import uvicorn

# יצירת אפליקציית FastAPI
app = FastAPI(
    title="Car Rental System API",
    description="מערכת ניהול השכרת רכבים עם PostgreSQL",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# יבוא הrouters והוספתם
from api.commands.car_commands import router as commands_router
from api.queries.car_queries import router as queries_router
from api.auth_endpoints import router as auth_router

app.include_router(commands_router)
app.include_router(queries_router)
app.include_router(auth_router)

# הוספת Admin router
try:
    from api.admin_endpoints import router as admin_router
    app.include_router(admin_router)
    print("✅ Admin Router נטען בהצלחה")
except ImportError as e:
    print(f"⚠️ Admin Router לא זמין: {e}")

# הוספת AI router
try:
    from api.ai_endpoints import router as ai_router
    app.include_router(ai_router)
    print("✅ AI Router נטען בהצלחה")
except ImportError as e:
    print(f"⚠️ AI Router לא זמין: {e}")

# הגדרת CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # בפרודקשיון נשנה את זה
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================
# חיבור לבסיס הנתונים PostgreSQL
# ====================

try:
    from database.postgres_connection import db
    print("✅ חיבור PostgreSQL נטען בהצלחה")
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ PostgreSQL לא זמין: {e}")
    print("💡 ודא שDocker רץ ושהחבילות psycopg2-binary ו-sqlalchemy מותקנות")
    DATABASE_AVAILABLE = False
    
    # חיבור חלופי ל-Event Store
    try:
        from database.event_store import event_service
        print("🔄 משתמש ב-Event Store כחלופה")
    except ImportError:
        print("❌ אין חיבור לבסיס נתונים")

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
    FAMILY = "family"

class TransmissionType(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"

class Car(BaseModel):
    id: int
    make: str  # יצרן
    model: str  # דגם
    year: int
    car_type: str
    transmission: str
    daily_rate: float  # מחיר יומי
    available: bool
    location: str
    fuel_type: str
    seats: int
    image_url: Optional[str] = None
    features: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CarSearchQuery(BaseModel):
    location: Optional[str] = None
    car_type: Optional[str] = None
    max_price: Optional[float] = None
    transmission: Optional[str] = None
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
# פונקציות עזר לבסיס הנתונים
# ====================

def get_database_service():
    """החזרת שירות בסיס הנתונים הזמין"""
    if DATABASE_AVAILABLE:
        return db
    else:
        return event_service

# ====================
# API Endpoints (CQRS Pattern)
# ====================

@app.get("/")
async def root():
    """נקודת קצה ראשית - בדיקת תקינות השרת"""
    return {
        "message": "🚗 מערכת השכרת רכבים פעילה!",
        "status": "running",
        "database": "PostgreSQL" if DATABASE_AVAILABLE else "Event Store",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """בדיקת בריאות השרת"""
    return {
        "status": "healthy", 
        "service": "car-rental-api",
        "database": "PostgreSQL" if DATABASE_AVAILABLE else "Event Store"
    }

# Query Endpoints (CQRS - Query Side)

@app.get("/api/cars", response_model=List[Car])
async def get_all_cars():
    """החזרת כל הרכבים במערכת"""
    try:
        db_service = get_database_service()
        cars_data = db_service.get_all_cars()
        
        cars = []
        for car_data in cars_data:
            # טיפול בתכונות JSON
            if 'features' in car_data and isinstance(car_data['features'], str):
                try:
                    import json
                    car_data['features'] = json.loads(car_data['features'])
                except:
                    car_data['features'] = []
            
            # המרה למבנה Pydantic
            car = Car(**car_data)
            cars.append(car)
        
        return cars
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת רכבים: {str(e)}")

@app.get("/api/cars/{car_id}", response_model=Car)
async def get_car_by_id(car_id: str):
    """קבלת פרטי רכב לפי ID"""
    try:
        db_service = get_database_service()
        car_data = db_service.get_car_by_id(car_id)
        
        if not car_data:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        
        # טיפול בתכונות JSON
        if 'features' in car_data and isinstance(car_data['features'], str):
            try:
                import json
                car_data['features'] = json.loads(car_data['features'])
            except:
                car_data['features'] = []
        
        return Car(**car_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת רכב: {str(e)}")

@app.post("/api/cars/search", response_model=List[Car])
async def search_cars(query: CarSearchQuery):
    """חיפוש רכבים לפי קריטריונים"""
    try:
        db_service = get_database_service()
        
        # המרת query ל-dict לDB
        filters = {}
        if query.location:
            filters['location'] = query.location
        if query.car_type:
            filters['car_type'] = query.car_type
        if query.max_price:
            filters['max_price'] = query.max_price
        if query.transmission:
            filters['transmission'] = query.transmission
        
        # חיפוש ברכבים
        if DATABASE_AVAILABLE:
            cars_data = db_service.search_cars(filters)
        else:
            # חיפוש ב-Event Store
            all_cars = db_service.get_all_cars()
            cars_data = []
            
            for car_data in all_cars:
                # בדיקת זמינות
                if not car_data.get('available', True):
                    continue
                
                # סינון לפי מיקום
                if query.location and query.location.lower() not in car_data.get('location', '').lower():
                    continue
                
                # סינון לפי סוג רכב
                if query.car_type and car_data.get('car_type') != query.car_type:
                    continue
                
                # סינון לפי מחיר מקסימלי
                if query.max_price and car_data.get('daily_rate', 0) > query.max_price:
                    continue
                
                # סינון לפי תיבת הילוכים
                if query.transmission and car_data.get('transmission') != query.transmission:
                    continue
                
                cars_data.append(car_data)
        
        # המרה לרשימת Car objects
        cars = []
        for car_data in cars_data:
            # טיפול בתכונות JSON
            if 'features' in car_data and isinstance(car_data['features'], str):
                try:
                    import json
                    car_data['features'] = json.loads(car_data['features'])
                except:
                    car_data['features'] = []
            
            cars.append(Car(**car_data))
        
        # רישום פעולת חיפוש
        if hasattr(db_service, 'log_search'):
            query_dict = query.dict(exclude_unset=True)
            db_service.log_search(query_dict, len(cars))
        
        return cars
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בחיפוש רכבים: {str(e)}")

@app.get("/api/stats/cars-by-type")
async def get_cars_stats():
    """סטטיסטיקות רכבים לפי סוג - לגרפים"""
    try:
        db_service = get_database_service()
        
        if DATABASE_AVAILABLE:
            # שימוש בפונקציית סטטיסטיקות של PostgreSQL
            stats_data = db_service.get_cars_by_type_stats()
        else:
            # חישוב סטטיסטיקות מ-Event Store
            cars = db_service.get_all_cars()
            from collections import Counter
            type_counts = Counter([car.get("car_type", "unknown") for car in cars])
            stats_data = [
                {"type": car_type, "count": count} 
                for car_type, count in type_counts.items()
            ]
        
        return {
            "data": stats_data,
            "total_cars": sum(item["count"] for item in stats_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקבלת סטטיסטיקות: {str(e)}")

@app.get("/api/stats/search-analytics")
async def get_search_analytics():
    """סטטיסטיקות חיפושים - לגרפים"""
    try:
        db_service = get_database_service()
        
        if hasattr(db_service, 'get_search_statistics'):
            return db_service.get_search_statistics()
        else:
            return {"searches": [], "total": 0, "message": "אנליטיקות חיפוש לא זמינות"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה באנליטיקות: {str(e)}")

# Command Endpoints (CQRS - Command Side)

@app.post("/api/bookings")
async def create_booking(booking: BookingRequest):
    """יצירת הזמנה חדשה"""
    try:
        db_service = get_database_service()
        
        # בדיקת קיום הרכב
        car_data = db_service.get_car_by_id(str(booking.car_id))
        if not car_data:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        
        # טיפול בתכונות JSON
        if 'features' in car_data and isinstance(car_data['features'], str):
            try:
                import json
                car_data['features'] = json.loads(car_data['features'])
            except:
                car_data['features'] = []
        
        car = Car(**car_data)
        if not car.available:
            raise HTTPException(status_code=400, detail="רכב לא זמין להזמנה")
        
        # חישוב מחיר כולל
        days = (booking.end_date - booking.start_date).days
        if days <= 0:
            raise HTTPException(status_code=400, detail="תאריכים לא תקינים")
        
        total_price = car.daily_rate * days
        
        # יצירת הזמנה
        booking_data = {
            "car_id": booking.car_id,
            "customer_name": booking.customer_name,
            "customer_email": booking.customer_email,
            "start_date": booking.start_date.isoformat(),
            "end_date": booking.end_date.isoformat(),
            "pickup_location": booking.pickup_location,
            "total_price": total_price,
            "days": days
        }
        
        if hasattr(db_service, 'create_booking'):
            booking_id = db_service.create_booking(booking_data)
        else:
            # שימוש ב-event service
            booking_id = db_service.create_booking(booking_data)
        
        return {
            "booking_id": booking_id,
            "status": "confirmed",
            "car": f"{car.make} {car.model}",
            "customer": booking.customer_name,
            "dates": f"{booking.start_date} - {booking.end_date}",
            "days": days,
            "daily_rate": car.daily_rate,
            "total_price": total_price,
            "message": "🎉 ההזמנה אושרה בהצלחה!"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה ביצירת הזמנה: {str(e)}")

@app.get("/api/database-info")
async def get_database_info():
    """מידע על בסיס הנתונים בשימוש"""
    return {
        "database_type": "PostgreSQL" if DATABASE_AVAILABLE else "Event Store",
        "available": DATABASE_AVAILABLE,
        "connection_status": "connected" if DATABASE_AVAILABLE else "using_fallback",
        "docker_required": DATABASE_AVAILABLE
    }

if __name__ == "__main__":
    print("🚗 מפעיל שרת השכרת רכבים...")
    print(f"📊 בסיס נתונים: {'PostgreSQL' if DATABASE_AVAILABLE else 'Event Store'}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # התחדשות אוטומטית בפיתוח
        log_level="info"
    )