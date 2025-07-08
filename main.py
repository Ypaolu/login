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


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]

    data = {
        "grant_type": "password",
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "username": username,
        "password": password,
        "scope": "openid"
    }

    token_resp = requests.post(token_url, data=data)
    if token_resp.status_code != 200:
        return f"Login inválido: {token_resp.text}", 401

    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    # Buscar dados do usuário
    userinfo_resp = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
    if userinfo_resp.status_code == 200:
        session["user_info"] = userinfo_resp.json()
        return redirect(url_for("home"))
    else:
        return "Erro ao obter dados do usuário", 400

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

@app.route("/delete", methods=["GET", "POST"])
def delete_account():
    if "user_info" not in session:
        return redirect("/")

    if request.method == "GET":
        return render_template("delete.html")  # Mostra a página de confirmação

    # POST: apagar conta
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
        return render_template("delete_success.html")
    else:
        return f"Erro ao excluir: {delete_resp.text}", 500

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    token = get_admin_token()

    # Criar usuário no Keycloak
    payload = {
        "username": username,
        "email": email,
        "enabled": True,
        "emailVerified": True,
    }

    create_resp = requests.post(
        f"{config.KEYCLOAK_SERVER}/admin/realms/{config.REALM}/users",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    if create_resp.status_code not in [201, 204]:
        return f"Erro ao criar usuário: {create_resp.text}", 500

    # Obter ID do usuário criado
    user_id = get_user_id(username, token)
    if not user_id:
        return "Usuário criado, mas não foi possível obter o ID.", 500

    # Definir a senha do usuário
    password_payload = {
        "type": "password",
        "value": password,
        "temporary": False
    }

    pwd_resp = requests.put(
        f"{config.KEYCLOAK_SERVER}/admin/realms/{config.REALM}/users/{user_id}/reset-password",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=password_payload
    )

    if pwd_resp.status_code != 204:
        return f"Usuário criado, mas erro ao definir senha: {pwd_resp.text}", 500

    return render_template("register_success.html", username=username)

@app.route("/edit", methods=["GET", "POST"])
def edit_account():
    if "user_info" not in session:
        return redirect("/login")

    username = session["user_info"]["preferred_username"]
    token = get_admin_token()
    user_id = get_user_id(username, token)
    if not user_id:
        return "Usuário não encontrado", 404

    if request.method == "GET":
        # Buscar dados atuais do usuário
        user_resp = requests.get(
            f"{config.KEYCLOAK_SERVER}/admin/realms/{config.REALM}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if user_resp.status_code != 200:
            return f"Erro ao buscar dados: {user_resp.text}", 500

        user_data = user_resp.json()
        return render_template("edit.html", user=user_data)

    # POST: atualizar dados
    email = request.form.get("email")
    first_name = request.form.get("firstName")
    last_name = request.form.get("lastName")

    update_payload = {
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
    }

    update_resp = requests.put(
        f"{config.KEYCLOAK_SERVER}/admin/realms/{config.REALM}/users/{user_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=update_payload
    )

    if update_resp.status_code == 204:
        # Atualizar sessão (opcional)
        session["user_info"].update(update_payload)
        return render_template("edit_success.html")
    else:
        return f"Erro ao atualizar: {update_resp.text}", 500


if __name__ == "__main__":
    app.run(debug=True)
