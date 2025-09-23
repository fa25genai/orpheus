from enum import Enum

class GenerationStatus(str, Enum):
    """An enumeration for the status of a generation job."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"