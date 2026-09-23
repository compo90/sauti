"""Couche 6 - Escalade humaine. Cree un ticket et notifie l'agent de garde.

v0 : journalise le ticket. Phase 4+ : SMS/appel reel via l'API operateur ou un
webhook vers le systeme du district.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from config.settings import settings

log = logging.getLogger("escalation")


@dataclass
class Ticket:
    horodatage: str
    signes: list
    action: str
    langue: str
    contexte: str


def escalader(signes: list, action: str, langue: str, contexte: str = "") -> Ticket:
    t = Ticket(horodatage=datetime.now(timezone.utc).isoformat(),
               signes=signes, action=action, langue=langue, contexte=contexte)
    log.warning("ESCALADE -> agent %s | %s", settings.escalation_agent_phone or "(non configure)", asdict(t))
    # TODO Phase 4 : POST vers settings.escalation_webhook_url / declenchement appel agent.
    return t
