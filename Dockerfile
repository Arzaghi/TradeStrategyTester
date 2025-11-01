# Use slim Python base image
FROM python:3.11-slim

# Declare build-time argument and set it as environment variable
ARG COMMIT_HASH
ENV COMMIT_HASH=$COMMIT_HASH

# Set working directory
WORKDIR /app

# Copy all source files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the main app
CMD ["python", "main.py"]