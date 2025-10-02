import re
from pathlib import Path

import inflect
import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


def numbers_to_words(text: str) -> str:
    p = inflect.engine()

    def repl(m):
        s = m.group(0)
        # ordinal numerals like 21st, 3rd
        m_ord = re.fullmatch(r"(\d+)(st|nd|rd|th)", s, re.I)
        if m_ord:
            return p.number_to_words(int(m_ord.group(1)), ordinal=True)
        # decimals or integers
        if "." in s:
            # e.g., 3.14 -> "three point one four"
            return p.number_to_words(s, wantlist=False)
        return p.number_to_words(int(s))

    return re.sub(r"\d+(?:\.\d+)?|(?:\d+(?:st|nd|rd|th))", repl, text)


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def generate_audio_chatterbox(voiceTrack: str | None = None):
    device = _pick_device()
    print(f"Using device: {device}")

    model = ChatterboxMultilingualTTS.from_pretrained(device=device)

    if not voiceTrack:
        voiceTrack = "Hello everyone! I want to give you a 182 minute talk about for-loops and the great university of Munich."

    voiceTrack = numbers_to_words(voiceTrack)

    # Default voice
    wav = model.generate(voiceTrack, language_id="en")  # <-- use voiceTrack
    ta.save("test-default.wav", wav, model.sr)

    # Optional voice prompt
    audio_prompt_path = Path("krusche_voice.mp3")
    if audio_prompt_path.is_file():
        wav = model.generate(voiceTrack, audio_prompt_path=audio_prompt_path, language_id="en")
        ta.save("test-krusche.wav", wav, model.sr)
    else:
        print(f"[warn] audio prompt not found: {audio_prompt_path} (skipping)")


if __name__ == "__main__":
    voiceTrack = "This is such a beautiful day. I could do like 1001 push ups and in the 3rd set of my workout, I could do 111 pull ups."
    generate_audio_chatterbox(voiceTrack=voiceTrack)
