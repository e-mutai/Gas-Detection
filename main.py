import os
import sys
import logging
import threading
import time
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('gas_detection.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure database - use DATABASE_URI from environment
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)

# Models
class GasReading(db.Model):
    __tablename__ = 'gas_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    gas_level = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "gas_level": self.gas_level,
            "status": self.status
        }

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.String(255), nullable=False)
    level = db.Column(db.String(50), nullable=False)  # "Warning" or "Danger"
    is_acknowledged = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "message": self.message,
            "level": self.level,
            "is_acknowledged": self.is_acknowledged
        }

class ArduinoCloudIntegration:
    """
    Class for integrating with Arduino Cloud IoT
    """
    def __init__(self):
        self.client_id = os.getenv('ARDUINO_CLIENT_ID')
        self.client_secret = os.getenv('ARDUINO_CLIENT_SECRET')
        self.thing_id = os.getenv('ARDUINO_THING_ID')
        
        # Check if Arduino Cloud credentials are available
        self.is_configured = all([self.client_id, self.client_secret, self.thing_id])
        if not self.is_configured:
            logger.error("Arduino Cloud integration not configured. Please set credentials in .env file.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_access_token(self):
        """
        Get Arduino Cloud access token
        """
        if not self.is_configured:
            raise ValueError("Arduino Cloud credentials not configured")
            
        token_url = "https://api2.arduino.cc/iot/v1/clients/token"
        
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'audience': 'https://api2.arduino.cc/iot'
        }
        
        try:
            response = requests.post(token_url, data=payload, timeout=10)
            response.raise_for_status()
            return response.json().get('access_token')
        except requests.RequestException as e:
            logger.error(f"Error obtaining Arduino Cloud token: {e}")
            raise




    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_latest_reading(self):
        """"
        Get the latest gas reading from Arduino Cloud
       """""
        if not self.is_configured:
            raise ValueError("Arduino Cloud credentials not configured")
            
        # Get access token
        access_token = self.get_access_token()
        if not access_token:
            raise ValueError("Failed to obtain access token")
                
        # Fetch properties
        properties_url = f"https://api2.arduino.cc/iot/v1/things/{self.thing_id}/properties"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        response = requests.get(properties_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Process response
        properties = response.json()
        gas_level = None
        
        # Extract the gas level property (adjust based on your Arduino property name)
        for prop in properties:
            if prop.get('name', '').lower() == 'gaslevel':
                gas_level = prop.get('last_value')
                break
        
        if gas_level is not None:
            # Determine status based on gas level
            status = determine_status(float(gas_level))
            
            return {
                'gas_level': float(gas_level),
                'status': status
            }
        else:
            logger.warning("No gas level property found in Arduino response")
            raise ValueError("Gas level property not found in Arduino response")


def determine_status(gas_level):
    """
    Determine status based on gas level
    """
    if gas_level > 100:
        return "Danger"
    elif gas_level > 75:
        return "Warning"
    else:
        return "Safe"

def create_alert_if_needed(gas_level, status):
    """
    Create an alert if the gas level is in the warning or danger zone
    """
    if status == "Warning" or status == "Danger":
        message = "Critical gas concentration detected" if status == "Danger" else "Gas levels above normal"
        
        alert = Alert(
            message=f"{message} ({gas_level:.1f} PPM)",
            level=status
        )
        
        db.session.add(alert)
        db.session.commit()
        logger.info(f"Alert created: {message} - {gas_level:.1f} PPM")

def store_gas_reading(data):
    """
    Store a gas reading in the database
    """
    gas_level = data['gas_level']
    status = data['status']
    
    # Create a new reading
    new_reading = GasReading(
        gas_level=gas_level,
        status=status
    )
    
    db.session.add(new_reading)
    
    # Create alert if needed
    create_alert_if_needed(gas_level, status)
    
    db.session.commit()
    logger.info(f"Gas reading stored: {gas_level:.1f} PPM, Status: {status}")
    
    return new_reading.to_dict()

def fetch_gas_reading():
    """
    Fetch gas reading from Arduino Cloud
    """
    arduino = ArduinoCloudIntegration()
    
    # Get data from Arduino Cloud
    arduino_data = arduino.get_latest_reading()
    logger.info("Successfully retrieved data from Arduino Cloud")
    return arduino_data

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/gas_readings', methods=['GET'])
def get_gas_readings():
    try:
        # Get readings from the last 24 hours
        readings = GasReading.query.filter(
            GasReading.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(GasReading.timestamp.desc()).all()
        
        return jsonify([reading.to_dict() for reading in readings])
    except Exception as e:
        logger.error(f"Error retrieving gas readings: {e}")
        return jsonify({"error": "Failed to retrieve gas readings"}), 500

@app.route('/api/current-reading', methods=['GET'])
def get_current_reading():
    try:
        # Get latest reading from database
        latest_reading = GasReading.query.order_by(GasReading.timestamp.desc()).first()
        
        # If no readings in database or last reading is older than 1 minute, fetch a new one
        if not latest_reading or (datetime.utcnow() - latest_reading.timestamp).total_seconds() > 60:
            try:
                data = fetch_gas_reading()
                latest_reading = store_gas_reading(data)
                return jsonify(latest_reading)
            except Exception as arduino_error:
                logger.error(f"Error fetching from Arduino Cloud: {arduino_error}")
                if latest_reading:
                    return jsonify(latest_reading.to_dict())
                else:
                    return jsonify({"error": "Unable to fetch gas reading from Arduino Cloud"}), 503
        else:
            return jsonify(latest_reading.to_dict())
    except Exception as e:
        logger.error(f"Error retrieving current reading: {e}")
        return jsonify({"error": "Failed to retrieve current reading"}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        # Get active alerts from the last 24 hours
        alerts = Alert.query.filter(
            Alert.timestamp >= datetime.utcnow() - timedelta(hours=24),
            Alert.is_acknowledged == False
        ).order_by(Alert.timestamp.desc()).all()
        
        return jsonify([alert.to_dict() for alert in alerts])
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        return jsonify({"error": "Failed to retrieve alerts"}), 500

@app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    try:
        alert = Alert.query.get_or_404(alert_id)
        alert.is_acknowledged = True
        db.session.commit()
        
        return jsonify({"success": True, "message": "Alert acknowledged"})
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return jsonify({"error": "Failed to acknowledge alert"}), 500

def background_data_collection():
    """
    Background thread to periodically collect data
    """
    while True:
        try:
            with app.app_context():
                try:
                    data = fetch_gas_reading()
                    store_gas_reading(data)
                    logger.info("Successfully collected data in background thread")
                except Exception as arduino_error:
                    logger.error(f"Failed to collect data from Arduino Cloud: {arduino_error}")
        except Exception as e:
            logger.error(f"Error in background data collection: {e}")
        
        # Wait for next collection
        time.sleep(60)  # Collect data every minute

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Start background data collection thread
        collector_thread = threading.Thread(target=background_data_collection, daemon=True)
        collector_thread.start()
        
        # Get host and port from environment
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        
        # Run the Flask app
        app.run(debug=debug, host=host, port=port)