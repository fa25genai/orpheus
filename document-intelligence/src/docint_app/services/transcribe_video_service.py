import os
from openai import AzureOpenAI
from pathlib import Path
from moviepy import VideoFileClip # Import moviepy for audio extraction

# --- Configuration ---
# IMPORTANT: Replace these placeholders with your actual values
AZURE_OPENAI_ENDPOINT = "https://ase-us03.openai.azure.com/"
AZURE_WHISPER_DEPLOYMENT_NAME = "whisper" 
AZURE_API_VERSION = "2024-06-01" 
AZURE_OPENAI_API_KEY = "a3ec8df6e7934d9fa2c62ce2372eddee"

# Path to your video file.
MEDIA_FILE_PATH = "vids/W01U01.mp4" 
# Output path for the extracted audio file. Using .mp3 is common.
OUTPUT_AUDIO_PATH = "vids/extracted_audio.mp3" 

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



# ----------------------------------------------------------------------
# 🗣️ WHISPER FUNCTION (from previous response)
# ----------------------------------------------------------------------

def transcribe_large_video(video_path, chunk_duration_seconds=60):
    # 1. Extract the full audio from the video
    clip = VideoFileClip(video_path)
    audio = clip.audio
    
    # Get the total duration of the audio in seconds
    total_duration = audio.duration
    
    # Base name for chunks
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    full_transcript = ""
    print(f"Total audio duration: {total_duration:.2f} seconds")
    
    # 2. Iterate through the audio, creating chunks
    for i, start_time in enumerate(range(0, int(total_duration), chunk_duration_seconds)):
        end_time = min(start_time + chunk_duration_seconds, total_duration)
        
        # Create a subclip (chunk)
        chunk = audio.subclipped(start_time, end_time)
        
        # Create a unique filename for the chunk
        chunk_filename = f"{base_name}_chunk_{i+1}.mp3"
        
        print(f"Processing chunk {i+1}: {start_time:.2f}s to {end_time:.2f}s")
        
        # Write the chunk to a file
        chunk.write_audiofile(chunk_filename)

        # 3. Transcribe the small chunk (THIS IS WHERE YOU CALL AZURE API)
        
        # ⚠️ Replace this Mock Call with your actual Azure API call
        chunk_transcript = transcribe_audio(chunk_filename,AZURE_WHISPER_DEPLOYMENT_NAME) 
        
        # 4. Combine the transcripts
        full_transcript += chunk_transcript + " " 
        
        # Clean up the temporary chunk file
        os.remove(chunk_filename)
        
    # Final cleanup
    audio.close()
    clip.close()
    return full_transcript

# ----------------------------------------------------------------------
# 🗣️ WHISPER FUNCTION (from previous response)
# ----------------------------------------------------------------------
def transcribe_audio(file_path: str, deployment_name: str):
    """
    Transcribes an audio file using the Azure OpenAI Whisper deployment.
    """
    try:
        if os.path.getsize(file_path) > 25 * 1024 * 1024:
            print("⚠️ Warning: File is larger than 25 MB. The Azure API might fail.")
            print("It's highly recommended to chunk the audio before uploading.")
            
        with open(file_path, "rb") as audio_file:
            print(f"Uploading and processing audio file: {Path(file_path).name}...")
            
            # Using translations.create() as requested, which can also transcribe English audio
            result = client.audio.translations.create(
                model=deployment_name, # In Azure, the model parameter is the deployment name
                file=audio_file,
            )

        transcribed_text = result.text
        return transcribed_text

    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"An error occurred during transcription: {e}"

# ----------------------------------------------------------------------
# ▶️ EXECUTION
# ----------------------------------------------------------------------
if __name__ == "__main__":
    
    if not os.path.exists(MEDIA_FILE_PATH):
        print(f"🔴 ERROR: The file path '{MEDIA_FILE_PATH}' does not exist.")
        print("Please update the 'MEDIA_FILE_PATH' variable.")
    else:
        
        transcription = transcribe_large_video(MEDIA_FILE_PATH, chunk_duration_seconds=120)
        
        # 4. Print the result
        print("\n--- Transcription Result ---")
        print(transcription)
        print("----------------------------")
        
    
