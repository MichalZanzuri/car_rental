import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Optional
import json
from datetime import datetime

class PostgreSQLDB:
    def __init__(self):
        self.connection_string = "postgresql://postgres:password123@localhost:5432/car_rental_db"
        try:
            self.engine = create_engine(self.connection_string)
            self.SessionLocal = sessionmaker(bind=self.engine)
            # בדיקת חיבור
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ חיבור PostgreSQL הצליח")
        except Exception as e:
            print(f"❌ שגיאה בחיבור PostgreSQL: {e}")
            raise
    
    # פונקציות רכבים
    def get_all_cars(self) -> List[Dict]:
        """קבלת כל הרכבים הזמינים"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM cars WHERE available = true ORDER BY id"))
            return [dict(row._mapping) for row in result]
    
    def get_car_by_id(self, car_id: str) -> Optional[Dict]:
        """קבלת רכב לפי ID"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM cars WHERE id = :id"), {"id": car_id})
            row = result.fetchone()
            return dict(row._mapping) if row else None
    
    def search_cars(self, filters: Dict) -> List[Dict]:
        """חיפוש רכבים לפי פילטרים"""
        query = "SELECT * FROM cars WHERE available = true"
        params = {}
        
        if filters.get('location'):
            query += " AND location ILIKE :location"
            params['location'] = f"%{filters['location']}%"
        
        if filters.get('car_type'):
            query += " AND car_type = :car_type"
            params['car_type'] = filters['car_type']
        
        if filters.get('max_price'):
            query += " AND daily_rate <= :max_price"
            params['max_price'] = filters['max_price']
        
        if filters.get('transmission'):
            query += " AND transmission = :transmission"
            params['transmission'] = filters['transmission']
        
        query += " ORDER BY daily_rate"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [dict(row._mapping) for row in result]
    
    def add_car(self, car_data: Dict) -> Optional[int]:
        """הוספת רכב חדש"""
        try:
            with self.engine.connect() as conn:
                features_json = json.dumps(car_data.get('features', []), ensure_ascii=False)
                
                result = conn.execute(text("""
                    INSERT INTO cars (make, model, year, car_type, transmission, daily_rate, 
                                     location, fuel_type, seats, features, available)
                    VALUES (:make, :model, :year, :car_type, :transmission, :daily_rate,
                            :location, :fuel_type, :seats, :features, :available)
                    RETURNING id
                """), {
                    'make': car_data['make'],
                    'model': car_data['model'], 
                    'year': car_data['year'],
                    'car_type': car_data['car_type'],
                    'transmission': car_data['transmission'],
                    'daily_rate': car_data['daily_rate'],
                    'location': car_data['location'],
                    'fuel_type': car_data['fuel_type'],
                    'seats': car_data['seats'],
                    'features': features_json,
                    'available': car_data.get('available', True)
                })
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(f"שגיאה בהוספת רכב: {e}")
            return None
    
    def update_car(self, car_id: int, update_data: Dict) -> bool:
        """עדכון רכב קיים"""
        try:
            if not update_data:
                return True
            
            # בניית שאילתת עדכון דינמית
            set_clauses = []
            params = {'car_id': car_id}
            
            for field, value in update_data.items():
                if field == 'features' and isinstance(value, list):
                    value = json.dumps(value, ensure_ascii=False)
                set_clauses.append(f"{field} = :{field}")
                params[field] = value
            
            # הוספת updated_at
            set_clauses.append("updated_at = :updated_at")
            params['updated_at'] = datetime.utcnow()
            
            query = f"UPDATE cars SET {', '.join(set_clauses)} WHERE id = :car_id"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            print(f"שגיאה בעדכון רכב: {e}")
            return False
    
    def delete_car(self, car_id: int) -> bool:
        """מחיקת רכב (סימון כלא זמין)"""
        return self.update_car(car_id, {'available': False})
    
    # פונקציות לקוחות
    def get_all_customers(self) -> List[Dict]:
        """קבלת כל הלקוחות"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM customers ORDER BY id"))
            return [dict(row._mapping) for row in result]
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Dict]:
        """קבלת לקוח לפי ID"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM customers WHERE id = :id"), {"id": customer_id})
            row = result.fetchone()
            return dict(row._mapping) if row else None
    
    def add_customer(self, customer_data: Dict) -> Optional[int]:
        """הוספת לקוח חדש"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO customers (first_name, last_name, email, phone, license_number, 
                                         date_of_birth, address)
                    VALUES (:first_name, :last_name, :email, :phone, :license_number,
                            :date_of_birth, :address)
                    RETURNING id
                """), {
                    'first_name': customer_data['first_name'],
                    'last_name': customer_data['last_name'],
                    'email': customer_data['email'],
                    'phone': customer_data.get('phone'),
                    'license_number': customer_data.get('license_number'),
                    'date_of_birth': customer_data.get('date_of_birth'),
                    'address': customer_data.get('address')
                })
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(f"שגיאה בהוספת לקוח: {e}")
            return None
    
    # פונקציות הזמנות
    def get_all_bookings(self) -> List[Dict]:
        """קבלת כל ההזמנות"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT b.*, c.make, c.model, cu.first_name, cu.last_name, cu.email
                FROM bookings b
                JOIN cars c ON b.car_id = c.id
                JOIN customers cu ON b.customer_id = cu.id
                ORDER BY b.created_at DESC
            """))
            return [dict(row._mapping) for row in result]
    
    def create_booking(self, booking_data: Dict) -> Optional[int]:
        """יצירת הזמנה חדשה"""
        try:
            with self.engine.connect() as conn:
                # צור לקוח אם לא קיים
                customer_result = conn.execute(text("""
                    INSERT INTO customers (first_name, last_name, email)
                    VALUES (:first_name, :last_name, :email)
                    ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                    RETURNING id
                """), {
                    'first_name': booking_data.get('customer_name', '').split()[0] if booking_data.get('customer_name') else 'Guest',
                    'last_name': booking_data.get('customer_name', '').split()[-1] if len(booking_data.get('customer_name', '').split()) > 1 else '',
                    'email': booking_data['customer_email']
                })
                customer_id = customer_result.fetchone()[0]
                
                # צור הזמנה
                result = conn.execute(text("""
                    INSERT INTO bookings (car_id, customer_id, start_date, end_date, 
                                        pickup_location, total_price, days)
                    VALUES (:car_id, :customer_id, :start_date, :end_date,
                            :pickup_location, :total_price, :days)
                    RETURNING id
                """), {
                    'car_id': booking_data['car_id'],
                    'customer_id': customer_id,
                    'start_date': booking_data['start_date'],
                    'end_date': booking_data['end_date'],
                    'pickup_location': booking_data['pickup_location'],
                    'total_price': booking_data['total_price'],
                    'days': booking_data['days']
                })
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(f"שגיאה ביצירת הזמנה: {e}")
            return None
    
    # פונקציות סטטיסטיקות
    def get_cars_by_type_stats(self) -> List[Dict]:
        """סטטיסטיקות רכבים לפי סוג"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT car_type as type, COUNT(*) as count 
                FROM cars 
                WHERE available = true
                GROUP BY car_type
                ORDER BY count DESC
            """))
            return [dict(row._mapping) for row in result]
    
    def get_booking_stats(self) -> Dict:
        """סטטיסטיקות הזמנות"""
        with self.engine.connect() as conn:
            # הזמנות לפי סטטוס
            status_result = conn.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM bookings 
                GROUP BY status
            """))
            
            # סכום הכנסות
            revenue_result = conn.execute(text("""
                SELECT SUM(total_price) as total_revenue,
                       AVG(total_price) as avg_booking_value,
                       COUNT(*) as total_bookings
                FROM bookings
            """))
            
            status_stats = [dict(row._mapping) for row in status_result]
            revenue_stats = dict(revenue_result.fetchone()._mapping) if revenue_result else {}
            
            return {
                "bookings_by_status": status_stats,
                "revenue_stats": revenue_stats
            }
    
    # פונקציות ניהול נתונים
    def log_search(self, query_params: Dict, results_count: int):
        """רישום חיפוש למטרות אנליטיקה"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO search_logs (query_params, results_count)
                    VALUES (:query_params, :results_count)
                """), {
                    'query_params': json.dumps(query_params, ensure_ascii=False),
                    'results_count': results_count
                })
                conn.commit()
        except Exception as e:
            print(f"שגיאה ברישום חיפוש: {e}")
    
    def log_ai_interaction(self, question: str, response: str, model: str, response_time: float):
        """רישום אינטראקציית AI"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO ai_interactions (user_question, ai_response, model_used, response_time)
                    VALUES (:question, :response, :model, :response_time)
                """), {
                    'question': question,
                    'response': response,
                    'model': model,
                    'response_time': response_time
                })
                conn.commit()
        except Exception as e:
            print(f"שגיאה ברישום AI: {e}")
    
    def clear_all_data(self):
        """ניקוי כל הנתונים (זהירות!)"""
        try:
            with self.engine.connect() as conn:
                # מחק בסדר נכון בגלל Foreign Keys
                conn.execute(text("DELETE FROM bookings"))
                conn.execute(text("DELETE FROM reviews"))
                conn.execute(text("DELETE FROM search_logs"))
                conn.execute(text("DELETE FROM ai_interactions"))
                conn.execute(text("DELETE FROM cars"))
                conn.execute(text("DELETE FROM customers"))
                conn.commit()
                print("כל הנתונים נמחקו")
        except Exception as e:
            print(f"שגיאה בניקוי נתונים: {e}")
    
    def get_search_statistics(self) -> Dict:
        """סטטיסטיקות חיפושים"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) as total_searches,
                           AVG(results_count) as avg_results,
                           DATE(timestamp) as search_date,
                           COUNT(*) as daily_searches
                    FROM search_logs
                    GROUP BY DATE(timestamp)
                    ORDER BY search_date DESC
                    LIMIT 30
                """))
                return {
                    "daily_searches": [dict(row._mapping) for row in result],
                    "total": 0
                }
        except Exception as e:
            print(f"שגיאה בסטטיסטיקות חיפוש: {e}")
            return {"daily_searches": [], "total": 0}

# יצירת instance גלובלי
db = PostgreSQLDB()