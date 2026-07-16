import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { fundApplication, getApplication, type LoanApplication } from '../api/client'
import UnderwritingSummary from '../components/UnderwritingSummary'

type ApplicationDetailProps = {
	applicationId?: string
	canFundApplications?: boolean
}

export default function ApplicationDetail({ applicationId, canFundApplications = false }: ApplicationDetailProps) {
	const resolvedApplicationId = applicationId ?? getApplicationIdFromLocation()
	const queryClient = useQueryClient()
	const [successMessage, setSuccessMessage] = useState<string | null>(null)
	const applicationQuery = useQuery({
		enabled: Boolean(resolvedApplicationId),
		queryFn: () => getApplication(resolvedApplicationId ?? ''),
		queryKey: ['applications', resolvedApplicationId],
	})
	const fundMutation = useMutation({
		mutationFn: fundApplication,
		onError: () => setSuccessMessage(null),
		onSuccess: () => {
			setSuccessMessage(`Application ${resolvedApplicationId} funded successfully.`)
			void queryClient.invalidateQueries({ queryKey: ['applications'] })
			void queryClient.invalidateQueries({ queryKey: ['applications', resolvedApplicationId] })
		},
	})

	if (!resolvedApplicationId) {
		return <section className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-600">Select an application to view details.</section>
	}

	if (applicationQuery.isLoading) {
		return <section className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-600">Loading application...</section>
	}

	if (applicationQuery.error) {
		return <section className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-red-700">{applicationQuery.error.message}</section>
	}

	if (!applicationQuery.data) {
		return null
	}

	return (
		<ApplicationDetailContent
			application={applicationQuery.data}
			canFundApplications={canFundApplications}
			fundingError={fundMutation.error?.message ?? null}
			isFunding={fundMutation.isPending}
			onFund={(id) => fundMutation.mutate(id)}
			successMessage={successMessage}
		/>
	)
}

function ApplicationDetailContent({
	application,
	canFundApplications,
	fundingError,
	isFunding,
	onFund,
	successMessage,
}: {
	application: LoanApplication
	canFundApplications: boolean
	fundingError: string | null
	isFunding: boolean
	onFund: (applicationId: string) => void
	successMessage: string | null
}) {
	const isFundable = canFundApplications && (application.decision_outcome === 'approved' || application.decision_outcome === 'approved_with_stipulations')

	return (
		<section className="space-y-5">
			{successMessage ? <p className="rounded-lg border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-700">{successMessage}</p> : null}
			{fundingError ? <p className="rounded-lg border border-red-100 bg-red-50 p-4 text-sm text-red-700">{fundingError}</p> : null}

			<div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
				<div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
					<div>
						<p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Application detail</p>
						<h2 className="mt-1 text-xl font-semibold text-slate-950">{application.application_id}</h2>
						<p className="mt-1 text-sm text-slate-600">
							{application.applicant_legal_name} · {application.applicant_state}
						</p>
					</div>
					{canFundApplications ? (
						<button
							className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
							disabled={!isFundable || isFunding}
							onClick={() => onFund(application.application_id)}
							type="button"
						>
							{isFunding ? 'Funding...' : 'Fund application'}
						</button>
					) : null}
				</div>

				<div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
					<Fact label="Requested amount" value={formatCurrency(application.requested_loan_amount)} />
					<Fact label="Term" value={`${application.requested_term_months} months`} />
					<Fact label="Vehicle" value={`${application.vehicle_model_year} ${application.vehicle_make} ${application.vehicle_model}`} />
					<Fact label="Dealer" value={`${application.dealer_id} (${application.dealer_status})`} />
				</div>
			</div>

			<UnderwritingSummary decision={application.underwriting} />
		</section>
	)
}

function Fact({ label, value }: { label: string; value: string }) {
	return (
		<div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
			<p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
			<p className="mt-1 text-sm font-semibold text-slate-950">{value}</p>
		</div>
	)
}

function getApplicationIdFromLocation() {
	const searchValue = new URLSearchParams(window.location.search).get('applicationId')
	if (searchValue) {
		return searchValue
	}

	const pathValue = window.location.pathname.split('/').filter(Boolean).at(-1)
	return pathValue?.startsWith('APP-') ? pathValue : undefined
}

function formatCurrency(value: string) {
	return new Intl.NumberFormat('en-US', { currency: 'USD', style: 'currency' }).format(Number(value))
}
