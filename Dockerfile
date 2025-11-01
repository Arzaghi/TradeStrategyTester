# Use slim Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all source files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the main app
CMD ["python", "main.py"]