from utils.arduino_cloud import ArduinoCloudAPI
from models.gas_readings import GasReading, Alert, SystemStatus, db
from datetime import datetime, timedelta
import logging
import os
import time
import threading
import json

# Configure logging
logger = logging.getLogger(__name__)

class ArduinoCloudIntegration:
    def __init__(self, app=None):
        self.app = app
        self.client_id = os.environ.get("ARDUINO_CLIENT_ID")
        self.client_secret = os.environ.get("ARDUINO_CLIENT_SECRET")
        self.thing_id = os.environ.get("ARDUINO_THING_ID")
        self.api = None
        self.properties = {}
        self.property_mappings = {
            "gas_level": None,      # Property ID for gas level
            "alert_status": None,   # Property ID for alert status
            "device_status": None,  # Property ID for device status
            "battery_level": None   # Property ID for battery level
        }
        self.sync_thread = None
        self.stop_sync = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask application"""
        self.app = app
        
        # Check if credentials are available
        if not self.client_id or not self.client_secret:
            logger.warning("Arduino Cloud credentials not found. Cloud integration disabled.")
            return False
            
        if not self.thing_id:
            logger.warning("Arduino Cloud Thing ID not found. Cloud integration disabled.")
            return False
        
        # Initialize the API client
        self.api = ArduinoCloudAPI(self.client_id, self.client_secret)
        
        # Authenticate
        if not self.api.authenticate():
            logger.error("Failed to authenticate with Arduino Cloud API.")
            return False
            
        # Get properties for the thing
        self._discover_properties()
        
        # Start background sync thread
        self._start_sync_thread()
        
        logger.info("Arduino Cloud integration initialized successfully.")
        return True
    
    def _discover_properties(self):
        """Discover properties for the configured thing"""
        if not self.api or not self.thing_id:
            return
            
        properties = self.api.get_thing_properties(self.thing_id)
        if not properties:
            logger.error(f"Failed to get properties for thing ID: {self.thing_id}")
            return
            
        # Store properties and create mappings
        self.properties = {prop['name']: prop for prop in properties}
        
        # Map properties by name
        for prop in properties:
            if prop['name'].lower() == 'gas_level':
                self.property_mappings['gas_level'] = prop['id']
            elif prop['name'].lower() == 'alert_status':
                self.property_mappings['alert_status'] = prop['id']
            elif prop['name'].lower() == 'device_status':
                self.property_mappings['device_status'] = prop['id']
            elif prop['name'].lower() == 'battery_level':
                self.property_mappings['battery_level'] = prop['id']
        
        missing_props = [k for k, v in self.property_mappings.items() if v is None]
        if missing_props:
            logger.warning(f"Some properties were not found in Arduino Cloud: {missing_props}")
            
        logger.info(f"Discovered {len(properties)} properties in Arduino Cloud.")
    
    def _start_sync_thread(self):
        """Start a background thread to sync data with Arduino Cloud"""
        if self.sync_thread and self.sync_thread.is_alive():
            return  # Thread already running
            
        self.stop_sync = False
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Arduino Cloud sync thread started.")
    
    def _sync_loop(self):
        """Background thread to sync data with Arduino Cloud"""
        with self.app.app_context():
            while not self.stop_sync:
                try:
                    self._sync_data_to_cloud()
                except Exception as e:
                    logger.error(f"Error syncing data to Arduino Cloud: {str(e)}")
                
                # Sleep for 30 seconds
                time.sleep(30)
    
    def _sync_data_to_cloud(self):
        """Sync gas readings and system status to Arduino Cloud"""
        if not self.api or not self.api.ensure_authenticated():
            logger.warning("Not authenticated with Arduino Cloud. Skipping sync.")
            return
            
        # Get latest gas reading
        latest_reading = GasReading.query.order_by(GasReading.timestamp.desc()).first()
        if latest_reading and self.property_mappings['gas_level']:
            # TODO: Implement Arduino Cloud property update method
            # This would use the Arduino Cloud REST API to update properties
            logger.info(f"Would sync gas level: {latest_reading.ppm} PPM")
            
        # Get active alerts
        active_alert = Alert.query.filter_by(is_active=True).order_by(Alert.timestamp.desc()).first()
        if active_alert and self.property_mappings['alert_status']:
            # TODO: Implement alert status sync
            logger.info(f"Would sync alert status: {active_alert.level}")
            
        # Get system status
        system_status = SystemStatus.query.order_by(SystemStatus.last_update.desc()).first()
        if system_status:
            if self.property_mappings['device_status']:
                # TODO: Implement device status sync
                status_value = "online" if system_status.is_online else "offline"
                logger.info(f"Would sync device status: {status_value}")
                
            if self.property_mappings['battery_level'] and system_status.battery_level:
                # TODO: Implement battery level sync
                logger.info(f"Would sync battery level: {system_status.battery_level}%")
    
    def stop(self):
        """Stop the sync thread"""
        self.stop_sync = True
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5.0)
            logger.info("Arduino Cloud sync thread stopped.")
    
    def get_cloud_status(self):
        """Get Arduino Cloud connection status"""
        if not self.api:
            return {
                "connected": False,
                "reason": "Not initialized"
            }
            
        if not self.api.token:
            return {
                "connected": False,
                "reason": "Not authenticated"
            }
            
        return {
            "connected": True,
            "thing_id": self.thing_id,
            "properties_mapped": sum(1 for v in self.property_mappings.values() if v is not None),
            "properties_total": len(self.properties)
        }