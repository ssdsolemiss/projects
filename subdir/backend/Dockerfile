# Use an official Python runtime as a parent image
FROM python:latest

# Set the working directory in the container
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libffi-dev \
        libssl-dev \
        npm \
    && rm -rf /var/lib/apt/lists/*


# Copy the backend requirements file
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application files into the container
COPY . /app

# Expose port 5000 (default Flask port)
EXPOSE 5000

# Define the command to run the Flask application
CMD ["python", "server.py"]
