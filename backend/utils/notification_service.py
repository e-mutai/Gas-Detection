import requests
import logging
from datetime import datetime

def send_notification(message, level, data=None):
    """
    Send notifications when gas levels are at warning or danger levels.
    This is a backend fallback for notification - as you mentioned the hardware
    will also handle alerts.
    
    In a production environment, this would integrate with SMS services,
    push notification services, etc.
    """
    logging.info(f"[{datetime.now().isoformat()}] ALERT {level.upper()}: {message}")
    
    # Example integration with a notification service (placeholder)
    # In a real implementation, you would replace this with actual service calls
    
    # Example for SMS notification service
    """
    try:
        response = requests.post(
            "https://api.smsservice.com/send",
            json={
                "to": "+1234567890",  # Replace with actual phone number
                "message": message,
                "priority": "high" if level == "danger" else "normal"
            },
            headers={"Authorization": "Bearer YOUR_API_KEY"}
        )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Failed to send SMS notification: {str(e)}")
        return False
    """
    
    # For now, just log that we would send a notification
    return True