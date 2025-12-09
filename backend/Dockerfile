# Use Python 3.10 Slim (Lightweight)
FROM python:3.10-slim

# 1. INSTALL SYSTEM DEPENDENCIES (FFmpeg + Aria2)
# This mimics what we did manually on Windows
RUN apt-get update && \
    apt-get install -y ffmpeg aria2 && \
    apt-get clean

# 2. SETUP WORKDIR
WORKDIR /app

# 3. INSTALL PYTHON PACKAGES
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. COPY CODE
COPY . .

# 5. CREATE DOWNLOADS FOLDER
RUN mkdir -p downloads

# 6. EXPOSE PORT
EXPOSE 8000

# 7. RUN COMMAND
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]