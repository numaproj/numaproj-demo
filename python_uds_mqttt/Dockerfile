FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY mqtt_udsource.py .

# Create directory for server info
RUN mkdir -p /var/run/numaflow

# Set environment variables with defaults
ENV MQTT_BROKER=localhost
ENV MQTT_PORT=1883
ENV MQTT_TOPIC=test

# Run the source
CMD ["python", "-u", "mqtt_udsource.py"]