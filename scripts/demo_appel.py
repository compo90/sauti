"""Simule un appel Sauti de bout en bout, a partir de vrais enregistrements (demo video).

Deroule : accueil -> question libre (ASR) -> TRIAGE DANGER -> reponse vocale
-> filet oui/non (une question de depistage) -> escalade si besoin.
Chaque phrase de Sauti est synthetisee (TTS Kiriku) dans experiments/demo/<nom>/
et peut etre jouee a l'ecran (--jouer) pendant l'enregistrement video.

Usage :
  python scripts/demo_appel.py --nom benin  --question q.ogg --oui-non non.ogg --jouer
  python scripts/demo_appel.py --nom danger --question amna_deret.ogg --jouer
  python scripts/demo_appel.py --messages      # tous les messages wolof, pour ecoute
N'utiliser que des voix dont la personne a accepte la diffusion publique.
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from sauti.dialog.screening import DepistageDanger, reconnaitre_oui_non  # noqa: E402
from sauti.escalation.escalation import escalader  # noqa: E402
from sauti.knowledge.messages import message_systeme, texte_parle  # noqa: E402
from sauti.pipeline import Pipeline  # noqa: E402

SORTIE = REPO / "experiments" / "demo"


class Appel:
    def __init__(self, nom: str, langue: str, jouer: bool):
        self.pipe, self.langue, self.jouer = Pipeline(mock=False), langue, jouer
        self.dir = SORTIE / nom
        self.dir.mkdir(parents=True, exist_ok=True)
        self.n = 0

    def dire(self, texte: str, etiquette: str):
        self.n += 1
        print(f"\n  SAUTI  > {texte_parle(texte)}")
        audio = self.pipe._dire(texte, self.langue)
        if audio is not None and audio.source == "tts":
            dest = self.dir / f"{self.n:02d}_sauti_{etiquette}.wav"
            shutil.copy(audio.contenu, dest)
            self._jouer(dest)

    def ecouter(self, chemin: str, etiquette: str) -> str:
        self.n += 1
        print(f"\n  ELLE   > [audio : {Path(chemin).name}]")
        self._jouer(Path(chemin))
        texte = self.pipe.asr.transcrire(chemin, langue_forcee=self.langue).texte
        print(f"  ASR    > « {texte} »")
        return texte

    def _jouer(self, chemin: Path):
        if not self.jouer:
            return
        if sys.platform != "win32":
            print(f"  (lire : {chemin})")
            return
        import subprocess, tempfile, winsound
        if chemin.suffix.lower() != ".wav":   # .ogg WhatsApp -> wav pour la lecture
            wav = Path(tempfile.gettempdir()) / f"sauti_lecture_{chemin.stem}.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(chemin), str(wav)],
                           check=True)
            chemin = wav
        winsound.PlaySound(str(chemin), winsound.SND_FILENAME)


def urgence(texte: str, langue: str) -> str:
    """Message d'urgence + annonce d'escalade, seulement si elle existe dans la meme langue."""
    esc, esc_langue = message_systeme("escalade", langue)
    return f"{texte} {esc}" if esc_langue == langue else texte


def scenario(a: Appel, question: str, oui_non: str | None, signe_filet: str):
    a.dire(message_systeme("accueil", a.langue)[0], "accueil")
    texte = a.ecouter(question, "question")
    res = a.pipe.danger.analyser(texte, langue=a.langue)
    if res.est_danger:
        print(f"\n  TRIAGE > DANGER : {', '.join(res.signes)} (action {res.action})")
        msg, servie = res.message(a.langue)
        a.dire(urgence(msg, a.langue), "urgence")
        escalader(signes=res.signes, action=res.action, langue=a.langue, contexte=texte)
        print("  ESCALADE > ticket transmis a la sage-femme de garde")
        return
    print("\n  TRIAGE > pas de signe de danger dans la phrase")
    intent, kb_id, _ = a.pipe.intent.predire(texte)
    entree = a.pipe.kb.entree(kb_id, langue=a.langue) if kb_id else None
    print(f"  INTENTION > {intent or 'non reconnue'}")
    a.dire(entree["texte"] if entree and entree["texte"]
           else message_systeme("pas_compris", a.langue)[0], "reponse")

    # Filet de securite : on depiste quand meme (l'ASR a pu perdre un signe)
    q = next(q for q in DepistageDanger().questions() if q.signe_id == signe_filet)
    print(f"\n  FILET  > question de depistage : {signe_filet}")
    a.dire(q.prompt(a.langue)[0], "question_oui_non")
    if not oui_non:
        return
    rep = reconnaitre_oui_non(a.ecouter(oui_non, "oui_non"), a.langue)
    print(f"  OUI/NON > {rep}")
    verdict = DepistageDanger().evaluer({signe_filet: rep})
    if verdict.est_danger:
        msg = next(s for s in json.loads((REPO / "data/knowledge_base/signes_danger.json")
                   .read_text(encoding="utf-8"))["signes"] if s["id"] == signe_filet)
        texte_urg = msg.get("message", {}).get(a.langue) or msg["message_fr"]
        a.dire(urgence(texte_urg, a.langue), "urgence")
        escalader(signes=verdict.signes, action=verdict.action, langue=a.langue,
                  contexte="filet oui/non")
        print("  ESCALADE > ticket transmis a la sage-femme de garde")
    else:
        print("  FILET  > « non » clair : pas d'escalade")


def messages_pour_ecoute(langue: str):
    """Synthetise tous les messages traduits : a ECOUTER par un locuteur natif."""
    a = Appel("messages", langue, jouer=False)
    kb = REPO / "data" / "knowledge_base"
    textes = {k: v.get(langue) for k, v in json.loads(
        (kb / "messages_systeme.json").read_text(encoding="utf-8"))["messages"].items()}
    for s in json.loads((kb / "signes_danger.json").read_text(encoding="utf-8"))["signes"]:
        textes[s["id"]] = s.get("message", {}).get(langue)
        textes["q_" + s["id"]] = s.get("question", {}).get(langue)
    for e in json.loads((kb / "faq_maternelle.json").read_text(encoding="utf-8")):
        textes[e["id"]] = e["reponses"].get(langue, {}).get("texte")
    for k, t in textes.items():
        if t:
            a.dire(t, k)
    print(f"\n-> {a.dir}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--nom", default="appel")
    ap.add_argument("--question")
    ap.add_argument("--oui-non")
    ap.add_argument("--signe-filet", default="fievre_forte")
    ap.add_argument("--langue", default="wol")
    ap.add_argument("--jouer", action="store_true")
    ap.add_argument("--messages", action="store_true")
    a = ap.parse_args()
    if a.messages:
        return messages_pour_ecoute(a.langue)
    if not a.question:
        ap.error("--question requis (ou --messages)")
    scenario(Appel(a.nom, a.langue, a.jouer), a.question, a.oui_non, a.signe_filet)


if __name__ == "__main__":
    main()
