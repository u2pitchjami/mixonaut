#!/bin/bash

AUDIO_FILE="$1"
JSON_OUT="$2"
PROFILE="$3"
echo "Audio in: $1"
echo "JSON out: $2"
echo "Profile: $3"

docker run --rm \
  -v "/home/pipo/data/appdata/mixonaut/essentia/temp:/app/music" \
  -v "/home/pipo/data/appdata/mixonaut/essentia:/app/profile" \
  bin:latest_test \
  essentia_streaming_extractor_music $AUDIO_FILE $JSON_OUT $PROFILE
