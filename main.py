from flask import Flask, redirect, request, session, url_for, render_template
import requests
import uuid
import config
from keycloak_admin import get_admin_token, get_user_id

app = Flask(__name__)
app.secret_key = "super-secreta"  # Use algo seguro no real

# URLs Keycloak
auth_url = config.KEYCLOAK_SERVER + "/realms/" + config.REALM + "/protocol/openid-connect/auth"
token_url = config.KEYCLOAK_SERVER + "/realms/" + config.REALM + "/protocol/openid-connect/token"
userinfo_url = config.KEYCLOAK_SERVER + "/realms/" + config.REALM + "/protocol/openid-connect/userinfo"

@app.route("/")
def home():
    if "user_info" in session:
        return render_template("home.html", username=session["user_info"]["preferred_username"])
    else:
        return render_template("home.html", username=None)


@app.route("/login")
def login():
    state = str(uuid.uuid4())
    session["state"] = state

    # Verifica se está vindo com ?register=1 na URL
    kc_action = "kc_action=register" if request.args.get("register") == "1" else ""

    query_params = "?client_id={}&response_type=code&scope=openid&redirect_uri={}&state={}".format(
        config.CLIENT_ID, config.REDIRECT_URI, state
    )

    if kc_action:
        query_params += "&" + kc_action

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
    logout_url = (
        config.KEYCLOAK_SERVER + "/realms/" + config.REALM + "/protocol/openid-connect/logout"
        + "?post_logout_redirect_uri=" + url_for("home", _external=True)
        + "&client_id=" + config.CLIENT_ID
    )
    return redirect(logout_url)

@app.route("/delete", methods=["POST"])
def delete_account():
    if "user_info" not in session:
        return redirect("/")

    username = session["user_info"]["preferred_username"]
    token = get_admin_token()
    user_id = get_user_id(username, token)

    if not user_id:
        return "Usuário não encontrado", 404

    delete_resp = requests.delete(
        f"{config.KEYCLOAK_SERVER}/admin/realms/{config.REALM}/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    if delete_resp.status_code == 204:
        session.clear()
        return (
            "Conta excluída com sucesso"
            "<p><a href='/'>Página Inicial</a></p>")
    else:
        return f"Erro ao excluir: {delete_resp.text}", 500


if __name__ == "__main__":
    app.run(debug=True)
