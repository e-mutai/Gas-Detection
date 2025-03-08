from flask import Blueprint, jsonify, request, current_app
from models.gas_readings import GasReading, Alert, SystemStatus, db
from datetime import datetime, timedelta
from utils.gas_utils import get_status_from_ppm
from utils.notification_service import send_notification
import logging

api_bp = Blueprint('api', __name__)

@api_bp.route('/current-reading')
def current_reading():
    device_id = request.args.get('device_id', 'default')
    latest_reading = GasReading.query.filter_by(device_id=device_id).order_by(GasReading.timestamp.desc()).first()
    
    if not latest_reading:
        return jsonify({"ppm": 0, "status": "unknown"})
    
    return jsonify({
        "ppm": latest_reading.ppm,
        "status": get_status_from_ppm(latest_reading.ppm),
        "timestamp": latest_reading.timestamp.isoformat(),
        "temperature": latest_reading.temperature,
        "humidity": latest_reading.humidity
    })

@api_bp.route('/gas-readings')
def gas_readings():
    device_id = request.args.get('device_id', 'default')
    hours = request.args.get('hours', 24, type=int)
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    readings = GasReading.query.filter(
        GasReading.timestamp >= start_time,
        GasReading.device_id == device_id
    ).order_by(GasReading.timestamp).all()
    
    return jsonify([{
        "time": reading.timestamp.strftime("%H:%M"),
        "ppm": reading.ppm,
        "timestamp": reading.timestamp.isoformat(),
        "temperature": reading.temperature,
        "humidity": reading.humidity
    } for reading in readings])

@api_bp.route('/alerts')
def alerts():
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    query = Alert.query
    if active_only:
        query = query.filter_by(is_active=True)
    
    alerts_list = query.order_by(Alert.timestamp.desc()).all()
    return jsonify([alert.to_dict() for alert in alerts_list])

@api_bp.route('/system-status')
def system_status():
    device_id = request.args.get('device_id', 'default')
    status = SystemStatus.query.filter_by(device_id=device_id).order_by(SystemStatus.last_update.desc()).first()
    
    if not status:
        return jsonify({
            "is_online": False,
            "battery_level": None,
            "last_update": None
        })
    
    return jsonify(status.to_dict())

# Handle incoming data from Arduino Cloud / ESP32
@api_bp.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        
        if not data or 'ppm' not in data:
            return jsonify({"error": "Invalid data format"}), 400
        
        device_id = data.get('device_id', 'default')
        
        # Create new reading
        reading = GasReading(
            ppm=data['ppm'],
            device_id=device_id,
            temperature=data.get('temperature'),
            humidity=data.get('humidity')
        )
        db.session.add(reading)
        
        # Update system status
        status = SystemStatus.query.filter_by(device_id=device_id).first()
        if not status:
            status = SystemStatus(device_id=device_id)
            db.session.add(status)
        
        status.is_online = True
        status.last_update = datetime.utcnow()
        status.battery_level = data.get('battery_level', status.battery_level)
        status.wifi_strength = data.get('wifi_strength', status.wifi_strength)
        status.firmware_version = data.get('firmware_version', status.firmware_version)
        
        # Check if we need to create an alert
        gas_status = get_status_from_ppm(data['ppm'])
        if gas_status in ['warning', 'danger']:
            alert = Alert(
                level=gas_status,
                message=f"Gas levels at {gas_status.upper()} level: {data['ppm']} PPM detected by device {device_id}"
            )
            db.session.add(alert)
            db.session.commit()  # Commit to get the alert ID
            
            # Send notification (this will be handled by the hardware as you mentioned, 
            # but including for completeness)
            try:
                send_notification(
                    message=alert.message,
                    level=alert.level,
                    data={"ppm": data['ppm'], "device_id": device_id}
                )
                alert.notification_sent = True
            except Exception as e:
                logging.error(f"Failed to send notification: {str(e)}")
        
        db.session.commit()
        
        return jsonify({"success": True, "reading_id": reading.id})
    
    except Exception as e:
        logging.error(f"Error processing sensor data: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Acknowledge an alert
@api_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_acknowledged = True
    db.session.commit()
    return jsonify({"success": True})