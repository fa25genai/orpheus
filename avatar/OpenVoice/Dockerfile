FROM python:3.9-bullseye

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=/root/.local/bin:$PATH

RUN apt-get update && apt-get install -y \
    git \
    wget \
    ffmpeg \
    curl \
    build-essential \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone https://github.com/myshell-ai/OpenVoice.git
WORKDIR /app/OpenVoice

RUN pip install -e . \
    && pip install git+https://github.com/myshell-ai/MeloTTS.git \
    && pip install fastapi uvicorn orjson \
    && python -m unidic download

# Download and extract checkpoints
RUN wget https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip \
    && unzip checkpoints_v2_0417.zip \
    && rm checkpoints_v2_0417.zip 

COPY generate_audio_function.py /app/OpenVoice/generate_audio_function.py
COPY kursche_voice.mp3 /app/OpenVoice/kursche_voice.mp3

EXPOSE 8000
CMD ["uvicorn", "generate_audio_function:app", "--host", "0.0.0.0", "--port", "8000"]
