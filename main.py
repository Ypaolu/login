from flask import Flask, redirect, request, session, url_for
import requests
import uuid
import config

app = Flask(__name__)
app.secret_key = "super-secreta"  # Use algo seguro no real

# URLs Keycloak
auth_url = config.KEYCLOAK_SERVER + "/realms/" + config.REALM + "/protocol/openid-connect/auth"
token_url = config.KEYCLOAK_SERVER + "/realms/" + config.REALM + "/protocol/openid-connect/token"
userinfo_url = config.KEYCLOAK_SERVER + "/realms/" + config.REALM + "/protocol/openid-connect/userinfo"

@app.route("/")
def home():
    if "user_info" in session:
        return (
            "<h1>Ola, " + session['user_info']['preferred_username'] + "!</h1>"
            "<p><a href='/logout'>Logout</a></p>"
        )
    else:
        return '<a href="/login">Login</a>'

@app.route("/login")
def login():
    state = str(uuid.uuid4())
    session["state"] = state

    query_params = "?client_id={}&response_type=code&scope=openid&redirect_uri={}&state={}".format(
        config.CLIENT_ID, config.REDIRECT_URI, state
    )
    return redirect(auth_url + query_params)

@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("state"):
        return "Estado invalido", 400

    code = request.args.get("code")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET
    }

    token_resp = requests.post(token_url, data=data)
    if token_resp.status_code != 200:
        return "Erro ao obter token: " + token_resp.text, 400

    access_token = token_resp.json().get("access_token")
    user_info_resp = requests.get(userinfo_url, headers={"Authorization": "Bearer " + access_token})

    if user_info_resp.status_code == 200:
        session["user_info"] = user_info_resp.json()
        return redirect(url_for("home"))
    else:
        return "Erro ao obter informacoes do usuario", 400

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
