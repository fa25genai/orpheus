import os

import nltk
import torch
from melo.api import TTS
from openvoice.api import ToneColorConverter

from openvoice import se_extractor

# Set device
device = "cuda:0" if torch.cuda.is_available() else "cpu"

# Defining paths
base_dir = os.path.dirname(os.path.abspath(__file__))  # folder where tts.py lives
ckpt_converter = os.path.join(base_dir, "checkpoints_v2", "converter")
output_dir = os.path.join(base_dir, "checkpoints_v2", "outputs_v2")
base_speakers_dir = os.path.join(base_dir, "checkpoints_v2", "base_speakers")
ses_dir = os.path.join(base_speakers_dir, "ses")

print("Looking for config at:", os.path.join(ckpt_converter, "config.json"))
print("Exists?", os.path.exists(os.path.join(ckpt_converter, "config.json")))

# Initialize ToneColorConverter
tone_color_converter = ToneColorConverter(os.path.join(ckpt_converter, "config.json"), device=device)
tone_color_converter.load_ckpt(os.path.join(ckpt_converter, "checkpoint.pth"))

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Here specify the reference speaker file you want to use
voice_file = "krusche_voice.mp3"
reference_speaker = os.path.join(base_dir, voice_file) # This is the voice you want to clone
target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, vad=True)


# Download required NLTK data first
print("Checking NLTK data...")
try:
    nltk.data.find('tokenizers/punkt')
    print("✓ Punkt tokenizer found")
except LookupError:
    print("Downloading Punkt tokenizer...")
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
    print("✓ Averaged perceptron tagger found")
except LookupError:
    print("Downloading averaged perceptron tagger...")
    nltk.download('averaged_perceptron_tagger', quiet=True)

# The texts to be synthesized, needs to be in the language of the TTS model
# You can add more languages/models if you want
texts = {
    'EN_NEWEST': "Hello students from FerienAkademie. How are you doing? It's beautiful weather today, I hope you are ready for a long hike. To tell more about myself, I love reading books and listening to music."
}

src_path = f'{output_dir}/tmp.wav'
# Experiment with these parameters:
speed = 1.0  # Slower speech (0.8-1.2)
noise_scale = 0.667  # More variation (0.5-0.8)
noise_scale_w = 0.8  # More expressiveness (0.6-1.0)
sdp_ratio = 0.5  # Balance between styles (0.0-1.0)

# Check if required variables exist
if 'target_se' not in locals() and 'target_se' not in globals():
    print("ERROR: target_se is not defined. You need to run the tone color extraction first!")
elif 'tone_color_converter' not in locals() and 'tone_color_converter' not in globals():
    print("ERROR: tone_color_converter is not defined. You need to initialize it first!")
else:
    for language, text in texts.items():
        print(f"Processing {language}...")
        model = TTS(language=language, device=device)
        speaker_ids = model.hps.data.spk2id
        
        for speaker_key in speaker_ids.keys():
            speaker_id = speaker_ids[speaker_key]
            speaker_key = speaker_key.lower().replace('_', '-')
            # Adjust the path as necessary
            ses_file_path = os.path.join(ses_dir, f"{speaker_key}.pth")
            
            if not os.path.exists(ses_file_path):
                print(f"File not found: {ses_file_path}")
                continue
                
            try:
                source_se = torch.load(ses_file_path, map_location=device)
                
                if torch.backends.mps.is_available() and device == 'cpu':
                    torch.backends.mps.is_available = lambda: False
                    
                print(f"Generating audio for {speaker_key}...")
                model.tts_to_file(text, speaker_id, src_path, speed=speed)
                # Save path for converted audio
                save_path = f'{output_dir}/output_v2_{language}_{speaker_key}.wav'

                encode_message = "@MyShell"
                tone_color_converter.convert(
                    audio_src_path=src_path, 
                    src_se=source_se, 
                    tgt_se=target_se, 
                    output_path=save_path,
                    message=encode_message)
                    
                print(f"✓ Saved: {save_path}")
                    
            except Exception as e:
                print(f"Error processing {speaker_key}: {e}")