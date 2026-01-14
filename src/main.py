from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from notificationMethods.notificationMethod import NotificationMethod
from notificator import Notificator
from notificators_setup import notificators
from logger import logger

class NotificationRequest(BaseModel):
    notificator_id: str
    message: str

class NotificationResponse(BaseModel):
    success: bool
    message: str
    notificator_id: Optional[str] = None

app = FastAPI(title="Notification Service", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "Notification Service API"}

@app.post("/notify", response_model=NotificationResponse)
async def send_notification(request: NotificationRequest):
    """
    Send a notification using the specified notificator ID
    """
    notificator = notificators.get(request.notificator_id)
    
    if not notificator:
        raise HTTPException(
            status_code=404, 
            detail=f"Notificator with id '{request.notificator_id}' not found"
        )
    
    try:
        notificator.notify(request.message)
        return NotificationResponse(
            success=True,
            message="Notification sent successfully",
            notificator_id=request.notificator_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send notification: {str(e)}"
        )


@app.get("/notificators")
async def list_notificators():
    """
    List all available notificators
    """
    return {
        "notificators": list(notificators.keys()),
        "count": len(notificators)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)