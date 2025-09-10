"""
RAG Service עם Ollama למערכת השכרת רכבים - משולב עם מאגר הרכבים
"""
import json
import requests
import re
from typing import Dict, List, Optional
import os
import sys

# הוספת נתיב לחיפוש מודולים
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

class CarRentalRAG:
    """RAG System למערכת השכרת רכבים עם Ollama ומאגר רכבים"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model_name = "gemma:2b"
        self.knowledge_base = self.load_car_knowledge()
        self.is_initialized = self.check_ollama_status()
        
        # בדיקת זמינות בסיס נתונים
        self.db_available = True
        print("RAG Service: גישה לבסיס נתונים זמינה")
    
    def check_ollama_status(self) -> bool:
        """בדיקה שOllama רץ ויש מודל זמין"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print(f"Ollama לא זמין - סטטוס: {response.status_code}")
                return False
            
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            
            if not available_models:
                print("אין מודלים זמינים ב-Ollama")
                return False
            
            if "gemma:2b" in available_models:
                self.model_name = "gemma:2b"
            elif "phi:latest" in available_models:
                self.model_name = "phi"
            elif "llama2:latest" in available_models:
                self.model_name = "llama2"
            else:
                self.model_name = available_models[0].split(":")[0]
            print(f"Ollama מוכן עם מודל: {self.model_name}")
            return True
            
        except Exception as e:
            print(f"שגיאה בחיבור ל-Ollama: {e}")
            return False
    
    def load_car_knowledge(self) -> str:
        """מסד ידע כטקסט מובנה"""
        return """
מסד ידע השכרת רכבים:

סוגי רכבים:
- Economy: טויוטה קורולה, הונדה סיויק. מחיר 100-180 ש״ח ליום. מתאים לזוגות, נסיעות קצרות, תקציב מוגבל.
- Family: טויוטה RAV4, הונדה CR-V, מאזדה CX-5. מחיר 200-300 ש״ח ליום. מתאים למשפחות עם ילדים, טיולים.
- Luxury: BMW X3, מרצדס GLC, אאודי Q5. מחיר 400-600 ש״ח ליום. מתאים לאירועים מיוחדים, לקוחות עסקיים.
- Commercial: פורד טרנזיט, מרצדס ספרינטר. מחיר 150-250 ש״ח ליום. מתאים להובלות, עסקים.

סוגי ביטוח:
- ביטוח בסיסי: ביטוח חובה וצד ג׳ בלבד. כלול במחיר. השתתפות עצמית 3000-5000 ש״ח.
- ביטוח מקיף: כולל נזק עצמי. עלות 30-70 ש״ח ליום. השתתפות עצמית 1500-2500 ש״ח.
- ביטוח פרמיום: כיסוי מלא ללא השתתפות עצמית. עלות 80-120 ש״ח ליום.

טיפי חיסכון:
- הזמנה מראש חוסכת עד 30%
- רכבי Economy חוסכים 40-60% מרכבי פרמיום
- השכירות ארוכות זולות יותר ליום
- הימנעות מתוספות יקרות כמו GPS

טיפי נהיגה:
בקיץ: בדוק מזגן, שתה מים, השאיר ברכב בצל
בחורף: חמם רכב לפני נסיעה, נהג לאט בגשם, השתמש באורות

דרישות:
- גיל מינימום 21 שנים
- רישיון נהיגה בתוקף לפחות שנה
- כרטיס אשראי על שם הנהג
- תיירים צריכים רישיון בינלאומי
        """
    
    def get_available_cars(self) -> List[Dict]:
        """קבלת כל הרכבים הזמינים - עם fallback לנתוני דמו"""
        try:
            # ניסיון ראשון - חיבור לשרת עם timeout ארוך יותר
            response = requests.get("http://localhost:8000/api/cars/all-sources", timeout=30)
            if response.status_code == 200:
                data = response.json()
                cars = data.get("cars", [])
                if cars:
                    print(f"נמצאו {len(cars)} רכבים זמינים במערכת")
                    return cars
        except Exception as e:
            print(f"שגיאה בחיבור לAPI: {e}")
        
        # Fallback - נתוני דמו אמינים
        print("משתמש בנתוני דמו")
        return self._get_demo_cars()
    
    def _get_demo_cars(self) -> List[Dict]:
        """נתוני דמו אמינים של רכבים"""
        return [
            {"id": 1, "make": "Toyota", "model": "Corolla", "year": 2023, "car_type": "economy", 
             "daily_rate": 180, "location": "תל אביב", "source": "מקומי", "available": True, "seats": 5},
            {"id": 2, "make": "Honda", "model": "CR-V", "year": 2023, "car_type": "family", 
             "daily_rate": 250, "location": "ירושלים", "source": "מקומי", "available": True, "seats": 7},
            {"id": 3, "make": "BMW", "model": "X3", "year": 2023, "car_type": "luxury", 
             "daily_rate": 450, "location": "חיפה", "source": "מקומי", "available": True, "seats": 5},
            {"id": 4, "make": "Mazda", "model": "CX-5", "year": 2022, "car_type": "suv", 
             "daily_rate": 280, "location": "תל אביב", "source": "מקומי", "available": True, "seats": 5},
            {"id": 5, "make": "Hyundai", "model": "i30", "year": 2023, "car_type": "compact", 
             "daily_rate": 160, "location": "באר שבע", "source": "מקומי", "available": True, "seats": 5},
            
            # רכבים חיצוניים
            {"id": 101, "make": "Hertz", "model": "Altima", "year": 2023, "car_type": "family", 
             "daily_rate": 220, "location": "Ben Gurion Airport", "source": "חיצוני", "available": True, "seats": 5},
            {"id": 102, "make": "Avis", "model": "Civic", "year": 2022, "car_type": "compact", 
             "daily_rate": 165, "location": "תל אביב", "source": "חיצוני", "available": True, "seats": 5},
            {"id": 103, "make": "Budget", "model": "Escape", "year": 2023, "car_type": "suv", 
             "daily_rate": 290, "location": "ירושלים", "source": "חיצוני", "available": True, "seats": 7},
            {"id": 104, "make": "Enterprise", "model": "Camry", "year": 2023, "car_type": "family", 
             "daily_rate": 240, "location": "חיפה", "source": "חיצוני", "available": True, "seats": 5},
            {"id": 105, "make": "Sixt", "model": "A4", "year": 2023, "car_type": "luxury", 
             "daily_rate": 420, "location": "תל אביב", "source": "חיצוני", "available": True, "seats": 5},
            {"id": 106, "make": "National", "model": "Sentra", "year": 2022, "car_type": "economy", 
             "daily_rate": 155, "location": "אילת", "source": "חיצוני", "available": True, "seats": 5},
            {"id": 107, "make": "Alamo", "model": "Rogue", "year": 2023, "car_type": "suv", 
             "daily_rate": 310, "location": "נתניה", "source": "חיצוני", "available": True, "seats": 7}
        ]
    
    def extract_search_criteria(self, question: str) -> Dict:
        """חילוץ קריטריונים לחיפוש מהשאלה"""
        criteria = {}
        question_lower = question.lower()
        
        # חיפוש מחיר/תקציב
        price_patterns = [
            r'תקציב.*?(\d+)',
            r'מחיר.*?(\d+)', 
            r'עד (\d+).*?שקל',
            r'(\d+).*?שקל',
            r'(\d+).*?ש"ח',
            r'(\d+).*?ליום'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, question)
            if match:
                criteria['max_price'] = int(match.group(1))
                break
        
        # חיפוש מיקום
        locations = ['תל אביב', 'tel aviv', 'ירושלים', 'jerusalem', 'חיפה', 'haifa', 
                    'בן גוריון', 'ben gurion', 'אילת', 'eilat', 'באר שבע', 'beer sheva']
        
        for location in locations:
            if location in question_lower:
                criteria['location'] = location
                break
        
        # חיפוש מספר נוסעים
        passengers_patterns = [
            r'(\d+)\s*נוסעים',
            r'(\d+)\s*אנשים', 
            r'(\d+)\s*מקומות',
            r'משפחה.*?(\d+)',
            r'עבור (\d+)'
        ]
        
        for pattern in passengers_patterns:
            match = re.search(pattern, question)
            if match:
                criteria['min_seats'] = int(match.group(1))
                break
        
        # זיהוי סוג רכב
        if any(word in question_lower for word in ['כלכלי', 'זול', 'חסכוני']):
            criteria['car_type'] = 'economy'
        elif any(word in question_lower for word in ['משפחתי', 'משפחה', 'ילדים']):
            criteria['car_type'] = 'family'
        elif any(word in question_lower for word in ['יוקרה', 'מפואר', 'יוקרתי']):
            criteria['car_type'] = 'luxury'
        elif any(word in question_lower for word in ['רכב שטח', 'suv', 'גדול']):
            criteria['car_type'] = 'suv'
        
        return criteria
    
    def filter_cars_by_criteria(self, cars: List[Dict], criteria: Dict) -> List[Dict]:
        """סינון רכבים לפי קריטריונים"""
        filtered_cars = cars.copy()
        
        # סינון לפי מחיר
        if 'max_price' in criteria:
            max_price = criteria['max_price']
            filtered_cars = [car for car in filtered_cars 
                           if car.get('daily_rate', 0) <= max_price]
        
        # סינון לפי מיקום
        if 'location' in criteria:
            location_search = criteria['location'].lower()
            filtered_cars = [car for car in filtered_cars 
                           if location_search in car.get('location', '').lower()]
        
        # סינון לפי מספר נוסעים
        if 'min_seats' in criteria:
            min_seats = criteria['min_seats']
            filtered_cars = [car for car in filtered_cars 
                           if car.get('seats', 5) >= min_seats]
        
        # סינון לפי סוג רכב
        if 'car_type' in criteria:
            car_type = criteria['car_type']
            filtered_cars = [car for car in filtered_cars 
                           if car.get('car_type', '') == car_type]
        
        return filtered_cars
    
    def format_car_list(self, cars: List[Dict], limit: int = 5) -> str:
        """עיצוב רשימת רכבים לתצוגה"""
        if not cars:
            return "לא נמצאו רכבים מתאימים לקריטריונים שלך."
        
        # מיון לפי מחיר
        sorted_cars = sorted(cars[:limit], key=lambda x: x.get('daily_rate', 0))
        
        result = "הנה הרכבים המתאימים ביותר עבורך:\n\n"
        
        for i, car in enumerate(sorted_cars, 1):
            make = car.get('make', 'לא ידוע')
            model = car.get('model', 'לא ידוע')
            year = car.get('year', 'לא ידוע')
            price = car.get('daily_rate', 0)
            location = car.get('location', 'לא ידוע')
            car_type = car.get('car_type', 'לא ידוע')
            source = car.get('source', 'לא ידוע')
            
            # תרגום סוג הרכב
            type_translation = {
                'economy': 'כלכלי',
                'compact': 'קומפקטי', 
                'family': 'משפחתי',
                'luxury': 'יוקרה',
                'suv': 'רכב שטח'
            }
            
            car_type_hebrew = type_translation.get(car_type, car_type)
            
            result += f"{i}. {make} {model} ({year})\n"
            result += f"   סוג: {car_type_hebrew} | מחיר: {price}₪ ליום\n"
            result += f"   מיקום: {location} | מקור: {source}\n\n"
        
        if len(cars) > limit:
            result += f"ועוד {len(cars) - limit} רכבים נוספים זמינים.\n"
        
        return result
    
    def generate_ai_response(self, question: str, context: str = "") -> str:
        """יצירת תשובה עם Ollama"""
        if not self.is_initialized:
            return "מצטער, יועץ ה-AI זמנית לא זמין. בדוק שOllama רץ ויש מודל מותקן."
        
        try:
            # הכנת prompt מקצועי
            prompt = f"""
אתה יועץ מקצועי לשכירת רכבים בישראל. ענה בעברית בצורה ידידותית ומקצועי.

מידע רקע על השכרת רכבים:
{self.knowledge_base}

{f"הקשר נוסף: {context}" if context else ""}

שאלת הלקוח: {question}

הוראות:
- ענה בעברית בלבד
- היה ידידותי ומקצועי
- תן עצות מעשיות וספציפיות
- השתמש במידע הרקע

תשובה:
"""

            # שליחה ל-Ollama
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 300
                    }
                },
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "").strip()
                
                if ai_response:
                    return ai_response
                else:
                    return "מצטער, לא הצלחתי לענות על השאלה. נסה לנסח אותה בצורה אחרת."
            else:
                return f"שגיאה בתקשורת עם יועץ ה-AI. נסה שוב מאוחר יותר."
                
        except requests.exceptions.Timeout:
            return "יועץ ה-AI לוקח זמן לחשוב. נסה שוב בעוד כמה רגעים."
        except Exception as e:
            print(f"שגיאה ב-Ollama: {e}")
            return "מצטער, יש בעיה זמנית עם יועץ ה-AI. נסה שוב מאוחר יותר."
    
    def answer_question(self, question: str) -> str:
        """מענה על שאלה עם Ollama"""
        print(f"DEBUG: שאלה התקבלה: {question}")
        
        # תמיד נחפש רכבים אם השאלה קשורה לרכבים
        question_lower = question.lower()
        car_related_keywords = ['רכב', 'רכבים', 'אוטו', 'השכרה', 'מתאים', 'תקציב', 'מחיר', 'משפחתי', 'כלכלי', 'יוקרה']
        
        is_car_question = any(keyword in question_lower for keyword in car_related_keywords)
        
        if is_car_question:
            print("DEBUG: זוהתה שאלה על רכבים")
            
            # קבלת כל הרכבים
            cars = self.get_available_cars()
            print(f"DEBUG: נמצאו {len(cars)} רכבים")
            
            if cars:
                # חיפוש קריטריונים
                criteria = self.extract_search_criteria(question)
                print(f"DEBUG: קריטריונים שזוהו: {criteria}")
                
                # סינון רכבים
                if criteria:
                    filtered_cars = self.filter_cars_by_criteria(cars, criteria)
                    print(f"DEBUG: אחרי סינון: {len(filtered_cars)} רכבים")
                else:
                    filtered_cars = cars[:8]  # אם אין קריטריונים, תן 8 רכבים ראשונים
                    print(f"DEBUG: ללא סינון: {len(filtered_cars)} רכבים ראשונים")
                
                # עיצוב רשימת רכבים
                car_recommendations = self.format_car_list(filtered_cars)
                
                # החזרת הרכבים עם הסבר קצר
                if "לא נמצאו רכבים" not in car_recommendations:
                    return f"מצאתי עבורך רכבים מתאימים:\n\n{car_recommendations}"
        
        # אם לא מצאנו רכבים או שזו לא שאלת רכבים - תשובה רגילה
        return self.generate_ai_response(question)

# יצירת instance גלובלי
rag_service = CarRentalRAG()

# פונקציות לשירות
async def get_ai_response(message: str) -> str:
    """נקודת כניסה אסינכרונית"""
    return rag_service.answer_question(message)

def get_ai_response_sync(message: str) -> str:
    """נקודת כניסה סינכרונית"""
    return rag_service.answer_question(message)

def get_car_recommendation(user_needs: Dict) -> str:
    """המלצת רכב"""
    budget = user_needs.get("budget", 200)
    passengers = user_needs.get("passengers", 2)
    purpose = user_needs.get("purpose", "city")
    duration = user_needs.get("duration", 3)
    
    question = f"איזה רכב הכי מתאים לי עם תקציב של {budget} שקל ליום עבור {passengers} נוסעים למטרת {purpose}?"
    
    return rag_service.answer_question(question)

def get_ollama_status() -> Dict:
    """מידע על סטטוס Ollama"""
    return {
        "available": rag_service.is_initialized,
        "model": rag_service.model_name if rag_service.is_initialized else None,
        "url": rag_service.ollama_url
    }

if __name__ == "__main__":
    # בדיקה מהירה
    print("🤖 בדיקת Ollama RAG משולב:")
    print(f"סטטוס: {'פעיל' if rag_service.is_initialized else 'לא זמין'}")
    
    if rag_service.is_initialized:
        print(f"מודל: {rag_service.model_name}")
        print("\nבדיקת שאלה עם חיפוש רכבים:")
        response = get_ai_response_sync("איזה רכב מתאים למשפחה עם תקציב של 250 שקל ליום?")
        print(response)
    else:
        print("Ollama לא זמין. וודא ש-Docker רץ והורד מודל.")