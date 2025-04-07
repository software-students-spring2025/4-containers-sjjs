# Base image with Python
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Copy all project files into container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run your app
CMD ["python", "voiceai.py"]
