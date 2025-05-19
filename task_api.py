import os
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import requests
from fastapi import Request

load_dotenv()  # Charge les variables d'environnement

CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID")
CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SALESFORCE_REDIRECT_URI")
AUTH_URL = os.getenv("SALESFORCE_AUTH_URL")
TOKEN_URL = os.getenv("SALESFORCE_TOKEN_URL")

@app.get("/login/salesforce")
def login_salesforce():
    """Redirige vers Salesforce pour l'authentification OAuth"""
    url = (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return RedirectResponse(url=url)

@app.get("/oauth/callback")
def oauth_callback(request: Request, code: Optional[str] = None):
    """Récupère le token d'accès depuis Salesforce après autorisation"""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    # Demande le token d’accès
    response = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    })

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get access token")

    token_data = response.json()
    return token_data  # Vous pouvez aussi stocker ou rediriger selon votre logique
