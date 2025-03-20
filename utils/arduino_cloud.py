import requests
import json
import time
from datetime import datetime, timedelta
import os

class ArduinoCloudAPI:
    def __init__(self, client_id, client_secret):
        """
        Initialize the Arduino Cloud API client.
        
        Args:
            client_id (str): Your Arduino Cloud API client ID
            client_secret (str): Your Arduino Cloud API client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api2.arduino.cc/iot/v2"
        self.token = None
        self.token_expiry = None
        
    def authenticate(self):
        """Authenticate with the Arduino Cloud API and get an access token."""
        auth_url = "https://api2.arduino.cc/iot/v1/clients/token"
        
        headers = {
            "content-type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": "https://api2.arduino.cc/iot"
        }
        
        response = requests.post(auth_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data['access_token']
            # Set token expiry (usually 1 hour, subtracting 5 minutes for safety)
            self.token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'] - 300)
            return True
        else:
            print(f"Authentication failed: {response.status_code} - {response.text}")
            return False
    
    def ensure_authenticated(self):
        """Ensure we have a valid authentication token."""
        if not self.token or datetime.now() >= self.token_expiry:
            return self.authenticate()
        return True
    
    def get_things(self):
        """Get a list of all things in your Arduino IoT Cloud account."""
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/things"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get things: {response.status_code} - {response.text}")
            return None
    
    def get_thing_properties(self, thing_id):
        """Get properties for a specific thing."""
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/things/{thing_id}/properties"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get properties: {response.status_code} - {response.text}")
            return None
    
    def get_property_values(self, thing_id, property_id, from_date=None, to_date=None):
        """
        Get historical values for a specific property.
        
        Args:
            thing_id (str): The ID of the thing
            property_id (str): The ID of the property
            from_date (datetime, optional): Start date for data retrieval
            to_date (datetime, optional): End date for data retrieval
        """
        if not self.ensure_authenticated():
            return None
        
        url = f"{self.base_url}/things/{thing_id}/properties/{property_id}/timeseries"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        params = {}
        if from_date:
            params["from"] = from_date.isoformat() + "Z"
        if to_date:
            params["to"] = to_date.isoformat() + "Z"
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get property values: {response.status_code} - {response.text}")
            return None

    def get_last_value(self, thing_id, property_id):
        """Get the last value for a specific property."""
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/things/{thing_id}/properties/{property_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get last value: {response.status_code} - {response.text}")
            return None


# Example usage
if __name__ == "__main__":
    # Replace with your actual credentials
    CLIENT_ID = "6iWUOO1wtYxeSAQNTJTNgfmnV4dxx3us"
    CLIENT_SECRET = "0JRHaOKFpjjSxIOuM31L6rA8gw6bRIbku11GJqsBlLxd0ku5pvyjtfzpCtKbuCJ9"
    
    # You can also load credentials from environment variables
    # CLIENT_ID = os.environ.get("ARDUINO_CLIENT_ID")
    # CLIENT_SECRET = os.environ.get("ARDUINO_CLIENT_SECRET")
    
    # Initialize the API client
    arduino_api = ArduinoCloudAPI(CLIENT_ID, CLIENT_SECRET)
    
    # Authenticate
    if arduino_api.authenticate():
        print("Authentication successful!")
        
        # Get all things
        things = arduino_api.get_things()
        if things:
            print(f"Found {len(things)} things:")
            for thing in things:
                print(f"  - {thing['name']} (ID: {thing['id']})")
                
            # If there's at least one thing, get its properties
            if len(things) > 0:
                thing_id = things[0]['id']
                print(f"\nGetting properties for thing: {things[0]['name']}")
                
                properties = arduino_api.get_thing_properties(thing_id)
                if properties:
                    print(f"Found {len(properties)} properties:")
                    for prop in properties:
                        print(f"  - {prop['name']} (ID: {prop['id']}, Type: {prop['type']})")
                        
                    # If there's at least one property, get its last value
                    if len(properties) > 0:
                        property_id = properties[0]['id']
                        print(f"\nGetting last value for property: {properties[0]['name']}")
                        
                        last_value = arduino_api.get_last_value(thing_id, property_id)
                        if last_value:
                            print(f"Last value: {last_value['last_value']}")
                            
                        # Get historical values for the last 24 hours
                        print(f"\nGetting historical values for the last 24 hours:")
                        to_date = datetime.now()
                        from_date = to_date - timedelta(days=1)
                        
                        historical_values = arduino_api.get_property_values(
                            thing_id, property_id, from_date, to_date
                        )
                        
                        if historical_values:
                            print(f"Found {len(historical_values)} historical values")
                            # Print the first few values
                            for i, value in enumerate(historical_values[:5]):
                                print(f"  - {value['value']} at {value['time']}")
                            
                            if len(historical_values) > 5:
                                print("  ...")
        else:
            print("No things found in your Arduino IoT Cloud account.")
    else:
        print("Authentication failed. Check your credentials.")