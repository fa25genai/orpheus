import datetime

# Global flag to control debug printing
DEBUG_ENABLED = True

def enable_debug():
    global DEBUG_ENABLED
    DEBUG_ENABLED = True

def disable_debug():
    global DEBUG_ENABLED
    DEBUG_ENABLED = False

def debug_print(message):
    if DEBUG_ENABLED:
        print(f"[DEBUG {datetime.datetime.now().isoformat()}]: {message}")