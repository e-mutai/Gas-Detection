import os
import logging
import time
from datetime import datetime, timedelta
from config import load_config
from main import app
from models.gas_readings import db, GasReading, SystemStatus
from utils.arduino_cloud import ArduinoCloudAPI
from utils.gas_utils import get_status_from_ppm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("arduino_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("arduino-sync")

def sync_data_from_arduino_cloud():
    """Pull data from Arduino Cloud and store it in the local database"""
    try:
        # Load Arduino Cloud API credentials from config
        load_config()
        client_id = os.environ.get("ARDUINO_CLIENT_ID")
        client_secret = os.environ.get("ARDUINO_CLIENT_SECRET")
        thing_id = os.environ.get("ARDUINO_THING_ID")
        
        if not all([client_id, client_secret, thing_id]):
            logger.error("Arduino Cloud credentials or Thing ID not found")
            return False
        
        # Initialize the API client
        arduino_api = ArduinoCloudAPI(client_id, client_secret)
        
        # Authenticate with Arduino Cloud
        if not arduino_api.authenticate():
            logger.error("Authentication with Arduino Cloud failed")
            return False
        
        logger.info("Authentication with Arduino Cloud successful")
        
        # Get thing properties
        properties = arduino_api.get_thing_properties(thing_id)
        if not properties:
            logger.error(f"Failed to get properties for thing ID: {thing_id}")
            return False
        
        # Map property names to IDs
        property_map = {}
        for prop in properties:
            property_map[prop['name'].lower()] = prop['id']
        
        logger.info(f"Found {len(properties)} properties: {', '.join(property_map.keys())}")
        
        # Check if we have the gas level property
        if 'gas_level' not in property_map:
            logger.warning("No 'gas_level' property found in Arduino Cloud")
        else:
            # Get last value for gas level
            property_id = property_map['gas_level']
            last_value = arduino_api.get_last_value(thing_id, property_id)
            
            if last_value and 'last_value' in last_value:
                # Save gas reading to database
                with app.app_context():
                    gas_reading = GasReading(
                        ppm=float(last_value['last_value']),
                        device_id=f"arduino_cloud_{thing_id[:8]}"  # Use first 8 chars of thing_id as device_id
                    )
                    db.session.add(gas_reading)
                    logger.info(f"Added gas reading: {gas_reading.ppm} PPM")
                    
                    # Get historical values for the last hour
                    now = datetime.now()
                    from_date = now - timedelta(hours=1)
                    historical_values = arduino_api.get_property_values(
                        thing_id, property_id, from_date, now
                    )
                    
                    if historical_values:
                        new_readings = 0
                        for value in historical_values:
                            # Check if reading already exists for this timestamp
                            reading_time = datetime.fromisoformat(value['time'].replace('Z', '+00:00'))
                            existing = GasReading.query.filter(
                                GasReading.timestamp >= reading_time - timedelta(seconds=5),
                                GasReading.timestamp <= reading_time + timedelta(seconds=5),
                                GasReading.device_id == f"arduino_cloud_{thing_id[:8]}"
                            ).first()
                            
                            if not existing:
                                reading = GasReading(
                                    ppm=float(value['value']),
                                    device_id=f"arduino_cloud_{thing_id[:8]}",
                                    timestamp=reading_time
                                )
                                db.session.add(reading)
                                new_readings += 1
                        
                        logger.info(f"Added {new_readings} historical readings from the last hour")
        
        # Update system status
        with app.app_context():
            # Check if we have battery level and device status properties
            battery_level = None
            if 'battery_level' in property_map:
                battery_data = arduino_api.get_last_value(thing_id, property_map['battery_level'])
                if battery_data and 'last_value' in battery_data:
                    battery_level = int(float(battery_data['last_value']))
            
            # Look for connectivity/online status properties
            is_online = True  # Default to online since we're getting data
            for status_prop in ['device_status', 'connectivity', 'online_status']:
                if status_prop in property_map:
                    status_data = arduino_api.get_last_value(thing_id, property_map[status_prop])
                    if status_data and 'last_value' in status_data:
                        # Check if it's a boolean or a string like "online"/"offline"
                        value = status_data['last_value']
                        if isinstance(value, bool):
                            is_online = value
                        elif isinstance(value, str) and value.lower() in ["online", "connected", "true"]:
                            is_online = True
                        elif isinstance(value, str) and value.lower() in ["offline", "disconnected", "false"]:
                            is_online = False
            
            # Update system status
            status = SystemStatus.query.filter_by(device_id=f"arduino_cloud_{thing_id[:8]}").first()
            if not status:
                status = SystemStatus(device_id=f"arduino_cloud_{thing_id[:8]}")
                db.session.add(status)
            
            status.is_online = is_online
            status.last_update = datetime.utcnow()
            if battery_level is not None:
                status.battery_level = battery_level
            
            # Commit all changes
            db.session.commit()
            logger.info(f"Updated system status: online={is_online}, battery={battery_level}%")
        
        return True
    
    except Exception as e:
        logger.error(f"Error syncing data from Arduino Cloud: {str(e)}", exc_info=True)
        return False

def run_periodic_sync(interval_minutes=5):
    """Run the sync process periodically"""
    logger.info(f"Starting periodic sync every {interval_minutes} minutes")
    
    while True:
        sync_data_from_arduino_cloud()
        logger.info(f"Waiting {interval_minutes} minutes until next sync...")
        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    # Create database directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Run once or periodically based on command-line arguments
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        interval = 5  # Default: 5 minutes
        if len(sys.argv) > 2:
            try:
                interval = int(sys.argv[2])
            except ValueError:
                pass
        run_periodic_sync(interval)
    else:
        # Run once
        success = sync_data_from_arduino_cloud()
        if success:
            logger.info("Data sync completed successfully")
        else:
            logger.error("Data sync failed")
            sys.exit(1)