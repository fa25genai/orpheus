from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from threading import Lock

class AppState:
    executor: Optional[ThreadPoolExecutor] = None
    lock = Lock() # Ensures the executor is created only once

app_state = AppState()

