#!/usr/bin/env python3

import sys
import json
import os
from pathlib import Path
import essentia
import essentia.standard as es

def add_replaygain(audio_path: str, json_path: str):
    # Charger l'audio (mono)
    audio = es.MonoLoader(filename=audio_path)()
    replaygain = es.ReplayGain()(audio)

    # Charger le JSON existant
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"JSON introuvable : {json_path}")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Injecter replaygain dans lowlevel
    data.setdefault("lowlevel", {})
    data["lowlevel"]["replaygain"] = replaygain

    if not os.access(json_file, os.W_OK):
        print(f"❌ Pas les droits d’écriture sur {json_file}")
        sys.exit(1)

    print(f"✅ Données replaygain injectées : {replaygain}")

    # Sauvegarde
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Fichier JSON mis à jour : {json_file}")

    print(f"ReplayGain ajouté ({replaygain:.2f} dB) dans {json_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python add_replaygain.py <audio_file> <json_file>")
        sys.exit(1)

    add_replaygain(sys.argv[1], sys.argv[2])
