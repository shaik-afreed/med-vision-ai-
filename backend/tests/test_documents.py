from tests.conftest import make_test_lab_report_text

PATIENT_PAYLOAD = {
    "full_name": "Jane Roe",
    "age": 52,
    "gender": "Female",
    "phone": "1234567890",
    "address": "123 Main St",
    "disease": None,
}


def _create_patient(client, headers):
    response = client.post("/patients/", json=PATIENT_PAYLOAD, headers=headers)
    return response.json()["patient"]["id"]


def test_upload_requires_auth(client):
    files = {"file": ("report.txt", make_test_lab_report_text(), "text/plain")}
    data = {"patient_id": "1"}
    response = client.post("/documents/upload", data=data, files=files)
    assert response.status_code == 401


def test_upload_rejects_unsupported_content_type(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)
    files = {"file": ("scan.jpg", b"not relevant", "image/jpeg")}
    data = {"patient_id": str(patient_id)}
    response = client.post(
        "/documents/upload", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 400


def test_upload_rejects_patient_not_owned(client, register_and_login):
    headers_a, _ = register_and_login()
    headers_b, _ = register_and_login()
    patient_id = _create_patient(client, headers_a)

    files = {"file": ("report.txt", make_test_lab_report_text(), "text/plain")}
    data = {"patient_id": str(patient_id)}
    response = client.post(
        "/documents/upload", data=data, files=files, headers=headers_b
    )
    assert response.status_code == 404


def test_upload_analyzes_lab_report_and_flags_abnormal_values(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)

    files = {"file": ("report.txt", make_test_lab_report_text(), "text/plain")}
    data = {"patient_id": str(patient_id)}
    response = client.post(
        "/documents/upload", data=data, files=files, headers=auth_headers
    )

    assert response.status_code == 200
    document = response.json()["document"]

    assert document["patient_id"] == patient_id
    assert document["status"] == "completed"
    assert document["summary"]

    findings_by_test = {f["test"]: f for f in document["findings"]}
    assert findings_by_test["Hemoglobin"]["status"] == "Low"
    assert findings_by_test["Hemoglobin"]["reference_source"] == "report"
    assert findings_by_test["WBC Count"]["status"] == "High"
    assert findings_by_test["Total Cholesterol"]["reference_source"] == "general_fallback"

    listing = client.get("/documents/", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_upload_handles_narrative_text_with_no_lab_values(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)

    narrative = (
        b"The patient presented with cough and mild fever for three days. "
        b"Chest examination was unremarkable. Advised rest and follow-up."
    )
    files = {"file": ("note.txt", narrative, "text/plain")}
    data = {"patient_id": str(patient_id)}
    response = client.post(
        "/documents/upload", data=data, files=files, headers=auth_headers
    )

    assert response.status_code == 200
    document = response.json()["document"]
    assert document["findings"] == []
    assert "no lab-style values" in document["summary"].lower()


def test_document_file_ownership_isolation(client, register_and_login):
    headers_a, _ = register_and_login()
    headers_b, _ = register_and_login()
    patient_id = _create_patient(client, headers_a)

    files = {"file": ("report.txt", make_test_lab_report_text(), "text/plain")}
    data = {"patient_id": str(patient_id)}
    upload = client.post(
        "/documents/upload", data=data, files=files, headers=headers_a
    ).json()
    document_id = upload["document"]["id"]

    own_view = client.get(f"/documents/{document_id}/file", headers=headers_a)
    assert own_view.status_code == 200

    other_view = client.get(f"/documents/{document_id}/file", headers=headers_b)
    assert other_view.status_code == 404


def test_patch_document_notes_and_status(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)
    files = {"file": ("report.txt", make_test_lab_report_text(), "text/plain")}
    data = {"patient_id": str(patient_id)}
    document_id = client.post(
        "/documents/upload", data=data, files=files, headers=auth_headers
    ).json()["document"]["id"]

    response = client.patch(
        f"/documents/{document_id}",
        json={"status": "reviewed", "notes": "Repeat CBC in 2 weeks."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewed"
    assert body["notes"] == "Repeat CBC in 2 weeks."
