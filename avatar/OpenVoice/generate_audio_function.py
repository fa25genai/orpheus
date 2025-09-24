import os
import torch
from openvoice import se_extractor
from openvoice.api import ToneColorConverter
import nltk
from melo.api import TTS
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict
from uuid import UUID

from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel, Field, UUID4, constr

app = FastAPI(
    title="Service Video-Generation APIs",
    version="0.1",
    description=(
        "API for the Orpheus video generation. Transforms fluent texts into "
        "interactive lecture videos with lifelike professor avatars."
    ),
)

# ---------------------------
# Pydantic models (from spec)
# ---------------------------

class Preferences(BaseModel):
    answerLength: Optional[Literal["short", "medium", "long"]] = None
    languageLevel: Optional[Literal["basic", "intermediate", "advanced"]] = None
    expertiseLevel: Optional[Literal["beginner", "intermediate", "advanced", "expert"]] = None
    includePictures: Optional[Literal["none", "few", "many"]] = None

class UserProfile(BaseModel):
    id: str
    role: Literal["student", "instructor"]
    language: Literal["german", "english"]
    preferences: Optional[Preferences] = None
    enrolledCourses: Optional[List[str]] = None


slide_texts = ["Welcome to the course on AI.", "In this slide, we will discuss machine learning."]
course_id = "course123"
voice_file = "kursche_voice.mp3"  # Path to a default voice file

def generate_audio(
    slide_texts: List[str],
    *,
    course_id: str, # 
    user_profile: UserProfile = None,
    voice_file: str
) -> List[str]:
    """
    Create per-slide audio files from text.

    Returns a list of file paths (one per slide).
    Replace the body with your TTS pipeline (e.g., Coqui, ElevenLabs, local TTS).
    """
    # TODO: implement real TTS.
    # For now, pretend we produced audio files:
    # Defining paths
   # Get the directory where THIS SCRIPT is located (not the current working directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Script directory: {script_dir}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Define ALL paths relative to the SCRIPT directory
    base_dir = script_dir  # This is the key fix!
    
    ckpt_converter = os.path.join(base_dir, "checkpoints_v2", "converter")
    output_dir = os.path.join(base_dir, "checkpoints_v2", "outputs_v2")
    base_speakers_dir = os.path.join(base_dir, "checkpoints_v2", "base_speakers")
    reference_speaker_dir = os.path.join(base_dir)
    ses_dir = os.path.join(base_speakers_dir, "ses")
    
    # Also make the voice file path absolute relative to script directory
    reference_speaker = os.path.join(reference_speaker_dir, voice_file)
    
    print(f"Looking for config at: {os.path.join(ckpt_converter, 'config.json')}")
    print(f"Config exists: {os.path.exists(os.path.join(ckpt_converter, 'config.json'))}")
    print(f"Voice file exists: {os.path.exists(reference_speaker)}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)

    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger', quiet=True)

    # Set device
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    # Initialize ToneColorConverter
    tone_color_converter = ToneColorConverter(os.path.join(ckpt_converter, "config.json"), device=device)
    tone_color_converter.load_ckpt(os.path.join(ckpt_converter, "checkpoint.pth"))

    try:
        import silero_vad
        print("✓ silero_vad is already installed")
    except ImportError:
        print("Installing silero_vad...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "silero-vad"])
        print("✓ silero_vad installed successfully")
        
    # Extract speaker embedding
    target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, vad=True)

    # TTS parameters
    speed = 1.0
    noise_scale = 0.667
    noise_scale_w = 0.8
    sdp_ratio = 0.5

    audio_paths = []
    
    # Process each slide text
    for i, text in enumerate(slide_texts):
        if not text.strip():  # Skip empty texts
            audio_paths.append("")
            continue
            
        # Generate audio for this slide
        # Choosing a language/model based on user profile could be added here
        language = 'EN_NEWEST'
        model = TTS(language=language, device=device)
        speaker_ids = model.hps.data.spk2id
        
        src_path = os.path.join(output_dir, f"tmp_{i}.wav")
        success = False
        
        # Try different speakers until one works
        for speaker_key in speaker_ids.keys():
            speaker_id = speaker_ids[speaker_key]
            normalized_speaker_key = speaker_key.lower().replace('_', '-')
            # Adjust the path as necessary
            ses_file_path = os.path.join(ses_dir, f"{normalized_speaker_key}.pth")
            
            if not os.path.exists(ses_file_path):
                continue
                
            try:
                source_se = torch.load(ses_file_path, map_location=device)
                
                # Generate base audio with given parameters
                model.tts_to_file(
                    text, 
                    speaker_id, 
                    src_path, 
                    speed=speed,
                    noise_scale=noise_scale,
                    noise_scale_w=noise_scale_w,
                    sdp_ratio=sdp_ratio
                )
                
                # Generate final output filename
                output_filename = f"{course_id}_slide_{i+1}.wav"
                save_path = os.path.join(output_dir, output_filename)
                
                # Convert voice
                tone_color_converter.convert(
                    audio_src_path=src_path, 
                    src_se=source_se, 
                    tgt_se=target_se, 
                    output_path=save_path,
                    message="@MyShell"
                )
                
                audio_paths.append(save_path)
                success = True
                print(f"✓ Generated audio for slide {i+1}: {save_path}")
                break  # Success, move to next slide
                
            except Exception as e:
                print(f"Error with speaker {speaker_key} for slide {i+1}: {e}")
                continue
        
        if not success:
            print(f"Failed to generate audio for slide {i+1}")
            audio_paths.append("")  # Add empty string for failed generation
            
        # Clean up temporary file
        try:
            if os.path.exists(src_path):
                os.remove(src_path)
        except:
            pass

    return audio_paths


'''
slide_texts = ["Welcome to the course on AI.", "In this slide, we will discuss machine learning."]
course_id = "course123"
voice_file = "kursche_voice.mp3" 
'''
def main():
    audio_paths = generate_audio(
        slide_texts=slide_texts,
        course_id=course_id,
        voice_file=voice_file
        # user_profile is now optional
    )
    
    print("Generated audio files:")
    for i, path in enumerate(audio_paths):
        print(f"Slide {i+1}: {path}")

if __name__ == '__main__':
    print('Starting audio generation...')
    main()