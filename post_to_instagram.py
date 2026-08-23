#!/usr/bin/env python3
"""
Publie l'image générée sur Instagram via la nouvelle API "Instagram avec
connexion Instagram" (Business Login for Instagram), qui utilise l'hôte
graph.instagram.com — et non plus graph.facebook.com comme dans l'ancien
système lié à une Page Facebook.

Nécessite que l'image soit déjà accessible publiquement à IMAGE_URL
(ex: raw.githubusercontent.com après un git push).

Variables d'environnement requises :
  IG_USER_ID      -> l'ID Instagram (ex: 28203023826003791, obtenu via
                      graph.instagram.com/me lors de la configuration)
  IG_ACCESS_TOKEN -> le token d'accès longue durée
  IMAGE_URL       -> URL publique de l'image (ex: raw.githubusercontent.com/...)
"""
import os
import sys
import time
import requests

GRAPH_API = "https://graph.instagram.com/v23.0"


def main():
    ig_user_id = os.environ["IG_USER_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    image_url = os.environ["IMAGE_URL"]

    here = os.path.dirname(os.path.abspath(__file__))
    caption_path = os.path.join(here, "caption.txt")
    caption = ""
    if os.path.exists(caption_path):
        with open(caption_path, encoding="utf-8") as f:
            caption = f.read()

    # 1. Créer le conteneur média
    create_resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
    )
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]
    print(f"Conteneur média créé : {creation_id}")

    # 2. Attendre que Meta ait fini de traiter l'image (statut FINISHED)
    for _ in range(10):
        status_resp = requests.get(
            f"{GRAPH_API}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
        )
        status_resp.raise_for_status()
        status = status_resp.json().get("status_code")
        print(f"Statut du conteneur : {status}")
        if status == "FINISHED":
            break
        time.sleep(5)
    else:
        print("Le conteneur n'est pas prêt après plusieurs tentatives.", file=sys.stderr)
        sys.exit(1)

    # 3. Publier
    publish_resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": access_token,
        },
    )
    publish_resp.raise_for_status()
    print("Publication réussie :", publish_resp.json())


if __name__ == "__main__":
    main()
