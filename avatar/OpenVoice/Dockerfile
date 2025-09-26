# Use an official PyTorch image with CUDA 11.8 pre-installed
FROM pytorch/pytorch:2.2.2-cuda11.8-cudnn8-runtime

# Set environment variables for non-interactive installs and Python behavior
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0 \
    DEBIAN_FRONTEND=noninteractive \
    PATH=/root/.local/bin:$PATH


RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    ffmpeg \
    curl \
    libsndfile1 \
    unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Clone the OpenVoice repository
RUN git clone https://github.com/myshell-ai/OpenVoice.git
WORKDIR /app/OpenVoice

RUN pip install "numpy<2.0" \
    && pip install -e . \
    && pip install git+https://github.com/myshell-ai/MeloTTS.git \
    && pip install fastapi uvicorn orjson \
    && python -m unidic download

RUN wget https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip \
    && unzip checkpoints_v2_0417.zip \
    && rm checkpoints_v2_0417.zip

ENV VOICE_GEN_DEBUG_WAV_PATH=./debug/mock.wav

COPY generate_audio_function.py /app/OpenVoice/generate_audio_function.py
COPY debug /app/OpenVoice/debug
EXPOSE 8000

CMD ["uvicorn", "generate_audio_function:app", "--host", "0.0.0.0", "--port", "8000"]