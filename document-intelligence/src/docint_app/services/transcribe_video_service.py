"""
Service for parallel transcription of large video files
using FFmpeg and Azure OpenAI's Whisper model.
"""

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import AzureOpenAI, RateLimitError

# Loading the environment variables
load_dotenv() 

# --- Thread-safe print Mechanism ---
print_lock = Lock()

def safe_print(*args: Any, **kwargs: Any) -> None:
    """Thread-safe output."""
    with print_lock:
        print(*args, **kwargs)


class AzureVideoTranscriberService:
    """
    Encapsulates the logic for splitting, audio extraction, and parallel transcription
    of large videos with Azure OpenAI Whisper.
    """

     # --- Default configuration ---
    _AZURE_OPENAI_ENDPOINT = "https://ase-us03.openai.azure.com/"
    _AZURE_WHISPER_DEPLOYMENT_NAME = "whisper" 
    _AZURE_API_VERSION = "2024-06-01" 
    _MAX_WORKERS = 4  
    _CHUNK_DURATION_SECONDS = 120 
    
    # --- Retry configuration ---
    _RATE_LIMIT_DELAY_SECONDS = 45 
    _MAX_RETRIES = 3

    def __init__(self, 
                 endpoint: Optional[str] = None, 
                 deployment_name: Optional[str] = None, 
                 api_version: Optional[str] = None,
                 max_workers: Optional[int] = None,
                 chunk_duration_seconds: Optional[int] = None,
                 max_retries: Optional[int] = None):
        
        # Use provided configuration or default values
        self.endpoint = endpoint or self._AZURE_OPENAI_ENDPOINT
        self.deployment_name = deployment_name or self._AZURE_WHISPER_DEPLOYMENT_NAME
        self.api_version = api_version or self._AZURE_API_VERSION
        self.max_workers = max_workers or self._MAX_WORKERS
        self.chunk_duration_seconds = chunk_duration_seconds or self._CHUNK_DURATION_SECONDS
        self.max_retries = max_retries or self._MAX_RETRIES
        
        # API key from environment variable
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")

        # Client initialization
        self.client: Optional[AzureOpenAI] = self._initialize_client()

    def _initialize_client(self) -> Optional[AzureOpenAI]:
        """Initializes the AzureOpenAI Client."""
        if not self.api_key:
            safe_print("🔴 ERROR: AZURE_OPENAI_API_KEY is not set.")
            return None
        try:
            client = AzureOpenAI(
                api_key=self.api_key,  
                azure_endpoint=self.endpoint,
                api_version=self.api_version,
            )
            return client
        except Exception as e:
            safe_print(f"🔴 ERROR initializing the AzureOpenAI client: {e}")
            return None

    def _get_video_duration(self, video_path: str) -> float:
        """Retrieves video duration using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())

    def _extract_audio_chunk_ffmpeg(self, video_path: str, start_time: float, duration: float, output_path: str) -> None:
        """Extracts a specific audio chunk using FFmpeg."""
        cmd = [
            'ffmpeg', '-y', '-ss', str(start_time), '-t', str(duration),
            '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
            output_path
        ]
        # Suppresses ffmpeg output
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def _transcribe_audio(self, file_path: str) -> str:
        """
        Transcribes an audio file using Azure OpenAI Whisper,
        including retry mechanism for RateLimitError.
        """
        if not self.client:
            return "[Error: AzureOpenAI Client not initialized]"
            
        if os.path.getsize(file_path) > 25 * 1024 * 1024:
            safe_print("Warning: File is larger than 25 MB. The Azure API may fail.")
                
        for attempt in range(self.max_retries):
            try:
                with open(file_path, "rb") as audio_file:
                    audio_file.seek(0) 
                    result = self.client.audio.translations.create(
                        model=self.deployment_name,
                        file=audio_file,
                    )
                return str(result.text)

            except RateLimitError:
                if attempt < self.max_retries - 1:
                    safe_print(f"🛑 Rate limit exceeded. Waiting {self._RATE_LIMIT_DELAY_SECONDS}s before retry {attempt + 2}/{self.max_retries}.")
                    time.sleep(self._RATE_LIMIT_DELAY_SECONDS)
                else:
                    safe_print(f"❌ Rate limit exceeded after {self.max_retries} attempts. Aborting.")
                    return f"[Error: RateLimitError after {self.max_retries} attempts]"
                    
            except FileNotFoundError:
                return f"Error: File not found at {file_path}"
            except Exception as e:
                error_message = str(e)
                if "status code 429" in error_message or "Rate limit" in error_message:
                    if attempt < self.max_retries - 1:
                        safe_print(f"🛑 Potential Rate Limit (429) error. Waiting {self._RATE_LIMIT_DELAY_SECONDS}s before retry {attempt + 2}/{self.max_retries}.")
                        time.sleep(self._RATE_LIMIT_DELAY_SECONDS)
                    else:
                        safe_print(f"❌ Potential Rate Limit (429) error after {self.max_retries} attempts. Aborting.")
                        return f"[Error: RateLimitError nach {self.max_retries} Wiederholungen]"
                else:
                    return f"An unhandled error occurred during transcription: {e}"
        return "[Error: Unknown error during transcription]"

    def _process_chunk(self, video_path: str, chunk_info: Tuple[int, float, float, str]) -> Tuple[int, str]:
        """Processes a single chunk: extracts, transcribes, cleans up."""
        chunk_id, start_time, chunk_duration, base_name = chunk_info
        
        chunk_filename = f"{base_name}_chunk_{chunk_id}.mp3"
        
        try:
            safe_print(f"🎬 Chunk {chunk_id}: Extracting {start_time:.2f}s to {start_time + chunk_duration:.2f}s")
            
            # Extraktion nur einmal durchführen
            if not os.path.exists(chunk_filename):
                self._extract_audio_chunk_ffmpeg(video_path, start_time, chunk_duration, chunk_filename)
            
            safe_print(f"🗣️  Chunk {chunk_id}: Transcribing...")
            chunk_transcript = self._transcribe_audio(chunk_filename)
            
            if chunk_transcript.startswith("[Error"):
                 safe_print(f"❌ Chunk {chunk_id}: Transcription failed.")
            else:
                safe_print(f"✅ Chunk {chunk_id}: Completed")
            
            return chunk_id, chunk_transcript
            
        except Exception as e:
            safe_print(f"❌ Chunk {chunk_id}: Unrecoverable error - {e}")
            return chunk_id, f"[Error in chunk {chunk_id}: {e}]"
            
        finally:
            # tidy up the chunk file
            if os.path.exists(chunk_filename):
                os.remove(chunk_filename)

    def transcribe_video_parallel(self, video_path: str, chunk_duration_seconds: Optional[int] = None, max_workers: Optional[int] = None) -> str:
        """
        Main method: Performs parallel transcription of a large video.
        """
        if not self.client:
            return "Transcription failed: AzureOpenAI Client not initialized."

        chunk_dur = chunk_duration_seconds if chunk_duration_seconds is not None else self.chunk_duration_seconds
        workers = max_workers if max_workers is not None else self.max_workers
        
        try:
            safe_print("Retrieving video duration...")
            total_duration = self._get_video_duration(video_path)
            safe_print(f"Total duration: {total_duration:.2f} seconds")
        except Exception as e:
            return f"❌ ERROR retrieving video duration with ffprobe: {e}"
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Prepare chunk info list
        chunks_info = []
        for i, start_time in enumerate(range(0, int(total_duration) + 1, chunk_dur)):
            chunk_duration = min(chunk_dur, total_duration - start_time)
            # Avoid creating chunks with duration <= 0
            if chunk_duration <= 0.01:
                 continue
            chunk_id = i + 1
            chunks_info.append((chunk_id, float(start_time), chunk_duration, base_name))
        
        safe_print(f"Process {len(chunks_info)} chunks parallel (max. {workers} workers)...\n")
        
        # save results with chunk IDs to maintain order
        results: Dict[int, str] = {}
        
        # parallel processing of chunks
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all jobs
            future_to_chunk = {
                executor.submit(self._process_chunk, video_path, chunk_info): chunk_info[0] 
                for chunk_info in chunks_info
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                try:
                    chunk_id, transcript = future.result()
                    results[chunk_id] = transcript
                except Exception as e:
                    chunk_id = future_to_chunk[future]
                    safe_print(f"❌ Unknown error while retrieving result for chunk {chunk_id}: {e}")
                    results[chunk_id] = f"[Error retrieving result for chunk {chunk_id}: {e}]"
        
        # Reassemble full transcript in correct order
        full_transcript = " ".join(results[chunk_id] for chunk_id in sorted(results.keys()))
        
        return full_transcript


# --- Factory Function (as in example) ---
_instance: Optional[AzureVideoTranscriberService] = None

def get_transcriber_service() -> AzureVideoTranscriberService:
    """Provides a singleton instance of the Transcriber Service."""
    global _instance
    if _instance is None:
        _instance = AzureVideoTranscriberService()
    return _instance


# ----------------------------------------------------------------------
# ▶️ Direct Execution for Testing (Optional: to demonstrate usage)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    
    # Media file configuration
    MEDIA_FILE_PATH = "vids/W01U02.mp4" 

    if not os.path.exists(MEDIA_FILE_PATH):
        safe_print(f"🔴 ERROR: The file path '{MEDIA_FILE_PATH}' does not exist.")
        safe_print("Please provide the file or adjust 'MEDIA_FILE_PATH'.")
    else:
        # Instantiate service (or use factory function: transcriber = get_transcriber_service())
        transcriber = AzureVideoTranscriberService(
            max_workers=4,
            chunk_duration_seconds=120  
        )
        
        # Start transcription
        safe_print(f"\nStarting transcription for {MEDIA_FILE_PATH}...")
        transcription = transcriber.transcribe_video_parallel(MEDIA_FILE_PATH)
        
        safe_print("\n" + "="*50)
        safe_print("--- Transcription Result ---")
        safe_print("="*50)
        safe_print(transcription)
        safe_print("="*50)