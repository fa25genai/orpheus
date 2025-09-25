class ProgressTracker:
    def __init__(self, total_steps):
        self.total_steps = total_steps
        self.current_step = 0

    def log(self, message):
        self.current_step += 1
        print(f"({self.current_step}/{self.total_steps}): {message}")

total_tasks = 4
tracker = ProgressTracker(total_steps=total_tasks)