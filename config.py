import os

KEYCLOAK_SERVER = os.getenv("KEYCLOAK_SERVER", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "meu-reino")
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "meu-cliente")
CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "minha-senha-secreta")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")
