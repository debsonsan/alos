import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { fundApplication, listApplications, type LoanApplication } from '../api/client'
import UnderwritingSummary from '../components/UnderwritingSummary'

export default function ApplicationsList({ canFundApplications }: { canFundApplications: boolean }) {
	const queryClient = useQueryClient()
	const [expandedApplicationId, setExpandedApplicationId] = useState<string | null>(null)
	const [successMessage, setSuccessMessage] = useState<string | null>(null)
	const applicationsQuery = useQuery({ queryKey: ['applications'], queryFn: listApplications })
	const fundMutation = useMutation({
		mutationFn: fundApplication,
		onError: () => setSuccessMessage(null),
		onSuccess: (response) => {
			setSuccessMessage(`Application ${response.application_id} funded successfully.`)
			void queryClient.invalidateQueries({ queryKey: ['applications'] })
		},
	})

	return (
		<section className="min-w-0 rounded-lg border border-slate-200 bg-white shadow-sm">
			<div className="flex flex-col gap-2 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h2 className="text-lg font-semibold text-slate-950">Applications</h2>
					<p className="mt-1 text-sm text-slate-600">Live applications with underwriting decisions from FastAPI.</p>
				</div>
				<button
					className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
					disabled={applicationsQuery.isFetching}
					onClick={() => void applicationsQuery.refetch()}
					type="button"
				>
					{applicationsQuery.isFetching ? 'Refreshing...' : 'Refresh'}
				</button>
			</div>

			{successMessage ? <p className="border-b border-emerald-100 bg-emerald-50 px-5 py-3 text-sm text-emerald-700">{successMessage}</p> : null}
			{applicationsQuery.isLoading ? <p className="p-5 text-sm text-slate-600">Loading applications...</p> : null}
			{applicationsQuery.error ? <p className="p-5 text-sm text-red-700">{applicationsQuery.error.message}</p> : null}

			{applicationsQuery.data ? (
				<div className="overflow-x-auto">
					<table className="w-full min-w-[980px] border-collapse text-left text-sm">
						<thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
							<tr>
								<th className="px-4 py-3 font-semibold">Application</th>
								<th className="px-4 py-3 font-semibold">Applicant</th>
								<th className="px-4 py-3 font-semibold">Vehicle</th>
								<th className="px-4 py-3 font-semibold">Amount</th>
								<th className="px-4 py-3 font-semibold">Tier</th>
								<th className="px-4 py-3 font-semibold">Decision</th>
								<th className="px-4 py-3 font-semibold">Underwriting</th>
								<th className="px-4 py-3 font-semibold">Action</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-slate-100">
							{applicationsQuery.data.map((application) => (
								<ApplicationRows
									application={application}
									canFundApplications={canFundApplications}
									expandedApplicationId={expandedApplicationId}
									fundingApplicationId={fundMutation.variables}
									isFunding={fundMutation.isPending}
									key={application.application_id}
									onFund={(applicationId) => fundMutation.mutate(applicationId)}
									onToggleSummary={(applicationId) =>
										setExpandedApplicationId((current) => (current === applicationId ? null : applicationId))
									}
								/>
							))}
						</tbody>
					</table>
					{applicationsQuery.data.length === 0 ? <p className="p-5 text-sm text-slate-600">No applications yet.</p> : null}
				</div>
			) : null}

			{fundMutation.error ? <p className="border-t border-slate-100 p-5 text-sm text-red-700">{fundMutation.error.message}</p> : null}
			{!canFundApplications ? <p className="border-t border-slate-100 p-5 text-sm text-slate-500">Funding is available to admin and underwriter roles.</p> : null}
		</section>
	)
}

function ApplicationRows({
	application,
	canFundApplications,
	expandedApplicationId,
	fundingApplicationId,
	isFunding,
	onFund,
	onToggleSummary,
}: {
	application: LoanApplication
	canFundApplications: boolean
	expandedApplicationId: string | null
	fundingApplicationId: string | undefined
	isFunding: boolean
	onFund: (applicationId: string) => void
	onToggleSummary: (applicationId: string) => void
}) {
	const isFundable = canFundApplications && (application.decision_outcome === 'approved' || application.decision_outcome === 'approved_with_stipulations')
	const isExpanded = expandedApplicationId === application.application_id
	const isThisFunding = isFunding && fundingApplicationId === application.application_id

	return (
		<>
			<tr className="hover:bg-slate-50">
				<td className="px-4 py-4 font-medium text-slate-950">{application.application_id}</td>
				<td className="px-4 py-4 text-slate-700">
					{application.applicant_legal_name}
					<span className="block text-xs text-slate-500">{application.applicant_state}</span>
				</td>
				<td className="px-4 py-4 text-slate-700">
					{application.vehicle_model_year} {application.vehicle_make} {application.vehicle_model}
					<span className="block text-xs text-slate-500">Dealer {application.dealer_id}</span>
				</td>
				<td className="px-4 py-4 text-slate-700">{formatCurrency(application.requested_loan_amount)}</td>
				<td className="px-4 py-4 text-slate-700">{application.final_risk_tier ?? '-'}</td>
				<td className="px-4 py-4">
					<span className={`rounded-md px-2 py-1 text-xs font-semibold ${decisionClass(application.decision_outcome)}`}>
						{application.decision_outcome ?? 'pending'}
					</span>
				</td>
				<td className="px-4 py-4 text-slate-700">
					<button className="text-xs font-semibold text-emerald-800 hover:text-emerald-950" onClick={() => onToggleSummary(application.application_id)} type="button">
						{isExpanded ? 'Hide result' : 'Show result'}
					</button>
				</td>
				<td className="px-4 py-4">
					{canFundApplications ? (
						<button
							className="rounded-md border border-emerald-700 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400"
							disabled={!isFundable || isFunding}
							onClick={() => onFund(application.application_id)}
							type="button"
						>
							{isThisFunding ? 'Funding...' : 'Fund'}
						</button>
					) : (
						<span className="text-xs text-slate-400">View only</span>
					)}
				</td>
			</tr>
			{isExpanded ? (
				<tr>
					<td className="bg-slate-50 px-4 py-4" colSpan={8}>
						<UnderwritingSummary decision={application.underwriting} />
					</td>
				</tr>
			) : null}
		</>
	)
}

function formatCurrency(value: string) {
	return new Intl.NumberFormat('en-US', { currency: 'USD', style: 'currency' }).format(Number(value))
}

function decisionClass(decision: string | null) {
	if (decision === 'approved' || decision === 'funded') {
		return 'bg-emerald-50 text-emerald-700'
	}
	if (decision === 'manual_review' || decision === 'approved_with_stipulations') {
		return 'bg-amber-50 text-amber-700'
	}
	if (decision === 'declined') {
		return 'bg-red-50 text-red-700'
	}
	return 'bg-slate-100 text-slate-600'
}
