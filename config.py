import os

KEYCLOAK_SERVER = os.getenv("KEYCLOAK_SERVER", "http://localhost:8081")
REALM = os.getenv("KEYCLOAK_REALM", "master")
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "myclient")
CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "bqKUCaXqRfOjUvL7oky2lljEGB8Ym9Qo")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")
