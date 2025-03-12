# Gas Detection System

A web-based dashboard for monitoring gas levels from IoT sensors.

## Setup Instructions

### Prerequisites
- Python 3.7+
- Flask
- SQLAlchemy

### Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/gas-detection-system.git
cd gas-detection-system
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Start the backend server:
```
cd backend
python app.py
```

4. Start the frontend server:
```
cd frontend
python main.py
```

5. Access the dashboard:
Open your browser and navigate to http://localhost:5000

## System Architecture

- **Frontend**: Runs on port 5000, serves the web interface
- **Backend**: Runs on port 5001, handles API requests and database operations
- **API Endpoints**:
  - `/api/current-reading`: Get latest gas reading
  - `/api/gas-readings`: Get historical gas readings
  - `/api/alerts`: Get active alerts
  - `/api/system-status`: Get system status information

## Development Notes

- Make sure both frontend and backend servers are running simultaneously
- The frontend makes API calls to the backend at http://localhost:5001
- Database is stored in backend/data/readings.db