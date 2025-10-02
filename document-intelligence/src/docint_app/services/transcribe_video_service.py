"""
Service zur parallelen Transkription großer Videodateien 
unter Verwendung von FFmpeg und Azure OpenAI's Whisper-Modell.
"""

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import AzureOpenAI, RateLimitError

# Laden der Umgebungsvariablen
load_dotenv() 

# --- Thread-safe print Mechanism ---
print_lock = Lock()

def safe_print(*args: Any, **kwargs: Any) -> None:
    """Thread-sichere Ausgabe."""
    with print_lock:
        print(*args, **kwargs)


class AzureVideoTranscriberService:
    """
    Kapselt die Logik zur Aufteilung, Audioextraktion und parallelen Transkription
    großer Videos mit Azure OpenAI Whisper.
    """

    # --- Standardkonfiguration ---
    _AZURE_OPENAI_ENDPOINT = "https://ase-us03.openai.azure.com/"
    _AZURE_WHISPER_DEPLOYMENT_NAME = "whisper" 
    _AZURE_API_VERSION = "2024-06-01" 
    _MAX_WORKERS = 4  # Anzahl paralleler Transkriptionsaufträge
    _CHUNK_DURATION_SECONDS = 120 # Standard-Chunk-Länge (2 Minuten)
    
    # --- Retry Konfiguration ---
    _RATE_LIMIT_DELAY_SECONDS = 45 # Wartezeit nach RateLimitError
    _MAX_RETRIES = 3 # Max. Anzahl der Wiederholungen

    def __init__(self, 
                 endpoint: Optional[str] = None, 
                 deployment_name: Optional[str] = None, 
                 api_version: Optional[str] = None,
                 max_workers: Optional[int] = None,
                 chunk_duration_seconds: Optional[int] = None,
                 max_retries: Optional[int] = None):
        
        # Konfiguration übernehmen oder Standardwerte verwenden
        self.endpoint = endpoint or self._AZURE_OPENAI_ENDPOINT
        self.deployment_name = deployment_name or self._AZURE_WHISPER_DEPLOYMENT_NAME
        self.api_version = api_version or self._AZURE_API_VERSION
        self.max_workers = max_workers or self._MAX_WORKERS
        self.chunk_duration_seconds = chunk_duration_seconds or self._CHUNK_DURATION_SECONDS
        self.max_retries = max_retries or self._MAX_RETRIES
        
        # API-Schlüssel aus Umgebungsvariable
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")

        # Client-Initialisierung
        self.client: Optional[AzureOpenAI] = self._initialize_client()

    def _initialize_client(self) -> Optional[AzureOpenAI]:
        """Initialisiert den AzureOpenAI Client."""
        if not self.api_key:
            safe_print("🔴 FEHLER: AZURE_OPENAI_API_KEY ist nicht gesetzt.")
            return None
        try:
            client = AzureOpenAI(
                api_key=self.api_key,  
                azure_endpoint=self.endpoint,
                api_version=self.api_version,
            )
            return client
        except Exception as e:
            safe_print(f"🔴 FEHLER beim Initialisieren des AzureOpenAI Clients: {e}")
            return None

    def _get_video_duration(self, video_path: str) -> float:
        """Ruft die Videodauer mit ffprobe ab."""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())

    def _extract_audio_chunk_ffmpeg(self, video_path: str, start_time: float, duration: float, output_path: str) -> None:
        """Extrahiert einen bestimmten Audio-Chunk mit FFmpeg."""
        cmd = [
            'ffmpeg', '-y', '-ss', str(start_time), '-t', str(duration),
            '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
            output_path
        ]
        # Unterdrückt die Ausgabe von ffmpeg
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def _transcribe_audio(self, file_path: str) -> str:
        """
        Transkribiert eine Audiodatei mit Azure OpenAI Whisper, 
        inkl. Wiederholungsmechanismus bei RateLimitError.
        """
        if not self.client:
            return "[Error: AzureOpenAI Client not initialized]"
            
        if os.path.getsize(file_path) > 25 * 1024 * 1024:
            safe_print("⚠️ Warnung: Datei ist größer als 25 MB. Die Azure API könnte fehlschlagen.")
                
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
                    safe_print(f"🛑 Rate Limit überschritten. Warte {self._RATE_LIMIT_DELAY_SECONDS}s vor Wiederholung {attempt + 2}/{self.max_retries}.")
                    time.sleep(self._RATE_LIMIT_DELAY_SECONDS)
                else:
                    safe_print(f"❌ Rate Limit nach {self.max_retries} Versuchen überschritten. Abbruch.")
                    return f"[Error: RateLimitError nach {self.max_retries} Wiederholungen]"
                    
            except FileNotFoundError:
                return f"Error: Datei nicht gefunden unter {file_path}"
            except Exception as e:
                error_message = str(e)
                if "status code 429" in error_message or "Rate limit" in error_message:
                    if attempt < self.max_retries - 1:
                        safe_print(f"🛑 Potenzieller Rate Limit (429) Fehler. Warte {self._RATE_LIMIT_DELAY_SECONDS}s vor Wiederholung {attempt + 2}/{self.max_retries}.")
                        time.sleep(self._RATE_LIMIT_DELAY_SECONDS)
                    else:
                        safe_print(f"❌ Potenzieller Rate Limit (429) Fehler nach {self.max_retries} Versuchen. Abbruch.")
                        return f"[Error: RateLimitError nach {self.max_retries} Wiederholungen]"
                else:
                    return f"Ein unbehandelter Fehler bei der Transkription ist aufgetreten: {e}"
        return "[Error: Unbekannter Fehler bei der Transkription]"

    def _process_chunk(self, video_path: str, chunk_info: Tuple[int, float, float, str]) -> Tuple[int, str]:
        """Verarbeitet einen einzelnen Chunk: extrahiert, transkribiert, räumt auf."""
        chunk_id, start_time, chunk_duration, base_name = chunk_info
        
        chunk_filename = f"{base_name}_chunk_{chunk_id}.mp3"
        
        try:
            safe_print(f"🎬 Chunk {chunk_id}: Extrahiere {start_time:.2f}s bis {start_time + chunk_duration:.2f}s")
            
            # Extraktion nur einmal durchführen
            if not os.path.exists(chunk_filename):
                self._extract_audio_chunk_ffmpeg(video_path, start_time, chunk_duration, chunk_filename)
            
            safe_print(f"🗣️  Chunk {chunk_id}: Transkribiere...")
            chunk_transcript = self._transcribe_audio(chunk_filename)
            
            if chunk_transcript.startswith("[Error"):
                 safe_print(f"❌ Chunk {chunk_id}: Transkription fehlgeschlagen.")
            else:
                safe_print(f"✅ Chunk {chunk_id}: Abgeschlossen")
            
            return chunk_id, chunk_transcript
            
        except Exception as e:
            safe_print(f"❌ Chunk {chunk_id}: Nicht behebbarer Fehler - {e}")
            return chunk_id, f"[Error in chunk {chunk_id}: {e}]"
            
        finally:
            # Aufräumen
            if os.path.exists(chunk_filename):
                os.remove(chunk_filename)

    def transcribe_video_parallel(self, video_path: str, chunk_duration_seconds: Optional[int] = None, max_workers: Optional[int] = None) -> str:
        """
        Hauptmethode: Führt die parallele Transkription eines großen Videos durch.
        """
        if not self.client:
            return "Transkription fehlgeschlagen: AzureOpenAI Client nicht initialisiert."

        chunk_dur = chunk_duration_seconds if chunk_duration_seconds is not None else self.chunk_duration_seconds
        workers = max_workers if max_workers is not None else self.max_workers
        
        try:
            safe_print("Rufe Videodauer ab...")
            total_duration = self._get_video_duration(video_path)
            safe_print(f"Gesamtdauer: {total_duration:.2f} Sekunden")
        except Exception as e:
            return f"❌ FEHLER beim Abrufen der Videodauer mit ffprobe: {e}"
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Vorbereiten aller Chunk-Informationen
        chunks_info = []
        for i, start_time in enumerate(range(0, int(total_duration) + 1, chunk_dur)):
            chunk_duration = min(chunk_dur, total_duration - start_time)
            # Vermeide das Erstellen von Chunks mit Dauer <= 0
            if chunk_duration <= 0.01:
                 continue
            chunk_id = i + 1
            chunks_info.append((chunk_id, float(start_time), chunk_duration, base_name))
        
        safe_print(f"Verarbeite {len(chunks_info)} Chunks parallel (max. {workers} Worker)...\n")
        
        # Speichere Ergebnisse mit Chunk-IDs zur Beibehaltung der Reihenfolge
        results: Dict[int, str] = {}
        
        # Parallele Verarbeitung der Chunks
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Übertrage alle Jobs
            future_to_chunk = {
                executor.submit(self._process_chunk, video_path, chunk_info): chunk_info[0] 
                for chunk_info in chunks_info
            }
            
            # Sammle Ergebnisse, sobald sie abgeschlossen sind
            for future in as_completed(future_to_chunk):
                try:
                    chunk_id, transcript = future.result()
                    results[chunk_id] = transcript
                except Exception as e:
                    chunk_id = future_to_chunk[future]
                    safe_print(f"❌ Unbekannter Fehler beim Abrufen des Ergebnisses für Chunk {chunk_id}: {e}")
                    results[chunk_id] = f"[Error beim Abrufen des Ergebnisses für Chunk {chunk_id}: {e}]"
        
        # Rekonstruiere die vollständige Transkription in der richtigen Reihenfolge
        full_transcript = " ".join(results[chunk_id] for chunk_id in sorted(results.keys()))
        
        return full_transcript


# --- Factory-Funktion (wie im Beispiel) ---
_instance: Optional[AzureVideoTranscriberService] = None

def get_transcriber_service() -> AzureVideoTranscriberService:
    """Stellt eine Singleton-Instanz des Transcriber Service bereit."""
    global _instance
    if _instance is None:
        _instance = AzureVideoTranscriberService()
    return _instance


# ----------------------------------------------------------------------
# ▶️ EXECUTION Beispiel (Optional: zur Demonstration der Nutzung)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    
    # Konfiguration der Mediendatei
    MEDIA_FILE_PATH = "vids/W01U02.mp4" 

    if not os.path.exists(MEDIA_FILE_PATH):
        safe_print(f"🔴 FEHLER: Der Dateipfad '{MEDIA_FILE_PATH}' existiert nicht.")
        safe_print("Bitte die Datei bereitstellen oder 'MEDIA_FILE_PATH' anpassen.")
    else:
        # Service instanziieren (oder Factory-Funktion verwenden: transcriber = get_transcriber_service())
        transcriber = AzureVideoTranscriberService(
            max_workers=4,
            chunk_duration_seconds=120
        )
        
        # Führen Sie die Transkription durch
        safe_print(f"\nStarte Transkription für {MEDIA_FILE_PATH}...")
        transcription = transcriber.transcribe_video_parallel(MEDIA_FILE_PATH)
        
        safe_print("\n" + "="*50)
        safe_print("--- Transkriptionsergebnis ---")
        safe_print("="*50)
        safe_print(transcription)
        safe_print("="*50)