from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_login_returns_jwt_and_current_user() -> None:
	login_response = client.post("/auth/token", json={"username": "admin", "password": "admin-password"})

	assert login_response.status_code == 200
	body = login_response.json()
	assert body["access_token"]
	assert body["token_type"] == "bearer"
	assert body["user"] == {"username": "admin", "role": "admin"}

	me_response = client.get("/auth/me", headers=auth_headers(body["access_token"]))

	assert me_response.status_code == 200
	assert me_response.json() == {"username": "admin", "role": "admin"}


def test_applications_require_bearer_token() -> None:
	response = client.get("/applications")

	assert response.status_code == 401
	assert response.json()["detail"]["code"] == "missing_token"


def test_dealer_can_create_application() -> None:
	token = login("dealer", "dealer-password")
	response = client.post("/applications", json=application_payload(), headers=auth_headers(token))

	assert response.status_code == 201
	body = response.json()
	assert body["decision_outcome"] == "approved"
	assert body["final_risk_tier"] == "A+"


def test_auditor_cannot_create_application() -> None:
	token = login("auditor", "auditor-password")
	response = client.post("/applications", json=application_payload(), headers=auth_headers(token))

	assert response.status_code == 403
	assert response.json()["detail"]["code"] == "insufficient_role"


def test_underwriter_can_fund_approved_application() -> None:
	dealer_token = login("dealer", "dealer-password")
	application = client.post("/applications", json=application_payload(), headers=auth_headers(dealer_token)).json()
	underwriter_token = login("underwriter", "underwriter-password")

	response = client.post(f"/applications/{application['application_id']}/fund", headers=auth_headers(underwriter_token))

	assert response.status_code == 200
	assert response.json()["funding_status"] == "funded"


def test_status_changes_are_audited_for_create_and_fund() -> None:
	dealer_token = login("dealer", "dealer-password")
	application = client.post("/applications", json=application_payload(), headers=auth_headers(dealer_token)).json()
	underwriter_token = login("underwriter", "underwriter-password")
	client.post(f"/applications/{application['application_id']}/fund", headers=auth_headers(underwriter_token))
	auditor_token = login("auditor", "auditor-password")

	response = client.get(
		f"/applications/{application['application_id']}/status-audit",
		headers=auth_headers(auditor_token),
	)

	assert response.status_code == 200
	audit_entries = response.json()
	assert [(entry["previous_status"], entry["new_status"]) for entry in audit_entries] == [
		(None, "approved"),
		("approved", "funded"),
	]
	assert audit_entries[0]["changed_by"] == "dealer"
	assert audit_entries[0]["changed_by_role"] == "dealer"
	assert audit_entries[0]["change_reason"] == "underwriting_decision"
	assert audit_entries[1]["changed_by"] == "underwriter"
	assert audit_entries[1]["changed_by_role"] == "underwriter"
	assert audit_entries[1]["change_reason"] == "funding"


def test_dealer_cannot_read_status_audit() -> None:
	dealer_token = login("dealer", "dealer-password")
	application = client.post("/applications", json=application_payload(), headers=auth_headers(dealer_token)).json()

	response = client.get(
		f"/applications/{application['application_id']}/status-audit",
		headers=auth_headers(dealer_token),
	)

	assert response.status_code == 403
	assert response.json()["detail"]["code"] == "insufficient_role"


def test_dealer_can_read_fake_credit_bureau_report() -> None:
	token = login("dealer", "dealer-password")

	response = client.get("/credit-bureau/reports/tok_prime_applicant", headers=auth_headers(token))

	assert response.status_code == 200
	body = response.json()
	assert body["tax_id_token"] == "tok_prime_applicant"
	assert body["credit_score"] == 785
	assert body["score_model"] == "FAKE_AUTO_V1"


def test_credit_bureau_score_is_used_for_underwriting() -> None:
	token = login("dealer", "dealer-password")
	payload = application_payload()
	payload["applicant_tax_id_token"] = "tok_subprime_applicant"
	payload["applicant_credit_score"] = 820

	response = client.post("/applications", json=payload, headers=auth_headers(token))

	assert response.status_code == 201
	body = response.json()
	assert body["applicant_credit_score"] == 552
	assert body["applicant_credit_bureau_attributes"]["report_reference"] == "CBR-SUBPRIME-001"
	assert body["decision_outcome"] == "declined"
	assert "credit_score_below_minimum" in body["underwriting"]["decline_reasons"]


def login(username: str, password: str) -> str:
	response = client.post("/auth/token", json={"username": username, "password": password})
	assert response.status_code == 200
	return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
	return {"Authorization": f"Bearer {token}"}


def application_payload() -> dict[str, object]:
	application_id = f"APP-{uuid4().hex[:8].upper()}"
	return {
		"application_id": application_id,
		"application_channel": "dealer_portal",
		"product_type": "retail_installment",
		"requested_loan_amount": 27000,
		"requested_term_months": 60,
		"down_payment_amount": 3000,
		"applicant_id": f"APL-{application_id[-8:]}",
		"applicant_legal_name": "Test Applicant",
		"applicant_date_of_birth": "1988-01-01",
		"applicant_tax_id_token": f"tok_{application_id.lower()}",
		"applicant_address": "100 Main St",
		"applicant_state": "TX",
		"applicant_residence_duration_months": 36,
		"applicant_employment_status": "employed",
		"applicant_monthly_gross_income": 8000,
		"applicant_monthly_housing_payment": 1200,
		"applicant_credit_score": 740,
		"vin": f"VIN{application_id[-8:]}",
		"vehicle_model_year": 2022,
		"vehicle_make": "Honda",
		"vehicle_model": "Accord",
		"vehicle_new_or_used": "used",
		"vehicle_mileage": 25000,
		"vehicle_valuation_source": "book",
		"vehicle_value": 30000,
		"vehicle_title_status": "clean",
		"vehicle_use": "personal",
		"vehicle_type": "car",
		"dealer_listed_price": 29500,
		"dealer_id": "DLR-001",
		"dealer_status": "active",
		"dealer_risk_rating": "standard",
		"dealer_state": "TX",
		"dealer_license_status": "active",
		"monthly_debt_obligations": 300,
		"estimated_monthly_payment": 450,
	}