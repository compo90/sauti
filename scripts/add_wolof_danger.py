#!/usr/bin/env python3
"""Injecte les mots-cles de danger en WOLOF (fournis par locuteur natif) dans
signes_danger.json. Le detecteur normalise (minuscules + suppression des
diacritiques) avant de comparer, donc on stocke les formes naturelles."""
import json
from pathlib import Path

KB = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"
p = KB / "signes_danger.json"
data = json.loads(p.read_text(encoding="utf-8"))

wolof = {
    "hemorragie": ["damay ñàkk", "ñàkk bu bari", "amna dëret", "dëret"],
    "convulsions": ["dama xëm", "xëm", "saayi"],
    "cephalees_vision": [
        "sama bopp dey metti", "bopp metti bu baax", "sama bopp dafa metti lool",
        "sama bët dey lëndem", "sama gis-gis dafa leerul", "damay miir",
    ],
    "fievre_forte": [
        "dama sibbiru", "sibbiru", "yaram bu tàng", "sama yaram tàng na lool",
        "yaram wi tàng na torop",
    ],
    "mouvements_foetaux": [
        "doom bi dootul yëngu", "sama doom bi dootul yëngu ci biir",
        "liir bi dootul yëngu", "dootul yëngu", "liir bi yëngu na tuuti",
    ],
    "oedeme": ["sama kanam dafa newwi", "sama tank dafa newwi", "newwi"],
}

for s in data["signes"]:
    if s["id"] in wolof:
        s["mots_cles"]["wol"] = wolof[s["id"]]

p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
n = sum(len(v) for v in wolof.values())
print(f"OK : {n} mots-cles wolof injectes sur {len(wolof)} signes.")
