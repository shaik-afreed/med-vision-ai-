def test_register_creates_user(client):
    response = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "pw12345"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert "password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"name": "Bob", "email": "bob@example.com", "password": "pw12345"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_login_success_returns_token(client):
    client.post(
        "/auth/register",
        json={"name": "Carl", "email": "carl@example.com", "password": "pw12345"},
    )

    response = client.post(
        "/auth/login",
        data={"username": "carl@example.com", "password": "pw12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 0


def test_login_wrong_password_rejected(client):
    client.post(
        "/auth/register",
        json={"name": "Dana", "email": "dana@example.com", "password": "correct-pw"},
    )

    response = client.post(
        "/auth/login",
        data={"username": "dana@example.com", "password": "wrong-pw"},
    )
    assert response.status_code == 401


def test_login_unknown_user_rejected(client):
    response = client.post(
        "/auth/login",
        data={"username": "ghost@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_profile_requires_token(client):
    response = client.get("/auth/profile")
    assert response.status_code == 401


def test_profile_returns_current_user(client, auth_headers):
    response = client.get("/auth/profile", headers=auth_headers)
    assert response.status_code == 200
    assert "@" in response.json()["email"]
