from tests.conftest import make_test_image_bytes

PATIENT_PAYLOAD = {
    "full_name": "John Doe",
    "age": 45,
    "gender": "Male",
    "phone": "1234567890",
    "address": "123 Main St",
    "disease": None,
}


def _create_patient(client, headers):
    response = client.post("/patients/", json=PATIENT_PAYLOAD, headers=headers)
    return response.json()["patient"]["id"]


def test_upload_requires_auth(client):
    files = {"file": ("xray.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {"patient_id": "1", "report_type": "X-Ray"}
    response = client.post("/reports/upload", data=data, files=files)
    assert response.status_code == 401


def test_upload_rejects_non_image_content_type(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    data = {"patient_id": str(patient_id), "report_type": "X-Ray"}
    response = client.post(
        "/reports/upload", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 400


def test_upload_rejects_corrupted_image(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)
    files = {"file": ("fake.jpg", b"not actually a jpeg", "image/jpeg")}
    data = {"patient_id": str(patient_id), "report_type": "X-Ray"}
    response = client.post(
        "/reports/upload", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 400


def test_upload_rejects_patient_not_owned(client, register_and_login):
    headers_a, _ = register_and_login()
    headers_b, _ = register_and_login()
    patient_id = _create_patient(client, headers_a)

    files = {"file": ("xray.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {"patient_id": str(patient_id), "report_type": "X-Ray"}
    response = client.post(
        "/reports/upload", data=data, files=files, headers=headers_b
    )
    assert response.status_code == 404


def test_upload_runs_ai_prediction_and_stores_report(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)

    files = {"file": ("xray.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {"patient_id": str(patient_id), "report_type": "X-Ray"}
    response = client.post(
        "/reports/upload", data=data, files=files, headers=auth_headers
    )

    assert response.status_code == 200
    report = response.json()["report"]

    assert report["patient_id"] == patient_id
    assert report["prediction"] in ("Normal", "Pneumonia")
    assert 0 <= report["confidence"] <= 100
    assert 0 <= report["pneumonia_probability"] <= 100
    assert report["threshold_used"] is not None
    assert report["model_version"] is not None
    assert report["status"] == "completed"

    listing = client.get("/reports/", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_report_image_ownership_isolation(client, register_and_login):
    headers_a, _ = register_and_login()
    headers_b, _ = register_and_login()
    patient_id = _create_patient(client, headers_a)

    files = {"file": ("xray.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {"patient_id": str(patient_id), "report_type": "X-Ray"}
    upload = client.post(
        "/reports/upload", data=data, files=files, headers=headers_a
    ).json()
    report_id = upload["report"]["id"]

    # Owner can view the image.
    own_view = client.get(f"/reports/{report_id}/image", headers=headers_a)
    assert own_view.status_code == 200

    # A different user cannot, and the response doesn't leak existence.
    other_view = client.get(f"/reports/{report_id}/image", headers=headers_b)
    assert other_view.status_code == 404


def test_patch_report_notes_and_status(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)
    files = {"file": ("xray.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {"patient_id": str(patient_id), "report_type": "X-Ray"}
    report_id = client.post(
        "/reports/upload", data=data, files=files, headers=auth_headers
    ).json()["report"]["id"]

    response = client.patch(
        f"/reports/{report_id}",
        json={"status": "reviewed", "notes": "Follow up recommended."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewed"
    assert body["notes"] == "Follow up recommended."
