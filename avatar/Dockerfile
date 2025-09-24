FROM python:3.10-slim

WORKDIR /app

# -- probably those imports can be removed cause they will be in the other containers

#RUN pip install --upgrade pip && \
#    pip install --index-url https://download.pytorch.org/whl/cu118 \
#        torch==2.5.1+cu118 torchvision==0.20.1+cu118 torchaudio==2.5.1+cu118

#COPY requirements.txt .

#RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]


