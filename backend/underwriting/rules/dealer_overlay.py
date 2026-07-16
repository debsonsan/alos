from typing import Any


WATCH_DEFAULT_RATE = 0.08
RESTRICTED_DEFAULT_RATE = 0.12
WATCH_FIRST_PAYMENT_DEFAULT_RATE = 0.03
RESTRICTED_FIRST_PAYMENT_DEFAULT_RATE = 0.06
WATCH_CONTRACT_DEFECT_RATE = 0.05
RESTRICTED_CONTRACT_DEFECT_RATE = 0.10
WATCH_COMPLAINT_RATE = 0.04
RESTRICTED_COMPLAINT_RATE = 0.08
WATCH_BUYBACK_FREQUENCY = 0.03
RESTRICTED_BUYBACK_FREQUENCY = 0.07


def evaluate(application: Any, metrics: dict[str, float | int], risk_tier: str) -> dict[str, Any]:
	level = _overlay_level(application)
	actions: list[str] = []
	decline_reasons: list[str] = []
	stipulations: list[str] = []
	manual_review_reasons: list[str] = []
	triggered_rules: list[dict[str, str]] = []

	def trigger(rule_id: str, severity: str, reason: str) -> None:
		triggered_rules.append(
			{
				"rule_id": rule_id,
				"category": "dealer_overlay",
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

	if level == "suspended":
		actions.append("block_submission")
		trigger("DO-STATUS-001", "decline", "dealer_suspended_or_terminated")
	elif level == "restricted":
		actions.extend(["manual_review", "reduce_ltv", "stronger_income_verification"])
		trigger("DO-RISK-001", "review", "restricted_dealer_requires_manual_review")
		stipulations.append("proof_of_income")
	elif level == "watch":
		actions.extend(["additional_stipulations", "block_automated_approval"])
		trigger("DO-RISK-002", "review", "watch_dealer_blocks_automated_approval")
		stipulations.append("proof_of_insurance")

	if application.dealer_license_status.lower() not in {"active", "valid"}:
		actions.append("license_review")
		trigger("DO-LICENSE-001", "review", "dealer_license_requires_review")
	if application.dealer_max_ltv_override is not None and metrics["loan_to_value"] > application.dealer_max_ltv_override:
		actions.append("reduce_ltv")
		trigger("DO-LTV-001", "review", "ltv_exceeds_dealer_overlay_limit")
	if _rate_at_or_above(application.dealer_default_rate, RESTRICTED_DEFAULT_RATE):
		actions.extend(["manual_review", "reduce_ltv"])
		trigger("DO-DEFAULT-001", "review", "dealer_default_rate_restricted")
	elif _rate_at_or_above(application.dealer_default_rate, WATCH_DEFAULT_RATE):
		actions.append("additional_stipulations")
		trigger("DO-DEFAULT-002", "review", "dealer_default_rate_watch")
	if _rate_at_or_above(application.dealer_first_payment_default_rate, RESTRICTED_FIRST_PAYMENT_DEFAULT_RATE):
		actions.extend(["manual_review", "stronger_income_verification"])
		trigger("DO-FPD-001", "review", "dealer_first_payment_default_rate_restricted")
	elif _rate_at_or_above(application.dealer_first_payment_default_rate, WATCH_FIRST_PAYMENT_DEFAULT_RATE):
		actions.append("stronger_income_verification")
		trigger("DO-FPD-002", "stipulation", "dealer_first_payment_default_rate_watch")
	if _rate_at_or_above(application.dealer_buyback_frequency, RESTRICTED_BUYBACK_FREQUENCY):
		actions.extend(["manual_review", "title_or_bookout_validation"])
		trigger("DO-BUYBACK-001", "review", "dealer_buyback_frequency_restricted")
	elif _rate_at_or_above(application.dealer_buyback_frequency, WATCH_BUYBACK_FREQUENCY):
		actions.append("title_or_bookout_validation")
		trigger("DO-BUYBACK-002", "stipulation", "dealer_buyback_frequency_watch")
	if _rate_at_or_above(application.dealer_contract_defect_rate, RESTRICTED_CONTRACT_DEFECT_RATE):
		actions.extend(["manual_review", "corrected_contract_required"])
		trigger("DO-CONTRACT-001", "review", "dealer_contract_defect_rate_restricted")
	elif _rate_at_or_above(application.dealer_contract_defect_rate, WATCH_CONTRACT_DEFECT_RATE):
		actions.append("corrected_contract_required")
		trigger("DO-CONTRACT-002", "stipulation", "dealer_contract_defect_rate_watch")
	if _rate_at_or_above(application.dealer_complaint_rate, RESTRICTED_COMPLAINT_RATE):
		actions.append("manual_review")
		trigger("DO-COMPLAINT-001", "review", "dealer_complaint_rate_restricted")
	elif _rate_at_or_above(application.dealer_complaint_rate, WATCH_COMPLAINT_RATE):
		actions.append("additional_stipulations")
		trigger("DO-COMPLAINT-002", "review", "dealer_complaint_rate_watch")
	if application.dealer_prior_exception_usage >= 5:
		actions.append("manual_review")
		trigger("DO-EXCEPTION-001", "review", "dealer_prior_exception_usage_requires_review")
	if risk_tier in {"D", "E"} and level != "standard":
		actions.append("tier_overlay_review")

	return {
		"level": level,
		"actions": actions,
		"decline_reasons": decline_reasons,
		"stipulations": stipulations,
		"manual_review_reasons": manual_review_reasons,
		"triggered_rules": triggered_rules,
	}


def _overlay_level(application: Any) -> str:
	status = application.dealer_status.lower()
	rating = application.dealer_risk_rating.lower()
	if status in {"suspended", "terminated"}:
		return "suspended"
	if rating in {"restricted", "high", "high_risk"} or _has_restricted_metrics(application):
		return "restricted"
	if rating in {"watch", "probation", "elevated"} or status == "probation" or _has_watch_metrics(application):
		return "watch"
	return "standard"


def _rate_at_or_above(value: float | None, threshold: float) -> bool:
	return value is not None and value >= threshold


def _has_restricted_metrics(application: Any) -> bool:
	return any(
		[
			_rate_at_or_above(application.dealer_default_rate, RESTRICTED_DEFAULT_RATE),
			_rate_at_or_above(application.dealer_first_payment_default_rate, RESTRICTED_FIRST_PAYMENT_DEFAULT_RATE),
			_rate_at_or_above(application.dealer_buyback_frequency, RESTRICTED_BUYBACK_FREQUENCY),
			_rate_at_or_above(application.dealer_contract_defect_rate, RESTRICTED_CONTRACT_DEFECT_RATE),
			_rate_at_or_above(application.dealer_complaint_rate, RESTRICTED_COMPLAINT_RATE),
		]
	)


def _has_watch_metrics(application: Any) -> bool:
	return any(
		[
			_rate_at_or_above(application.dealer_default_rate, WATCH_DEFAULT_RATE),
			_rate_at_or_above(application.dealer_first_payment_default_rate, WATCH_FIRST_PAYMENT_DEFAULT_RATE),
			_rate_at_or_above(application.dealer_buyback_frequency, WATCH_BUYBACK_FREQUENCY),
			_rate_at_or_above(application.dealer_contract_defect_rate, WATCH_CONTRACT_DEFECT_RATE),
			_rate_at_or_above(application.dealer_complaint_rate, WATCH_COMPLAINT_RATE),
		]
	)
