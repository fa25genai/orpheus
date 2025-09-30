import os
from typing import Tuple, Union

from pydantic import StrictBytes, StrictStr


class MockUploadPDFService:
    def upload_pdf(self, courseId: str, body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]]) -> str:
        # Extract PDF bytes from body
        if isinstance(body, tuple):
            _, pdf_bytes = body
        elif isinstance(body, bytes):
            pdf_bytes = body
        else:
            # For string, assume it's base64 or raw bytes
            pdf_bytes = body.encode() if isinstance(body, str) else body

        # Create tmp directory if it doesn't exist
        os.makedirs("tmp", exist_ok=True)

        # Save as output.pdf (will replace if exists)
        with open("tmp/output.pdf", "wb") as f:
            f.write(pdf_bytes)

        # Return a mock document ID
        return f"doc_{courseId}_{len(pdf_bytes)}"


def get_upload_pdf_service() -> MockUploadPDFService:
    return MockUploadPDFService()
