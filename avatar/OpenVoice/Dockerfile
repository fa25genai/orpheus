# Runtime image building on the pre-built OpenVoice base image
FROM orpheus-openvoice-base:latest

# Ensure we are inside the repository cloned in the base image
WORKDIR /app/OpenVoice

ENV VOICE_GEN_DEBUG_WAV_PATH=./debug/mock.wav

COPY generate_audio_function.py /app/OpenVoice/generate_audio_function.py
COPY debug /app/OpenVoice/debug
EXPOSE 8000

CMD ["uvicorn", "generate_audio_function:app", "--host", "0.0.0.0", "--port", "8000"]
