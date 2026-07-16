# Underwriting Rules Engine Specification

## Purpose

The underwriting rules engine evaluates an auto loan application and returns a repeatable, explainable decision. It combines hard-decline checks, risk-tier assignment, vehicle eligibility constraints, dealer risk overlays, and final decision logic.

The engine should be deterministic for the same application inputs, rule version, and dealer configuration. Every decision must include rule outcomes, reasons, stipulations, and audit metadata.

## Engine Location

- [../backend/underwriting/engine.py](../backend/underwriting/engine.py): Coordinates rule execution and final decision construction.
- [../backend/underwriting/rules/hard_declines.py](../backend/underwriting/rules/hard_declines.py): Hard-decline rules.
- [../backend/underwriting/rules/risk_tiers.py](../backend/underwriting/rules/risk_tiers.py): Risk-tier calculation.
- [../backend/underwriting/rules/vehicle_constraints.py](../backend/underwriting/rules/vehicle_constraints.py): Vehicle eligibility and collateral rules.
- [../backend/underwriting/rules/dealer_overlay.py](../backend/underwriting/rules/dealer_overlay.py): Dealer-specific overlays and exceptions.
- [../backend/tests/underwriting/test_engine.py](../backend/tests/underwriting/test_engine.py): Engine and rule tests.

## Decision Outcomes

The engine returns one of the following outcomes:

- **Approved**: Application satisfies all required checks and is eligible without manual review.
- **Approved With Stipulations**: Application is eligible, but funding requires additional documents, verification, or conditions.
- **Manual Review**: Application is not automatically approved or declined and requires human underwriter review.
- **Declined**: Application fails one or more hard-decline rules or non-waivable constraints.

## Required Inputs

### Application Inputs

- Application ID.
- Application channel, such as dealer portal, direct-to-consumer, branch, or partner API.
- Submission timestamp.
- Requested loan amount.
- Requested term in months.
- Down payment amount.
- Trade-in value and payoff, when applicable.
- Product type, such as new auto, used auto, refinance, lease buyout, or private-party purchase.
- Co-applicant indicator.
- Prior decision reference, when the application is a resubmission.

### Applicant Inputs

- Applicant ID.
- Legal name.
- Date of birth.
- Social Security number or tax identifier token.
- Address and residence duration.
- Employment status.
- Employer name.
- Employment duration.
- Monthly gross income.
- Monthly housing payment.
- Credit score.
- Credit bureau attributes, such as bankruptcies, delinquencies, charge-offs, inquiries, and tradeline history.
- Fraud, identity, or sanctions-screening indicators.

When a matching fake credit bureau report is available for the submitted tax identifier token, the bureau score and bureau-derived credit attributes supersede client-submitted credit fields before underwriting runs. This keeps risk-tier assignment, hard-decline credit policy, and fraud indicators tied to a single bureau snapshot.

### Co-Applicant Inputs

When a co-applicant is present, capture the same core identity, income, employment, and credit attributes used for the primary applicant.

Risk-tier logic may consider combined income and blended credit attributes, but hard declines can still apply to either applicant independently.

### Vehicle Inputs

- VIN.
- Model year.
- Make, model, and trim.
- New or used status.
- Mileage.
- Vehicle valuation source and value.
- Title status.
- Vehicle use, such as personal, rideshare, commercial, or fleet.
- Vehicle type, such as passenger car, truck, motorcycle, recreational vehicle, or salvage vehicle.
- Dealer-listed price.
- Add-ons, warranty, GAP, and backend product amounts.

### Dealer Inputs

- Dealer ID.
- Dealer status, such as active, probation, suspended, or terminated.
- Dealer risk rating.
- Dealer default rate.
- Dealer buyback history.
- Dealer fraud or complaint flags.
- Maximum allowed loan-to-value override.
- Program eligibility.
- State and licensing status.

### Derived Inputs

The engine calculates these values before rule evaluation:

- Loan-to-value ratio.
- Payment-to-income ratio.
- Debt-to-income ratio.
- Amount financed.
- Net trade equity.
- Vehicle age.
- Applicant age.
- Combined income, when co-applicant data is available.
- Credit score band.
- Risk-tier candidate.
- Dealer overlay category.

## Rule Execution Order

Rules should execute in this order:

1. Validate required input completeness.
2. Compute derived fields.
3. Evaluate hard-decline rules.
4. Evaluate vehicle constraints.
5. Assign base risk tier.
6. Apply dealer risk overlay.
7. Produce final decision.
8. Generate reasons, stipulations, and audit metadata.

Hard declines are terminal unless the rule is explicitly configured as reviewable. Non-terminal rules continue evaluation so the returned decision includes a complete explanation.

## Hard Declines

Hard declines are non-negotiable eligibility failures. If any active hard-decline rule fails, the default final decision is **Declined**.

### Identity And Fraud

- Applicant fails identity verification.
- Co-applicant fails identity verification.
- Applicant appears on prohibited-party, sanctions, or internal exclusion lists.
- Confirmed synthetic identity indicator is present.
- Confirmed fraud indicator is present.
- SSN or tax identifier is invalid, deceased, or mismatched.

### Applicant Eligibility

- Applicant is under the minimum legal age for the product and state.
- Applicant residence is outside eligible lending states.
- Applicant has no verifiable income when income verification is required.
- Applicant is currently in active bankruptcy where policy prohibits approval.
- Applicant has an unresolved prior fraud or first-payment-default investigation.

### Credit Policy

- Credit score below the absolute minimum threshold.
- Open bankruptcy where product policy requires automatic decline.
- Recent repossession inside the non-waivable lookback window.
- Excessive recent severe delinquency inside the non-waivable lookback window.
- Charged-off prior account with the lender that is not resolved or approved for exception.

### Loan Structure

- Requested loan amount below minimum or above maximum program limits.
- Requested term exceeds product maximum.
- Payment-to-income exceeds absolute maximum.
- Debt-to-income exceeds absolute maximum.
- Loan-to-value exceeds absolute maximum after all allowable backend products and fees.
- Down payment below minimum required for the product, state, or risk tier.

### Dealer Status

- Dealer is suspended, terminated, unlicensed, or outside eligible program participation.
- Dealer is blocked for suspected fraud or unresolved compliance issues.

## Risk Tiers

Risk tiers classify eligible applications by expected credit risk. Tiers influence pricing, stipulations, maximum loan-to-value, maximum term, and manual review requirements.

### Tier Inputs

- Credit score.
- Credit history depth.
- Recent delinquencies.
- Bankruptcy and repossession history.
- Debt-to-income ratio.
- Payment-to-income ratio.
- Loan-to-value ratio.
- Employment duration.
- Residence stability.
- Prior lender relationship.
- Co-applicant strength.

### Base Tier Definitions

| Tier | Description | Typical Policy Treatment |
| --- | --- | --- |
| A+ | Prime, low risk | Highest automation eligibility, best pricing, broad vehicle eligibility |
| A | Strong credit | Automated approval eligible with standard stipulations |
| B | Near-prime | Moderate pricing, tighter LTV and term limits |
| C | Elevated risk | More stipulations, tighter affordability and collateral requirements |
| D | High risk | Manual review likely, lower LTV, shorter terms, stronger income verification |
| E | Very high risk | Usually manual review or decline unless compensating factors are strong |

### Example Tier Bands

These example bands are placeholders and must be replaced by approved credit policy before production use.

| Credit Score | Candidate Tier |
| --- | --- |
| 760+ | A+ |
| 720-759 | A |
| 680-719 | B |
| 640-679 | C |
| 600-639 | D |
| Below 600 | E or hard decline depending on minimum score policy |

### Tier Adjustments

The engine may adjust the candidate tier based on compensating or adverse factors.

Downgrade factors:

- Thin credit file.
- Multiple recent inquiries.
- Recent severe delinquency.
- Short employment duration.
- Short residence duration.
- High payment-to-income.
- High debt-to-income.
- High loan-to-value.
- Negative equity carryover.
- Dealer risk overlay.

Upgrade or stabilizing factors:

- Strong co-applicant.
- Long employment duration.
- Low debt-to-income.
- Low loan-to-value.
- Meaningful down payment.
- Prior positive lender relationship.

Tier upgrades should be capped and auditable. The engine should never upgrade an application past a hard-decline or non-waivable vehicle constraint.

## Vehicle Constraints

Vehicle constraints ensure collateral eligibility and appropriate loan structure.

### Vehicle Eligibility Rules

- Vehicle age must be within product limits.
- Mileage must be within product limits.
- VIN must be valid and decode successfully.
- Title must be clean unless the product explicitly allows branded titles.
- Salvage, flood, lemon, rebuilt, or total-loss titles are declined unless policy explicitly allows review.
- Vehicle cannot be used for prohibited commercial or rideshare purposes unless a commercial product applies.
- Vehicle type must be supported by the selected product.

### Collateral Value Rules

- Vehicle valuation must come from an approved valuation source.
- Dealer sale price must be within an acceptable variance from verified market value.
- Loan-to-value must not exceed the tier, product, and dealer limits.
- Backend products such as warranties and GAP must stay within allowed caps.
- Negative equity carryover must stay within allowed limits.

### Term And Mileage Rules

- Older vehicles receive shorter maximum terms.
- Higher-mileage vehicles receive shorter maximum terms.
- High-risk tiers receive shorter maximum terms.
- Maximum term is the most restrictive limit from product, tier, vehicle age, mileage, and dealer overlay.

### Vehicle Decision Outcomes

Vehicle rules can return:

- **Pass**: Vehicle is eligible.
- **Stipulation**: Vehicle is eligible if additional proof is supplied, such as title documentation or valuation support.
- **Manual Review**: Vehicle may be eligible but requires underwriter judgment.
- **Decline**: Vehicle fails a non-waivable constraint.

## Dealer Risk Overlay

Dealer overlays modify underwriting treatment based on dealer behavior, risk profile, program status, and compliance standing.

### Dealer Risk Inputs

- Dealer approval status.
- Dealer risk rating.
- Historical default rate.
- First-payment-default rate.
- Buyback frequency.
- Contract defect rate.
- Fraud alerts.
- Complaint rate.
- State licensing status.
- Program eligibility.
- Prior exception usage.

### Overlay Actions

Dealer overlays may apply any of the following actions:

- Reduce maximum loan-to-value.
- Reduce maximum term.
- Require manual review.
- Require stronger income verification.
- Require proof of residence.
- Require proof of insurance.
- Require title or bookout validation.
- Block specific products or programs.
- Block automated approval.
- Hard decline applications from suspended or terminated dealers.

### Dealer Overlay Levels

| Level | Description | Treatment |
| --- | --- | --- |
| Standard | Normal dealer standing | No overlay beyond base policy |
| Watch | Elevated monitoring | Additional stipulations or reduced automation |
| Restricted | High operational or credit risk | Manual review, lower LTV, shorter terms |
| Suspended | Not eligible to submit fundable deals | Hard decline or block submission |

Dealer overlays should be applied after base risk-tier assignment so the final decision clearly separates applicant risk from dealer risk.

## Final Decision Logic

### Decision Precedence

Final decision precedence should be:

1. Hard decline.
2. Non-waivable vehicle decline.
3. Suspended or terminated dealer decline.
4. Manual review requirement.
5. Approval with stipulations.
6. Approval.

### Decline Logic

Return **Declined** when:

- Any non-reviewable hard-decline rule fails.
- Vehicle collateral fails a non-waivable eligibility rule.
- Dealer is suspended, terminated, or blocked.
- Loan structure exceeds absolute policy caps.

The decision response must include all triggered decline reasons that are safe and compliant to display.

### Manual Review Logic

Return **Manual Review** when no terminal decline applies and at least one review condition is triggered.

Examples:

- Borderline credit profile.
- High but not absolute debt-to-income.
- High but not absolute loan-to-value.
- Recent credit derogatory item outside hard-decline thresholds.
- Dealer watch or restricted overlay.
- Vehicle valuation variance requiring review.
- Exception request is present.

### Approval With Stipulations Logic

Return **Approved With Stipulations** when the application is eligible but funding requires conditions.

Examples:

- Proof of income.
- Proof of residence.
- Proof of insurance.
- Driver license verification.
- Title documentation.
- Corrected contract.
- Updated bookout.
- Down payment verification.

### Approval Logic

Return **Approved** when:

- No hard-decline rules fail.
- Vehicle constraints pass.
- Dealer overlay allows automated approval.
- Risk tier is eligible for automation.
- Loan structure is within tier and product limits.
- No required stipulations or manual-review triggers remain.

## Decision Response Contract

The underwriting engine should return a structured response with these fields:

- Application ID.
- Decision outcome.
- Risk tier.
- Rule version.
- Evaluation timestamp.
- Decline reasons.
- Stipulations.
- Manual review reasons.
- Triggered rules.
- Passed rules.
- Derived metrics, such as loan-to-value, debt-to-income, payment-to-income, and vehicle age.
- Dealer overlay result.
- Vehicle eligibility result.
- Audit correlation ID.

Example shape:

```json
{
	"application_id": "APP-10001",
	"decision": "approved_with_stipulations",
	"risk_tier": "B",
	"rule_version": "2026.07.15",
	"reasons": [],
	"stipulations": ["proof_of_income", "proof_of_insurance"],
	"manual_review_reasons": [],
	"metrics": {
		"loan_to_value": 0.92,
		"debt_to_income": 0.34,
		"payment_to_income": 0.11,
		"vehicle_age_years": 3
	},
	"dealer_overlay": {
		"level": "standard",
		"actions": []
	}
}
```

## Rule Metadata

Every rule should expose metadata for traceability:

- Rule ID.
- Rule name.
- Rule category.
- Rule severity.
- Rule version.
- Effective date.
- Expiration date, when applicable.
- Policy reference.
- Result status.
- Human-readable reason.
- Machine-readable reason code.

Reason codes should be stable because they may be used by analytics, customer communications, compliance review, and downstream workflows.

## Audit And Explainability

The engine must persist enough detail to reconstruct a decision:

- Input snapshot or input reference.
- Rule version used at decision time.
- Derived values used in evaluation.
- Each rule result.
- Final decision and reason codes.
- User or system actor that requested evaluation.
- Timestamp and correlation ID.

Sensitive applicant data should be masked in logs. Full applicant data should be stored only in approved systems with proper access controls.

## Testing Requirements

Tests should cover:

- One passing approval scenario per eligible risk tier.
- One hard-decline scenario per hard-decline rule.
- Boundary values for score, loan-to-value, debt-to-income, payment-to-income, age, mileage, and term.
- Dealer overlay behavior for standard, watch, restricted, and suspended dealers.
- Vehicle constraint behavior for clean, stipulation, manual-review, and decline outcomes.
- Final decision precedence when multiple rules fire.
- Deterministic output for the same inputs and rule version.

Test fixtures should use synthetic applicants only. Do not use real customer data.

## Copilot Usage Notes

### Recommended Prompts

Use Copilot to generate implementation and tests from policy-level examples. Provide the rule, expected outcome, and boundary cases.

Useful prompt patterns:

- "Add tests for the vehicle mileage boundary rule in [../backend/tests/underwriting/test_engine.py](../backend/tests/underwriting/test_engine.py)."
- "Implement a hard-decline rule in [../backend/underwriting/rules/hard_declines.py](../backend/underwriting/rules/hard_declines.py) for applications below the minimum credit score. Include reason codes."
- "Update [../backend/underwriting/engine.py](../backend/underwriting/engine.py) so hard-decline results take precedence over manual review."
- "Compare the implementation against [UNDERWRITING_RULES.md](UNDERWRITING_RULES.md) and identify missing tests."

### Guardrails For Copilot-Generated Rules

- Treat generated underwriting code as a draft until reviewed by a human policy owner.
- Require tests before accepting a new rule or rule change.
- Keep policy thresholds configurable rather than hardcoded when thresholds may vary by product, state, dealer, or effective date.
- Do not include real applicant data in prompts, tests, logs, or fixtures.
- Preserve explainability by returning rule IDs and reason codes for every triggered rule.
- Update this document whenever rule behavior changes.

### Copilot Review Checklist

Ask Copilot to check:

- Whether hard-decline rules are terminal.
- Whether final decision precedence is correct.
- Whether all thresholds have boundary tests.
- Whether every triggered rule returns a stable reason code.
- Whether sensitive data is excluded from logs and test fixtures.
- Whether dealer overlays are separated from applicant credit risk.
- Whether rule changes require updates to [ARCHITECTURE.md](ARCHITECTURE.md) or [STACK.md](STACK.md).
