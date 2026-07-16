from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class CreditBureauReport:
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

	def to_attributes(self) -> dict[str, object]:
		return asdict(self)


FAKE_CREDIT_BUREAU_REPORTS: dict[str, CreditBureauReport] = {
	"tok_prime_applicant": CreditBureauReport(
		tax_id_token="tok_prime_applicant",
		bureau_name="Fictional Bureau One",
		score_model="FAKE_AUTO_V1",
		credit_score=785,
		credit_history_depth_months=156,
		recent_inquiries=1,
		recent_delinquencies=0,
		recent_severe_delinquencies=0,
		bankruptcies=0,
		open_bankruptcy=False,
		recent_repossessions=0,
		charge_offs=0,
		fraud_flag=False,
		synthetic_identity_flag=False,
		sanctions_flag=False,
		tax_id_valid=True,
		deceased_tax_id_flag=False,
		report_reference="CBR-PRIME-001",
	),
	"tok_near_prime_applicant": CreditBureauReport(
		tax_id_token="tok_near_prime_applicant",
		bureau_name="Fictional Bureau One",
		score_model="FAKE_AUTO_V1",
		credit_score=705,
		credit_history_depth_months=84,
		recent_inquiries=2,
		recent_delinquencies=0,
		recent_severe_delinquencies=0,
		bankruptcies=0,
		open_bankruptcy=False,
		recent_repossessions=0,
		charge_offs=0,
		fraud_flag=False,
		synthetic_identity_flag=False,
		sanctions_flag=False,
		tax_id_valid=True,
		deceased_tax_id_flag=False,
		report_reference="CBR-NEAR-PRIME-001",
	),
	"tok_subprime_applicant": CreditBureauReport(
		tax_id_token="tok_subprime_applicant",
		bureau_name="Fictional Bureau One",
		score_model="FAKE_AUTO_V1",
		credit_score=552,
		credit_history_depth_months=42,
		recent_inquiries=6,
		recent_delinquencies=2,
		recent_severe_delinquencies=1,
		bankruptcies=0,
		open_bankruptcy=False,
		recent_repossessions=0,
		charge_offs=0,
		fraud_flag=False,
		synthetic_identity_flag=False,
		sanctions_flag=False,
		tax_id_valid=True,
		deceased_tax_id_flag=False,
		report_reference="CBR-SUBPRIME-001",
	),
	"tok_fraud_alert_applicant": CreditBureauReport(
		tax_id_token="tok_fraud_alert_applicant",
		bureau_name="Fictional Bureau One",
		score_model="FAKE_AUTO_V1",
		credit_score=690,
		credit_history_depth_months=96,
		recent_inquiries=3,
		recent_delinquencies=0,
		recent_severe_delinquencies=0,
		bankruptcies=0,
		open_bankruptcy=False,
		recent_repossessions=0,
		charge_offs=0,
		fraud_flag=True,
		synthetic_identity_flag=False,
		sanctions_flag=False,
		tax_id_valid=True,
		deceased_tax_id_flag=False,
		report_reference="CBR-FRAUD-001",
	),
}


def get_credit_bureau_report(tax_id_token: str) -> CreditBureauReport | None:
	return FAKE_CREDIT_BUREAU_REPORTS.get(tax_id_token)