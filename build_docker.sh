#!/bin/sh

# short commit description for this image
COMMIT_DESC=$(git log --oneline --decorate | head -n 1)

docker build \
    --build-arg COMMIT_DESC="$COMMIT_DESC" \
    -t docker.maxiv.lu.se/fragmax .
