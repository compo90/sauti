"""Configuration centralisee, chargee depuis .env (couche 8 : ne jamais coder en dur).

Codes langue internes = ISO 639-3 : wol (wolof), ful (pulaar), srr (serere).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hf_token: str = ""

    # --- Backend voix : "api" (API Kiriku du challenge), "local" (modeles HF
    # charges localement) ou "auto" (api si KIRIKU_API_KEY est renseignee). ---
    voice_backend: str = "auto"
    kiriku_api_key: str = ""
    kiriku_api_base: str = "https://14hyb7tjwzuh9q-8000.proxy.runpod.net/v1"

    # --- ASR : un seul modele MULTILINGUE couvre wolof + pulaar + serere ---
    # AIHubSN/M-Kiriku-ASR (fine-tune whisper-large-v3, gated, apache-2.0)
    kiriku_asr_model: str = "AIHubSN/M-Kiriku-ASR"

    # --- TTS : un modele PAR langue. Pas de TTS serere a ce jour. ---
    # Le routage se fait dans src/sauti/voice/tts.py ; ces valeurs restent
    # surchargeables via .env si besoin (KIRIKU_TTS_WOL / KIRIKU_TTS_FUL).
    kiriku_tts_wol: str = "AIHubSN/Kiriku-Wolof-TTS"
    kiriku_tts_ful: str = "AIHubSN/Kiriku-Pulaar-TTS"
    kiriku_tts_srr: str = ""  # aucun modele -> repli audio pre-enregistre

    # Escalade — contact du poste de sante / sage-femme de garde (district pilote)
    escalation_agent_phone: str = ""
    escalation_webhook_url: str = ""

    log_level: str = "INFO"
    default_lang: str = "wol"

    @property
    def utilise_api(self) -> bool:
        if self.voice_backend == "auto":
            return bool(self.kiriku_api_key)
        return self.voice_backend == "api"

    @property
    def tts_par_langue(self) -> dict[str, str]:
        """Mapping langue -> id de modele TTS (vide si non disponible)."""
        return {"wol": self.kiriku_tts_wol, "ful": self.kiriku_tts_ful, "srr": self.kiriku_tts_srr}


settings = Settings()

# Langues supportees et niveau de couverture (source de verite unique).
LANGUES = {
    "wol": {"nom": "Wolof",   "asr": True, "tts": True},
    "ful": {"nom": "Pulaar",  "asr": True, "tts": True},
    "srr": {"nom": "Serere",  "asr": True, "tts": False},  # ASR ok, TTS manquant
}
