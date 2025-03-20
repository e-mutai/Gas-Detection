import logging
from datetime import datetime

def send_notification(message, level, data=None):
    """
    Send notifications when gas levels are at warning or danger levels.
    
    This is a backend notification system. The hardware will handle the actual
    SMS sending through the GSM module, but we log it here and mark it in the database.
    
    Returns True to indicate notification was logged (actual SMS sending is handled by hardware)
    """
    logging.info(f"[{datetime.now().isoformat()}] ALERT {level.upper()}: {message}")
    
    # Log that a notification should be sent via GSM
    # The actual SMS sending will be handled by the ESP8266 with GSM module
    logging.info(f"Notification marked for GSM delivery: {message}")
    
    return True

def get_sms_config():
    """
    Return SMS configuration for the GSM module
    This would be sent to the ESP8266 to configure the GSM module
    """
    return {
        "recipient_numbers": ["+254792688998"],  # Replace with actual numbers
        "alert_threshold": "warning",  # Send SMS for both warning and danger levels
        "include_ppm": True,
        "include_timestamp": True
    }