from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

try:
	from .auth import (
		AuthenticatedUser,
		LoginRequest,
		TokenResponse,
		authenticate_user,
		create_token_response,
		get_current_user,
		require_roles,
	)
	from .credit_bureau import CreditBureauReport, get_credit_bureau_report
	from .database import Base, engine, get_db
	from .models import ApplicationStatusAudit, LoanApplication
	from .underwriting.engine import UnderwritingEngine, UnderwritingResult
except ImportError:
	from auth import (
		AuthenticatedUser,
		LoginRequest,
		TokenResponse,
		authenticate_user,
		create_token_response,
		get_current_user,
		require_roles,
	)
	from credit_bureau import CreditBureauReport, get_credit_bureau_report
	from database import Base, engine, get_db
	from models import ApplicationStatusAudit, LoanApplication
	from underwriting.engine import UnderwritingEngine, UnderwritingResult


app = FastAPI(
	title="Auto Loan Origination API",
	version="0.1.0",
	description="Application intake, underwriting decisioning, and funding workflow API.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


class ApiError(BaseModel):
	code: str
	message: str


class ApplicationCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	application_id: str = Field(min_length=1, max_length=64)
	application_channel: str = Field(min_length=1, max_length=64)
	product_type: str = Field(min_length=1, max_length=64)
	requested_loan_amount: Decimal = Field(gt=0)
	requested_term_months: int = Field(gt=0)
	down_payment_amount: Decimal = Field(default=Decimal("0"), ge=0)
	trade_in_value: Decimal | None = None
	trade_in_payoff: Decimal | None = None
	prior_decision_reference: str | None = None

	applicant_id: str = Field(min_length=1, max_length=64)
	applicant_legal_name: str = Field(min_length=1, max_length=255)
	applicant_date_of_birth: date
	applicant_tax_id_token: str = Field(min_length=1, max_length=255)
	applicant_address: str = Field(min_length=1)
	applicant_state: str = Field(min_length=2, max_length=32)
	applicant_residence_duration_months: int = Field(ge=0)
	applicant_employment_status: str = Field(min_length=1, max_length=64)
	applicant_employer_name: str | None = None
	applicant_employment_duration_months: int | None = Field(default=None, ge=0)
	applicant_monthly_gross_income: Decimal = Field(ge=0)
	applicant_monthly_housing_payment: Decimal = Field(default=Decimal("0"), ge=0)
	applicant_credit_score: int = Field(ge=300, le=850)
	applicant_credit_history_depth_months: int | None = Field(default=None, ge=0)
	applicant_recent_delinquencies: int = Field(default=0, ge=0)
	applicant_recent_severe_delinquencies: int = Field(default=0, ge=0)
	applicant_bankruptcies: int = Field(default=0, ge=0)
	applicant_open_bankruptcy: bool = False
	applicant_recent_repossessions: int = Field(default=0, ge=0)
	applicant_charge_offs: int = Field(default=0, ge=0)
	applicant_recent_inquiries: int = Field(default=0, ge=0)
	applicant_tradeline_history: dict[str, Any] | None = None
	applicant_credit_bureau_attributes: dict[str, Any] | None = None
	applicant_identity_verified: bool = True
	applicant_fraud_flag: bool = False
	applicant_synthetic_identity_flag: bool = False
	applicant_sanctions_flag: bool = False
	applicant_tax_id_valid: bool = True
	applicant_deceased_tax_id_flag: bool = False
	applicant_prior_fraud_investigation: bool = False
	applicant_prior_first_payment_default_investigation: bool = False
	applicant_prior_positive_lender_relationship: bool = False

	has_co_applicant: bool = False
	co_applicant_id: str | None = None
	co_applicant_legal_name: str | None = None
	co_applicant_date_of_birth: date | None = None
	co_applicant_tax_id_token: str | None = None
	co_applicant_address: str | None = None
	co_applicant_state: str | None = None
	co_applicant_residence_duration_months: int | None = Field(default=None, ge=0)
	co_applicant_employment_status: str | None = None
	co_applicant_employer_name: str | None = None
	co_applicant_employment_duration_months: int | None = Field(default=None, ge=0)
	co_applicant_monthly_gross_income: Decimal | None = Field(default=None, ge=0)
	co_applicant_monthly_housing_payment: Decimal | None = Field(default=None, ge=0)
	co_applicant_credit_score: int | None = Field(default=None, ge=300, le=850)
	co_applicant_credit_history_depth_months: int | None = Field(default=None, ge=0)
	co_applicant_recent_delinquencies: int | None = Field(default=None, ge=0)
	co_applicant_recent_severe_delinquencies: int | None = Field(default=None, ge=0)
	co_applicant_bankruptcies: int | None = Field(default=None, ge=0)
	co_applicant_open_bankruptcy: bool | None = None
	co_applicant_recent_repossessions: int | None = Field(default=None, ge=0)
	co_applicant_charge_offs: int | None = Field(default=None, ge=0)
	co_applicant_recent_inquiries: int | None = Field(default=None, ge=0)
	co_applicant_tradeline_history: dict[str, Any] | None = None
	co_applicant_credit_bureau_attributes: dict[str, Any] | None = None
	co_applicant_identity_verified: bool | None = None
	co_applicant_fraud_flag: bool | None = None
	co_applicant_synthetic_identity_flag: bool | None = None
	co_applicant_sanctions_flag: bool | None = None
	co_applicant_tax_id_valid: bool | None = None
	co_applicant_deceased_tax_id_flag: bool | None = None

	vin: str = Field(min_length=1, max_length=32)
	vehicle_model_year: int = Field(ge=1900)
	vehicle_make: str = Field(min_length=1, max_length=128)
	vehicle_model: str = Field(min_length=1, max_length=128)
	vehicle_trim: str | None = None
	vehicle_new_or_used: str = Field(min_length=1, max_length=32)
	vehicle_mileage: int = Field(ge=0)
	vehicle_valuation_source: str = Field(min_length=1, max_length=128)
	vehicle_value: Decimal = Field(gt=0)
	vehicle_title_status: str = Field(min_length=1, max_length=64)
	vehicle_use: str = Field(min_length=1, max_length=64)
	vehicle_type: str = Field(min_length=1, max_length=64)
	dealer_listed_price: Decimal = Field(gt=0)
	warranty_amount: Decimal = Field(default=Decimal("0"), ge=0)
	gap_amount: Decimal = Field(default=Decimal("0"), ge=0)
	backend_product_amount: Decimal = Field(default=Decimal("0"), ge=0)
	add_ons_amount: Decimal = Field(default=Decimal("0"), ge=0)
	negative_equity_amount: Decimal = Field(default=Decimal("0"), ge=0)
	vin_decoded: bool = True

	dealer_id: str = Field(min_length=1, max_length=64)
	dealer_status: str = Field(min_length=1, max_length=64)
	dealer_risk_rating: str = Field(min_length=1, max_length=64)
	dealer_default_rate: float | None = Field(default=None, ge=0)
	dealer_first_payment_default_rate: float | None = Field(default=None, ge=0)
	dealer_buyback_history: dict[str, Any] | None = None
	dealer_buyback_frequency: float | None = Field(default=None, ge=0)
	dealer_contract_defect_rate: float | None = Field(default=None, ge=0)
	dealer_fraud_flag: bool = False
	dealer_complaint_rate: float | None = Field(default=None, ge=0)
	dealer_max_ltv_override: float | None = Field(default=None, gt=0)
	dealer_program_eligibility: dict[str, Any] | None = None
	dealer_state: str = Field(min_length=2, max_length=32)
	dealer_license_status: str = Field(min_length=1, max_length=64)
	dealer_prior_exception_usage: int = Field(default=0, ge=0)

	monthly_debt_obligations: Decimal = Field(default=Decimal("0"), ge=0)
	estimated_monthly_payment: Decimal | None = Field(default=None, ge=0)


class CreditBureauReportRead(BaseModel):
	tax_id_token: str
	bureau_name: str
	score_model: str
	credit_score: int
	credit_history_depth_months: int
	recent_inquiries: int
	recent_delinquencies: int
	recent_severe_delinquencies: int
	bankruptcies: int
	open_bankruptcy: bool
	recent_repossessions: int
	charge_offs: int
	fraud_flag: bool
	synthetic_identity_flag: bool
	sanctions_flag: bool
	tax_id_valid: bool
	deceased_tax_id_flag: bool
	report_reference: str


class UnderwritingDecisionRead(BaseModel):
	decision: str | None
	risk_tier: str | None
	rule_version: str | None
	evaluated_at: datetime | None
	decline_reasons: list[str]
	stipulations: list[str]
	manual_review_reasons: list[str]
	triggered_rules: list[dict[str, Any]]
	passed_rules: list[str]
	metrics: dict[str, float | int | None]
	dealer_overlay: dict[str, Any] | None
	vehicle_eligibility: dict[str, Any] | None
	audit_correlation_id: str | None


class ApplicationRead(BaseModel):
	id: int
	application_id: str
	application_channel: str
	product_type: str
	applicant_id: str
	applicant_legal_name: str
	applicant_state: str
	applicant_credit_score: int
	applicant_credit_bureau_attributes: dict[str, Any] | None
	requested_loan_amount: Decimal
	requested_term_months: int
	down_payment_amount: Decimal
	vin: str
	vehicle_model_year: int
	vehicle_make: str
	vehicle_model: str
	dealer_id: str
	dealer_status: str
	decision_outcome: str | None
	final_risk_tier: str | None
	created_at: datetime
	updated_at: datetime
	underwriting: UnderwritingDecisionRead


class ApplicationStatusAuditRead(BaseModel):
	id: int
	application_id: str
	previous_status: str | None
	new_status: str
	changed_by: str
	changed_by_role: str
	change_reason: str
	audit_correlation_id: str | None
	created_at: datetime


class FundingResponse(BaseModel):
	application_id: str
	funding_status: str
	previous_decision: str | None
	updated_at: datetime


def _now() -> datetime:
	return datetime.now(UTC)


def _get_application_or_404(application_identifier: str, db: Session) -> LoanApplication:
	query = db.query(LoanApplication)
	if application_identifier.isdigit():
		application = query.filter(LoanApplication.id == int(application_identifier)).first()
	else:
		application = query.filter(LoanApplication.application_id == application_identifier).first()

	if application is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail={"code": "application_not_found", "message": "Application was not found."},
		)
	return application


def _underwriting_input(
	application: LoanApplication,
	estimated_monthly_payment: Decimal | None = None,
	monthly_debt_obligations: Decimal = Decimal("0"),
) -> SimpleNamespace:
	values = {
		column.name: _underwriting_value(getattr(application, column.name)) for column in LoanApplication.__table__.columns
	}
	values["estimated_monthly_payment"] = _underwriting_value(estimated_monthly_payment)
	values["monthly_debt_obligations"] = _underwriting_value(monthly_debt_obligations)
	return SimpleNamespace(**values)


def _underwriting_value(value: Any) -> Any:
	if isinstance(value, Decimal):
		return float(value)
	return value


def _apply_underwriting_result(application: LoanApplication, result: UnderwritingResult) -> None:
	metrics = result.metrics
	application.loan_to_value_ratio = metrics.get("loan_to_value")
	application.payment_to_income_ratio = metrics.get("payment_to_income")
	application.debt_to_income_ratio = metrics.get("debt_to_income")
	application.amount_financed = Decimal(str(metrics.get("amount_financed", 0)))
	application.net_trade_equity = Decimal(str(metrics.get("net_trade_equity", 0)))
	application.vehicle_age_years = int(metrics.get("vehicle_age_years", 0))
	application.applicant_age_years = int(metrics.get("applicant_age_years", 0))
	application.combined_monthly_income = Decimal(str(metrics.get("combined_monthly_income", 0)))
	application.final_risk_tier = result.risk_tier
	application.risk_tier_candidate = result.risk_tier
	application.dealer_overlay_category = result.dealer_overlay.get("level")
	application.rule_version = result.rule_version
	application.decline_reasons = result.decline_reasons
	application.stipulations = result.stipulations
	application.manual_review_reasons = result.manual_review_reasons
	application.triggered_rules = result.triggered_rules
	application.passed_rules = result.passed_rules
	application.dealer_overlay_result = result.dealer_overlay
	application.vehicle_eligibility_result = result.vehicle_eligibility
	application.audit_correlation_id = result.audit_correlation_id
	application.evaluated_at = result.evaluated_at
	application.updated_at = _now()


def _change_application_status(
	db: Session,
	application: LoanApplication,
	new_status: str | None,
	current_user: AuthenticatedUser,
	change_reason: str,
) -> None:
	previous_status = application.decision_outcome
	if new_status is None or previous_status == new_status:
		return

	application.decision_outcome = new_status
	db.add(
		ApplicationStatusAudit(
			application_id=application.application_id,
			previous_status=previous_status,
			new_status=new_status,
			changed_by=current_user.username,
			changed_by_role=current_user.role,
			change_reason=change_reason,
			audit_correlation_id=application.audit_correlation_id,
		)
	)


def _apply_credit_bureau_report(data: dict[str, Any], report: CreditBureauReport | None) -> None:
	if report is None:
		return

	data["applicant_credit_score"] = report.credit_score
	data["applicant_credit_history_depth_months"] = report.credit_history_depth_months
	data["applicant_recent_inquiries"] = report.recent_inquiries
	data["applicant_recent_delinquencies"] = report.recent_delinquencies
	data["applicant_recent_severe_delinquencies"] = report.recent_severe_delinquencies
	data["applicant_bankruptcies"] = report.bankruptcies
	data["applicant_open_bankruptcy"] = report.open_bankruptcy
	data["applicant_recent_repossessions"] = report.recent_repossessions
	data["applicant_charge_offs"] = report.charge_offs
	data["applicant_fraud_flag"] = report.fraud_flag
	data["applicant_synthetic_identity_flag"] = report.synthetic_identity_flag
	data["applicant_sanctions_flag"] = report.sanctions_flag
	data["applicant_tax_id_valid"] = report.tax_id_valid
	data["applicant_deceased_tax_id_flag"] = report.deceased_tax_id_flag
	data["applicant_credit_bureau_attributes"] = report.to_attributes()


def _credit_bureau_read_model(report: CreditBureauReport) -> CreditBureauReportRead:
	return CreditBureauReportRead(**report.to_attributes())


def _audit_read_model(audit: ApplicationStatusAudit) -> ApplicationStatusAuditRead:
	return ApplicationStatusAuditRead(
		id=audit.id,
		application_id=audit.application_id,
		previous_status=audit.previous_status,
		new_status=audit.new_status,
		changed_by=audit.changed_by,
		changed_by_role=audit.changed_by_role,
		change_reason=audit.change_reason,
		audit_correlation_id=audit.audit_correlation_id,
		created_at=audit.created_at,
	)


def _read_model(application: LoanApplication) -> ApplicationRead:
	return ApplicationRead(
		id=application.id,
		application_id=application.application_id,
		application_channel=application.application_channel,
		product_type=application.product_type,
		applicant_id=application.applicant_id,
		applicant_legal_name=application.applicant_legal_name,
		applicant_state=application.applicant_state,
		applicant_credit_score=application.applicant_credit_score,
		applicant_credit_bureau_attributes=application.applicant_credit_bureau_attributes,
		requested_loan_amount=application.requested_loan_amount,
		requested_term_months=application.requested_term_months,
		down_payment_amount=application.down_payment_amount,
		vin=application.vin,
		vehicle_model_year=application.vehicle_model_year,
		vehicle_make=application.vehicle_make,
		vehicle_model=application.vehicle_model,
		dealer_id=application.dealer_id,
		dealer_status=application.dealer_status,
		decision_outcome=application.decision_outcome,
		final_risk_tier=application.final_risk_tier,
		created_at=application.created_at,
		updated_at=application.updated_at,
		underwriting=UnderwritingDecisionRead(
			decision=application.decision_outcome,
			risk_tier=application.final_risk_tier,
			rule_version=application.rule_version,
			evaluated_at=application.evaluated_at,
			decline_reasons=application.decline_reasons or [],
			stipulations=application.stipulations or [],
			manual_review_reasons=application.manual_review_reasons or [],
			triggered_rules=application.triggered_rules or [],
			passed_rules=application.passed_rules or [],
			metrics={
				"loan_to_value": application.loan_to_value_ratio,
				"payment_to_income": application.payment_to_income_ratio,
				"debt_to_income": application.debt_to_income_ratio,
				"amount_financed": float(application.amount_financed) if application.amount_financed is not None else None,
				"net_trade_equity": float(application.net_trade_equity) if application.net_trade_equity is not None else None,
				"vehicle_age_years": application.vehicle_age_years,
				"applicant_age_years": application.applicant_age_years,
				"combined_monthly_income": (
					float(application.combined_monthly_income) if application.combined_monthly_income is not None else None
				),
			},
			dealer_overlay=application.dealer_overlay_result,
			vehicle_eligibility=application.vehicle_eligibility_result,
			audit_correlation_id=application.audit_correlation_id,
		),
	)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.post(
	"/auth/token",
	response_model=TokenResponse,
	responses={status.HTTP_401_UNAUTHORIZED: {"model": ApiError}},
	tags=["auth"],
)
def login(payload: LoginRequest) -> TokenResponse:
	user = authenticate_user(payload.username, payload.password)
	if user is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail={"code": "invalid_credentials", "message": "Username or password is incorrect."},
			headers={"WWW-Authenticate": "Bearer"},
		)
	return create_token_response(user)


@app.get("/auth/me", response_model=AuthenticatedUser, tags=["auth"])
def read_current_user(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
	return current_user


@app.get(
	"/credit-bureau/reports/{tax_id_token}",
	response_model=CreditBureauReportRead,
	responses={status.HTTP_404_NOT_FOUND: {"model": ApiError}},
	tags=["credit-bureau"],
)
def read_credit_bureau_report(
	tax_id_token: str,
	_current_user: AuthenticatedUser = Depends(require_roles("admin", "underwriter", "dealer")),
) -> CreditBureauReportRead:
	report = get_credit_bureau_report(tax_id_token)
	if report is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail={"code": "credit_bureau_report_not_found", "message": "Credit bureau report was not found."},
		)
	return _credit_bureau_read_model(report)


@app.post(
	"/applications",
	response_model=ApplicationRead,
	status_code=status.HTTP_201_CREATED,
	responses={status.HTTP_409_CONFLICT: {"model": ApiError}},
	tags=["applications"],
)
def create_application(
	payload: ApplicationCreate,
	current_user: AuthenticatedUser = Depends(require_roles("admin", "dealer")),
	db: Session = Depends(get_db),
) -> ApplicationRead:
	data = payload.model_dump(exclude={"estimated_monthly_payment", "monthly_debt_obligations"})
	_apply_credit_bureau_report(data, get_credit_bureau_report(payload.applicant_tax_id_token))
	application = LoanApplication(**data)
	result = UnderwritingEngine().evaluate(
		_underwriting_input(application, payload.estimated_monthly_payment, payload.monthly_debt_obligations)
	)
	_apply_underwriting_result(application, result)

	db.add(application)
	_change_application_status(db, application, result.decision, current_user, "underwriting_decision")
	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail={"code": "duplicate_application", "message": "Application ID already exists."},
		) from exc

	db.refresh(application)
	return _read_model(application)


@app.get("/applications", response_model=list[ApplicationRead], tags=["applications"])
def list_applications(
	_current_user: AuthenticatedUser = Depends(require_roles("admin", "underwriter", "dealer", "auditor")),
	db: Session = Depends(get_db),
) -> list[ApplicationRead]:
	applications = db.query(LoanApplication).order_by(LoanApplication.created_at.desc()).all()
	return [_read_model(application) for application in applications]


@app.get(
	"/applications/{application_identifier}",
	response_model=ApplicationRead,
	responses={status.HTTP_404_NOT_FOUND: {"model": ApiError}},
	tags=["applications"],
)
def get_application(
	application_identifier: str,
	_current_user: AuthenticatedUser = Depends(require_roles("admin", "underwriter", "dealer", "auditor")),
	db: Session = Depends(get_db),
) -> ApplicationRead:
	return _read_model(_get_application_or_404(application_identifier, db))


@app.post(
	"/applications/{application_identifier}/fund",
	response_model=FundingResponse,
	responses={
		status.HTTP_404_NOT_FOUND: {"model": ApiError},
		status.HTTP_409_CONFLICT: {"model": ApiError},
	},
	tags=["applications"],
)
def fund_application(
	application_identifier: str,
	current_user: AuthenticatedUser = Depends(require_roles("admin", "underwriter")),
	db: Session = Depends(get_db),
) -> FundingResponse:
	application = _get_application_or_404(application_identifier, db)
	previous_decision = application.decision_outcome

	if previous_decision == "funded":
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail={"code": "application_already_funded", "message": "Application has already been funded."},
		)
	if previous_decision not in {"approved", "approved_with_stipulations"}:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail={"code": "application_not_fundable", "message": "Only approved applications can be funded."},
		)

	application.updated_at = _now()
	_change_application_status(db, application, "funded", current_user, "funding")
	db.commit()
	db.refresh(application)

	return FundingResponse(
		application_id=application.application_id,
		funding_status="funded",
		previous_decision=previous_decision,
		updated_at=application.updated_at,
	)


@app.get(
	"/applications/{application_identifier}/status-audit",
	response_model=list[ApplicationStatusAuditRead],
	responses={status.HTTP_404_NOT_FOUND: {"model": ApiError}},
	tags=["applications"],
)
def list_application_status_audit(
	application_identifier: str,
	_current_user: AuthenticatedUser = Depends(require_roles("admin", "underwriter", "auditor")),
	db: Session = Depends(get_db),
) -> list[ApplicationStatusAuditRead]:
	application = _get_application_or_404(application_identifier, db)
	audits = (
		db.query(ApplicationStatusAudit)
		.filter(ApplicationStatusAudit.application_id == application.application_id)
		.order_by(ApplicationStatusAudit.created_at.asc(), ApplicationStatusAudit.id.asc())
		.all()
	)
	return [_audit_read_model(audit) for audit in audits]


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
	app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
