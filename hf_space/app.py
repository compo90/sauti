"""Sauti — démo en ligne (Hugging Face Space, Gradio).

Rejoue le parcours de la ligne vocale avec le VRAI code du dépôt :
  voix (M-Kiriku-ASR) -> TRIAGE DANGER -> réponse wolof (Kiriku-TTS)
  -> filet oui/non -> alerte si besoin.
La clé de l'API Kiriku est un secret du Space (KIRIKU_API_KEY), jamais publiée.
Aucun audio n'est conservé par Sauti ; il est transmis à l'API Kiriku pour transcription.
"""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

# Racine du code : le Space assemblé (src/ à côté de app.py) ou le dépôt (Render).
ICI = Path(__file__).resolve().parent
if not (ICI / "src").exists():
    ICI = ICI.parent
sys.path.insert(0, str(ICI / "src"))
sys.path.insert(0, str(ICI))

import gradio as gr  # noqa: E402

from config.settings import settings  # noqa: E402
from sauti.dialog.screening import DepistageDanger, reconnaitre_oui_non  # noqa: E402
from sauti.escalation.escalation import escalader  # noqa: E402
from sauti.knowledge.messages import message_systeme, texte_parle  # noqa: E402
from sauti.pipeline import Pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO)
LANGUE = "wol"
MOCK = not settings.utilise_api          # sans clé : logique seule, sans voix
PIPE = Pipeline(mock=MOCK)
DEPISTAGE = DepistageDanger()
FILET = DEPISTAGE.questions()[0]          # le signe le plus grave d'abord (hémorragie)
SIGNES = {s.signe_id: s for s in DEPISTAGE.questions()}

PANNE = ("⚠️ Le service vocal Kiriku ne répond pas pour le moment (API du challenge "
         "saturée ou arrêtée). Réessayez dans une minute, ou tapez la phrase dans le champ texte. "
         "Sur la vraie ligne, Sauti passerait au menu par touches ou transférerait l'appel.")


def _voix(texte: str):
    """Chemin du WAV Kiriku-TTS, ou None (la réponse reste affichée en texte)."""
    audio = PIPE._dire(texte, LANGUE)
    return audio.contenu if audio is not None and audio.source == "tts" else None


def _entendre(audio, texte_tape: str) -> str:
    if texte_tape and texte_tape.strip():
        return texte_tape.strip()
    if not audio:
        raise gr.Error("Aucune voix reçue : cliquez sur « Arrêter » pour finir l'enregistrement "
                       "(l'envoi est alors automatique), ou tapez la phrase en wolof.")
    if MOCK:
        raise gr.Error("Démo sans clé API : tapez la phrase en wolof dans le champ texte.")
    return PIPE.asr.transcrire(audio, langue_forcee=LANGUE).texte


def _urgence(msg: str) -> str:
    esc, esc_langue = message_systeme("escalade", LANGUE)
    return f"{msg} {esc}" if esc_langue == LANGUE else msg


def tour_1(audio, texte_tape):
    """Question libre -> triage danger -> réponse + question de dépistage."""
    cache = gr.update(visible=False)
    try:
        texte = _entendre(audio, texte_tape)
    except gr.Error:
        raise
    except Exception as e:  # réseau, quota, 5xx
        logging.exception("ASR indisponible")
        return "", PANNE + f"\n\n`{type(e).__name__}`", None, cache

    d = PIPE.danger.analyser(texte, langue=LANGUE)
    if d.est_danger:
        escalader(signes=d.signes, action=d.action, langue=LANGUE, contexte=texte)
        msg, _ = d.message(LANGUE)
        msg = _urgence(msg) if d.action == "urgent" else msg
        verdict = (f"### 🚨 Signe de danger détecté : {', '.join(d.signes)}\n"
                   f"**Sauti :** {texte_parle(msg)}\n\n"
                   f"➡️ *Alerte transmise à la sage-femme de garde (simulée dans cette démo).*")
        return texte, verdict, _voix(msg), cache

    intent, kb_id, _ = PIPE.intent.predire(texte)
    entree = PIPE.kb.entree(kb_id, langue=LANGUE) if kb_id else None
    reponse = (entree["texte"] if entree and entree["texte"]
               else message_systeme("pas_compris", LANGUE)[0])
    question, _ = FILET.prompt(LANGUE)
    verdict = (f"### ✅ Pas de signe de danger dans la phrase\n"
               f"Sujet reconnu : **{intent or 'non reconnu'}**\n\n"
               f"**Sauti :** {texte_parle(reponse)}\n\n"
               f"### 🛡️ Filet de sécurité\nL'IA a pu mal entendre : Sauti vérifie quand même un "
               f"signe de danger.\n\n**Sauti :** {texte_parle(question)}\n\n"
               f"👉 Répondez **« waaw »** (oui) ou **« déedéet »** (non) à l'étape 2.")
    return texte, verdict, _voix(f"{reponse} {question}"), gr.update(visible=True)


def tour_2(audio, texte_tape):
    """Réponse oui/non -> évaluation recall-first (seul un « non » clair rassure)."""
    try:
        texte = _entendre(audio, texte_tape)
    except gr.Error:
        raise
    except Exception as e:
        logging.exception("ASR indisponible")
        return "", PANNE + f"\n\n`{type(e).__name__}`", None
    rep = reconnaitre_oui_non(texte, LANGUE)
    v = DEPISTAGE.evaluer({FILET.signe_id: rep})
    if not v.est_danger:
        return texte, f"Réponse comprise : **{rep}**\n\n### ✅ « Non » clair : pas d'alerte.", None
    import json
    signes = json.loads((ICI / "data/knowledge_base/signes_danger.json").read_text(encoding="utf-8"))
    s = next(x for x in signes["signes"] if x["id"] == FILET.signe_id)
    msg = _urgence(s.get("message", {}).get(LANGUE) or s["message_fr"])
    escalader(signes=v.signes, action=v.action, langue=LANGUE, contexte="filet oui/non")
    pourquoi = "" if rep == "oui" else " (réponse incertaine : dans le doute, Sauti alerte)"
    return (texte, f"Réponse comprise : **{rep}**{pourquoi}\n\n### 🚨 Alerte\n**Sauti :** "
            f"{texte_parle(msg)}\n\n➡️ *Sage-femme de garde prévenue (simulée).*", _voix(msg))


INTRO = """
# Sauti 🤰📞 — la ligne vocale de santé maternelle en wolof
Sur la vraie ligne, une femme enceinte appelle depuis **un téléphone simple** et parle wolof.
Ici, votre micro remplace le téléphone. **Modèles : M-Kiriku-ASR + Kiriku-TTS (AI Hub Senegal).**

**Phrases à essayer (dites-les ou tapez-les) :**
- 🚨 « **amna dëret** » (je saigne) → alerte immédiate
- 💬 « **lan laa wara lekk** » (que dois-je manger ?) → conseil en wolof, puis question de sécurité
"""
AVERTISSEMENT = """
---
⚠️ **Prototype de recherche.** Contenu médical en attente de validation par des soignants ;
ne remplace pas une consultation. L'alerte est simulée. Votre voix est envoyée à l'API Kiriku
pour transcription et n'est pas conservée par Sauti.
Équipe **Echo Sahel** · [Code](https://github.com/compo90/sauti) ·
[Vidéo](https://youtu.be/SiCGVt_BgjM) · Kiriku Voice Inclusive & Creative Challenge 2026
"""

with gr.Blocks(title="Sauti — démo", theme=gr.themes.Soft()) as demo:
    gr.Markdown(INTRO)
    if MOCK:
        gr.Markdown("ℹ️ *Mode sans voix (clé API absente) : tapez les phrases.*")
    with gr.Group():
        gr.Markdown("## Étape 1 — Posez votre question en wolof")
        micro1 = gr.Audio(sources=["microphone", "upload"], type="filepath",
                          label="Votre voix (60 s max) — cliquez sur Arrêter : l'envoi est automatique")
        texte1 = gr.Textbox(label="… ou tapez la phrase en wolof (ou cliquez un exemple)")
        gr.Examples([["amna dëret"], ["lan laa wara lekk"]], inputs=[texte1], label="Exemples")
        go1 = gr.Button("📞 Envoyer à Sauti", variant="primary")
        asr1 = gr.Textbox(label="Ce que l'IA a entendu (M-Kiriku-ASR)", interactive=False)
        verdict1 = gr.Markdown()
        voix1 = gr.Audio(label="Réponse de Sauti (Kiriku-TTS wolof)", autoplay=True,
                         interactive=False)
    with gr.Group(visible=False) as etape2:
        gr.Markdown("## Étape 2 — Répondez « waaw » (oui) ou « déedéet » (non)")
        micro2 = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Votre réponse — cliquez sur Arrêter : envoi automatique")
        texte2 = gr.Textbox(label="… ou tapez")
        gr.Examples([["waaw"], ["déedéet"]], inputs=[texte2], label="Exemples")
        go2 = gr.Button("Répondre", variant="primary")
        asr2 = gr.Textbox(label="Ce que l'IA a entendu", interactive=False)
        verdict2 = gr.Markdown()
        voix2 = gr.Audio(label="Sauti", autoplay=True, interactive=False)
    gr.Markdown(AVERTISSEMENT)

    go1.click(tour_1, [micro1, texte1], [asr1, verdict1, voix1, etape2])
    micro1.stop_recording(lambda a: tour_1(a, ""), [micro1], [asr1, verdict1, voix1, etape2])
    go2.click(tour_2, [micro2, texte2], [asr2, verdict2, voix2])
    micro2.stop_recording(lambda a: tour_2(a, ""), [micro2], [asr2, verdict2, voix2])

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=4).launch(
        server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
