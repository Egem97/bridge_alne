#!/bin/bash
set -e

IMAGE_NAME="app-alza"
CONTAINER_NAME="app-alza-web"
PORT=8554

echo ">> Pulling latest changes..."
git pull origin master

echo ">> Building Docker image..."
docker build -t $IMAGE_NAME .

echo ">> Stopping old container (if running)..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo ">> Running migrations..."
docker run --rm --env-file .env $IMAGE_NAME python manage.py migrate

echo ">> Starting new container..."
docker run -d \
  --name $CONTAINER_NAME \
  --env-file .env \
  -p $PORT:8000 \
  --restart unless-stopped \
  $IMAGE_NAME

echo ">> Done! App running at http://localhost:$PORT"
