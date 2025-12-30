#!/bin/bash
set -e

TAG="${TAG:-latest}"

echo "Building and pushing images with tag: $TAG"

echo "Building images..."
docker compose build mem-backend mem-frontend mem-rtmp

echo "Pushing images..."
./push-images.sh

echo "Done"
