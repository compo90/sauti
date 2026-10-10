#!/usr/bin/env bash
# Colle la piste de la demo sur la video enregistree (si l'enregistreur n'a pas capte le son).
# Usage : bash scripts/coller_son.sh <video.mp4> <secondes>
#   <secondes> = instant, dans la video, ou l'ecran passe a « APPEL 1 » (ex. 4.5)
# Sortie : EchoSahel_Sauti_Demo.mp4 a la racine du depot.
set -e
cd "$(dirname "$0")/.."
VIDEO="$1"; DECALAGE="${2:-0}"
ffmpeg -y -loglevel error -i "$VIDEO" -itsoffset "$DECALAGE" -i experiments/demo/piste_demo.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -shortest EchoSahel_Sauti_Demo.mp4
echo "OK -> EchoSahel_Sauti_Demo.mp4"
