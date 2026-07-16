from typing import Any


MAX_VEHICLE_AGE_YEARS = 12
REVIEW_VEHICLE_AGE_YEARS = 8
MAX_MILEAGE = 150_000
REVIEW_MILEAGE = 100_000
MAX_BACKEND_PRODUCT_RATIO = 0.20
MAX_NEGATIVE_EQUITY_RATIO = 0.25
MAX_DEALER_PRICE_VARIANCE = 1.20
REVIEW_LTV = 1.35
APPROVED_VALUATION_SOURCES = {"book", "nada", "kbb", "black_book", "jd_power", "dealer_bookout"}
SUPPORTED_VEHICLE_TYPES = {"passenger_car", "car", "truck", "suv", "van"}
PROHIBITED_TITLE_STATUSES = {"salvage", "flood", "lemon", "rebuilt", "total_loss", "branded"}
PROHIBITED_USES = {"rideshare", "commercial", "fleet"}


def evaluate(application: Any, metrics: dict[str, float | int]) -> dict[str, Any]:
	triggered_rules: list[dict[str, str]] = []
	decline_reasons: list[str] = []
	stipulations: list[str] = []
	manual_review_reasons: list[str] = []

	def trigger(rule_id: str, severity: str, reason: str) -> None:
		triggered_rules.append(
			{
				"rule_id": rule_id,
				"category": "vehicle_constraints",
				"severity": severity,
				"reason": reason,
			}
		)
		if severity == "decline":
			decline_reasons.append(reason)
		elif severity == "stipulation":
			stipulations.append(reason)
		elif severity == "review":
			manual_review_reasons.append(reason)

	if not application.vin_decoded:
		trigger("VC-VIN-001", "stipulation", "vin_decode_or_bookout_required")
	if application.vehicle_valuation_source.lower() not in APPROVED_VALUATION_SOURCES:
		trigger("VC-VALUE-002", "stipulation", "approved_vehicle_valuation_required")
	if metrics["vehicle_age_years"] > MAX_VEHICLE_AGE_YEARS:
		trigger("VC-AGE-001", "decline", "vehicle_age_exceeds_limit")
	elif metrics["vehicle_age_years"] > REVIEW_VEHICLE_AGE_YEARS:
		trigger("VC-AGE-002", "review", "older_vehicle_requires_review")
	if application.vehicle_mileage > MAX_MILEAGE:
		trigger("VC-MILEAGE-001", "decline", "vehicle_mileage_exceeds_limit")
	elif application.vehicle_mileage > REVIEW_MILEAGE:
		trigger("VC-MILEAGE-002", "review", "high_mileage_vehicle_requires_review")
	if application.vehicle_title_status.lower() in PROHIBITED_TITLE_STATUSES:
		trigger("VC-TITLE-001", "decline", "non_clean_title_status")
	elif application.vehicle_title_status.lower() not in {"clean", "clear"}:
		trigger("VC-TITLE-002", "stipulation", "title_documentation_required")
	if application.vehicle_use.lower() in PROHIBITED_USES:
		trigger("VC-USE-001", "review", "vehicle_use_requires_review")
	if application.vehicle_type.lower() not in SUPPORTED_VEHICLE_TYPES:
		trigger("VC-TYPE-001", "decline", "vehicle_type_not_supported")
	if metrics["loan_to_value"] > REVIEW_LTV:
		trigger("VC-LTV-001", "review", "high_vehicle_ltv_requires_review")
	if application.dealer_listed_price > application.vehicle_value * MAX_DEALER_PRICE_VARIANCE:
		trigger("VC-VALUE-001", "review", "dealer_price_exceeds_valuation_tolerance")
	backend_products = application.warranty_amount + application.gap_amount + application.backend_product_amount
	if application.vehicle_value > 0 and backend_products / application.vehicle_value > MAX_BACKEND_PRODUCT_RATIO:
		trigger("VC-BACKEND-001", "review", "backend_products_exceed_allowed_cap")
	if application.vehicle_value > 0 and application.negative_equity_amount / application.vehicle_value > MAX_NEGATIVE_EQUITY_RATIO:
		trigger("VC-NEGATIVE-EQUITY-001", "review", "negative_equity_exceeds_allowed_limit")
	if application.requested_term_months > _maximum_term(application, metrics):
		trigger("VC-TERM-001", "review", "requested_term_exceeds_vehicle_or_tier_limit")

	return {
		"status": _status(decline_reasons, manual_review_reasons, stipulations),
		"decline_reasons": decline_reasons,
		"stipulations": stipulations,
		"manual_review_reasons": manual_review_reasons,
		"triggered_rules": triggered_rules,
	}


def _status(declines: list[str], reviews: list[str], stipulations: list[str]) -> str:
	if declines:
		return "decline"
	if reviews:
		return "manual_review"
	if stipulations:
		return "stipulation"
	return "pass"


def _maximum_term(application: Any, metrics: dict[str, float | int]) -> int:
	max_term = 84
	if metrics["vehicle_age_years"] > REVIEW_VEHICLE_AGE_YEARS:
		max_term = min(max_term, 60)
	if application.vehicle_mileage > REVIEW_MILEAGE:
		max_term = min(max_term, 60)
	if application.applicant_credit_score < 640:
		max_term = min(max_term, 60)
	return max_term
