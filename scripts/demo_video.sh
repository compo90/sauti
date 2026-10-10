#!/usr/bin/env bash
# Enchaine les 3 scenarios de la video de demo, avec une pause (Entree) entre chacun.
# Usage (terminal Git Bash de VS Code, a la racine du depot) :  bash scripts/demo_video.sh
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

titre "Ligne vocale de sante maternelle, en wolof"
echo
echo "   Appuyez sur Entree pour lancer l'appel 1..."
read -r

titre "APPEL 1 · Une question courante"
$PY scripts/demo_appel.py --nom video_1 --question $D/question.ogg --oui-non $D/deedeet.ogg --jouer 2>/dev/null
echo; echo "   Appuyez sur Entree pour l'appel 2..."; read -r

titre "APPEL 2 · Un signe de danger mal entendu par l'IA"
$PY scripts/demo_appel.py --nom video_2 --question $D/danger.ogg --signe-filet hemorragie --oui-non $D/waaw.ogg --jouer 2>/dev/null
echo; echo "   Appuyez sur Entree pour l'appel 3..."; read -r

titre "APPEL 3 · Toujours verifier le danger"
$PY scripts/demo_appel.py --nom video_3 --question $D/question.ogg --oui-non $D/waaw.ogg --jouer 2>/dev/null
echo; echo "   Fin de la demonstration."
