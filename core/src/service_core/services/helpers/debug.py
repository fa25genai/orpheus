import datetime

def debug_print(message: str) -> None:
    print(f"[DEBUG {datetime.datetime.now().isoformat()}]: {message}")
