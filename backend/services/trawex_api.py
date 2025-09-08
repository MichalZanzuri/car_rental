"""
שירות חיבור ל-Trawex Car Rental API דרך RapidAPI
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, date
import os

class TrawexCarRentalAPI:
    """ממשק ל-Trawex Car Rental API"""
    
    def __init__(self):
        # הגדרת API credentials
        self.api_key = "96c6526bb5msh30dddd7cd3fb1c2p162bdejsn837cfaf14169"  # המפתח שלך
        self.api_host = "trawex-car-rental.p.rapidapi.com"
        self.base_url = "https://trawex-car-rental.p.rapidapi.com"
        
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host,
            "Content-Type": "application/json"
        }
    
    def search_cars(self, pickup_location: str, pickup_date: str, return_date: str, 
                   pickup_time: str = "10:00", return_time: str = "10:00") -> List[Dict]:
        """חיפוש רכבים זמינים"""
        try:
            url = f"{self.base_url}/search"
            
            params = {
                "pickup_location": pickup_location,
                "pickup_date": pickup_date,  # YYYY-MM-DD
                "pickup_time": pickup_time,   # HH:MM
                "return_date": return_date,   # YYYY-MM-DD
                "return_time": return_time,   # HH:MM
                "currency": "ILS"  # שקלים
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self.process_car_results(data)
            else:
                print(f"שגיאה בחיפוש רכבים: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"שגיאה בקריאה ל-Trawex API: {e}")
            return []
    
    def get_car_details(self, car_id: str) -> Optional[Dict]:
        """קבלת פרטי רכב ספציפי"""
        try:
            url = f"{self.base_url}/car-details/{car_id}"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"שגיאה בקבלת פרטי רכב: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"שגיאה בקבלת פרטי רכב: {e}")
            return None
    
    def get_locations(self, query: str = "") -> List[Dict]:
        """קבלת רשימת מיקומים זמינים"""
        try:
            url = f"{self.base_url}/locations"
            
            params = {}
            if query:
                params["query"] = query
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json().get("locations", [])
            else:
                print(f"שגיאה בקבלת מיקומים: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"שגיאה בקבלת מיקומים: {e}")
            return []
    
    def create_booking(self, booking_data: Dict) -> Optional[Dict]:
        """יצירת הזמנה חדשה"""
        try:
            url = f"{self.base_url}/booking"
            
            response = requests.post(url, headers=self.headers, json=booking_data, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"שגיאה ביצירת הזמנה: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"שגיאה ביצירת הזמנה: {e}")
            return None
    
    def process_car_results(self, api_data: Dict) -> List[Dict]:
        """עיבוד נתוני רכבים מה-API לפורמט הפנימי"""
        processed_cars = []
        
        cars = api_data.get("cars", [])
        
        for car in cars:
            processed_car = {
                "id": car.get("id", ""),
                "make": car.get("make", ""),
                "model": car.get("model", ""),
                "year": car.get("year", 2023),
                "car_type": self.map_car_category(car.get("category", "")),
                "transmission": car.get("transmission", "automatic"),
                "daily_rate": float(car.get("price", {}).get("amount", 0)),
                "location": car.get("pickup_location", ""),
                "fuel_type": car.get("fuel_type", "gasoline"),
                "seats": car.get("passengers", 5),
                "available": True,
                "features": car.get("features", []),
                "image_url": car.get("image", ""),
                "supplier": car.get("supplier", ""),
                "external_api": "trawex"  # סימון שזה מ-API חיצוני
            }
            processed_cars.append(processed_car)
        
        return processed_cars
    
    def map_car_category(self, api_category: str) -> str:
        """המרת קטגוריות מה-API לפורמט הפנימי"""
        category_mapping = {
            "ECAR": "economy",
            "CCAR": "compact", 
            "ICAR": "intermediate",
            "SCAR": "standard",
            "FCAR": "family",
            "PCAR": "premium",
            "LCAR": "luxury",
            "XCAR": "executive"
        }
        
        return category_mapping.get(api_category.upper(), "economy")
    
    def test_connection(self) -> bool:
        """בדיקת חיבור ל-API"""
        try:
            url = f"{self.base_url}/locations"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False

# יצירת instance גלובלי
trawex_api = TrawexCarRentalAPI()

# פונקציות עזר לשימוש ב-endpoints
def search_external_cars(pickup_location: str, pickup_date: str, return_date: str, 
                         pickup_time: str = "10:00", return_time: str = "10:00") -> List[Dict]:
    """חיפוש רכבים מ-API חיצוני"""
    return trawex_api.search_cars(pickup_location, pickup_date, return_date, pickup_time, return_time)

def get_external_locations(query: str = "") -> List[Dict]:
    """קבלת מיקומים מ-API חיצוני"""
    return trawex_api.get_locations(query)

def create_external_booking(booking_data: Dict) -> Optional[Dict]:
    """יצירת הזמנה ב-API חיצוני"""
    return trawex_api.create_booking(booking_data)

def test_external_api() -> bool:
    """בדיקת זמינות API חיצוני"""
    return trawex_api.test_connection()