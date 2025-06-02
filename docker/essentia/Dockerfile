# Base image
FROM debian:bullseye-slim

# Install system dependencies
COPY assets/* /app/
RUN apt-get update && apt-get install -y \
    wget git \
    python3-pip python3-gi \
    # for Gaia :
    qtbase5-dev pkg-config libtag1-dev \
    # for Gaia & chroma plugin :
    libchromaprint-dev \
    # for Gaia & Essentia :
    python3-dev libyaml-dev build-essential \
    # for Essentia :
    yasm python3-numpy-dev python3-six ffmpeg libavcodec-dev libavformat-dev libswresample-dev libavutil-dev libsamplerate0-dev \
    #for Essentia & librekey
    cmake libfftw3-dev \
    libavresample-dev \
    libcairo2-dev \
    # for Essentia :
    && pip3 install numpy==1.19.5 pycairo==1.20.1 essentia\
    && ln -s /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Add python alias for waf compatibility
ENV CXXFLAGS="-I/usr/local/include/eigen3"
# Set working directory
WORKDIR /app
# Install SWIG for Gaia
RUN cd /app \
    && tar -xzf swig-3.0.12.tar.gz \
    && cd swig-3.0.12 \
    && ./configure \
    && make \
    && make install \
    && rm -rf /app/swig-3.0.12 /app/swig-3.0.12.tar.gz \
# Install Eigen for Gaia & Essentia
    && cd /app \
    && tar -xzf eigen-3.4.0.tar.gz \
    && cd eigen-3.4.0 \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make install \
    && rm -rf /app/eigen-3.4.0 /app/eigen-3.4.0.tar.gz \
    && cd /app \
# Install Gaia from GitHub
    && git clone https://github.com/MTG/gaia.git /app/gaia \
    && cd /app/gaia \
    && ./waf configure --with-python-bindings --with-asserts \
    && ./waf build \
    && ./waf install \
    && ldconfig \
    && rm -rf /app/gaia \
    && cd /app \
# Extract and build Essentia + SVM models for Essentia
    && cd /app \
    && tar -xzf essentia-2.1_beta5.tar.gz \
    && cd essentia-2.1_beta5 \
    && wget https://waf.io/waf-2.0.23 \
    && mv waf-2.0.23 waf \
    && chmod +x waf \
    && ./waf configure --build-static --with-python --with-examples --with-gaia \
    && ./waf build \
    && ./waf install \
    && ldconfig \
    && cd /app \
    && mkdir -p /app/default_config/svm_models \
    && tar -xzf essentia-extractor-svm_models-v2.1_beta5.tar.gz \
    && cp -r essentia-extractor-svm_models-v2.1_beta5/* /app/default_config/svm_models/ \
    && rm -rf /app/essentia-extractor-svm_models-v2.1_beta5 /app/essentia-extractor-svm_models-v2.1_beta5.tar.gz \
    && rm -rf /app/essentia-2.1_beta5 /app/essentia-2.1_beta5.tar.gz
COPY scripts/add_replaygain.py /usr/local/bin/add_replaygain.py
COPY config/svm_models/ /app/default_config/svm_models/
RUN chmod +x /usr/local/bin/add_replaygain.py

WORKDIR /app
