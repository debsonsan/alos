# Auto Loan Origination System Technology Stack

## Purpose

This system supports the end-to-end lifecycle for auto loan applications: intake, applicant and vehicle capture, underwriting evaluation, decisioning, dealer overlays, risk tiering, review workflows, and operational reporting.

The stack is designed for a modular full-stack application with a Python API backend, a React frontend, Azure-hosted infrastructure, automated testing, and a Copilot-assisted engineering workflow.

## Backend Stack

### Runtime And Framework

- **Python 3.12**: Primary backend runtime.
- **FastAPI**: HTTP API framework for application intake, underwriting evaluation, decision retrieval, and operational endpoints.
- **Uvicorn**: ASGI server for local development and container hosting.
- **Pydantic v2**: Request validation, response schemas, underwriting input models, and configuration models.
- **SQLAlchemy 2.x**: ORM and database access layer.
- **PyJWT**: JWT access-token encoding and verification for role-based API access.
- **Alembic**: Database schema migrations.

### Backend Modules

- [../backend/main.py](../backend/main.py): FastAPI application entry point, route registration, middleware, and health checks.
- [../backend/auth.py](../backend/auth.py): JWT authentication helpers, demo user login, current-user dependency, and role authorization guards.
- [../backend/credit_bureau.py](../backend/credit_bureau.py): Fake credit bureau dataset and lookup helper for local underwriting integration.
- [../backend/database.py](../backend/database.py): SQLAlchemy engine, session factory, transaction helpers, and migration integration.
- [../backend/models.py](../backend/models.py): Core persistence models such as applications, underwriting decisions, dealers, and application status audit records.
- [../backend/underwriting/engine.py](../backend/underwriting/engine.py): Underwriting orchestration layer that evaluates rules and returns a decision summary.
- [../backend/underwriting/rules/hard_declines.py](../backend/underwriting/rules/hard_declines.py): Non-negotiable decline rules such as fraud flags, invalid identity data, or prohibited loan structures.
- [../backend/underwriting/rules/risk_tiers.py](../backend/underwriting/rules/risk_tiers.py): Risk segmentation based on credit, debt-to-income, loan-to-value, payment-to-income, and application history.
- [../backend/underwriting/rules/vehicle_constraints.py](../backend/underwriting/rules/vehicle_constraints.py): Vehicle eligibility rules such as age, mileage, title status, and collateral value.
- [../backend/underwriting/rules/dealer_overlay.py](../backend/underwriting/rules/dealer_overlay.py): Dealer-specific constraints, caps, program exclusions, and review requirements.

### API Design

- REST endpoints with JSON payloads.
- JWT bearer authentication for application routes.
- Role-based access control for `admin`, `underwriter`, `dealer`, and `auditor` users.
- Fake credit bureau report API for local development and underwriting test scenarios.
- Application status audit endpoint for authorized operational review of status transitions.
- Versioned route prefix such as `/api/v1`.
- Separate schemas for create, update, read, and underwriting decision responses.
- Idempotent decision evaluation for repeatable underwriting results.
- Structured error responses with stable error codes.
- Request correlation IDs for traceability across logs and decision records.

### Data Layer

- **Primary database**: Azure SQL Database or PostgreSQL, selected during deployment planning.
- **Local development database**: SQLite or PostgreSQL in Docker.
- **ORM mapping**: SQLAlchemy declarative models.
- **Migrations**: Alembic versioned migration scripts.
- **Data validation boundary**: Pydantic schemas at API edges; SQLAlchemy models for persistence.

### Backend Configuration

- Environment variables for secrets and deployment-specific settings.
- `JWT_SECRET_KEY` for access-token signing; production values must come from a secret store.
- Optional demo-user password overrides: `AUTH_ADMIN_PASSWORD`, `AUTH_UNDERWRITER_PASSWORD`, `AUTH_DEALER_PASSWORD`, and `AUTH_AUDITOR_PASSWORD`.
- `.env` files for local development only.
- Azure Key Vault for production secrets.
- Managed identity for Azure resource access when hosted in Azure.

## Frontend Stack

### Runtime And Framework

- **React 19**: Frontend UI framework.
- **TypeScript**: Static typing for components, API contracts, and state models.
- **Vite**: Development server, bundler, and frontend build tooling.
- **Tailwind CSS**: Utility-first styling system.
- **React Router**: Client-side routing for application list, detail, and creation flows.
- **TanStack Query**: Server-state fetching, caching, retries, and mutation management.

### Frontend Modules

- [../frontend/src/App.tsx](../frontend/src/App.tsx): Application shell, route configuration, providers, and layout.
- [../frontend/src/api/client.ts](../frontend/src/api/client.ts): Typed API client for backend calls.
- [../frontend/src/pages/ApplicationsList.tsx](../frontend/src/pages/ApplicationsList.tsx): Pipeline view for submitted loan applications.
- [../frontend/src/pages/ApplicationDetail.tsx](../frontend/src/pages/ApplicationDetail.tsx): Detailed application, applicant, collateral, loan terms, and decision history view.
- [../frontend/src/pages/NewApplication.tsx](../frontend/src/pages/NewApplication.tsx): Application intake workflow.
- [../frontend/src/components/UnderwritingSummary.tsx](../frontend/src/components/UnderwritingSummary.tsx): Decision result, risk tier, stipulations, and rule outcome summary.

### Frontend Design Principles

- Operational dashboard style with dense, scannable information.
- Clear separation between intake, review, underwriting result, and decision history.
- Accessible form controls with validation messages tied to backend schema rules.
- Responsive layouts for desktop-first underwriting workflows with usable tablet support.
- No hardcoded API URLs; use environment-based configuration.

## Infrastructure Stack

### Azure Hosting

- **Azure App Service** or **Azure Container Apps** for the FastAPI backend.
- **Azure Static Web Apps** or **Azure App Service static hosting** for the React frontend.
- **Azure SQL Database** or **Azure Database for PostgreSQL** for transactional data.
- **Azure Key Vault** for secrets, database credentials, and external service keys.
- **Azure Application Insights** for telemetry, traces, exceptions, dependencies, and performance metrics.
- **Azure Log Analytics** for centralized logs and operational queries.
- **Azure Storage Account** for generated documents, uploaded stipulations, or audit exports.
- **Azure Front Door** optional for global routing, TLS termination, WAF, and edge caching.

### Infrastructure As Code

- Bicep or Terraform for repeatable Azure provisioning.
- Separate environments for development, test, staging, and production.
- Parameterized infrastructure definitions for region, SKU, database tier, and domain names.
- Managed identities preferred over stored credentials.

### Containerization

- [../backend/Dockerfile](../backend/Dockerfile): Python 3.12 FastAPI runtime image using Uvicorn on port 8000.
- [../backend/requirements.txt](../backend/requirements.txt): Backend runtime dependencies for FastAPI, Uvicorn, SQLAlchemy, Pydantic, and PostgreSQL connectivity.
- [../frontend/Dockerfile](../frontend/Dockerfile): Multi-stage Node build and Nginx static runtime image for the Vite frontend.
- [../frontend/nginx.conf](../frontend/nginx.conf): Static asset serving and single-page application fallback configuration.
- [../docker-compose.yml](../docker-compose.yml): Local multi-container stack for PostgreSQL, FastAPI backend, and Nginx-served frontend.
- [../.dockerignore](../.dockerignore): Shared Docker build exclusions for local caches, virtual environments, generated assets, and secrets.

### Security And Compliance

- HTTPS-only endpoints.
- JWT access tokens required for application intake, listing, detail, and funding APIs.
- Role policy: `admin` can create and fund; `dealer` can create and view; `underwriter` can view and fund; `auditor` can view only.
- Least-privilege Azure RBAC assignments.
- Secrets stored in Key Vault, never committed to the repository.
- Database encryption at rest and TLS in transit.
- Audit logging for underwriting decisions, rule versions, user actions, and data changes.
- Application status changes are written to an audit table with previous status, new status, actor, role, reason, correlation ID, and timestamp.
- Personally identifiable information handled through explicit data retention and access policies.

## Testing Stack

### Backend Testing

- **pytest**: Backend unit and integration test runner.
- **httpx**: FastAPI endpoint testing through ASGI clients.
- **pytest-cov**: Coverage reporting.
- **factory-boy** or lightweight fixtures: Repeatable application, applicant, dealer, and vehicle test data.
- **freezegun**: Deterministic date-sensitive rule tests.

Backend tests should focus heavily on underwriting rules because those rules are business-critical and regression-prone.

Primary test location:

- [../backend/tests/test_api_auth.py](../backend/tests/test_api_auth.py)
- [../backend/tests/underwriting/test_engine.py](../backend/tests/underwriting/test_engine.py)

### Frontend Testing

- **Vitest**: Unit tests for components, helpers, and API-client behavior.
- **React Testing Library**: Component rendering and user interaction tests.
- **Mock Service Worker**: Browser-level API mocking for frontend tests and local workflows.
- **Playwright**: End-to-end tests for intake, list, detail, and underwriting summary flows.

### Quality Gates

- Backend linting and formatting with Ruff.
- Backend type checking with mypy or pyright.
- Frontend linting with ESLint.
- Frontend formatting with Prettier.
- TypeScript checks through `tsc --noEmit`.
- Coverage thresholds for underwriting rules, API validation, and critical UI workflows.

## CI/CD Stack

### Source Control

- Git repository with pull-request based review.
- Main branch protected by tests, linting, type checks, and build validation.
- Feature branches for business-rule updates, API additions, UI features, and infrastructure changes.

### GitHub Actions Pipeline

Recommended CI jobs:

- Backend install, lint, type check, and pytest.
- Frontend install, lint, type check, and build.
- Security scan for dependencies and committed secrets.
- Infrastructure validation for Bicep or Terraform.
- Artifact creation for backend and frontend deployables.

Implemented workflow:

- [../.github/workflows/ci.yml](../.github/workflows/ci.yml): GitHub Actions workflow for Python lint/tests, Node lint/tests/build, Docker image builds, and gated Azure deployment with GitHub OIDC.

Recommended CD jobs:

- Deploy to development on merge to main.
- Deploy to staging with approval gate.
- Deploy to production with manual approval and rollback plan.
- Run smoke tests after each deployment.

### Deployment Strategy

- Blue-green or slot-based backend deployment when using App Service.
- Immutable container image deployment when using Container Apps.
- Frontend static asset deployment with cache invalidation.
- Database migrations run as a controlled release step before app traffic is shifted.

## Repository Structure

```text
auto-loan-origination/
	.github/
		workflows/
			ci.yml
	.dockerignore
	docker-compose.yml
	backend/
		Dockerfile
		requirements.txt
		auth.py
		main.py
		database.py
		models.py
		underwriting/
			engine.py
			rules/
				hard_declines.py
				risk_tiers.py
				vehicle_constraints.py
				dealer_overlay.py
		tests/
			test_api_auth.py
			underwriting/
				test_engine.py
	frontend/
		Dockerfile
		nginx.conf
		src/
			App.tsx
			api/
				client.ts
			pages/
				ApplicationsList.tsx
				ApplicationDetail.tsx
				NewApplication.tsx
			components/
				UnderwritingSummary.tsx
	docs/
		STACK.md
		UNDERWRITING_RULES.md
		ARCHITECTURE.md
```

## Copilot Workflow

### Development Usage

- Use Copilot to draft FastAPI route handlers, Pydantic schemas, SQLAlchemy models, and migration outlines.
- Use Copilot to generate focused underwriting rule tests before implementing new rules.
- Use Copilot to propose React component structure, typed API client functions, and form validation flows.
- Use Copilot to create documentation updates when business rules, architecture, or deployment assumptions change.

### Review Workflow

- Ask Copilot for targeted code reviews of underwriting logic, data validation, and API authorization changes.
- Ask Copilot to identify missing edge cases in rule tests.
- Ask Copilot to compare implementation behavior against [UNDERWRITING_RULES.md](UNDERWRITING_RULES.md).
- Ask Copilot to summarize pull-request changes with risk areas and recommended validation steps.

### Prompting Conventions

- Provide the business rule, expected decision, and sample applicant data when asking for underwriting code.
- Include the target file path and nearby function when asking for edits.
- Ask for minimal, test-backed changes for rule updates.
- Ask for validation commands after implementation.

### Guardrails

- Do not rely on generated code for final credit policy interpretation without human review.
- Keep underwriting rule changes traceable to documented policy requirements.
- Require tests for every new hard-decline, risk-tier, vehicle, or dealer-overlay rule.
- Avoid committing secrets, production data, or real applicant information in prompts, tests, fixtures, or docs.

## Initial Local Tooling Targets

Backend commands to add as the project matures:

```powershell
python -m venv .venv
pip install fastapi uvicorn sqlalchemy pydantic pytest httpx ruff
pytest backend/tests
```

Frontend commands to add as the project matures:

```powershell
npm create vite@latest frontend -- --template react-ts
npm install
npm run dev
npm run build
```

CI commands to standardize:

```powershell
ruff check backend
pytest backend/tests
npm --prefix frontend run lint
npm --prefix frontend run build
```

## Stack Decisions To Finalize

- Choose Azure SQL Database or Azure Database for PostgreSQL as the production database.
- Choose App Service or Container Apps as the backend hosting target.
- Choose Static Web Apps or App Service static hosting for the frontend.
- Define authentication and authorization approach, such as Microsoft Entra ID.
- Define document storage requirements for uploaded stipulations and generated loan packages.
- Define audit retention, data retention, and masking requirements for applicant information.
