"""
AI Endpoints למערכת השכרת רכבים - עם Ollama - ללא imports בעייתיים
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
import sys
import os
import requests

# הוסף נתיב לai-service
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_service_path = os.path.join(current_dir, "..", "..", "ai-service")
sys.path.insert(0, ai_service_path)

# ייבוא rag_service עם טיפול בשגיאות
try:
    from rag_service import get_ai_response_sync, get_car_recommendation, get_ollama_status
    AI_AVAILABLE = True
    print("✅ RAG Service נטען בהצלחה")
except ImportError as e:
    print(f"⚠️ RAG Service לא זמין: {e}")
    AI_AVAILABLE = False
    
    # פונקציות חלופיות
    def get_ai_response_sync(message: str) -> str:
        return f"יועץ ה-AI זמנית לא זמין. השאלה שלך: '{message}' - נתקן בקרוב!"
    
    def get_car_recommendation(user_needs: Dict) -> str:
        return "שירות ההמלצות זמנית לא זמין."
    
    def get_ollama_status() -> Dict:
        return {"available": False, "model": "unavailable"}

router = APIRouter(prefix="/api/ai", tags=["AI Advisor"])

# מודלי נתונים
class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict] = None

class CarRecommendationRequest(BaseModel):
    category: Optional[str] = "רכב קומפקטי"
    passengers: Optional[int] = 2
    budget: Optional[str] = "100-200 ₪"
    duration: Optional[int] = 3
    preferences: Optional[List[str]] = []

class AIResponse(BaseModel):
    response: str
    type: str
    metadata: Optional[Dict] = None

@router.get("/health")
async def ai_health():
    """בדיקת זמינות יועץ AI"""
    if not AI_AVAILABLE:
        return {"status": "unavailable", "message": "RAG service לא זמין"}
    
    # בדיקת Ollama
    try:
        ollama_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_ok = ollama_response.status_code == 200
        
        if ollama_ok:
            models = ollama_response.json().get("models", [])
            model_names = [model["name"] for model in models]
        else:
            model_names = []
    except:
        ollama_ok = False
        model_names = []
    
    # בדיקת ChromaDB
    try:
        chroma_response = requests.get("http://localhost:8001/api/v1/heartbeat", timeout=5)
        chroma_ok = chroma_response.status_code == 200
    except:
        chroma_ok = False
    
    # סטטוס מה-RAG service
    ollama_status = get_ollama_status()
    
    status = "available" if ollama_ok and AI_AVAILABLE else "partial"
    
    return {
        "status": status,
        "services": {
            "ollama": "online" if ollama_ok else "offline",
            "chromadb": "online" if chroma_ok else "offline", 
            "rag": "available" if AI_AVAILABLE else "unavailable"
        },
        "ollama_models": model_names,
        "active_model": ollama_status.get("model"),
        "message": "יועץ AI מוכן!" if status == "available" else "יש בעיה עם חלק מהשירותים"
    }

@router.post("/chat", response_model=AIResponse)
async def chat_with_ai(message: ChatMessage):
    """צ'אט עם יועץ ה-AI"""
    try:
        if not AI_AVAILABLE:
            return AIResponse(
                response="יועץ ה-AI זמנית לא זמין. אנא נסה מאוחר יותר.",
                type="error"
            )
        
        # קבל תשובה מהמערכת
        ai_response = get_ai_response_sync(message.message)
        
        return AIResponse(
            response=ai_response,
            type="chat_response",
            metadata={
                "model": get_ollama_status().get("model"),
                "available": AI_AVAILABLE
            }
        )
        
    except Exception as e:
        return AIResponse(
            response=f"מצטער, יש בעיה זמנית עם יועץ ה-AI: {str(e)}",
            type="error"
        )

@router.post("/recommend-car", response_model=AIResponse)
async def recommend_car(request: CarRecommendationRequest):
    """המלצה על רכב"""
    try:
        if not AI_AVAILABLE:
            return AIResponse(
                response="שירות ההמלצות זמנית לא זמין.",
                type="error"
            )
        
        user_needs = {
            "category": request.category,
            "passengers": request.passengers,
            "budget": request.budget,
            "duration": request.duration,
            "preferences": request.preferences or []
        }
        
        # קבל המלצה
        recommendation = get_car_recommendation(user_needs)
        
        return AIResponse(
            response=recommendation,
            type="car_recommendation",
            metadata={
                "user_needs": user_needs,
                "model": get_ollama_status().get("model")
            }
        )
        
    except Exception as e:
        return AIResponse(
            response=f"מצטער, לא הצלחתי לתת המלצה: {str(e)}",
            type="error"
        )

@router.get("/quick-tips")
async def get_quick_tips(category: Optional[str] = None):
    """טיפים מהירים"""
    try:
        if not AI_AVAILABLE:
            return {"response": "שירות הטיפים זמנית לא זמין.", "type": "error"}
        
        category_queries = {
            "family": "איזה רכב הכי מתאים למשפחה עם ילדים?",
            "budget": "איך לחסוך כסף בהשכרת רכב?", 
            "insurance": "הסבר על סוגי הביטוח ברכב שכור",
            "driving": "תן טיפי נהיגה בטוחה ברכב שכור",
            "luxury": "מתי כדאי לשכור רכב יוקרה?",
            "commercial": "מתי נצרך רכב מסחרי?"
        }
        
        query = category_queries.get(category, "תן טיפים כלליים על השכרת רכבים")
        
        ai_response = get_ai_response_sync(query)
        
        return {
            "response": ai_response,
            "type": "tips",
            "metadata": {
                "category": category,
                "model": get_ollama_status().get("model")
            }
        }
        
    except Exception as e:
        return {
            "response": f"מצטער, לא הצלחתי לקבל טיפים: {str(e)}",
            "type": "error"
        }

@router.get("/rag-status")
async def get_rag_status():
    """סטטוס מערכת RAG"""
    ollama_status = get_ollama_status()
    
    return {
        "status": "available" if AI_AVAILABLE and ollama_status.get("available") else "partial",
        "ai_available": AI_AVAILABLE,
        "ollama_status": ollama_status,
        "services": {
            "rag_service": "loaded" if AI_AVAILABLE else "not_loaded",
            "ollama": "online" if ollama_status.get("available") else "offline"
        }
    }

@router.get("/initialize-rag")
async def initialize_rag():
    """אתחול מערכת RAG"""
    if not AI_AVAILABLE:
        return {"status": "error", "message": "RAG service לא זמין"}
    
    ollama_status = get_ollama_status()
    
    return {
        "status": "success" if ollama_status.get("available") else "partial",
        "message": "מערכת RAG מוכנה" if ollama_status.get("available") else "חלק מהשירותים לא פעילים",
        "model": ollama_status.get("model")
    }