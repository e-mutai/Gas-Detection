from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    return db

class GasReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ppm = db.Column(db.Float, nullable=False)
    device_id = db.Column(db.String(50), nullable=False)
    temperature = db.Column(db.Float, nullable=True)  # Optional sensor data
    humidity = db.Column(db.Float, nullable=True)     # Optional sensor data
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "ppm": self.ppm,
            "device_id": self.device_id,
            "temperature": self.temperature,
            "humidity": self.humidity
        }

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20), nullable=False)  # 'warning', 'danger'
    message = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_acknowledged = db.Column(db.Boolean, default=False)
    notification_sent = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "is_active": self.is_active,
            "is_acknowledged": self.is_acknowledged
        }

class SystemStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    last_update = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=True)
    battery_level = db.Column(db.Integer, nullable=True)
    wifi_strength = db.Column(db.Integer, nullable=True)  # ESP32 specific
    firmware_version = db.Column(db.String(20), nullable=True)
    
    def to_dict(self):
        return {
            "device_id": self.device_id,
            "is_online": self.is_online,
            "battery_level": self.battery_level,
            "wifi_strength": self.wifi_strength,
            "firmware_version": self.firmware_version,
            "last_update": self.last_update.isoformat()
        }