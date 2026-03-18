FROM python:3.12-slim

WORKDIR /app

# Install system fonts for Pillow text rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8888

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8888"]
