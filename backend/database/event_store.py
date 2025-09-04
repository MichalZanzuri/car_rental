"""
Event Sourcing Database Implementation
מממש מסד נתונים מבוסס אירועים
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import os

class EventType(str, Enum):
    CAR_ADDED = "car_added"
    CAR_UPDATED = "car_updated"
    CAR_DELETED = "car_deleted"
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_UPDATED = "user_updated"
    USER_PASSWORD_CHANGED = "user_password_changed"
    USER_LOCKED = "user_locked"
    USER_DELETED = "user_deleted"
    SEARCH_PERFORMED = "search_performed"

class Event:
    """אירוע במערכת"""
    def __init__(self, event_type: EventType, aggregate_id: str, data: Dict[Any, Any], user_id: str = None):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.aggregate_id = aggregate_id
        self.data = data
        self.user_id = user_id
        self.timestamp = datetime.now()
        self.version = 1

class EventStore:
    """מחלקה לניהול Event Store"""
    
    def __init__(self, db_path: str = "car_rental_events.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """יצירת מבנה הדאטהבייס"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # טבלת אירועים
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    user_id TEXT,
                    timestamp TEXT NOT NULL,
                    version INTEGER NOT NULL
                )
            """)
            
            # טבלת snapshots (לביצועים)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    aggregate_id TEXT PRIMARY KEY,
                    aggregate_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # אינדקסים לביצועים
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aggregate_id ON events(aggregate_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
            
            conn.commit()
    
    def append_event(self, event: Event) -> bool:
        """הוספת אירוע למסד הנתונים"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO events (event_id, event_type, aggregate_id, data, user_id, timestamp, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.event_type.value,
                    event.aggregate_id,
                    json.dumps(event.data, ensure_ascii=False),
                    event.user_id,
                    event.timestamp.isoformat(),
                    event.version
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"שגיאה בהוספת אירוע: {e}")
            return False
    
    def get_events(self, aggregate_id: str) -> List[Event]:
        """קבלת כל האירועים של aggregate מסויים"""
        events = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT event_id, event_type, aggregate_id, data, user_id, timestamp, version
                    FROM events 
                    WHERE aggregate_id = ?
                    ORDER BY timestamp
                """, (aggregate_id,))
                
                for row in cursor.fetchall():
                    event = Event(
                        event_type=EventType(row[1]),
                        aggregate_id=row[2],
                        data=json.loads(row[3])
                    )
                    event.event_id = row[0]
                    event.user_id = row[4]
                    event.timestamp = datetime.fromisoformat(row[5])
                    event.version = row[6]
                    events.append(event)
                    
        except Exception as e:
            print(f"שגיאה בקבלת אירועים: {e}")
            
        return events
    
    def get_all_events(self, event_type: EventType = None) -> List[Event]:
        """קבלת כל האירועים במערכת"""
        events = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if event_type:
                    cursor.execute("""
                        SELECT event_id, event_type, aggregate_id, data, user_id, timestamp, version
                        FROM events 
                        WHERE event_type = ?
                        ORDER BY timestamp DESC
                    """, (event_type.value,))
                else:
                    cursor.execute("""
                        SELECT event_id, event_type, aggregate_id, data, user_id, timestamp, version
                        FROM events 
                        ORDER BY timestamp DESC
                    """)
                
                for row in cursor.fetchall():
                    event = Event(
                        event_type=EventType(row[1]),
                        aggregate_id=row[2],
                        data=json.loads(row[3])
                    )
                    event.event_id = row[0]
                    event.user_id = row[4]
                    event.timestamp = datetime.fromisoformat(row[5])
                    event.version = row[6]
                    events.append(event)
                    
        except Exception as e:
            print(f"שגיאה בקבלת אירועים: {e}")
            
        return events

class CarAggregate:
    """אגרגט רכב - בונה את מצב הרכב מהאירועים"""
    
    def __init__(self, car_id: str):
        self.car_id = car_id
        self.make = ""
        self.model = ""
        self.year = 0
        self.car_type = ""
        self.transmission = ""
        self.daily_rate = 0.0
        self.available = True
        self.location = ""
        self.fuel_type = ""
        self.seats = 0
        self.image_url = None
        self.created_at = None
        self.updated_at = None
        self.deleted = False
    
    def apply_event(self, event: Event):
        """יישום אירוע על האגרגט"""
        if event.event_type == EventType.CAR_ADDED:
            self._apply_car_added(event.data)
        elif event.event_type == EventType.CAR_UPDATED:
            self._apply_car_updated(event.data)
        elif event.event_type == EventType.CAR_DELETED:
            self._apply_car_deleted(event.data)
    
    def _apply_car_added(self, data):
        self.make = data.get("make", "")
        self.model = data.get("model", "")
        self.year = data.get("year", 0)
        self.car_type = data.get("car_type", "")
        self.transmission = data.get("transmission", "")
        self.daily_rate = data.get("daily_rate", 0.0)
        self.available = data.get("available", True)
        self.location = data.get("location", "")
        self.fuel_type = data.get("fuel_type", "")
        self.seats = data.get("seats", 0)
        self.image_url = data.get("image_url")
        self.created_at = data.get("created_at")
    
    def _apply_car_updated(self, data):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = data.get("updated_at")
    
    def _apply_car_deleted(self, data):
        self.deleted = True
        self.available = False
    
    def to_dict(self):
        """המרה למילון"""
        return {
            "id": self.car_id,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "car_type": self.car_type,
            "transmission": self.transmission,
            "daily_rate": self.daily_rate,
            "available": self.available,
            "location": self.location,
            "fuel_type": self.fuel_type,
            "seats": self.seats,
            "image_url": self.image_url
        }

class EventSourcingService:
    """שירות ניהול Event Sourcing"""
    
    def __init__(self):
        self.event_store = EventStore()
        self._init_sample_data()
    
    def _init_sample_data(self):
        """יצירת נתונים לדוגמא אם הדאטהבייס ריקה"""
        existing_events = self.event_store.get_all_events()
        if len(existing_events) == 0:
            self._create_sample_cars()
    
    def _create_sample_cars(self):
        """יצירת רכבים לדוגמא"""
        sample_cars = [
            {
                "id": "car-1", "make": "טויוטה", "model": "קורולה", "year": 2023,
                "car_type": "compact", "transmission": "automatic", "daily_rate": 180.0,
                "location": "תל אביב", "fuel_type": "בנזין", "seats": 5
            },
            {
                "id": "car-2", "make": "הונדה", "model": "סיויק", "year": 2022,
                "car_type": "compact", "transmission": "manual", "daily_rate": 160.0,
                "location": "חיפה", "fuel_type": "בנזין", "seats": 5
            },
            {
                "id": "car-3", "make": "BMW", "model": "X3", "year": 2024,
                "car_type": "suv", "transmission": "automatic", "daily_rate": 450.0,
                "location": "ירושלים", "fuel_type": "היברידי", "seats": 7
            },
            {
                "id": "car-4", "make": "מרצדס", "model": "C-Class", "year": 2023,
                "car_type": "luxury", "transmission": "automatic", "daily_rate": 380.0,
                "location": "תל אביב", "fuel_type": "בנזין", "seats": 5
            }
        ]
        
        for car_data in sample_cars:
            car_id = car_data.pop("id")
            car_data["created_at"] = datetime.now().isoformat()
            event = Event(
                event_type=EventType.CAR_ADDED,
                aggregate_id=car_id,
                data=car_data,
                user_id="system"
            )
            self.event_store.append_event(event)
    
    def add_car(self, car_data: Dict, user_id: str = "system") -> str:
        """הוספת רכב חדש"""
        car_id = str(uuid.uuid4())
        car_data["created_at"] = datetime.now().isoformat()
        
        event = Event(
            event_type=EventType.CAR_ADDED,
            aggregate_id=car_id,
            data=car_data,
            user_id=user_id
        )
        
        if self.event_store.append_event(event):
            return car_id
        return None
    
    def get_all_cars(self) -> List[Dict]:
        """קבלת כל הרכבים הפעילים"""
        cars = []
        
        # קבלת כל אירועי הרכבים
        car_events = self.event_store.get_all_events(EventType.CAR_ADDED)
        car_ids = set(event.aggregate_id for event in car_events)
        
        for car_id in car_ids:
            car = self._rebuild_car_from_events(car_id)
            if car and not car.deleted:
                cars.append(car.to_dict())
        
        return cars
    
    def get_car_by_id(self, car_id: str) -> Optional[Dict]:
        """קבלת רכב לפי ID"""
        car = self._rebuild_car_from_events(car_id)
        if car and not car.deleted:
            return car.to_dict()
        return None
    
    def _rebuild_car_from_events(self, car_id: str) -> Optional[CarAggregate]:
        """בנייה מחדש של רכב מהאירועים"""
        events = self.event_store.get_events(car_id)
        if not events:
            return None
        
        car = CarAggregate(car_id)
        for event in events:
            car.apply_event(event)
        
        return car
    
    def log_search(self, query_data: Dict, results_count: int, user_id: str = "anonymous"):
        """רישום פעולת חיפוש"""
        search_data = {
            "query": query_data,
            "results_count": results_count,
            "timestamp": datetime.now().isoformat()
        }
        
        event = Event(
            event_type=EventType.SEARCH_PERFORMED,
            aggregate_id=f"search-{uuid.uuid4()}",
            data=search_data,
            user_id=user_id
        )
        
        self.event_store.append_event(event)
    
    def get_search_statistics(self) -> Dict:
        """קבלת סטטיסטיקות חיפושים"""
        search_events = self.event_store.get_all_events(EventType.SEARCH_PERFORMED)
        
        total_searches = len(search_events)
        popular_locations = {}
        popular_car_types = {}
        
        for event in search_events:
            query = event.data.get("query", {})
            
            location = query.get("location")
            if location:
                popular_locations[location] = popular_locations.get(location, 0) + 1
            
            car_type = query.get("car_type")
            if car_type:
                popular_car_types[car_type] = popular_car_types.get(car_type, 0) + 1
        
        return {
            "total_searches": total_searches,
            "popular_locations": popular_locations,
            "popular_car_types": popular_car_types,
            "recent_searches": search_events[:10]  # 10 חיפושים אחרונים
        }

# יצירת instance גלובלי
event_service = EventSourcingService()