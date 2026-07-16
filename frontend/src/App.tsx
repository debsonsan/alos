import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { getAccessToken, getCurrentUser, login, setAccessToken, type AuthenticatedUser, type UserRole } from './api/client'
import ApplicationsList from './pages/ApplicationsList'
import NewApplication from './pages/NewApplication'

const queryClient = new QueryClient()

export default function App() {
	const [authToken, setAuthToken] = useState(() => getAccessToken())
	const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null)

	function handleAuthenticated(token: string, user: AuthenticatedUser) {
		setAccessToken(token)
		setAuthToken(token)
		setCurrentUser(user)
	}

	function handleLogout() {
		setAccessToken(null)
		setAuthToken(null)
		setCurrentUser(null)
		queryClient.clear()
	}

	return (
		<QueryClientProvider client={queryClient}>
			<AppContent authToken={authToken} currentUser={currentUser} onAuthenticated={handleAuthenticated} onLogout={handleLogout} />
		</QueryClientProvider>
	)
}

function AppContent({
	authToken,
	currentUser,
	onAuthenticated,
	onLogout,
}: {
	authToken: string | null
	currentUser: AuthenticatedUser | null
	onAuthenticated: (token: string, user: AuthenticatedUser) => void
	onLogout: () => void
}) {
	const sessionQuery = useQuery({
		enabled: Boolean(authToken && !currentUser),
		queryFn: getCurrentUser,
		queryKey: ['auth', 'me', authToken],
		retry: false,
	})
	const resolvedUser = currentUser ?? sessionQuery.data ?? null
	const isRestoringSession = Boolean(authToken && !resolvedUser && sessionQuery.isLoading)
	const sessionError = sessionQuery.error?.message ?? null

	return (
			<main className="min-h-screen bg-[#f4f7f6] text-slate-900">
				<header className="border-b border-slate-200 bg-white">
					<div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-5 md:flex-row md:items-end md:justify-between">
						<div>
							<p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Auto Loan Origination</p>
							<h1 className="mt-1 text-2xl font-semibold text-slate-950">Application Pipeline</h1>
						</div>
						{resolvedUser ? (
							<div className="flex flex-col gap-2 text-sm text-slate-600 sm:items-end">
								<span>
									Signed in as <strong className="text-slate-950">{resolvedUser.username}</strong> ({resolvedUser.role})
								</span>
								<button className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" onClick={onLogout} type="button">
									Sign out
								</button>
							</div>
						) : (
							<p className="max-w-xl text-sm text-slate-600">Sign in to submit, review, and fund applications.</p>
						)}
					</div>
				</header>

				{isRestoringSession ? <p className="mx-auto max-w-7xl px-6 py-8 text-sm text-slate-600">Restoring session...</p> : null}
				{sessionError ? <p className="mx-auto max-w-7xl px-6 py-8 text-sm text-red-700">{sessionError}</p> : null}

				{resolvedUser ? (
					<div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 xl:grid-cols-[420px_1fr]">
						<NewApplication canCreateApplication={canCreateApplication(resolvedUser.role)} />
						<ApplicationsList canFundApplications={canFundApplications(resolvedUser.role)} />
					</div>
				) : isRestoringSession ? null : (
					<div className="mx-auto max-w-md px-6 py-8">
						<LoginPanel onAuthenticated={onAuthenticated} />
					</div>
				)}
			</main>
	)
}

function LoginPanel({ onAuthenticated }: { onAuthenticated: (token: string, user: AuthenticatedUser) => void }) {
	const [username, setUsername] = useState<UserRole>('dealer')
	const [password, setPassword] = useState('dealer-password')
	const [error, setError] = useState<string | null>(null)
	const [isSubmitting, setIsSubmitting] = useState(false)

	async function handleSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault()
		setError(null)
		setIsSubmitting(true)
		try {
			const response = await login({ username, password })
			onAuthenticated(response.access_token, response.user)
		} catch (loginError) {
			setError(loginError instanceof Error ? loginError.message : 'Unable to sign in.')
		} finally {
			setIsSubmitting(false)
		}
	}

	function chooseRole(role: UserRole) {
		setUsername(role)
		setPassword(`${role}-password`)
	}

	return (
		<section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
			<h2 className="text-lg font-semibold text-slate-950">Sign in</h2>
			<form className="mt-5 space-y-4" onSubmit={handleSubmit}>
				<label className="block text-sm font-medium text-slate-700">
					Role
					<select
						className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
						onChange={(event) => chooseRole(event.target.value as UserRole)}
						value={username}
					>
						<option value="admin">admin</option>
						<option value="underwriter">underwriter</option>
						<option value="dealer">dealer</option>
						<option value="auditor">auditor</option>
					</select>
				</label>
				<label className="block text-sm font-medium text-slate-700">
					Password
					<input
						className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
						onChange={(event) => setPassword(event.target.value)}
						type="password"
						value={password}
					/>
				</label>
				{error ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
				<button
					className="w-full rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
					disabled={isSubmitting}
					type="submit"
				>
					{isSubmitting ? 'Signing in...' : 'Sign in'}
				</button>
			</form>
		</section>
	)
}

function canCreateApplication(role: UserRole) {
	return role === 'admin' || role === 'dealer'
}

function canFundApplications(role: UserRole) {
	return role === 'admin' || role === 'underwriter'
}
