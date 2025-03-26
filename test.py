import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print all required variables for debugging
required_vars = ["ARDUINO_CLIENT_ID", "ARDUINO_CLIENT_SECRET", "ARDUINO_THING_ID"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

for var in required_vars:
    print(f"{var}: {os.getenv(var)}")

# Check if any variables are missing
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
