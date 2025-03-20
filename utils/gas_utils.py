def get_status_from_ppm(ppm):
    """
    Determine gas level status based on PPM reading
    Returns: 'safe', 'warning', or 'danger'
    
    Note: These thresholds should be adjusted based on the specific
    combustible gas being monitored and sensor specifications
    """
    if ppm < 30:
        return "safe"
    elif ppm < 50:
        return "warning"
    return "danger"

def validate_reading(ppm):
    """
    Validate that a gas reading is within expected range
    Returns: (is_valid, message)
    """
    if ppm < 0:
        return False, "Negative PPM reading detected"
    
    if ppm > 1000:  # Example threshold - adjust based on sensor specs
        return False, "Reading exceeds maximum expected value"
    
    return True, "Valid reading"