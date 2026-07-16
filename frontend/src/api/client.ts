export type DecisionOutcome = 'approved' | 'approved_with_stipulations' | 'declined' | 'funded' | 'manual_review'

export type RuleSeverity = 'decline' | 'review' | 'stipulation'

export type TriggeredRule = {
	rule_id: string
	category: string
	severity: RuleSeverity
	reason: string
}

export type UnderwritingMetrics = {
	loan_to_value: number | null
	payment_to_income: number | null
	debt_to_income: number | null
	amount_financed: number | null
	net_trade_equity: number | null
	vehicle_age_years: number | null
	applicant_age_years: number | null
	combined_monthly_income: number | null
}

export type DealerOverlay = {
	level?: string
	actions?: string[]
	decline_reasons?: string[]
	stipulations?: string[]
	manual_review_reasons?: string[]
	triggered_rules?: TriggeredRule[]
	[key: string]: unknown
}

export type VehicleEligibility = {
	status?: 'decline' | 'manual_review' | 'pass' | 'stipulation'
	decline_reasons?: string[]
	stipulations?: string[]
	manual_review_reasons?: string[]
	triggered_rules?: TriggeredRule[]
	[key: string]: unknown
}

export type UnderwritingDecision = {
	decision: string | null
	risk_tier: string | null
	rule_version?: string | null
	evaluated_at?: string | null
	decline_reasons: string[]
	stipulations: string[]
	manual_review_reasons: string[]
	triggered_rules?: TriggeredRule[]
	passed_rules?: string[]
	metrics?: UnderwritingMetrics
	dealer_overlay?: DealerOverlay | null
	vehicle_eligibility?: VehicleEligibility | null
	audit_correlation_id?: string | null
}

export type LoanApplication = {
	id: number
	application_id: string
	applicant_legal_name: string
	applicant_state: string
	applicant_credit_score: number
	applicant_credit_bureau_attributes?: CreditBureauReport | null
	requested_loan_amount: string
	requested_term_months: number
	vehicle_make: string
	vehicle_model: string
	vehicle_model_year: number
	dealer_id: string
	dealer_status: string
	decision_outcome: DecisionOutcome | null
	final_risk_tier: string | null
	created_at?: string
	updated_at?: string
	underwriting: UnderwritingDecision
}

export type CreateApplicationPayload = {
	application_id: string
	application_channel: string
	product_type: string
	requested_loan_amount: number
	requested_term_months: number
	down_payment_amount: number
	trade_in_value?: number
	trade_in_payoff?: number
	prior_decision_reference?: string
	applicant_id: string
	applicant_legal_name: string
	applicant_date_of_birth: string
	applicant_tax_id_token: string
	applicant_address: string
	applicant_state: string
	applicant_residence_duration_months: number
	applicant_employment_status: string
	applicant_employer_name?: string
	applicant_employment_duration_months?: number
	applicant_monthly_gross_income: number
	applicant_monthly_housing_payment: number
	applicant_credit_score: number
	applicant_credit_history_depth_months?: number
	applicant_recent_delinquencies?: number
	applicant_recent_severe_delinquencies?: number
	applicant_bankruptcies?: number
	applicant_open_bankruptcy?: boolean
	applicant_recent_repossessions?: number
	applicant_charge_offs?: number
	applicant_recent_inquiries?: number
	applicant_identity_verified?: boolean
	applicant_fraud_flag?: boolean
	applicant_synthetic_identity_flag?: boolean
	applicant_sanctions_flag?: boolean
	applicant_tax_id_valid?: boolean
	applicant_deceased_tax_id_flag?: boolean
	applicant_prior_fraud_investigation?: boolean
	applicant_prior_first_payment_default_investigation?: boolean
	applicant_prior_positive_lender_relationship?: boolean
	has_co_applicant?: boolean
	co_applicant_monthly_gross_income?: number
	co_applicant_credit_score?: number
	vin: string
	vehicle_model_year: number
	vehicle_make: string
	vehicle_model: string
	vehicle_trim?: string
	vehicle_new_or_used: string
	vehicle_mileage: number
	vehicle_valuation_source: string
	vehicle_value: number
	vehicle_title_status: string
	vehicle_use: string
	vehicle_type: string
	dealer_listed_price: number
	warranty_amount?: number
	gap_amount?: number
	backend_product_amount?: number
	add_ons_amount?: number
	negative_equity_amount?: number
	vin_decoded?: boolean
	dealer_id: string
	dealer_status: string
	dealer_risk_rating: string
	dealer_default_rate?: number
	dealer_first_payment_default_rate?: number
	dealer_buyback_frequency?: number
	dealer_contract_defect_rate?: number
	dealer_fraud_flag?: boolean
	dealer_complaint_rate?: number
	dealer_max_ltv_override?: number
	dealer_state: string
	dealer_license_status: string
	dealer_prior_exception_usage?: number
	monthly_debt_obligations?: number
	estimated_monthly_payment?: number
}

export type FundingResponse = {
	application_id: string
	funding_status: 'funded'
	previous_decision: DecisionOutcome | null
	updated_at: string
}

export type CreditBureauReport = {
	tax_id_token: string
	bureau_name: string
	score_model: string
	credit_score: number
	credit_history_depth_months: number
	recent_inquiries: number
	recent_delinquencies: number
	recent_severe_delinquencies: number
	bankruptcies: number
	open_bankruptcy: boolean
	recent_repossessions: number
	charge_offs: number
	fraud_flag: boolean
	synthetic_identity_flag: boolean
	sanctions_flag: boolean
	tax_id_valid: boolean
	deceased_tax_id_flag: boolean
	report_reference: string
}

export type UserRole = 'admin' | 'underwriter' | 'dealer' | 'auditor'

export type AuthenticatedUser = {
	username: string
	role: UserRole
}

export type LoginPayload = {
	username: string
	password: string
}

export type TokenResponse = {
	access_token: string
	token_type: 'bearer'
	expires_in: number
	user: AuthenticatedUser
}

type ApiErrorBody = {
	detail?: string | { code?: string; message?: string }
}

const API_BASE_URL = 'http://localhost:8000'
const ACCESS_TOKEN_STORAGE_KEY = 'auto-loan-auth-token'

function endpoint(path: string): string {
	return `${API_BASE_URL}${path}`
}

export function getAccessToken(): string | null {
	return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function setAccessToken(token: string | null) {
	if (token) {
		window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
		return
	}

	window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}

function authHeaders(): HeadersInit {
	const token = getAccessToken()
	return token ? { Authorization: `Bearer ${token}` } : {}
}

async function parseResponse<T>(response: Response): Promise<T> {
	if (response.ok) {
		return response.json()
	}

	const body = (await response.json().catch(() => null)) as ApiErrorBody | null
	const message = typeof body?.detail === 'string' ? body.detail : body?.detail?.message ?? `Request failed: ${response.status} ${response.statusText}`
	throw new Error(message)
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
	const response = await fetch(endpoint('/auth/token'), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload),
	})

	return parseResponse<TokenResponse>(response)
}

export async function getCurrentUser(): Promise<AuthenticatedUser> {
	const response = await fetch(endpoint('/auth/me'), {
		headers: authHeaders(),
	})

	return parseResponse<AuthenticatedUser>(response)
}

export async function listApplications(): Promise<LoanApplication[]> {
	const response = await fetch(endpoint('/applications'), {
		headers: authHeaders(),
	})
	return parseResponse<LoanApplication[]>(response)
}

export async function getApplication(applicationId: string): Promise<LoanApplication> {
	const response = await fetch(endpoint(`/applications/${encodeURIComponent(applicationId)}`), {
		headers: authHeaders(),
	})
	return parseResponse<LoanApplication>(response)
}

export async function getCreditBureauReport(taxIdToken: string): Promise<CreditBureauReport> {
	const response = await fetch(endpoint(`/credit-bureau/reports/${encodeURIComponent(taxIdToken)}`), {
		headers: authHeaders(),
	})
	return parseResponse<CreditBureauReport>(response)
}

export async function createApplication(payload: CreateApplicationPayload): Promise<LoanApplication> {
	const response = await fetch(endpoint('/applications'), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(payload),
	})

	return parseResponse<LoanApplication>(response)
}

export async function fundApplication(applicationId: string): Promise<FundingResponse> {
	const response = await fetch(endpoint(`/applications/${encodeURIComponent(applicationId)}/fund`), {
		method: 'POST',
		headers: authHeaders(),
	})

	return parseResponse<FundingResponse>(response)
}
