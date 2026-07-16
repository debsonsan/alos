from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

try:
	from .rules import dealer_overlay, hard_declines, risk_tiers, vehicle_constraints
except ImportError:
	from rules import dealer_overlay, hard_declines, risk_tiers, vehicle_constraints


RULE_VERSION = "2026.07.15"


@dataclass(slots=True)
class Application:
	application_id: str
	application_channel: str
	requested_loan_amount: Decimal | float | int
	requested_term_months: int
	down_payment_amount: Decimal | float | int
	product_type: str
	applicant_id: str
	applicant_legal_name: str
	applicant_date_of_birth: date
	applicant_tax_id_token: str
	applicant_state: str
	applicant_residence_duration_months: int
	applicant_employment_status: str
	applicant_monthly_gross_income: Decimal | float | int
	applicant_monthly_housing_payment: Decimal | float | int
	applicant_credit_score: int
	vin: str
	vehicle_model_year: int
	vehicle_make: str
	vehicle_model: str
	vehicle_new_or_used: str
	vehicle_mileage: int
	vehicle_valuation_source: str
	vehicle_value: Decimal | float | int
	vehicle_title_status: str
	vehicle_use: str
	vehicle_type: str
	dealer_listed_price: Decimal | float | int
	dealer_id: str
	dealer_status: str
	dealer_risk_rating: str
	dealer_state: str
	dealer_license_status: str
	submission_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
	trade_in_value: Decimal | float | int = 0
	trade_in_payoff: Decimal | float | int = 0
	prior_decision_reference: str | None = None
	co_applicant_monthly_gross_income: Decimal | float | int = 0
	co_applicant_credit_score: int | None = None
	monthly_debt_obligations: Decimal | float | int = 0
	estimated_monthly_payment: Decimal | float | int | None = None
	warranty_amount: Decimal | float | int = 0
	gap_amount: Decimal | float | int = 0
	backend_product_amount: Decimal | float | int = 0
	add_ons_amount: Decimal | float | int = 0
	negative_equity_amount: Decimal | float | int = 0
	applicant_identity_verified: bool = True
	applicant_fraud_flag: bool = False
	applicant_synthetic_identity_flag: bool = False
	applicant_sanctions_flag: bool = False
	applicant_tax_id_valid: bool = True
	applicant_deceased_tax_id_flag: bool = False
	applicant_open_bankruptcy: bool = False
	applicant_recent_repossessions: int = 0
	applicant_recent_severe_delinquencies: int = 0
	applicant_charge_offs: int = 0
	applicant_recent_inquiries: int = 0
	vin_decoded: bool = True
	dealer_default_rate: float | None = None
	dealer_first_payment_default_rate: float | None = None
	dealer_buyback_frequency: float | None = None
	dealer_contract_defect_rate: float | None = None
	dealer_fraud_flag: bool = False
	dealer_complaint_rate: float | None = None
	dealer_max_ltv_override: float | None = None
	dealer_prior_exception_usage: int = 0


@dataclass(slots=True)
class UnderwritingResult:
	application_id: str
	decision: str
	risk_tier: str
	rule_version: str
	evaluated_at: datetime
	decline_reasons: list[str]
	stipulations: list[str]
	manual_review_reasons: list[str]
	triggered_rules: list[dict[str, Any]]
	passed_rules: list[str]
	metrics: dict[str, float | int]
	dealer_overlay: dict[str, Any]
	vehicle_eligibility: dict[str, Any]
	audit_correlation_id: str


class UnderwritingEngine:
	def __init__(self, rule_version: str = RULE_VERSION) -> None:
		self.rule_version = rule_version

	def evaluate(self, application: Application) -> UnderwritingResult:
		metrics = self._compute_metrics(application)
		hard_decline_results = hard_declines.evaluate(application, metrics)
		vehicle_results = vehicle_constraints.evaluate(application, metrics)
		risk_tier = risk_tiers.assign(application, metrics)
		dealer_result = dealer_overlay.evaluate(application, metrics, risk_tier)

		triggered_rules = [
			*hard_decline_results,
			*vehicle_results.get("triggered_rules", []),
			*dealer_result.get("triggered_rules", []),
		]
		decline_reasons = [rule["reason"] for rule in hard_decline_results]
		decline_reasons.extend(vehicle_results.get("decline_reasons", []))
		decline_reasons.extend(dealer_result.get("decline_reasons", []))

		stipulations = [
			*vehicle_results.get("stipulations", []),
			*dealer_result.get("stipulations", []),
		]
		manual_review_reasons = [
			*vehicle_results.get("manual_review_reasons", []),
			*dealer_result.get("manual_review_reasons", []),
		]
		if risk_tier in {"D", "E"} and not decline_reasons:
			manual_review_reasons.append(f"risk_tier_{risk_tier.lower()}_requires_review")

		decision = self._final_decision(decline_reasons, manual_review_reasons, stipulations)

		return UnderwritingResult(
			application_id=application.application_id,
			decision=decision,
			risk_tier=risk_tier,
			rule_version=self.rule_version,
			evaluated_at=datetime.now(UTC),
			decline_reasons=decline_reasons,
			stipulations=stipulations,
			manual_review_reasons=manual_review_reasons,
			triggered_rules=triggered_rules,
			passed_rules=self._passed_rule_categories(triggered_rules),
			metrics=metrics,
			dealer_overlay=dealer_result,
			vehicle_eligibility=vehicle_results,
			audit_correlation_id=str(uuid4()),
		)

	def _compute_metrics(self, application: Application) -> dict[str, float | int]:
		monthly_income = self._money(application.applicant_monthly_gross_income) + self._money(
			application.co_applicant_monthly_gross_income
		)
		net_trade_equity = self._money(application.trade_in_value) - self._money(application.trade_in_payoff)
		amount_financed = (
			self._money(application.requested_loan_amount)
			+ self._money(application.warranty_amount)
			+ self._money(application.gap_amount)
			+ self._money(application.backend_product_amount)
			+ self._money(application.add_ons_amount)
			+ self._money(application.negative_equity_amount)
			- self._money(application.down_payment_amount)
			- max(net_trade_equity, Decimal("0"))
		)
		amount_financed = max(amount_financed, Decimal("0"))
		vehicle_value = self._money(application.vehicle_value)
		estimated_payment = self._estimated_payment(application, amount_financed)
		total_monthly_debt = (
			self._money(application.monthly_debt_obligations)
			+ self._money(application.applicant_monthly_housing_payment)
			+ estimated_payment
		)

		return {
			"loan_to_value": self._ratio(amount_financed, vehicle_value),
			"debt_to_income": self._ratio(total_monthly_debt, monthly_income),
			"payment_to_income": self._ratio(estimated_payment, monthly_income),
			"amount_financed": float(amount_financed),
			"net_trade_equity": float(net_trade_equity),
			"vehicle_age_years": max(date.today().year - application.vehicle_model_year, 0),
			"applicant_age_years": self._age(application.applicant_date_of_birth),
			"combined_monthly_income": float(monthly_income),
		}

	def _estimated_payment(self, application: Application, amount_financed: Decimal) -> Decimal:
		if application.estimated_monthly_payment is not None:
			return self._money(application.estimated_monthly_payment)
		if application.requested_term_months <= 0:
			return Decimal("0")
		return amount_financed / Decimal(application.requested_term_months)

	@staticmethod
	def _money(value: Decimal | float | int | None) -> Decimal:
		if value is None:
			return Decimal("0")
		return Decimal(str(value))

	@staticmethod
	def _ratio(numerator: Decimal, denominator: Decimal) -> float:
		if denominator <= 0:
			return 0.0
		return float(numerator / denominator)

	@staticmethod
	def _age(birth_date: date) -> int:
		today = date.today()
		return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

	@staticmethod
	def _final_decision(
		decline_reasons: list[str], manual_review_reasons: list[str], stipulations: list[str]
	) -> str:
		if decline_reasons:
			return "declined"
		if manual_review_reasons:
			return "manual_review"
		if stipulations:
			return "approved_with_stipulations"
		return "approved"

	@staticmethod
	def _passed_rule_categories(triggered_rules: list[dict[str, Any]]) -> list[str]:
		triggered_categories = {rule.get("category") for rule in triggered_rules}
		return [
			category
			for category in ["hard_declines", "vehicle_constraints", "risk_tiers", "dealer_overlay"]
			if category not in triggered_categories
		]
