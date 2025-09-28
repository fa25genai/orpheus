from typing import Tuple, Union

from pydantic import StrictBytes, StrictStr


class MockVideoUploadService:
    async def upload_video(self, courseId: str, body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]]) -> str:
        # Extract video bytes from body
        if isinstance(body, tuple):
            _, video_bytes = body
        elif isinstance(body, bytes):
            video_bytes = body
        else:
            # For string, assume it's base64 or raw bytes
            video_bytes = body.encode() if isinstance(body, str) else body

        # # Create tmp directory if it doesn't exist
        # os.makedirs("tmp", exist_ok=True)

        # # Save as output.mp4 (will replace if exists)
        # with open("tmp/output.mp4", "wb") as f:
        #     f.write(video_bytes)

        # Return a mock video ID
        return f"video_{courseId}_{len(video_bytes)}"


def get_video_upload_service() -> MockVideoUploadService:
    return MockVideoUploadService()