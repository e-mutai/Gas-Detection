import os
import logging
import time
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import load_config
from main import app
from models.gas_readings import db, GasReading, SystemStatus
from utils.arduino_cloud import ArduinoCloudAPI

# Load environment variables
load_dotenv()


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("arduino_sync.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("arduino-sync")


def sync_data_from_arduino_cloud():
    """Pull data from Arduino Cloud and store it in the local database."""
    try:
        client_id = os.environ.get("ARDUINO_CLIENT_ID")
        client_secret = os.environ.get("ARDUINO_CLIENT_SECRET")
        thing_id = os.environ.get("ARDUINO_THING_ID")

        if not all([client_id, client_secret, thing_id]):
            logger.error("Arduino Cloud credentials or Thing ID not found")
            return False

        # Initialize Arduino Cloud API client
        arduino_api = ArduinoCloudAPI(client_id, client_secret)

        if not arduino_api.authenticate():
            logger.error("Authentication with Arduino Cloud failed")
            return False

        logger.info("Successfully authenticated with Arduino Cloud")

        # Fetch Thing properties
        properties = arduino_api.get_thing_properties(thing_id)
        if not properties:
            logger.error(f"Failed to retrieve properties for Thing ID: {thing_id}")
            return False

        # Map property names to IDs
        property_map = {prop["name"].lower(): prop["id"] for prop in properties}
        logger.info(f"Properties found: {', '.join(property_map.keys())}")

        with app.app_context():
            # Sync gas readings
            if "gas_level" in property_map:
                property_id = property_map["gas_level"]
                last_value = arduino_api.get_last_value(thing_id, property_id)

                if last_value and "last_value" in last_value:
                    ppm_value = float(last_value["last_value"])
                    gas_reading = GasReading(
                        ppm=ppm_value,
                        device_id=f"arduino_cloud_{thing_id[:8]}",
                    )
                    db.session.add(gas_reading)
                    logger.info(f"Added gas reading: {ppm_value} PPM")

            # Sync system status
            battery_level = None
            if "battery_level" in property_map:
                battery_data = arduino_api.get_last_value(thing_id, property_map["battery_level"])
                if battery_data and "last_value" in battery_data:
                    battery_level = int(float(battery_data["last_value"]))

            is_online = True  # Assume online if we can fetch data
            for status_prop in ["device_status", "connectivity", "online_status"]:
                if status_prop in property_map:
                    status_data = arduino_api.get_last_value(thing_id, property_map[status_prop])
                    if status_data and "last_value" in status_data:
                        value = status_data["last_value"]
                        if isinstance(value, bool):
                            is_online = value
                        elif isinstance(value, str) and value.lower() in ["online", "connected", "true"]:
                            is_online = True
                        elif isinstance(value, str) and value.lower() in ["offline", "disconnected", "false"]:
                            is_online = False

            # Update or create system status
            status = SystemStatus.query.filter_by(device_id=f"arduino_cloud_{thing_id[:8]}").first()
            if not status:
                status = SystemStatus(device_id=f"arduino_cloud_{thing_id[:8]}")
                db.session.add(status)

            status.is_online = is_online
            status.last_update = datetime.now(datetime.UTC)
            if battery_level is not None:
                status.battery_level = battery_level

            # Commit all changes atomically
            db.session.commit()
            logger.info(f"Updated system status: online={is_online}, battery={battery_level}%")

        return True

    except Exception as e:
        logger.error(f"Error syncing data from Arduino Cloud: {str(e)}", exc_info=True)
        return False


def run_periodic_sync(interval_minutes=5):
    """Run the sync process periodically."""
    logger.info(f"Starting periodic sync every {interval_minutes} minutes")

    while True:
        try:
            sync_data_from_arduino_cloud()
        except Exception as e:
            logger.error(f"Unexpected error in periodic sync: {e}", exc_info=True)

        logger.info(f"Waiting {interval_minutes} minutes until next sync...")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    # Ensure database directory exists
    os.makedirs("data", exist_ok=True)

    # Command-line argument parsing
    parser = argparse.ArgumentParser(description="Arduino Cloud Data Sync")
    parser.add_argument("--daemon", action="store_true", help="Run sync in loop")
    parser.add_argument("--interval", type=int, default=5, help="Sync interval in minutes")

    args = parser.parse_args()

    if args.daemon:
        run_periodic_sync(args.interval)
    else:
        success = sync_data_from_arduino_cloud()
        if success:
            logger.info("Data sync completed successfully")
        else:
            logger.error("Data sync failed")
            exit(1)
