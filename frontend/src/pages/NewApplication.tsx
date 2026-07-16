import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { createApplication, type CreateApplicationPayload } from '../api/client'
import UnderwritingSummary from '../components/UnderwritingSummary'

type ApplicationFormState = {
	applicantName: string
	state: string
	creditScore: string
	monthlyIncome: string
	monthlyDebt: string
	monthlyHousing: string
	loanAmount: string
	termMonths: string
	downPayment: string
	vehicleYear: string
	vehicleMake: string
	vehicleModel: string
	vehicleMileage: string
	vehicleValue: string
	dealerId: string
	dealerStatus: string
	dealerRiskRating: string
}

const initialForm: ApplicationFormState = {
	applicantName: 'Sample Applicant',
	state: 'TX',
	creditScore: '740',
	monthlyIncome: '8000',
	monthlyDebt: '300',
	monthlyHousing: '1200',
	loanAmount: '27000',
	termMonths: '60',
	downPayment: '3000',
	vehicleYear: '2022',
	vehicleMake: 'Honda',
	vehicleModel: 'Accord',
	vehicleMileage: '25000',
	vehicleValue: '30000',
	dealerId: 'DLR-001',
	dealerStatus: 'active',
	dealerRiskRating: 'standard',
}

export default function NewApplication({ canCreateApplication }: { canCreateApplication: boolean }) {
	const queryClient = useQueryClient()
	const [form, setForm] = useState<ApplicationFormState>(initialForm)
	const [successMessage, setSuccessMessage] = useState<string | null>(null)
	const createMutation = useMutation({
		mutationFn: createApplication,
		onError: () => setSuccessMessage(null),
		onSuccess: (application) => {
			setSuccessMessage(`Application ${application.application_id} submitted successfully.`)
			void queryClient.invalidateQueries({ queryKey: ['applications'] })
			setForm((current) => ({ ...current, applicantName: '', creditScore: '740', loanAmount: '27000' }))
		},
	})

	function updateField(field: keyof ApplicationFormState, value: string) {
		setForm((current) => ({ ...current, [field]: value }))
	}

	function handleSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault()
		if (!canCreateApplication) {
			return
		}
		createMutation.mutate(toCreatePayload(form))
	}

	return (
		<section className="space-y-5">
			<div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
				<div className="mb-5">
					<h2 className="text-lg font-semibold text-slate-950">New application</h2>
					<p className="mt-1 text-sm text-slate-600">
						{canCreateApplication ? 'Submit a request and review the returned underwriting result.' : 'Application creation is available to admin and dealer roles.'}
					</p>
				</div>

				<form className="space-y-5" onSubmit={handleSubmit}>
					{successMessage ? <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{successMessage}</p> : null}

					<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
						<TextInput label="Applicant" value={form.applicantName} onChange={(value) => updateField('applicantName', value)} />
						<TextInput label="State" value={form.state} onChange={(value) => updateField('state', value.toUpperCase())} />
						<NumberInput label="Credit score" value={form.creditScore} onChange={(value) => updateField('creditScore', value)} />
						<NumberInput label="Monthly income" value={form.monthlyIncome} onChange={(value) => updateField('monthlyIncome', value)} />
						<NumberInput label="Monthly debt" value={form.monthlyDebt} onChange={(value) => updateField('monthlyDebt', value)} />
						<NumberInput label="Housing payment" value={form.monthlyHousing} onChange={(value) => updateField('monthlyHousing', value)} />
					</div>

					<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
						<NumberInput label="Loan amount" value={form.loanAmount} onChange={(value) => updateField('loanAmount', value)} />
						<NumberInput label="Term months" value={form.termMonths} onChange={(value) => updateField('termMonths', value)} />
						<NumberInput label="Down payment" value={form.downPayment} onChange={(value) => updateField('downPayment', value)} />
						<NumberInput label="Vehicle value" value={form.vehicleValue} onChange={(value) => updateField('vehicleValue', value)} />
					</div>

					<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
						<NumberInput label="Vehicle year" value={form.vehicleYear} onChange={(value) => updateField('vehicleYear', value)} />
						<TextInput label="Make" value={form.vehicleMake} onChange={(value) => updateField('vehicleMake', value)} />
						<TextInput label="Model" value={form.vehicleModel} onChange={(value) => updateField('vehicleModel', value)} />
						<NumberInput label="Mileage" value={form.vehicleMileage} onChange={(value) => updateField('vehicleMileage', value)} />
					</div>

					<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
						<TextInput label="Dealer ID" value={form.dealerId} onChange={(value) => updateField('dealerId', value)} />
						<SelectInput
							label="Dealer status"
							onChange={(value) => updateField('dealerStatus', value)}
							options={['active', 'probation', 'suspended', 'terminated']}
							value={form.dealerStatus}
						/>
						<SelectInput
							label="Dealer risk"
							onChange={(value) => updateField('dealerRiskRating', value)}
							options={['standard', 'watch', 'restricted']}
							value={form.dealerRiskRating}
						/>
					</div>

					{createMutation.error ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{createMutation.error.message}</p> : null}

					<button
						className="w-full rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
						disabled={!canCreateApplication || createMutation.isPending}
						type="submit"
					>
						{createMutation.isPending ? 'Submitting...' : 'Submit application'}
					</button>
				</form>
			</div>

			{createMutation.data ? <UnderwritingSummary decision={createMutation.data.underwriting} /> : null}
		</section>
	)
}

function TextInput({ label, onChange, value }: { label: string; onChange: (value: string) => void; value: string }) {
	return (
		<label className="block text-sm font-medium text-slate-700">
			{label}
			<input
				className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
				onChange={(event) => onChange(event.target.value)}
				required
				value={value}
			/>
		</label>
	)
}

function NumberInput({ label, onChange, value }: { label: string; onChange: (value: string) => void; value: string }) {
	return (
		<label className="block text-sm font-medium text-slate-700">
			{label}
			<input
				className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
				onChange={(event) => onChange(event.target.value)}
				required
				type="number"
				value={value}
			/>
		</label>
	)
}

function SelectInput({ label, onChange, options, value }: { label: string; onChange: (value: string) => void; options: string[]; value: string }) {
	return (
		<label className="block text-sm font-medium text-slate-700">
			{label}
			<select
				className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
				onChange={(event) => onChange(event.target.value)}
				value={value}
			>
				{options.map((option) => (
					<option key={option} value={option}>
						{option}
					</option>
				))}
			</select>
		</label>
	)
}

function toCreatePayload(form: ApplicationFormState): CreateApplicationPayload {
	const applicationId = `APP-${crypto.randomUUID().slice(0, 8).toUpperCase()}`
	const loanAmount = numberValue(form.loanAmount)
	const vehicleValue = numberValue(form.vehicleValue)
	const termMonths = numberValue(form.termMonths)

	return {
		application_id: applicationId,
		application_channel: 'dealer_portal',
		product_type: 'retail_installment',
		requested_loan_amount: loanAmount,
		requested_term_months: termMonths,
		down_payment_amount: numberValue(form.downPayment),
		applicant_id: `APL-${applicationId.slice(-8)}`,
		applicant_legal_name: form.applicantName,
		applicant_date_of_birth: '1988-01-01',
		applicant_tax_id_token: `tok_${applicationId.toLowerCase()}`,
		applicant_address: '100 Main St',
		applicant_state: form.state,
		applicant_residence_duration_months: 36,
		applicant_employment_status: 'employed',
		applicant_monthly_gross_income: numberValue(form.monthlyIncome),
		applicant_monthly_housing_payment: numberValue(form.monthlyHousing),
		applicant_credit_score: numberValue(form.creditScore),
		vin: `VIN${applicationId.slice(-8)}`,
		vehicle_model_year: numberValue(form.vehicleYear),
		vehicle_make: form.vehicleMake,
		vehicle_model: form.vehicleModel,
		vehicle_new_or_used: 'used',
		vehicle_mileage: numberValue(form.vehicleMileage),
		vehicle_valuation_source: 'book',
		vehicle_value: vehicleValue,
		vehicle_title_status: 'clean',
		vehicle_use: 'personal',
		vehicle_type: 'car',
		dealer_listed_price: Math.max(vehicleValue - 500, 1),
		dealer_id: form.dealerId,
		dealer_status: form.dealerStatus,
		dealer_risk_rating: form.dealerRiskRating,
		dealer_state: form.state,
		dealer_license_status: 'active',
		monthly_debt_obligations: numberValue(form.monthlyDebt),
		estimated_monthly_payment: Math.round(Math.max(loanAmount - numberValue(form.downPayment), 0) / Math.max(termMonths, 1)),
	}
}

function numberValue(value: string) {
	return Number(value || 0)
}
