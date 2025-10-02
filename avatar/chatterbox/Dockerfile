# Base image already contains torch 2.5.1 + CUDA 11.8
FROM pytorch/pytorch:2.5.1-cuda11.8-cudnn9-runtime

# Avoid .pyc files, ensure logs are flushed, disable pip cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Make sure pip prefers CUDA 11.8 wheels for torch/torchaudio
ENV PIP_INDEX_URL=https://download.pytorch.org/whl/cu118 \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple

# System deps commonly needed for audio (librosa/soundfile) and builds
# - libsndfile1: required by soundfile/librosa
# - ffmpeg: useful for audio/video I/O
# - build-essential: safety for any package that needs compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip toolchain
RUN pip install --upgrade pip setuptools wheel

# Workdir for the app
WORKDIR /app

# Copy project metadata first (better layer caching when only source changes)
COPY pyproject.toml ./

# Copy source
# Your package is configured with setuptools to find packages under "src/"
COPY src ./src

# Install the project.
RUN pip install .
RUN pip install inflect python-multipart uvicorn orjson

# Copy the run script
COPY generate_audio.py ./generate_audio.py

# Run the script on container start
CMD ["uvicorn", "generate_audio:app", "--host", "0.0.0.0", "--port", "8000"]
