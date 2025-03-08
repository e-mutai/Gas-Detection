from flask import Flask, jsonify, request
from flask_cors import CORS
from models.gas_readings import init_db, GasReading, Alert, SystemStatus
from routes.api import api_bp
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Arduino Cloud integration

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/readings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = init_db(app)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    # Create database directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)