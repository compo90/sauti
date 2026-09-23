"""Couche 1 - Passerelle IVR (Asterisk). Squelette d'integration.

L'idee : Asterisk recoit l'appel (SIP trunk operateur) et delegue chaque tour de
parole au pipeline via AGI/ARI. Ce fichier documente l'interface ; l'integration
Asterisk reelle se fera en Phase 4 (dialplan + AGI Python, ou ARI/ari-py).
"""
from __future__ import annotations
from sauti.pipeline import Pipeline


class IVRHandler:
    """Pont entre Asterisk (audio telephonique) et le pipeline applicatif."""

    def __init__(self, pipeline: Pipeline | None = None):
        self.pipeline = pipeline or Pipeline(mock=True)

    def sur_appel_entrant(self, chemin_audio_tour: str, langue: str):
        """Appele par l'AGI a chaque enonce capte. Renvoie l'audio a jouer."""
        res = self.pipeline.traiter(chemin_audio=chemin_audio_tour, langue=langue)
        return res["audio_reponse"]

    # TODO Phase 4 :
    #  - dialplan Asterisk (contexts entrant/sortant, Record(), enregistrement)
    #  - script AGI qui streame l'audio vers sur_appel_entrant()
    #  - gestion DTMF pour le menu "ecoute puis choisis"
