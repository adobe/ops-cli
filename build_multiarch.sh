#!/bin/bash
set -e

# Multiarch Docker Build Script
# This script builds the ops-cli Docker image for multiple architectures

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/adobe/ops-cli}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
PUSH="${PUSH:-false}"

echo "Building multiarch Docker image..."
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Platforms: ${PLATFORMS}"
echo "Push to registry: ${PUSH}"

# Login to GitHub Container Registry if pushing
if [ "$PUSH" = "true" ]; then
    if [ -z "$GITHUB_USERNAME" ] || [ -z "$GITHUB_TOKEN" ]; then
        echo "Error: GITHUB_USERNAME and GITHUB_TOKEN environment variables must be set when PUSH=true"
        exit 1
    fi
    
    echo "Logging in to ghcr.io..."
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to login to GitHub Container Registry"
        exit 1
    fi
    echo "Successfully logged in to ghcr.io"
fi

# Build the image
BUILD_ARGS=""
if [ "$PUSH" = "true" ]; then
    BUILD_ARGS="--push"
else
    BUILD_ARGS="--load"
fi

# Note: --load only works for single platform builds
# For multiplatform builds without pushing, use --output type=docker
if [ "$PUSH" = "false" ] && [[ "$PLATFORMS" == *","* ]]; then
    echo "Warning: Cannot use --load with multiple platforms."
    echo "Building without --load (image will not be loaded to local docker)."
    echo "To load to local docker, specify a single platform or use --push to push to registry."
    BUILD_ARGS=""
fi

docker buildx build \
    --platform ${PLATFORMS} \
    --tag ${IMAGE_NAME}:${IMAGE_TAG} \
    ${BUILD_ARGS} \
    --file Dockerfile \
    .

echo "Build complete!"

if [ "$PUSH" = "true" ]; then
    echo "Image pushed to registry as ${IMAGE_NAME}:${IMAGE_TAG}"
else
    if [[ "$PLATFORMS" == *","* ]]; then
        echo "Note: Multi-platform images were built but not loaded to local docker."
        echo "To use them, either:"
        echo "  1. Push to a registry: PUSH=true ./build_multiarch.sh"
        echo "  2. Build for single platform: PLATFORMS=linux/amd64 ./build_multiarch.sh"
    else
        echo "Image loaded to local docker as ${IMAGE_NAME}:${IMAGE_TAG}"
    fi
fi
