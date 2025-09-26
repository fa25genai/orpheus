# Use an official PyTorch image with CUDA 11.8 pre-installed
FROM pytorch/pytorch:2.2.2-cuda11.8-cudnn8-devel

# Set environment variables for non-interactive installs and Python behavior
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH=/root/.local/bin:$PATH

# Install system-level dependencies required by the application
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    ffmpeg \
    curl \
    libsndfile1 \
    unzip \
    # build-essential is often included in -devel images but explicit is safer
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Clone the OpenVoice repository
RUN git clone https://github.com/myshell-ai/OpenVoice.git
WORKDIR /app/OpenVoice

# Install all Python dependencies in a single layer for better caching
# Pin numpy to version 1.x to meet the requirement
RUN pip install "numpy<2.0" \
    && pip install -e . \
    && pip install git+https://github.com/myshell-ai/MeloTTS.git \
    && pip install fastapi uvicorn orjson \
    && python -m unidic download

# Download and extract the pre-trained model checkpoints
RUN wget https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip \
    && unzip checkpoints_v2_0417.zip \
    && rm checkpoints_v2_0417.zip \

RUN mkdir -p $HF_HOME && \
    TRANSFORMERS_CACHE=$HF_HOME python -c "from transformers import AutoTokenizer, AutoModel; \
    AutoTokenizer.from_pretrained('bert-base-uncased'); \
    AutoModel.from_pretrained('bert-base-uncased'); \
    AutoTokenizer.from_pretrained('bert-base-multilingual-cased'); \
    AutoModel.from_pretrained('bert-base-multilingual-cased')"

# Copy your custom application file into the container
COPY generate_audio_function.py /app/OpenVoice/generate_audio_function.py

# Expose the port the application will run on
EXPOSE 8000

# Define the command to run the Uvicorn server
CMD ["uvicorn", "generate_audio_function:app", "--host", "0.0.0.0", "--port", "8000"]