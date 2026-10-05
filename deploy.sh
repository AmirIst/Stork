#!/bin/bash
# Stork German Bot deployment script for Ubuntu / Debian Linux

set -e

echo "=== Updating system packages and installing Docker ==="
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

echo "=== Deploying Stork German Bot container ==="
sudo docker-compose down || true
sudo docker-compose up -d --build

echo "=== Verifying container health ==="
sudo docker ps
echo "Stork Bot successfully deployed and running in background!"
