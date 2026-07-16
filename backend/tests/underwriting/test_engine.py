from datetime import date

import pytest

from backend.underwriting.engine import Application, UnderwritingEngine


def make_application(**overrides: object) -> Application:
	data = {
		"application_id": "APP-TEST-001",
		"application_channel": "dealer_portal",
		"requested_loan_amount": 27_000,
		"requested_term_months": 60,
		"down_payment_amount": 3_000,
		"product_type": "retail_installment",
		"applicant_id": "APL-001",
		"applicant_legal_name": "Sample Applicant",
		"applicant_date_of_birth": date(1988, 1, 1),
		"applicant_tax_id_token": "tok_sample",
		"applicant_state": "TX",
		"applicant_residence_duration_months": 36,
		"applicant_employment_status": "employed",
		"applicant_monthly_gross_income": 8_000,
		"applicant_monthly_housing_payment": 1_200,
		"applicant_credit_score": 740,
		"vin": "1HGCM82633A004352",
		"vehicle_model_year": 2022,
		"vehicle_make": "Honda",
		"vehicle_model": "Accord",
		"vehicle_new_or_used": "used",
		"vehicle_mileage": 25_000,
		"vehicle_valuation_source": "book",
		"vehicle_value": 30_000,
		"vehicle_title_status": "clean",
		"vehicle_use": "personal",
		"vehicle_type": "car",
		"dealer_listed_price": 29_500,
		"dealer_id": "DLR-001",
		"dealer_status": "active",
		"dealer_risk_rating": "standard",
		"dealer_state": "TX",
		"dealer_license_status": "active",
		"monthly_debt_obligations": 300,
		"estimated_monthly_payment": 520,
	}
	data.update(overrides)
	return Application(**data)


def evaluate(**overrides: object):
	return UnderwritingEngine().evaluate(make_application(**overrides))


@pytest.mark.parametrize(
	("overrides", "expected_reason"),
	[
		({"applicant_identity_verified": False}, "applicant_identity_verification_failed"),
		({"applicant_fraud_flag": True}, "confirmed_applicant_fraud_flag"),
		({"applicant_open_bankruptcy": True}, "open_bankruptcy"),
		({"applicant_credit_score": 560}, "credit_score_below_minimum"),
		({"requested_term_months": 96}, "requested_term_exceeds_absolute_maximum"),
		({"dealer_status": "suspended"}, "dealer_not_eligible"),
	]
)
def test_hard_declines_are_terminal(overrides: dict[str, object], expected_reason: str) -> None:
	result = evaluate(**overrides)

	assert result.decision == "declined"
	assert expected_reason in result.decline_reasons
	assert any(rule["category"] == "hard_declines" for rule in result.triggered_rules)


@pytest.mark.parametrize(
	("credit_score", "expected_tier"),
	[
		(780, "A+"),
		(730, "A"),
		(700, "B"),
		(660, "C"),
		(620, "D"),
		(590, "E"),
	]
)
def test_risk_tier_classification_by_credit_band(credit_score: int, expected_tier: str) -> None:
	result = evaluate(
		applicant_credit_score=credit_score,
		down_payment_amount=0,
		requested_loan_amount=24_000,
		vehicle_value=30_000,
		estimated_monthly_payment=420,
		monthly_debt_obligations=0,
	)

	assert result.risk_tier == expected_tier


def test_risk_tier_downgrades_for_adverse_affordability_and_ltv() -> None:
	result = evaluate(
		applicant_credit_score=720,
		requested_loan_amount=35_000,
		down_payment_amount=0,
		vehicle_value=30_000,
		estimated_monthly_payment=1_300,
		monthly_debt_obligations=2_500,
		negative_equity_amount=2_000,
		applicant_recent_inquiries=6,
	)

	assert result.risk_tier in {"D", "E"}
	assert result.decision in {"manual_review", "declined"}


@pytest.mark.parametrize(
	("overrides", "expected_reason", "expected_status"),
	[
		({"vehicle_title_status": "salvage"}, "non_clean_title_status", "decline"),
		({"vehicle_model_year": 2010}, "vehicle_age_exceeds_limit", "decline"),
		({"vehicle_mileage": 160_000}, "vehicle_mileage_exceeds_limit", "decline"),
		({"vehicle_type": "motorcycle"}, "vehicle_type_not_supported", "decline"),
		({"vin_decoded": False}, "vin_decode_or_bookout_required", "stipulation"),
		({"vehicle_mileage": 120_000}, "high_mileage_vehicle_requires_review", "manual_review"),
	]
)
def test_vehicle_constraints_follow_collateral_rules(
	overrides: dict[str, object], expected_reason: str, expected_status: str
) -> None:
	result = evaluate(**overrides)

	assert result.vehicle_eligibility["status"] == expected_status
	all_vehicle_reasons = (
		result.vehicle_eligibility["decline_reasons"]
		+ result.vehicle_eligibility["stipulations"]
		+ result.vehicle_eligibility["manual_review_reasons"]
	)
	assert expected_reason in all_vehicle_reasons


def test_dealer_watch_overlay_blocks_automated_approval() -> None:
	result = evaluate(dealer_risk_rating="watch")

	assert result.decision == "manual_review"
	assert result.dealer_overlay["level"] == "watch"
	assert "block_automated_approval" in result.dealer_overlay["actions"]
	assert "watch_dealer_blocks_automated_approval" in result.manual_review_reasons
	assert "proof_of_insurance" in result.stipulations


def test_dealer_restricted_overlay_requires_manual_review_and_income_stipulation() -> None:
	result = evaluate(dealer_default_rate=0.12)

	assert result.decision == "manual_review"
	assert result.dealer_overlay["level"] == "restricted"
	assert "manual_review" in result.dealer_overlay["actions"]
	assert "stronger_income_verification" in result.dealer_overlay["actions"]
	assert "proof_of_income" in result.stipulations


def test_suspended_dealer_declines_application_by_decision_precedence() -> None:
	result = evaluate(dealer_status="terminated")

	assert result.decision == "declined"
	assert "dealer_not_eligible" in result.decline_reasons
	assert "dealer_suspended_or_terminated" in result.decline_reasons
	assert result.dealer_overlay["level"] == "suspended"


def test_end_to_end_clean_application_is_approved_with_metrics_and_audit() -> None:
	result = evaluate()

	assert result.decision == "approved"
	assert result.risk_tier == "A+"
	assert result.decline_reasons == []
	assert result.stipulations == []
	assert result.manual_review_reasons == []
	assert result.vehicle_eligibility["status"] == "pass"
	assert result.dealer_overlay["level"] == "standard"
	assert result.metrics["loan_to_value"] == pytest.approx(0.8)
	assert result.metrics["debt_to_income"] == pytest.approx(0.2525)
	assert result.audit_correlation_id
	assert result.rule_version == "2026.07.15"
