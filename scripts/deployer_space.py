"""Publie la démo Gradio (hf_space/) sur un Hugging Face Space.

Assemble hf_space/ + le vrai code (src/sauti, config) + la base de connaissances,
crée le Space s'il n'existe pas, pose KIRIKU_API_KEY en SECRET (jamais dans les
fichiers), puis téléverse.

Prérequis dans .env : HF_TOKEN_WRITE (jeton Hugging Face en écriture) et KIRIKU_API_KEY.
Usage : python scripts/deployer_space.py [--space compo9/sauti]
"""
from __future__ import annotations
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def lire_env() -> dict[str, str]:
    env = {}
    for ligne in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.lstrip().startswith("#"):
            k, v = ligne.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def assembler(dest: Path):
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(REPO / "hf_space", dest, dirs_exist_ok=True, ignore=ignore)
    shutil.copytree(REPO / "src" / "sauti", dest / "src" / "sauti", ignore=ignore)
    shutil.copytree(REPO / "config", dest / "config", ignore=ignore)
    kb = dest / "data" / "knowledge_base"
    kb.mkdir(parents=True)
    for f in (REPO / "data" / "knowledge_base").glob("*.json"):
        shutil.copy(f, kb / f.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", default="compo9/sauti")
    a = ap.parse_args()
    env = lire_env()
    jeton, cle = env.get("HF_TOKEN_WRITE"), env.get("KIRIKU_API_KEY")
    if not jeton or not cle:
        sys.exit("HF_TOKEN_WRITE et KIRIKU_API_KEY doivent être renseignés dans .env")

    from huggingface_hub import HfApi
    api = HfApi(token=jeton)
    api.create_repo(a.space, repo_type="space", space_sdk="gradio", exist_ok=True)
    api.add_space_secret(a.space, "KIRIKU_API_KEY", cle)
    with tempfile.TemporaryDirectory() as tmp:
        assembler(Path(tmp))
        api.upload_folder(repo_id=a.space, repo_type="space", folder_path=tmp,
                          commit_message="Déploiement de la démo Sauti")
    print(f"OK -> https://huggingface.co/spaces/{a.space}")


if __name__ == "__main__":
    main()
