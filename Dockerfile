FROM python:3.11-slim

WORKDIR /addon

# Copy all addon files
COPY . .

# Install only required dependencies
RUN pip install --no-cache-dir pyyaml python-dateutil pytz requests

# Start the addon
CMD ["python3", "run.py"]
