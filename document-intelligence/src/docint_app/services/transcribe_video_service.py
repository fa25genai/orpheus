import os
import subprocess
from openai import AzureOpenAI
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

load_dotenv() 

# --- Configuration ---
AZURE_OPENAI_ENDPOINT = "https://ase-us03.openai.azure.com/"
AZURE_WHISPER_DEPLOYMENT_NAME = "whisper" 
AZURE_API_VERSION = "2024-06-01" 
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

MEDIA_FILE_PATH = "vids/W02U03.mp4" 
MAX_WORKERS = 4  # Number of parallel transcription jobs

# --- Client Initialization ---
try:
    client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,  
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_API_VERSION,
    )
except Exception as e:
    print(f"Error initializing AzureOpenAI client: {e}")
    exit()

# Thread-safe print
print_lock = Lock()

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


def get_video_duration(video_path):
    """Get video duration using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())


def extract_audio_chunk_ffmpeg(video_path, start_time, duration, output_path):
    """Extract a specific audio chunk using FFmpeg"""
    cmd = [
        'ffmpeg', '-y', '-ss', str(start_time), '-t', str(duration),
        '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def transcribe_audio(file_path: str, deployment_name: str):
    """Transcribes an audio file using Azure OpenAI Whisper"""
    try:
        if os.path.getsize(file_path) > 25 * 1024 * 1024:
            safe_print("⚠️ Warning: File is larger than 25 MB. The Azure API might fail.")
            
        with open(file_path, "rb") as audio_file:
            result = client.audio.translations.create(
                model=deployment_name,
                file=audio_file,
            )
        return result.text

    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"An error occurred during transcription: {e}"


def process_chunk(video_path, chunk_info):
    """Process a single chunk: extract, transcribe, cleanup"""
    chunk_id, start_time, chunk_duration, base_name, deployment_name = chunk_info
    
    chunk_filename = f"{base_name}_chunk_{chunk_id}.mp3"
    
    try:
        safe_print(f"🎬 Chunk {chunk_id}: Extracting {start_time:.2f}s to {start_time + chunk_duration:.2f}s")
        extract_audio_chunk_ffmpeg(video_path, start_time, chunk_duration, chunk_filename)
        
        safe_print(f"🗣️  Chunk {chunk_id}: Transcribing...")
        chunk_transcript = transcribe_audio(chunk_filename, deployment_name)
        
        safe_print(f"✅ Chunk {chunk_id}: Complete")
        
        return chunk_id, chunk_transcript
        
    except Exception as e:
        safe_print(f"❌ Chunk {chunk_id}: Error - {e}")
        return chunk_id, f"[Error in chunk {chunk_id}: {e}]"
        
    finally:
        # Cleanup
        if os.path.exists(chunk_filename):
            os.remove(chunk_filename)


def transcribe_large_video_parallel(video_path, chunk_duration_seconds=120, max_workers=4):
    """Fast parallel video transcription using FFmpeg and ThreadPoolExecutor"""
    
    print(f"Getting video duration...")
    total_duration = get_video_duration(video_path)
    print(f"Total duration: {total_duration:.2f} seconds")
    
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # Prepare all chunk information
    chunks_info = []
    for i, start_time in enumerate(range(0, int(total_duration), chunk_duration_seconds)):
        chunk_duration = min(chunk_duration_seconds, total_duration - start_time)
        chunk_id = i + 1
        chunks_info.append((chunk_id, start_time, chunk_duration, base_name, AZURE_WHISPER_DEPLOYMENT_NAME))
    
    print(f"Processing {len(chunks_info)} chunks in parallel (max {max_workers} workers)...\n")
    
    # Store results with chunk IDs to maintain order
    results = {}
    
    # Process chunks in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        future_to_chunk = {
            executor.submit(process_chunk, video_path, chunk_info): chunk_info[0] 
            for chunk_info in chunks_info
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            chunk_id, transcript = future.result()
            results[chunk_id] = transcript
    
    # Reconstruct transcript in correct order
    full_transcript = " ".join(results[chunk_id] for chunk_id in sorted(results.keys()))
    
    return full_transcript


# ----------------------------------------------------------------------
# ▶️ EXECUTION
# ----------------------------------------------------------------------
if __name__ == "__main__":
    
    if not os.path.exists(MEDIA_FILE_PATH):
        print(f"🔴 ERROR: The file path '{MEDIA_FILE_PATH}' does not exist.")
        print("Please update the 'MEDIA_FILE_PATH' variable.")
    else:
        transcription = transcribe_large_video_parallel(
            MEDIA_FILE_PATH, 
            chunk_duration_seconds=120,
            max_workers=MAX_WORKERS
        )
        
        print("\n" + "="*50)
        print("--- Transcription Result ---")
        print("="*50)
        print(transcription)
        print("="*50)