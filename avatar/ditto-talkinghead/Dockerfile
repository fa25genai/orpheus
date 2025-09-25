FROM pytorch/pytorch:2.5.1-cuda11.8-cudnn9-runtime

ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies like ffmpeg, which is required by the inference script
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

# Set Python environment variables for best practices in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install the Python packages from the original Dockerfile, plus fastapi and uvicorn
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
    numpy \
    onnxruntime \
    mediapipe \
    einops \
    # Add API-specific packages
    fastapi \
    uvicorn[standard]

# Set the working directory
WORKDIR /app

# Copy your application code and models into the container
# TODO: To support multiple avatars, we can not rely on this COPY command to copy the example files into the image.
COPY . /app/

# Expose the port the API server will run on
EXPOSE 8000

# Set default model paths via environment variables, as used in the startup script.
# These can be overridden during `docker run`.
ENV DITTO_DATA_ROOT=./checkpoints/ditto_pytorch
ENV DITTO_CFG_PKL=./checkpoints/ditto_cfg/v0.4_hubert_cfg_pytorch.pkl

# Command to run the Uvicorn server for your FastAPI application.
# It uses the filename and the FastAPI app instance name (`app`).
# --host 0.0.0.0 is crucial to make it accessible from outside the container.
CMD ["uvicorn", "fast_api_wrapper_for_ditto_inference:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]