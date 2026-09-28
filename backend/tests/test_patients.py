PATIENT_PAYLOAD = {
    "full_name": "John Doe",
    "age": 45,
    "gender": "Male",
    "phone": "1234567890",
    "address": "123 Main St",
    "disease": None,
}


def test_create_patient_requires_auth(client):
    response = client.post("/patients/", json=PATIENT_PAYLOAD)
    assert response.status_code == 401


def test_create_and_list_patient(client, auth_headers):
    response = client.post("/patients/", json=PATIENT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 200
    patient = response.json()["patient"]
    assert patient["full_name"] == "John Doe"
    assert patient["owner_id"] is not None

    listing = client.get("/patients/", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_get_update_delete_patient(client, auth_headers):
    created = client.post(
        "/patients/", json=PATIENT_PAYLOAD, headers=auth_headers
    ).json()["patient"]
    patient_id = created["id"]

    get_response = client.get(f"/patients/{patient_id}", headers=auth_headers)
    assert get_response.status_code == 200

    updated_payload = {**PATIENT_PAYLOAD, "full_name": "Jane Doe", "age": 50}
    update_response = client.put(
        f"/patients/{patient_id}", json=updated_payload, headers=auth_headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["patient"]["full_name"] == "Jane Doe"

    delete_response = client.delete(f"/patients/{patient_id}", headers=auth_headers)
    assert delete_response.status_code == 200

    missing_response = client.get(f"/patients/{patient_id}", headers=auth_headers)
    assert missing_response.status_code == 404


def test_get_nonexistent_patient_404(client, auth_headers):
    response = client.get("/patients/999999", headers=auth_headers)
    assert response.status_code == 404


def test_patient_isolation_between_users(client, register_and_login):
    headers_a, _ = register_and_login()
    headers_b, _ = register_and_login()

    created = client.post(
        "/patients/", json=PATIENT_PAYLOAD, headers=headers_a
    ).json()["patient"]
    patient_id = created["id"]

    # User B cannot see user A's patient in their list.
    listing_b = client.get("/patients/", headers=headers_b)
    assert listing_b.json()["total"] == 0

    # User B cannot fetch, update, or delete user A's patient - all 404,
    # not 403, so the resource's existence isn't leaked either.
    assert client.get(f"/patients/{patient_id}", headers=headers_b).status_code == 404
    assert client.put(
        f"/patients/{patient_id}", json=PATIENT_PAYLOAD, headers=headers_b
    ).status_code == 404
    assert client.delete(f"/patients/{patient_id}", headers=headers_b).status_code == 404

    # User A still has it.
    assert client.get(f"/patients/{patient_id}", headers=headers_a).status_code == 200
