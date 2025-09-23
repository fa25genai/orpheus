FROM pytorch/pytorch:2.5.1-cuda11.8-cudnn9-runtime

ARG DEBIAN_FRONTEND=noninteractive

# Python, build-essential, and core libs are already in the base image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    git \
 && rm -rf /var/lib/apt/lists/*

# Python quality-of-life
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install remaining pip packages.
RUN python3 -m pip install --no-cache-dir \
    librosa \
    tqdm \
    filetype \
    imageio \
    scikit-image \
    cython \
    cuda-python \
    imageio-ffmpeg \
    colored \
    polygraphy \
    numpy==2.0.1 \
    onnxruntime \
    mediapipe \
    einops

# App code
WORKDIR /app
COPY . /app

# Default entrypoint and command remain the same
ENTRYPOINT ["python3", "inference.py"]
CMD ["--data_root","./checkpoints/ditto_pytorch", \
     "--cfg_pkl","./checkpoints/ditto_cfg/v0.4_hubert_cfg_pytorch.pkl", \
     "--audio_path","./example/krusche_voice.wav", \
     "--source_path","./example/image_michal.png", \
     "--output_path","./tmp/result_michal.mp4"]
