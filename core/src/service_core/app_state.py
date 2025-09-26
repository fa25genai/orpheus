from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Optional


class AppState:
    executor: Optional[ThreadPoolExecutor] = None
    lock = Lock() # Ensures the executor is created only once

app_state = AppState()

