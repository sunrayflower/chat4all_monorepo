FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn boto3 motor
CMD ["uvicorn","uploader:app","--host","0.0.0.0","--port","8100"]
