from typing import Any


ABSOLUTE_MIN_CREDIT_SCORE = 580
ABSOLUTE_MAX_TERM_MONTHS = 84
ABSOLUTE_MAX_PAYMENT_TO_INCOME = 0.22
ABSOLUTE_MAX_DEBT_TO_INCOME = 0.60
ABSOLUTE_MAX_LOAN_TO_VALUE = 1.50
MIN_LOAN_AMOUNT = 1_000
MAX_LOAN_AMOUNT = 150_000
MIN_DOWN_PAYMENT_AMOUNT = 0
MIN_APPLICANT_AGE = 18
ELIGIBLE_STATES = {
	"AL",
	"AK",
	"AZ",
	"AR",
	"CA",
	"CO",
	"CT",
	"DE",
	"FL",
	"GA",
	"HI",
	"ID",
	"IL",
	"IN",
	"IA",
	"KS",
	"KY",
	"LA",
	"ME",
	"MD",
	"MA",
	"MI",
	"MN",
	"MS",
	"MO",
	"MT",
	"NE",
	"NV",
	"NH",
	"NJ",
	"NM",
	"NY",
	"NC",
	"ND",
	"OH",
	"OK",
	"OR",
	"PA",
	"RI",
	"SC",
	"SD",
	"TN",
	"TX",
	"UT",
	"VT",
	"VA",
	"WA",
	"WV",
	"WI",
	"WY",
}


def evaluate(application: Any, metrics: dict[str, float | int]) -> list[dict[str, str]]:
	rules: list[dict[str, str]] = []

	def decline(rule_id: str, reason: str) -> None:
		rules.append(
			{
				"rule_id": rule_id,
				"category": "hard_declines",
				"severity": "decline",
				"reason": reason,
			}
		)

	if not application.applicant_identity_verified:
		decline("HD-IDENTITY-001", "applicant_identity_verification_failed")
	if getattr(application, "has_co_applicant", False) and getattr(application, "co_applicant_identity_verified", True) is False:
		decline("HD-IDENTITY-002", "co_applicant_identity_verification_failed")
	if application.applicant_fraud_flag:
		decline("HD-FRAUD-001", "confirmed_applicant_fraud_flag")
	if getattr(application, "co_applicant_fraud_flag", False):
		decline("HD-FRAUD-003", "confirmed_co_applicant_fraud_flag")
	if application.applicant_synthetic_identity_flag:
		decline("HD-FRAUD-002", "synthetic_identity_flag")
	if getattr(application, "co_applicant_synthetic_identity_flag", False):
		decline("HD-FRAUD-004", "co_applicant_synthetic_identity_flag")
	if application.applicant_sanctions_flag:
		decline("HD-SANCTIONS-001", "applicant_sanctions_or_exclusion_match")
	if getattr(application, "co_applicant_sanctions_flag", False):
		decline("HD-SANCTIONS-002", "co_applicant_sanctions_or_exclusion_match")
	if not application.applicant_tax_id_valid or application.applicant_deceased_tax_id_flag:
		decline("HD-TAXID-001", "invalid_or_deceased_tax_identifier")
	if getattr(application, "has_co_applicant", False) and (
		getattr(application, "co_applicant_tax_id_valid", True) is False
		or getattr(application, "co_applicant_deceased_tax_id_flag", False)
	):
		decline("HD-TAXID-002", "invalid_or_deceased_co_applicant_tax_identifier")
	if metrics["applicant_age_years"] < MIN_APPLICANT_AGE:
		decline("HD-ELIGIBILITY-001", "applicant_below_minimum_age")
	if application.applicant_state.upper() not in ELIGIBLE_STATES:
		decline("HD-ELIGIBILITY-002", "applicant_state_not_eligible")
	if metrics["combined_monthly_income"] <= 0:
		decline("HD-ELIGIBILITY-003", "no_verifiable_income")
	if getattr(application, "applicant_prior_fraud_investigation", False):
		decline("HD-ELIGIBILITY-004", "unresolved_prior_fraud_investigation")
	if getattr(application, "applicant_prior_first_payment_default_investigation", False):
		decline("HD-ELIGIBILITY-005", "unresolved_prior_first_payment_default_investigation")
	if application.applicant_open_bankruptcy:
		decline("HD-CREDIT-001", "open_bankruptcy")
	if application.applicant_credit_score < ABSOLUTE_MIN_CREDIT_SCORE:
		decline("HD-CREDIT-002", "credit_score_below_minimum")
	if application.applicant_recent_repossessions > 0:
		decline("HD-CREDIT-003", "recent_repossession")
	if application.applicant_recent_severe_delinquencies >= 2:
		decline("HD-CREDIT-004", "excessive_recent_severe_delinquency")
	if getattr(application, "applicant_charge_offs", 0) > 0:
		decline("HD-CREDIT-005", "unresolved_prior_charge_off")
	if application.requested_loan_amount < MIN_LOAN_AMOUNT or application.requested_loan_amount > MAX_LOAN_AMOUNT:
		decline("HD-STRUCTURE-005", "requested_loan_amount_outside_program_limits")
	if application.requested_term_months > ABSOLUTE_MAX_TERM_MONTHS:
		decline("HD-STRUCTURE-001", "requested_term_exceeds_absolute_maximum")
	if metrics["payment_to_income"] > ABSOLUTE_MAX_PAYMENT_TO_INCOME:
		decline("HD-STRUCTURE-002", "payment_to_income_exceeds_absolute_maximum")
	if metrics["debt_to_income"] > ABSOLUTE_MAX_DEBT_TO_INCOME:
		decline("HD-STRUCTURE-003", "debt_to_income_exceeds_absolute_maximum")
	if metrics["loan_to_value"] > ABSOLUTE_MAX_LOAN_TO_VALUE:
		decline("HD-STRUCTURE-004", "loan_to_value_exceeds_absolute_maximum")
	if application.down_payment_amount < MIN_DOWN_PAYMENT_AMOUNT:
		decline("HD-STRUCTURE-006", "down_payment_below_minimum")
	if application.dealer_status.lower() in {"suspended", "terminated"}:
		decline("HD-DEALER-001", "dealer_not_eligible")
	if application.dealer_license_status.lower() not in {"active", "valid"}:
		decline("HD-DEALER-003", "dealer_unlicensed_or_license_invalid")
	if application.dealer_fraud_flag:
		decline("HD-DEALER-002", "dealer_fraud_flag")

	return rules
