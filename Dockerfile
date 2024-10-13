# Use the official lightweight Python image.
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Enter explicit working dir
WORKDIR /app

# Copy requirements and install before copying code for faster builds
COPY requirements requirements

# install requirements
RUN pip install -r requirements/core-requirements.txt

# Set non-root user
RUN groupadd -r service && useradd --no-log-init -r -g service service
USER service

# Copy local code to the container image.
COPY src src
COPY main.py main.py

ENTRYPOINT ["python", "main.py"]
