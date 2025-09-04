"""
CQRS Commands - פקודות לשינוי מצב המערכת
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sys
import os

# הוספת נתיב לחיפוש מודולים
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.event_store import event_service, EventType, Event

router = APIRouter(prefix="/api/commands", tags=["Commands"])

# ====================
# Command Models
# ====================

class AddCarCommand(BaseModel):
    make: str
    model: str
    year: int
    car_type: str  # economy, compact, midsize, fullsize, luxury, suv
    transmission: str  # automatic, manual
    daily_rate: float
    location: str
    fuel_type: str
    seats: int
    image_url: Optional[str] = None

class UpdateCarCommand(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    car_type: Optional[str] = None
    transmission: Optional[str] = None
    daily_rate: Optional[float] = None
    location: Optional[str] = None
    fuel_type: Optional[str] = None
    seats: Optional[int] = None
    image_url: Optional[str] = None
    available: Optional[bool] = None

class BookingCommand(BaseModel):
    car_id: str
    customer_name: str
    customer_email: str
    start_date: str
    end_date: str
    pickup_location: str

# ====================
# Command Handlers
# ====================

@router.post("/cars")
async def add_car(command: AddCarCommand):
    """הוספת רכב חדש למערכת"""
    try:
        car_data = command.dict()
        car_data["available"] = True  # רכב חדש תמיד זמין
        
        car_id = event_service.add_car(car_data, user_id="admin")
        
        if car_id:
            return {
                "success": True,
                "message": "רכב נוסף בהצלחה",
                "car_id": car_id
            }
        else:
            raise HTTPException(status_code=500, detail="שגיאה בהוספת הרכב")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה: {str(e)}")

@router.put("/cars/{car_id}")
async def update_car(car_id: str, command: UpdateCarCommand):
    """עדכון פרטי רכב"""
    try:
        # בדיקה שהרכב קיים
        existing_car = event_service.get_car_by_id(car_id)
        if not existing_car:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        
        # יצירת נתוני עדכון
        update_data = command.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.now().isoformat()
            
            # יצירת אירוע עדכון
            from database.event_store import Event
            event = Event(
                event_type=EventType.CAR_UPDATED,
                aggregate_id=car_id,
                data=update_data,
                user_id="admin"
            )
            
            if event_service.event_store.append_event(event):
                return {
                    "success": True,
                    "message": "רכב עודכן בהצלחה",
                    "car_id": car_id
                }
        
        raise HTTPException(status_code=400, detail="אין נתונים לעדכון")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.delete("/cars/{car_id}")
async def delete_car(car_id: str):
    """מחיקת רכב מהמערכת"""
    try:
        # בדיקה שהרכב קיים
        existing_car = event_service.get_car_by_id(car_id)
        if not existing_car:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        
        # יצירת אירוע מחיקה
        from database.event_store import Event
        delete_data = {"deleted_at": datetime.now().isoformat()}
        event = Event(
            event_type=EventType.CAR_DELETED,
            aggregate_id=car_id,
            data=delete_data,
            user_id="admin"
        )
        
        if event_service.event_store.append_event(event):
            return {
                "success": True,
                "message": "רכב נמחק בהצלחה",
                "car_id": car_id
            }
        
        raise HTTPException(status_code=500, detail="שגיאה במחיקת הרכב")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")

@router.post("/bookings")
async def create_booking(command: BookingCommand):
    """יצירת הזמנה חדשה"""
    try:
        # בדיקה שהרכב קיים וזמין
        car = event_service.get_car_by_id(command.car_id)
        if not car:
            raise HTTPException(status_code=404, detail="רכב לא נמצא")
        
        if not car.get("available", False):
            raise HTTPException(status_code=400, detail="רכב לא זמין להזמנה")
        
        # חישוב מחיר כולל
        from datetime import datetime
        start_date = datetime.fromisoformat(command.start_date)
        end_date = datetime.fromisoformat(command.end_date)
        days = (end_date - start_date).days
        
        if days <= 0:
            raise HTTPException(status_code=400, detail="תאריכים לא תקינים")
        
        total_price = car["daily_rate"] * days
        
        # יצירת נתוני הזמנה
        booking_data = command.dict()
        booking_data.update({
            "days": days,
            "daily_rate": car["daily_rate"],
            "total_price": total_price,
            "status": "confirmed",
            "created_at": datetime.now().isoformat()
        })
        
        # יצירת אירוע הזמנה
        from database.event_store import Event
        import uuid
        booking_id = str(uuid.uuid4())
        
        event = Event(
            event_type=EventType.BOOKING_CREATED,
            aggregate_id=booking_id,
            data=booking_data,
            user_id=command.customer_email
        )
        
        if event_service.event_store.append_event(event):
            return {
                "success": True,
                "booking_id": booking_id,
                "status": "confirmed",
                "car": f"{car['make']} {car['model']}",
                "customer": command.customer_name,
                "dates": f"{command.start_date} - {command.end_date}",
                "days": days,
                "daily_rate": car["daily_rate"],
                "total_price": total_price,
                "message": "ההזמנה אושרה בהצלחה!"
            }
        
        raise HTTPException(status_code=500, detail="שגיאה ביצירת ההזמנה")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")