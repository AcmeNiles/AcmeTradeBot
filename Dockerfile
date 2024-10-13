# Use the official lightweight Python image.
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Enter explicit working dir
WORKDIR /app

# Copy requirements and install before copying code for faster builds
COPY requirements.txt requirements.txt

# install requirements
RUN pip install -r requirements.txt

# Set non-root user
RUN groupadd -r service && useradd --no-log-init -r -g service service
USER service

# Copy local code to the container image.
COPY actions actions
COPY handlers handlers
COPY utils utils
COPY config.py config.py
COPY messages_photos.py messages_photos.py
COPY main.py main.py

ENTRYPOINT ["python", "main.py"]
