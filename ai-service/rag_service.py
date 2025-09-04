"""
RAG Service עם Ollama למערכת השכרת רכבים
"""
import json
import requests
from typing import Dict, List, Optional

class CarRentalRAG:
    """RAG System למערכת השכרת רכבים עם Ollama"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model_name = "gemma:2b"  # או "llama2" אם הורדת
        self.knowledge_base = self.load_car_knowledge()
        self.is_initialized = self.check_ollama_status()
        
    def check_ollama_status(self) -> bool:
        """בדיקה שOllama רץ ויש מודל זמין"""
        try:
            # בדוק שOllama רץ
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print(f"Ollama לא זמין - סטטוס: {response.status_code}")
                return False
            
            # בדוק שיש מודלים זמינים
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            
            if not available_models:
                print("אין מודלים זמינים ב-Ollama")
                return False
            
            # בחר מודל זמין
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
    
    def generate_ai_response(self, question: str, context: str = "") -> str:
        """יצירת תשובה עם Ollama"""
        if not self.is_initialized:
            return "מצטער, יועץ ה-AI זמנית לא זמין. בדוק שOllama רץ ויש מודל מותקן."
        
        try:
            # הכנת prompt מקצועי
            prompt = f"""
אתה יועץ מקצועי לשכירת רכבים בישראל. ענה בעברית בצורה ידידותית ומקצועית.

מידע רקע על השכרת רכבים:
{self.knowledge_base}

{f"הקשר נוסף: {context}" if context else ""}

שאלת הלקוח: {question}

הוראות:
- ענה בעברית בלבד
- היה ידידותי ומקצועי
- תן עצות מעשיות וספציפיות
- השתמש במידע הרקע
- אם אין לך מידע מספיק, תן עצה כללית טובה
- השתמש ברכבים ומחירים מהמידע שלמעלה

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
                        "num_predict": 200
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
    
    def get_car_recommendation(self, user_needs: Dict) -> str:
        """המלצת רכב מותאמת עם Ollama"""
        budget = user_needs.get("budget", 200)
        passengers = user_needs.get("passengers", 2)
        purpose = user_needs.get("purpose", "city")
        duration = user_needs.get("duration", 3)
        
        context = f"המשתמש מחפש רכב עם תקציב {budget} ש״ח ליום, עבור {passengers} נוסעים, למטרת {purpose}, למשך {duration} ימים."
        
        question = f"איזה רכב הכי מתאים לי עם תקציב של {budget} שקל ליום עבור {passengers} נוסעים למטרת {purpose}? תן המלצה ספציפית עם הסבר מדוע."
        
        return self.generate_ai_response(question, context)
    
    def answer_question(self, question: str) -> str:
        """מענה על שאלה עם Ollama"""
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
    return rag_service.get_car_recommendation(user_needs)

def get_ollama_status() -> Dict:
    """מידע על סטטוס Ollama"""
    return {
        "available": rag_service.is_initialized,
        "model": rag_service.model_name if rag_service.is_initialized else None,
        "url": rag_service.ollama_url
    }

if __name__ == "__main__":
    # בדיקה מהירה
    print("🤖 בדיקת Ollama RAG:")
    print(f"סטטוס: {'פעיל' if rag_service.is_initialized else 'לא זמין'}")
    
    if rag_service.is_initialized:
        print(f"מודל: {rag_service.model_name}")
        print("\nבדיקת שאלה:")
        response = get_ai_response_sync("איזה רכב מתאים למשפחה?")
        print(response)
    else:
        print("Ollama לא זמין. וודא ש-Docker רץ והורד מודל.")