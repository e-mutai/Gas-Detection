# app.py
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import random  # For mock data, replace with real sensor data in production

app = Flask(__name__)

# Mock database (replace with real database in production)
class MockDB:
    def __init__(self):
        self.gas_readings = []
        self.alerts = []
        self.system_status = {
            "is_online": True,
            "battery_level": 85,
            "last_calibration": datetime.now() - timedelta(days=5)
        }
        
        # Initialize with some mock data
        self._generate_mock_data()
    
    def _generate_mock_data(self):
        # Generate 24 hours of readings
        for i in range(24):
            timestamp = datetime.now() - timedelta(hours=24-i)
            self.gas_readings.append({
                "timestamp": timestamp,
                "ppm": random.uniform(20, 50),
            })
        #will be changed with real data from the backend
        # Generate some mock alerts
        self.alerts = [
            {
                "id": 1,
                "timestamp": datetime.now() - timedelta(minutes=30),
                "level": "warning",
                "message": "Gas levels above normal"
            },
            {
                "id": 2,
                "timestamp": datetime.now() - timedelta(minutes=45),
                "level": "danger",
                "message": "Critical gas concentration detected"
            }
        ]

db = MockDB()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/current-reading')
def current_reading():
    latest_reading = db.gas_readings[-1] if db.gas_readings else {"ppm": 0}
    return jsonify({
        "ppm": latest_reading["ppm"],
        "status": get_status_from_ppm(latest_reading["ppm"])
    })

@app.route('/api/gas-readings')
def gas_readings():
    return jsonify([{
        "time": reading["timestamp"].strftime("%H:%M"),
        "ppm": reading["ppm"]
    } for reading in db.gas_readings])

@app.route('/api/alerts')
def alerts():
    return jsonify(db.alerts)

@app.route('/api/system-status')
def system_status():
    return jsonify(db.system_status)

def get_status_from_ppm(ppm):
    if ppm < 30:
        return "safe"
    elif ppm < 50:
        return "warning"
    return "danger"

#if __name__ == '__main__':
   # app.run(debug=1)