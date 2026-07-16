import type { UnderwritingDecision } from '../api/client'

type UnderwritingSummaryProps = {
	decision: UnderwritingDecision | null | undefined
	compact?: boolean
}

type PricingAdjustment = {
	label: string
	detail: string
	impact: 'favorable' | 'neutral' | 'review' | 'restrictive'
}

export default function UnderwritingSummary({ compact = false, decision }: UnderwritingSummaryProps) {
	if (!decision) {
		return <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">No underwriting result yet.</section>
	}

	const metrics = decision.metrics
	const pricingAdjustments = getPricingAdjustments(decision)
	const reasons = [
		...decision.decline_reasons.map((reason) => ({ label: 'Decline', reason })),
		...decision.manual_review_reasons.map((reason) => ({ label: 'Review', reason })),
		...decision.stipulations.map((reason) => ({ label: 'Stipulation', reason })),
	]

	return (
		<section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
			<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div>
					<p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Underwriting result</p>
					<div className="mt-2 flex flex-wrap items-center gap-2">
						<SummaryBadge label="Decision" value={decision.decision ?? 'pending'} variant={decisionVariant(decision.decision)} />
						<SummaryBadge label="Risk tier" value={decision.risk_tier ?? '-'} variant="neutral" />
					</div>
				</div>
				{decision.evaluated_at ? <p className="text-xs text-slate-500">Evaluated {formatDate(decision.evaluated_at)}</p> : null}
			</div>

			{metrics ? (
				<div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
					<Metric label="DTI" value={formatPercent(metrics.debt_to_income)} />
					<Metric label="LTV" value={formatPercent(metrics.loan_to_value)} />
					<Metric label="Risk tier" value={decision.risk_tier ?? '-'} />
					<Metric label="Decision" value={formatDecision(decision.decision)} />
				</div>
			) : null}

			{compact ? (
				<p className="mt-3 text-sm text-slate-600">{reasons[0]?.reason ?? `${decision.triggered_rules?.length ?? 0} rules triggered.`}</p>
			) : (
				<div className="mt-4 grid gap-4 xl:grid-cols-2">
					<ReasonList title="Decision reasons" reasons={reasons} />
					<PricingAdjustments adjustments={pricingAdjustments} />
					<div className="xl:col-span-2">
						<RuleList rules={decision.triggered_rules ?? []} />
					</div>
				</div>
			)}
		</section>
	)
}

function SummaryBadge({ label, value, variant }: { label: string; value: string; variant: PricingAdjustment['impact'] }) {
	return (
		<span className={`rounded-md px-2 py-1 text-xs font-semibold ${variantClass(variant)}`}>
			{label}: {value}
		</span>
	)
}

function Metric({ label, value }: { label: string; value: string }) {
	return (
		<div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
			<p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
			<p className="mt-1 text-sm font-semibold text-slate-950">{value}</p>
		</div>
	)
}

function ReasonList({ reasons, title }: { reasons: { label: string; reason: string }[]; title: string }) {
	return (
		<div>
			<h3 className="text-sm font-semibold text-slate-950">{title}</h3>
			{reasons.length > 0 ? (
				<ul className="mt-2 space-y-2 text-sm text-slate-700">
					{reasons.map((item) => (
						<li className="rounded-md bg-slate-50 px-3 py-2" key={`${item.label}-${item.reason}`}>
							<span className="font-semibold text-slate-950">{item.label}:</span> {item.reason}
						</li>
					))}
				</ul>
			) : (
				<p className="mt-2 text-sm text-slate-600">No decline, review, or stipulation reasons.</p>
			)}
		</div>
	)
}

function PricingAdjustments({ adjustments }: { adjustments: PricingAdjustment[] }) {
	return (
		<div>
			<h3 className="text-sm font-semibold text-slate-950">Pricing adjustments</h3>
			{adjustments.length > 0 ? (
				<ul className="mt-2 space-y-2 text-sm text-slate-700">
					{adjustments.map((adjustment) => (
						<li className="rounded-md bg-slate-50 px-3 py-2" key={`${adjustment.label}-${adjustment.detail}`}>
							<div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
								<span>
									<span className="font-semibold text-slate-950">{adjustment.label}:</span> {adjustment.detail}
								</span>
								<span className={`w-fit rounded-md px-2 py-1 text-xs font-semibold ${variantClass(adjustment.impact)}`}>
									{adjustment.impact}
								</span>
							</div>
						</li>
					))}
				</ul>
			) : (
				<p className="mt-2 text-sm text-slate-600">No pricing adjustments returned or derived.</p>
			)}
		</div>
	)
}

function RuleList({ rules }: { rules: NonNullable<UnderwritingDecision['triggered_rules']> }) {
	return (
		<div>
			<h3 className="text-sm font-semibold text-slate-950">Triggered rules</h3>
			{rules.length > 0 ? (
				<ul className="mt-2 space-y-2 text-sm text-slate-700">
					{rules.slice(0, 6).map((rule) => (
						<li className="rounded-md bg-slate-50 px-3 py-2" key={rule.rule_id}>
							<span className="font-semibold text-slate-950">{rule.rule_id}</span> {rule.reason}
						</li>
					))}
				</ul>
			) : (
				<p className="mt-2 text-sm text-slate-600">No triggered rules returned.</p>
			)}
		</div>
	)
}

function getPricingAdjustments(decision: UnderwritingDecision): PricingAdjustment[] {
	const adjustments: PricingAdjustment[] = []
	const tierAdjustment = tierPricingAdjustment(decision.risk_tier)

	if (tierAdjustment) {
		adjustments.push(tierAdjustment)
	}

	const ltv = decision.metrics?.loan_to_value
	if (ltv !== null && ltv !== undefined) {
		if (ltv <= 0.8) {
			adjustments.push({ detail: `${formatPercent(ltv)} LTV supports better collateral pricing.`, impact: 'favorable', label: 'Collateral' })
		} else if (ltv >= 1.1) {
			adjustments.push({ detail: `${formatPercent(ltv)} LTV requires restrictive pricing or review.`, impact: 'restrictive', label: 'Collateral' })
		} else if (ltv >= 1) {
			adjustments.push({ detail: `${formatPercent(ltv)} LTV tightens price and advance limits.`, impact: 'review', label: 'Collateral' })
		}
	}

	const dti = decision.metrics?.debt_to_income
	if (dti !== null && dti !== undefined) {
		if (dti <= 0.35) {
			adjustments.push({ detail: `${formatPercent(dti)} DTI is a favorable affordability factor.`, impact: 'favorable', label: 'Affordability' })
		} else if (dti >= 0.5) {
			adjustments.push({ detail: `${formatPercent(dti)} DTI requires higher risk pricing or manual review.`, impact: 'review', label: 'Affordability' })
		}
	}

	const dealerLevel = decision.dealer_overlay?.level
	if (typeof dealerLevel === 'string' && dealerLevel !== 'standard') {
		adjustments.push({ detail: `${formatLabel(dealerLevel)} dealer overlay adds controls to pricing or automation.`, impact: 'review', label: 'Dealer overlay' })
	}

	if (decision.stipulations.length > 0) {
		adjustments.push({ detail: `${decision.stipulations.length} stipulation${decision.stipulations.length === 1 ? '' : 's'} must clear before final pricing/funding.`, impact: 'review', label: 'Conditions' })
	}

	if (decision.decision === 'declined') {
		adjustments.push({ detail: 'Declined applications are not eligible for pricing.', impact: 'restrictive', label: 'Decision' })
	}

	return adjustments
}

function tierPricingAdjustment(riskTier: string | null): PricingAdjustment | null {
	if (riskTier === 'A+') {
		return { detail: 'Prime tier receives best available pricing.', impact: 'favorable', label: 'Tier pricing' }
	}
	if (riskTier === 'A') {
		return { detail: 'Strong tier receives standard preferred pricing.', impact: 'favorable', label: 'Tier pricing' }
	}
	if (riskTier === 'B') {
		return { detail: 'Near-prime tier receives moderate risk pricing.', impact: 'neutral', label: 'Tier pricing' }
	}
	if (riskTier === 'C') {
		return { detail: 'Elevated tier receives tighter pricing and collateral limits.', impact: 'review', label: 'Tier pricing' }
	}
	if (riskTier === 'D' || riskTier === 'E') {
		return { detail: `Tier ${riskTier} requires high-risk pricing and manual review.`, impact: 'restrictive', label: 'Tier pricing' }
	}
	return null
}

function decisionVariant(decision: string | null): PricingAdjustment['impact'] {
	if (decision === 'approved' || decision === 'funded') {
		return 'favorable'
	}
	if (decision === 'declined') {
		return 'restrictive'
	}
	if (decision === 'manual_review' || decision === 'approved_with_stipulations') {
		return 'review'
	}
	return 'neutral'
}

function variantClass(variant: PricingAdjustment['impact']) {
	if (variant === 'favorable') {
		return 'bg-emerald-50 text-emerald-700'
	}
	if (variant === 'review') {
		return 'bg-amber-50 text-amber-700'
	}
	if (variant === 'restrictive') {
		return 'bg-red-50 text-red-700'
	}
	return 'bg-slate-100 text-slate-700'
}

function formatDecision(decision: string | null) {
	return decision ? formatLabel(decision) : 'Pending'
}

function formatLabel(value: string) {
	return value
		.split('_')
		.map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
		.join(' ')
}

function formatDate(value: string) {
	return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function formatPercent(value: number | null | undefined) {
	if (value === null || value === undefined) {
		return '-'
	}
	return `${(value * 100).toFixed(1)}%`
}
