import datetime

# Global flag to control debug printing
DEBUG_ENABLED: bool = True


def enable_debug() -> None:
    global DEBUG_ENABLED
    DEBUG_ENABLED = True


def disable_debug() -> None:
    global DEBUG_ENABLED
    DEBUG_ENABLED = False


def debug_print(message: str) -> None:
    if DEBUG_ENABLED:
        print(f"[DEBUG {datetime.datetime.now().isoformat()}]: {message}")
