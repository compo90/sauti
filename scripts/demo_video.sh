#!/usr/bin/env bash
# Enchaine les 3 scenarios de la video de demo, avec une pause (Entree) entre chacun.
# Usage (terminal Git Bash de VS Code, a la racine du depot) :  bash scripts/demo_video.sh
# Le script filme lui-meme l'ecran entier (ffmpeg gdigrab : OBS donnait une image noire)
# et colle le son des appels dessus -> EchoSahel_Sauti_Demo.mp4 a la racine du depot.
# Avant de lancer : agrandir le terminal (panneau maximise), fermer ce qui ne doit pas etre filme.
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="src;."
PY=.venv/Scripts/python
D=experiments/demo

titre() {
  clear
  echo
  echo "=============================================================="
  echo "   SAUTI — $1"
  echo "=============================================================="
}

# Enregistrement de l'ecran ; on l'arrete en envoyant « q » sur l'entree de ffmpeg.
DEBUT_ECRAN=$($PY -c "import time; print(time.time())")
exec 3> >(ffmpeg -y -loglevel error -f gdigrab -framerate 30 -i desktop   -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p $D/ecran.mkv)
arreter_ecran() { echo q >&3 2>/dev/null || true; exec 3>&-; sleep 3; }
trap arreter_ecran EXIT

titre "Ligne vocale de sante maternelle, en wolof"
echo
echo "   Appuyez sur Entree pour lancer l'appel 1..."
read -r
SAUTI_T0=$($PY -c "import time; print(time.time())")
export SAUTI_T0

titre "APPEL 1 · Une question courante"
$PY scripts/demo_appel.py --nom video_1 --question $D/question.ogg --oui-non $D/deedeet.ogg --jouer 2>/dev/null
echo; echo "   Appuyez sur Entree pour l'appel 2..."; read -r

titre "APPEL 2 · Un signe de danger mal entendu par l'IA"
$PY scripts/demo_appel.py --nom video_2 --question $D/danger.ogg --signe-filet hemorragie --oui-non $D/waaw.ogg --jouer 2>/dev/null
echo; echo "   Appuyez sur Entree pour l'appel 3..."; read -r

titre "APPEL 3 · Toujours verifier le danger"
$PY scripts/demo_appel.py --nom video_3 --question $D/question.ogg --oui-non $D/waaw.ogg --jouer 2>/dev/null
echo; echo "   Fin de la demonstration."
sleep 3
trap - EXIT
arreter_ecran

# Les 3 pistes partagent la meme horloge : on les superpose.
ffmpeg -y -loglevel error -i $D/video_1/piste_appel.wav -i $D/video_2/piste_appel.wav \
  -i $D/video_3/piste_appel.wav -filter_complex "amix=inputs=3:normalize=0:duration=longest" \
  $D/piste_demo.wav

# Son cale sur l'image : t=0 de la piste = SAUTI_T0, soit DECALAGE s apres le debut du film.
DECALAGE=$($PY -c "print(round($SAUTI_T0 - $DEBUT_ECRAN, 3))")
ffmpeg -y -loglevel error -i $D/ecran.mkv -itsoffset "$DECALAGE" -i $D/piste_demo.wav   -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -movflags +faststart EchoSahel_Sauti_Demo.mp4
echo "OK -> EchoSahel_Sauti_Demo.mp4 (decalage son : $DECALAGE s)"
