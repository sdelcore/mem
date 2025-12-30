#!/bin/bash
set -e

REGISTRY="registry.sdelcore.com"
TAG="${TAG:-latest}"

images=(
    "mem/backend"
    "mem/frontend"
    "mem/rtmp"
)

echo "Pushing images to $REGISTRY with tag: $TAG"

for image in "${images[@]}"; do
    full_image="$REGISTRY/$image:$TAG"
    echo "Pushing $full_image..."
    docker push "$full_image"
done

echo "Done"
