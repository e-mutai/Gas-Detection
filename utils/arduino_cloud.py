import os
import requests
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

class ArduinoCloudAPI:
    def __init__(self, client_id=None, client_secret=None):
        """
        Initialize the Arduino Cloud API client.

        Args:
            client_id (str, optional): Arduino Cloud API client ID. Defaults to environment variable.
            client_secret (str, optional): Arduino Cloud API client secret. Defaults to environment variable.
        """
        self.client_id = os.getenv("ARDUINO_CLIENT_ID")
        self.client_secret = os.getenv("ARDUINO_CLIENT_SECRET")
        self.base_url = "https://api2.arduino.cc/iot/v2"
        self.token = None
        self.token_expiry = None

        if not self.client_id or not self.client_secret:
            logging.error("Client ID or Client Secret is missing.")
            raise ValueError("Missing Arduino API credentials.")

    def authenticate(self):
        """Authenticate with the Arduino Cloud API and retrieve an access token."""
        auth_url = "https://api2.arduino.cc/iot/v1/clients/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": "https://api2.arduino.cc/iot"
        }

        try:
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data['access_token']
            self.token_expiry = datetime.utcnow() + timedelta(seconds=token_data['expires_in'] - 300)
            logging.info("Successfully authenticated with Arduino Cloud API.")
            return True
        except requests.RequestException as e:
            logging.error(f"Authentication failed: {e}")
            return False

    def ensure_authenticated(self):
        """Ensure the authentication token is valid."""
        if not self.token or datetime.utcnow() >= self.token_expiry:
            return self.authenticate()
        return True

    def _make_request(self, method, endpoint, params=None):
        """
        Helper method to make authenticated API requests.

        Args:
            method (str): HTTP method (GET, POST, etc.).
            endpoint (str): API endpoint.
            params (dict, optional): Query parameters.

        Returns:
            dict or None: JSON response if successful, otherwise None.
        """
        if not self.ensure_authenticated():
            return None

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        try:
            response = requests.request(method, url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Request failed ({method} {url}): {e}")
            return None

    def get_things(self):
        """Retrieve a list of all things in the Arduino IoT Cloud."""
        return self._make_request("GET", "/things")

    def get_thing_properties(self, thing_id):
        """Retrieve properties of a specific thing."""
        return self._make_request("GET", f"/things/{thing_id}/properties")

    def get_property_values(self, thing_id, property_id, from_date=None, to_date=None):
        """
        Retrieve historical values for a specific property.

        Args:
            thing_id (str): The ID of the thing.
            property_id (str): The ID of the property.
            from_date (datetime, optional): Start time for retrieval.
            to_date (datetime, optional): End time for retrieval.

        Returns:
            dict or None: JSON response containing historical values.
        """
        params = {}
        if from_date:
            params["from"] = from_date.isoformat() + "Z"
        if to_date:
            params["to"] = to_date.isoformat() + "Z"

        return self._make_request("GET", f"/things/{thing_id}/properties/{property_id}/timeseries", params)

    def get_last_value(self, thing_id, property_id):
        """Retrieve the last recorded value of a property."""
        return self._make_request("GET", f"/things/{thing_id}/properties/{property_id}")


# Example usage
if __name__ == "__main__":
    try:
        arduino_api = ArduinoCloudAPI()
        
        if arduino_api.authenticate():
            logging.info("Successfully authenticated!")

            # Get things
            things = arduino_api.get_things()
            if things:
                logging.info(f"Found {len(things)} things.")
                for thing in things:
                    logging.info(f"- {thing['name']} (ID: {thing['id']})")

                # Get properties of the first thing
                thing_id = things[0]['id']
                properties = arduino_api.get_thing_properties(thing_id)
                if properties:
                    logging.info(f"Found {len(properties)} properties.")
                    for prop in properties:
                        logging.info(f"- {prop['name']} (ID: {prop['id']})")

                    # Get last value of the first property
                    property_id = properties[0]['id']
                    last_value = arduino_api.get_last_value(thing_id, property_id)
                    if last_value:
                        logging.info(f"Last value: {last_value.get('last_value')}")

                    # Get historical values (last 24 hours)
                    from_date = datetime.utcnow() - timedelta(days=1)
                    to_date = datetime.utcnow()
                    historical_values = arduino_api.get_property_values(thing_id, property_id, from_date, to_date)
                    if historical_values:
                        logging.info(f"Retrieved {len(historical_values)} historical values.")
            else:
                logging.warning("No things found in your Arduino IoT Cloud account.")
        else:
            logging.error("Failed to authenticate with Arduino Cloud API.")

    except Exception as e:
        logging.critical(f"Unexpected error: {e}", exc_info=True)
