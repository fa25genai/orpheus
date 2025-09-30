"""
Video Upload Service
Processes video files by generating transcription and storing video metadata 
and transcription text in a vector database.
"""

import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional, Tuple, Union

from pydantic import StrictBytes, StrictStr

from docint_app.services.ingestion_service import IngestionService  # Annahme: Der existierende IngestionService

# --- Importe der Kernkomponenten (Annahme basierend auf Ihrem Projektstruktur) ---
# Import des Transkriptions- und Verarbeitungs-Service aus der vorherigen Antwort
from docint_app.services.transcribe_video_service import AzureVideoTranscriberService, get_transcriber_service

# --- Hilfsfunktion (zur thread-sicheren Ausgabe, beibehalten) ---
print_lock = Lock()
def safe_print(*args: Any, **kwargs: Any) -> None:
    """Thread-sichere Ausgabe."""
    with print_lock:
        print(*args, **kwargs)
# --------------------------------------------------------------------------------


# 

## II. Video Upload Service Implementierung


class VideoUploadService:
    def __init__(self, base_url: str = "http://docint-weaviate:28947", storage_dir: str = "uploaded_videos"):
        """
        Initialize the Video upload service with all required components.

        Args:
            base_url: Weaviate database URL
            storage_dir: Directory to store uploaded videos (optional, da der ProcessingService
                         die temporäre Speicherung übernimmt, aber für persistente Speicherung nützlich).
        """
        base_url = os.getenv("WEAVIATE_URL", base_url)
        safe_print(f"Initializing VideoUploadService with base_url: {base_url}")
        
        try:
            # Nutzt den Service, der die Azure-Transkriptionslogik kapselt
            self.video_processor: AzureVideoTranscriberService = get_transcriber_service()
            self.ingestion_service = IngestionService(base_url=base_url)
            
            # Persistenter Speicherort (optional, nur für langfristige Ablage des Originals)
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(exist_ok=True)
            
            safe_print("Successfully initialized all Video processing services")
        except Exception as e:
            safe_print(f"Failed to initialize VideoUploadService: {e}")
            raise

    def _save_video(self, course_id: str, original_filename: str, video_bytes: bytes) -> Tuple[str, str]:
        """
        Save the original video to persistent storage with course name and timestamp.
        
        Args:
            course_id: Course identifier
            original_filename: The name of the file being uploaded (e.g., 'lecture.mp4')
            video_bytes: Video file bytes

        Returns:
            Tuple of (saved_file_path, document_id)
        """
        # Erstelle Zeitstempel und bereinige den Dateinamen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_suffix = Path(original_filename).suffix or ".mp4"
        base_name = Path(original_filename).stem or "video"

        # Erstelle Kursverzeichnis
        course_dir = self.storage_dir / course_id
        course_dir.mkdir(exist_ok=True)

        # Generiere Dokument-ID und Dateiname
        document_id = f"{course_id}_{base_name}_{timestamp}"
        filename = f"{document_id}{file_suffix}"
        file_path = course_dir / filename

        # Speichere die Videodatei
        with open(file_path, "wb") as f:
            f.write(video_bytes)

        safe_print(f"Saved original video to: {file_path} (Document ID: {document_id})")
        return str(file_path), document_id

    def _extract_video_info(self, body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]]) -> Tuple[bytes, str]:
        """
        Extract video bytes and original filename from different input formats.
        
        Args:
            body: Video data in various formats

        Returns:
            Tuple of (video_bytes, original_filename)
        """
        original_filename = "upload_default.mp4" # Standardwert
        video_bytes = b''
        
        if isinstance(body, tuple):
            # Format: (filename, video_bytes)
            original_filename, video_bytes = body
            if isinstance(video_bytes, str):
                video_bytes = video_bytes.encode()
        elif isinstance(body, bytes):
            video_bytes = body
        elif isinstance(body, str):
            # Annahme: Bei String ist es entweder Base64-kodiert oder der Rohinhalt (encode)
            try:
                import base64
                video_bytes = base64.b64decode(body)
            except Exception:
                video_bytes = body.encode()
        else:
            raise ValueError(f"Unsupported body format: {type(body)}")

        if not isinstance(video_bytes, bytes):
            raise TypeError("Video body could not be converted to bytes.")
            
        return video_bytes, original_filename


    async def upload_video(self, course_id: str, body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]]) -> str:
        """
        Process and upload video to vector database after transcription.

        Args:
            course_id: Unique course identifier
            body: Video file data (bytes, string, or tuple of filename and bytes)

        Returns:
            Document ID string
        """
        safe_print(f"\n🎬 Starting Video upload for course_id: '{course_id}'")

        if not course_id or not course_id.strip():
            raise ValueError("course_id must be a non-empty string")
        
        try:
            # 1. Video-Bytes und Dateiname extrahieren
            video_bytes, original_filename = self._extract_video_info(body)
            video_path, document_id = self._save_video(course_id, original_filename, video_bytes)
            print(f"video saved with ID: {document_id}")
            # 2. Transkription durchführen (nutzt den VideoProcessingService)
            # Hinweis: Der VideoProcessingService speichert die Videodaten temporär 
            # für FFmpeg und Azure, um die Transkription zu ermöglichen.
            print(video_path)
            transcription = get_transcriber_service().transcribe_video_parallel(video_path=video_path)
            #print(f"TRANSCRIPTION DONE: {transcription}")
        
            
            # 4. Ingest in die Vektordatenbank
            # Da es ein Video ist, injizieren wir das Transkript als einen Textblock.
            safe_print("Ingesting data into vector database...")
            
            # Metadaten für das Video
            """video_metadata = { # dont need metadata for now -- delete everything that is not used
                "document_type": "Video",
                "original_filename": original_filename,
                "storage_path": video_path,
                "duration_seconds": self.video_processor.transcriber._get_video_duration(video_path) # Dauer abrufen
            }"""

            # Verwende den Ingestion Service, um das Transkript zu speichern
            # Wir behandeln das gesamte Transkript als EINEN grossen Text-Slide/Dokument
            await self.ingestion_service.ingest_video_transcription(
                course_id=course_id,
                video_id=document_id,
                transcription_text=transcription
            )

            safe_print(f"Video upload completed successfully! Document ID: {document_id}")
            return document_id

        except Exception as e:
            safe_print(f"Video upload failed: {e}")
            raise


# --- Factory-Funktion ---
_video_instance: Optional[VideoUploadService] = None

def get_upload_video_service() -> VideoUploadService:
    """Singleton accessor for VideoUploadService"""
    global _video_instance
    if _video_instance is None:
        _video_instance = VideoUploadService()
    return _video_instance
