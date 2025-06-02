FROM python:3.11-slim

# Installation de base
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    #Bad Plugin
    mp3val flac \
    #embedart
    imagemagick \
    libjpeg-dev libpng-dev libtiff-dev libwebp-dev libtool libxml2-dev libfontconfig-dev libfreetype6-dev liblcms2-dev libopenexr-dev libx11-dev libxext-dev libxt-dev \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/convert /usr/local/bin/magick

# Beets core uniquement au début
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

VOLUME /app /import /config
WORKDIR /app

# Copy default config
COPY config/config.yaml.example /app/default_config/config.yaml
COPY config/lastgenre/ /app/default_config/
COPY config/svm_models/ /app/default_config/
COPY config/beatport_credentials.yaml.example /app/default_config/beatport_credentials.yaml

# Set entrypoint script
COPY scripts/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/app/entrypoint.sh"]
