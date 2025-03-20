from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from models.gas_readings import init_db, GasReading, Alert, SystemStatus
from routes.api import api_bp
from integrations.arduino_cloud_integration import ArduinoCloudIntegration
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gas_monitor.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for ESP8266 integration

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/readings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = init_db(app)

# Initialize Arduino Cloud integration
arduino_cloud = ArduinoCloudIntegration(app)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

# Serve the frontend directly from the backend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path == "" or path == "/":
        return send_from_directory(app.static_folder, 'index.html')
    return send_from_directory(app.static_folder, path)

# Add a teardown function to clean up resources
@app.teardown_appcontext
def shutdown_arduino_cloud(exception=None):
    if hasattr(app, 'arduino_cloud') and app.arduino_cloud:
        app.arduino_cloud.stop()

if __name__ == '__main__':
    # Create database directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Use environment variable for port if available, otherwise use 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=port)