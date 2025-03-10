import datetime

def log(message):
    """Print a log message with timestamp"""
    timestamp = datetime.datetime.now().isoformat()
    print(f"[LOG] {timestamp}: {message}")

def error(message):
    """Print an error message with timestamp"""
    timestamp = datetime.datetime.now().isoformat()
    print(f"[ERROR] {timestamp}: {message}")

def handle_error(error):
    """Handle and log an error"""
    timestamp = datetime.datetime.now().isoformat()
    print(f"[ERROR] {timestamp}: {str(error)}")