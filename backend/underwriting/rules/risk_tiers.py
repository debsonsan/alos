from typing import Any


TIERS = ["A+", "A", "B", "C", "D", "E"]


def assign(application: Any, metrics: dict[str, float | int]) -> str:
	score = _effective_credit_score(application)

	if score >= 760:
		tier = "A+"
	elif score >= 720:
		tier = "A"
	elif score >= 680:
		tier = "B"
	elif score >= 640:
		tier = "C"
	elif score >= 600:
		tier = "D"
	else:
		tier = "E"

	for _ in range(_downgrade_count(application, metrics)):
		tier = _downgrade(tier)
	for _ in range(_upgrade_count(application, metrics)):
		tier = _upgrade(tier)

	return tier


def _effective_credit_score(application: Any) -> int:
	score = application.applicant_credit_score
	co_applicant_score = getattr(application, "co_applicant_credit_score", None)
	if co_applicant_score is not None:
		score = max(score, co_applicant_score)
	return score


def _downgrade_count(application: Any, metrics: dict[str, float | int]) -> int:
	count = 0
	if metrics["debt_to_income"] > 0.45:
		count += 1
	if metrics["payment_to_income"] > 0.15:
		count += 1
	if metrics["loan_to_value"] > 1.15:
		count += 1
	if getattr(application, "negative_equity_amount", 0) > 0:
		count += 1
	if getattr(application, "applicant_recent_inquiries", 0) >= 5:
		count += 1
	if getattr(application, "applicant_recent_delinquencies", 0) > 0:
		count += 1
	if getattr(application, "applicant_recent_severe_delinquencies", 0) > 0:
		count += 1
	if getattr(application, "applicant_bankruptcies", 0) > 0:
		count += 1
	if getattr(application, "applicant_recent_repossessions", 0) > 0:
		count += 1
	employment_duration_months = getattr(application, "applicant_employment_duration_months", None)
	if employment_duration_months is not None:
		if employment_duration_months < 12:
			count += 1
	if application.applicant_residence_duration_months < 12:
		count += 1
	if application.dealer_risk_rating.lower() in {"watch", "probation", "restricted", "high", "high_risk"}:
		count += 1
	return count


def _upgrade_count(application: Any, metrics: dict[str, float | int]) -> int:
	count = 0
	if getattr(application, "co_applicant_credit_score", None) is not None:
		count += 1
	employment_duration_months = getattr(application, "applicant_employment_duration_months", 0)
	if employment_duration_months and employment_duration_months >= 60:
		count += 1
	if metrics["debt_to_income"] < 0.30:
		count += 1
	if metrics["loan_to_value"] < 0.80:
		count += 1
	if application.down_payment_amount >= application.requested_loan_amount * 0.10:
		count += 1
	if getattr(application, "applicant_prior_positive_lender_relationship", False):
		count += 1
	return min(count // 2, 1)


def _downgrade(tier: str) -> str:
	current_index = TIERS.index(tier)
	return TIERS[min(current_index + 1, len(TIERS) - 1)]


def _upgrade(tier: str) -> str:
	current_index = TIERS.index(tier)
	return TIERS[max(current_index - 1, 0)]
