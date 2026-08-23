#!/usr/bin/env python3
"""
Renouvelle automatiquement le token d'accès Instagram et met à jour le
secret GitHub correspondant, pour qu'il ne soit jamais nécessaire d'y
retoucher manuellement.

Avec la nouvelle API "Instagram avec connexion Instagram", le renouvellement
utilise le grant ig_refresh_token, qui NE nécessite PAS l'App Secret — juste
le token actuel. Un token longue durée est valable 60 jours et peut être
rafraîchi (pour 60 jours de plus) à condition d'avoir au moins 24h et de ne
pas être expiré. En le faisant chaque jour dans ce workflow, le token ne
meurt donc jamais tant que l'automatisation tourne.

Variables d'environnement requises :
  IG_ACCESS_TOKEN   -> token actuel (à renouveler)
  GH_PAT            -> Personal Access Token GitHub avec la permission
                        "Secrets: write" (fine-grained) ou le scope "repo"
                        (classic), utilisé pour mettre à jour le secret
                        IG_ACCESS_TOKEN dans le dépôt.
  GITHUB_REPOSITORY -> fourni automatiquement par GitHub Actions (owner/repo)

Sortie : écrit le nouveau token dans $GITHUB_OUTPUT sous la clé "new_token"
pour que l'étape de publication de CE MÊME run l'utilise directement, sans
attendre la propagation du secret GitHub (qui ne sera visible qu'au run
suivant).
"""
import base64
import os
import sys

import requests
from nacl import encoding, public


def refresh_instagram_token(current_token):
    resp = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={
            "grant_type": "ig_refresh_token",
            "access_token": current_token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data.get("expires_in")


def encrypt_secret(public_key_b64, secret_value):
    """Chiffre une valeur pour l'API des secrets GitHub (libsodium sealed box)."""
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_github_secret(repo, pat, secret_name, secret_value):
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
    }
    key_resp = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=headers,
        timeout=15,
    )
    key_resp.raise_for_status()
    key_data = key_resp.json()

    encrypted_value = encrypt_secret(key_data["key"], secret_value)

    put_resp = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": key_data["key_id"]},
        timeout=15,
    )
    put_resp.raise_for_status()


def main():
    current_token = os.environ["IG_ACCESS_TOKEN"]
    gh_pat = os.environ["GH_PAT"]
    repo = os.environ["GITHUB_REPOSITORY"]

    try:
        new_token, expires_in = refresh_instagram_token(current_token)
        print(f"Nouveau token obtenu (valable ~{expires_in} secondes).")
    except requests.RequestException as e:
        print(f"Échec du renouvellement du token : {e}", file=sys.stderr)
        print("On continue avec l'ancien token pour cette publication.", file=sys.stderr)
        new_token = current_token

    try:
        update_github_secret(repo, gh_pat, "IG_ACCESS_TOKEN", new_token)
        print("Secret GitHub IG_ACCESS_TOKEN mis à jour.")
    except requests.RequestException as e:
        print(f"Échec de la mise à jour du secret GitHub : {e}", file=sys.stderr)
        print("Le token fonctionnera quand même pour cette publication,", file=sys.stderr)
        print("mais il faudra le régénérer manuellement avant expiration.", file=sys.stderr)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"new_token={new_token}\n")


if __name__ == "__main__":
    main()
