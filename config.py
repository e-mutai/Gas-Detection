import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///data/gas_monitor.db')

# Arduino Cloud configuration
ARDUINO_CLIENT_ID = os.getenv('ARDUINO_CLIENT_ID')
ARDUINO_CLIENT_SECRET = os.getenv('ARDUINO_CLIENT_SECRET')
ARDUINO_THING_ID = os.getenv('ARDUINO_THING_ID')

# ESP8266 Device configuration
ESP_DEVICE_ID = os.getenv('ESP_DEVICE_ID')
ESP_SECRET_KEY = os.getenv('ESP_SECRET_KEY')

# Web server configuration
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '0.0.0.0')
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')