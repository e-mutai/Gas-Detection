# Gas Detection System

A real-time combustible gas monitoring system using ESP8266, MQ-6 sensor, and GSM module for SMS alerts. This project provides both hardware sensing capabilities and a web-based dashboard for monitoring gas levels.

## Features

- **Real-time gas level monitoring** with MQ-6 combustible gas sensor
- **SMS alerts** via GSM module when dangerous gas levels are detected
- **Responsive dashboard** with dark/light mode and real-time updates
- **Historical data tracking** with 24-hour gas level charts
- **Alert management system** with acknowledgment capability
- **Battery and signal monitoring** for the IoT device

## Hardware Requirements

- ESP8266 (NodeMCU or similar)
- MQ-6 Gas Sensor
- SIM800L GSM Module
- SIM card with SMS capability
- Power supply (for ESP8266 and GSM module)
- Jumper wires 

## Software Requirements

- Python 3.6+
- Flask and related packages
- Arduino IDE with ESP8266 support
- Web browser with JavaScript enabled

## Installation

### Backend Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/gas-detection-system.git
   cd gas-detection-system
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create necessary directories:
   ```
   mkdir -p data
   mkdir -p static
   ```

4. Copy the frontend file:
   ```
   # Ensure index.html is in the static directory
   ```

### ESP8266 Setup

1. Open the Arduino IDE
2. Install required libraries:
   - ESP8266WiFi
   - ESP8266HTTPClient
   - ArduinoJson
   - SoftwareSerial

3. Open the ESP8266 sketch from the `arduino` directory
4. Update the following variables:
   - Wi-Fi credentials (`ssid` and `password`)
   - Server URL (`serverUrl`)
   - Phone numbers for SMS alerts (`phoneNumbers`)

5. Connect your ESP8266 to your computer
6. Upload the sketch to your device

### Hardware Assembly

1. Connect the MQ-6 sensor to ESP8266:
   - VCC to 5V
   - GND to GND
   - AO to A0 on ESP8266

2. Connect the SIM800L GSM module:
   - TX to D1 on ESP8266
   - RX to D2 on ESP8266
   - GND to GND
   - VCC to external 3.7-4.2V power source (NOT to ESP8266)

3. Connect the buzzer:
   - Positive to D3 on ESP8266
   - Negative to GND

4. Optional: Connect an external LED:
   - Positive (longer leg) to D4 via a 220Ω resistor
   - Negative to GND

## Running the System

1. Start the backend server:
   ```
   python app.py
   ```

2. Access the dashboard:
   Open your web browser and navigate to `http://localhost:5000`

3. Power on your ESP8266 device

4. The system should automatically begin monitoring gas levels and displaying them on the dashboard

## Dashboard Features

- **Real-time gas level indicator** with status (Safe, Warning, Danger)
- **Historical chart** showing 24 hours of gas level readings
- **System status panel** showing battery level and connectivity
- **Active alerts panel** with acknowledgment option
- **Dark/light mode toggle** for comfortable viewing
- **Settings panel** for customizing server address and refresh intervals

## API Endpoints

The system exposes several API endpoints:

- `GET /api/current-reading` - Get the latest gas reading
- `GET /api/gas-readings` - Get historical gas readings (default 24h)
- `GET /api/alerts` - Get all active alerts
- `GET /api/system-status` - Get device status information
- `GET /api/gsm-config` - Get GSM/SMS configuration
- `POST /api/sensor-data` - Submit new sensor readings from ESP8266
- `POST /api/alerts/{id}/acknowledge` - Acknowledge an alert
- `POST /api/alerts/{id}/sms-status` - Update SMS status for an alert

## Alert Thresholds

The default alert thresholds for the MQ-6 gas sensor are:
- **Safe**: 0-29 PPM
- **Warning**: 30-49 PPM
- **Danger**: 50+ PPM

These thresholds can be adjusted in the `utils/gas_utils.py` file based on your specific requirements and the gases you're monitoring.

## Customization

### Adjusting Gas Thresholds

Edit the `get_status_from_ppm` function in `utils/gas_utils.py`:

```python
def get_status_from_ppm(ppm):
    if ppm < 30:  # Change this value
        return "safe"
    elif ppm < 50:  # Change this value
        return "warning"
    return "danger"
```

### Adding SMS Recipients

Edit the `phoneNumbers` array in the ESP8266 sketch:

```cpp
String phoneNumbers[] = {
    "+1234567890",  // Replace with actual numbers
    "+0987654321"   // Add more numbers as needed
};
```

### Calibrating the MQ-6 Sensor

The MQ-6 sensor requires calibration for accurate readings. In the ESP8266 code, adjust the conversion formula in the `readGasSensor()` function:

```cpp
// Convert analog reading to PPM
float ppm = 50.0 * voltage;  // Adjust this formula based on calibration
```

## Troubleshooting

### ESP8266 Connection Issues

- Ensure Wi-Fi credentials are correct
- Verify the server is running and accessible
- Check the server URL includes "http://" and correct IP/port

### GSM Module Issues

- Ensure SIM card is active and has credit
- Check power supply (3.7-4.2V required)
- Verify TX/RX connections are correct
- Monitor serial output for AT command responses

### MQ-6 Sensor Issues

- Allow 24-48 hours for initial warm-up and stabilization
- Verify analog pin connection
- Check power supply (5V required)

### Server Issues

- Check if port 5000 is already in use
- Verify database directory has write permissions
- Check log messages for detailed errors

## License

[MIT License](LICENSE)

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Chart.js](https://www.chartjs.org/) - JavaScript charting library
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework