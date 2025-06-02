#!/bin/bash
# Entry point for Docker container

CONFIG_DIR="/app/config"
DEFAULT_CONFIG="/app/default_config"

# Crée un dossier temporaire avec la config par défaut dans l'image
# if [ ! -d "$CONFIG_DIR" ] || [ -z "$(ls -A $CONFIG_DIR)" ]; then
#     echo "Config folder is empty, copying default config..."
#     mkdir -p "$CONFIG_DIR"
#     cp -r $DEFAULT_CONFIG/* $CONFIG_DIR/
# fi

# Environment setup if needed
#export PATH="/usr/local/bin:$PATH"
export BEETSDIR=/app/config

# Launch Beets with user-provided arguments
exec "$@"