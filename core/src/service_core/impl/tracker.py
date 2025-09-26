from typing import Final


class ProgressTracker:
    def __init__(self, total_steps: int) -> None:
        self.total_steps: int = total_steps
        self.current_step: int = 0

    def log(self, message: str) -> None:
        self.current_step += 1
        print(f"({self.current_step}/{self.total_steps}): {message}", flush=True)


total_tasks: Final[int] = 7
tracker: ProgressTracker = ProgressTracker(total_steps=total_tasks)
