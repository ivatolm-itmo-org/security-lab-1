from flask import Flask, request
import bcrypt
import jwt

import datetime

from db import get_db


app = Flask(__name__)
SECRET_KEY = "opqiwemvu823ry98hd27"

def auth_only(f):
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return {"error": "Missing or invalid token"}, 400
        
        token = auth.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"error": "Token expired"}, 400
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 400

        request.user_id = payload["user_id"]
        return f(*args, **kwargs)
    return wrapper

def generate_password_hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password_hash(stored_hash, password):
    return bcrypt.checkpw(password.encode(), stored_hash.encode())

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username, password = data.get("username"), data.get("password")
    if not username or not password:
        return {"error": "Username and password required"}, 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        conn.commit()
        return {"message": "User created"}, 200
    except Exception:
        return {"error": "Username already exists"}, 400
    finally:
        conn.close()

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username, password = data.get("username"), data.get("password")

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password"], password):
        return {"error": "Invalid credentials"}, 400

    token = jwt.encode({
        "user_id": user["id"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, SECRET_KEY, algorithm="HS256")

    return {"token": token}

@app.route("/api/data")
@auth_only
def get_data():
    conn = get_db()
    users = conn.execute("SELECT id, username FROM users").fetchall()
    conn.close()
    return {"users": [dict(u) for u in users]}

if __name__ == "__main__":
    app.run(debug=False)
