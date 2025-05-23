#!/bin/bash

# CONFIG
IMAGE_NAME="beets_metaflac_img"
HOST_MUSIC_DIR="/chemin/vers/musique"
CONTAINER_MUSIC_DIR="/music"

# VÉRIF : chemin de fichier fourni ?
if [ -z "$1" ]; then
  echo "❌ Erreur : Aucun fichier fourni."
  echo "➡️  Utilisation : $0 <chemin_relatif_fichier> TAG=VALEUR [TAG=VALEUR ...]"
  exit 1
fi

FILE_RELATIVE_PATH="$1"
shift

# VÉRIF : au moins un tag fourni ?
if [ $# -eq 0 ]; then
  echo "❌ Erreur : Aucun tag à écrire."
  echo "➡️  Utilisation : $0 <chemin_relatif_fichier> TAG=VALEUR [TAG=VALEUR ...]"
  exit 1
fi

TAGS=("$@")
EXT="${FILE_RELATIVE_PATH##*.}"
FILE_IN_CONTAINER="$CONTAINER_MUSIC_DIR/$FILE_RELATIVE_PATH"

# TRAITEMENT
if [[ "$EXT" == "flac" ]]; then
  docker run --rm \
    -v "$HOST_MUSIC_DIR":"$CONTAINER_MUSIC_DIR" \
    "$IMAGE_NAME" \
    bash -c "$(for TAG in "${TAGS[@]}"; do echo -n "metaflac --set-tag=$TAG \"$FILE_IN_CONTAINER\" && "; done) true"

elif [[ "$EXT" == "mp3" ]]; then
  docker run --rm \
    -v "$HOST_MUSIC_DIR":"$CONTAINER_MUSIC_DIR" \
    "$IMAGE_NAME" \
    bash -c "eyeD3 $(for TAG in "${TAGS[@]}"; do echo -n "--add-frame=TXXX:$TAG "; done) \"$FILE_IN_CONTAINER\""

else
  echo "❌ Erreur : Format non supporté : $EXT"
  exit 1
fi
