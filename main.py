from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from models.gas_readings import init_db, GasReading, Alert, SystemStatus
from routes.api import api_bp
from integrations.arduino_cloud_integration import ArduinoCloudIntegration
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gas_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for ESP8266 integration

# Validate required environment variables
required_env_vars = ['DATABASE_URI', 'ARDUINO_CLIENT_ID', 'ARDUINO_CLIENT_SECRET', 'ARDUINO_THING_ID']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise EnvironmentError("Missing required environment variables. Check your .env file.")

# Configure SQLite database using environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

try:
    db = init_db(app)
    with app.app_context():
        db.create_all()
        logger.info("Database initialized successfully.")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    raise

# Initialize Arduino Cloud integration
try:
    arduino_cloud = ArduinoCloudIntegration(app)
    logger.info("Arduino Cloud integration initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Arduino Cloud integration: {e}")
    raise

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

# Serve static files safely
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    try:
        if not path or path == '/':
            return send_from_directory(app.static_folder, 'index.html')
        return send_from_directory(app.static_folder, path)
    except Exception as e:
        logger.error(f"Error serving static file '{path}': {e}")
        return jsonify({"error": "File not found"}), 404

# Add a teardown function to clean up resources
@app.teardown_appcontext
def shutdown_arduino_cloud(exception=None):
    if hasattr(app, 'arduino_cloud') and app.arduino_cloud:
        app.arduino_cloud.stop()
        logger.info("Arduino Cloud connection closed.")

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)  # Ensure database directory exists
    
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    
    logger.info(f"Starting Flask server on port {port} (debug={debug_mode})")
    app.run(debug=debug_mode, host=os.getenv('HOST', '0.0.0.0'), port=port)
