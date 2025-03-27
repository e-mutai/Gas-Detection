from flask import Blueprint, jsonify, request
from models.gas_readings import GasReading, Alert, SystemStatus, db
from datetime import datetime, timedelta
from utils.gas_utils import get_status_from_ppm, validate_reading
from utils.notification_service import send_notification, get_sms_config
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
        "timestamp": latest_reading.timestamp.isoformat()
    })

@api_bp.route('/gas-readings')
def gas_readings():
    device_id = request.args.get('device_id', 'default')
    hours = request.args.get('hours', 24, type=int)
    start_time = datetime.now(datetime.UTC) - timedelta(hours=hours)
    
    readings = GasReading.query.filter(
        GasReading.timestamp >= start_time,
        GasReading.device_id == device_id
    ).order_by(GasReading.timestamp).all()
    
    return jsonify([{
        "time": reading.timestamp.strftime("%H:%M"),
        "ppm": reading.ppm,
        "timestamp": reading.timestamp.isoformat()
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

@api_bp.route('/gsm-config')
def gsm_config():
    """Endpoint for ESP8266 to fetch GSM/SMS configuration"""
    return jsonify(get_sms_config())

# Handle incoming data from ESP8266 with MQ-6 sensor
@api_bp.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        
        if not data or 'ppm' not in data:
            return jsonify({"error": "Invalid data format"}), 400
        
        device_id = data.get('device_id', 'default')
        
        # Validate reading
        is_valid, message = validate_reading(data['ppm'])
        if not is_valid:
            logging.warning(f"Invalid reading from device {device_id}: {message}")
            return jsonify({"error": message}), 400
        
        # Create new reading
        reading = GasReading(
            ppm=data['ppm'],
            device_id=device_id
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
        status.gsm_signal = data.get('gsm_signal', status.gsm_signal)
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
            
            # Log the notification (actual SMS will be sent by ESP8266/GSM module)
            try:
                send_notification(
                    message=alert.message,
                    level=alert.level,
                    data={"ppm": data['ppm'], "device_id": device_id}
                )
                alert.notification_sent = True
                
                # Mark SMS as queued for sending
                if data.get('gsm_ready', False):
                    alert.sms_sent = True
                
            except Exception as e:
                logging.error(f"Failed to process notification: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "reading_id": reading.id,
            "status": gas_status,
            "should_alert": gas_status in ['warning', 'danger']
        })
    
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

# Update GSM SMS status
@api_bp.route('/alerts/<int:alert_id>/sms-status', methods=['POST'])
def update_sms_status(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    data = request.json
    
    if 'sms_sent' in data:
        alert.sms_sent = data['sms_sent']
        db.session.commit()
        return jsonify({"success": True})
    
    return jsonify({"error": "Missing sms_sent parameter"}), 400