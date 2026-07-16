# End-to-End Test Plan

## Purpose

This test plan defines the verification strategy for the Auto Loan Origination System across backend APIs, frontend workflows, underwriting rules, persistence, and full data flow. It is intended to guide local development, CI validation, release readiness, and regression testing when underwriting policy changes.

## Scope

The plan covers the implemented system components:

- FastAPI backend routes: `GET /health`, `POST /applications`, `GET /applications`, `GET /applications/{id}`, and `POST /applications/{id}/fund`.
- SQLAlchemy persistence using the local SQLite development database and PostgreSQL-ready configuration.
- Underwriting engine orchestration and rule modules for hard declines, risk tiers, vehicle constraints, and dealer overlay.
- React, TypeScript, Vite, Tailwind frontend workflows for application intake, application list, application detail, funding, and underwriting summary display.
- Static frontend serving from the FastAPI root when `frontend/dist` exists.
- Local development data flow from browser form submission through API validation, underwriting evaluation, database persistence, and UI refresh.

Future production scope should include authentication, authorization, audit-history immutability, document upload, telemetry, and Azure deployment validation when those capabilities are implemented.

## Test Environments

### Local Development

- Backend runtime: Python 3.12.
- Backend server: Uvicorn on `http://127.0.0.1:8000`.
- Frontend dev server: Vite on `http://127.0.0.1:5173`.
- Frontend API target: `http://localhost:8000`.
- Database: SQLite file database through `DATABASE_URL` default.

### CI Environment

- Fresh checkout with clean dependency installation.
- Isolated SQLite test database or temporary database path.
- Backend tests run without relying on existing local data.
- Frontend lint and build run from `frontend/`.
- E2E browser tests run against a started backend and either the Vite dev server or FastAPI-served production build.

### Staging Environment

- Production-like database engine, preferably PostgreSQL or Azure SQL.
- Built frontend served through the selected hosting model.
- HTTPS enabled.
- Seeded synthetic applications for approved, declined, manual-review, stipulation, and funded states.

## Test Data Strategy

Use deterministic synthetic applications. No real applicant, tax, credit, dealer, or vehicle data should be used in test fixtures.

Maintain fixture families for:

- Clean prime approval.
- Hard decline by identity or fraud.
- Hard decline by credit score or bankruptcy.
- Vehicle decline by title, age, mileage, unsupported vehicle type, or invalid VIN decode.
- Manual review by dealer watch or restricted overlay.
- Approved with stipulations for reviewable vehicle or documentation conditions.
- Duplicate application ID conflict.
- Funding-eligible approved application.
- Funding-ineligible declined or manual-review application.

Each fixture should declare the expected decision, risk tier, key metrics, triggered reasons, and allowed funding behavior.

## Backend API Tests

### Health And Routing

Validate:

- `GET /health` returns `200` with `{"status":"ok"}`.
- `GET /` returns the built frontend when `frontend/dist` exists.
- API routes continue to resolve before the static frontend fallback.
- Unknown API-like paths return structured errors where applicable.

### Application Creation

Validate `POST /applications`:

- Accepts a complete valid application and returns `201`.
- Persists the application and generated underwriting result.
- Returns stable read fields such as `id`, `application_id`, applicant summary, vehicle summary, dealer summary, `decision_outcome`, `final_risk_tier`, timestamps, and `underwriting`.
- Rejects missing required fields with `422`.
- Rejects unknown request fields because the create schema uses `extra="forbid"`.
- Rejects invalid numeric ranges such as negative income, zero requested loan amount, invalid credit score, invalid term, or negative mileage.
- Rejects duplicate `application_id` with `409` and `duplicate_application`.

### Application Retrieval

Validate:

- `GET /applications` returns newest applications first.
- `GET /applications/{numeric_id}` retrieves by database ID.
- `GET /applications/{application_id}` retrieves by business application ID.
- Missing applications return `404` with `application_not_found`.
- Decimal, datetime, JSON, metric, and reason fields serialize in the frontend contract shape.

### Funding

Validate `POST /applications/{id}/fund`:

- Approved applications can be funded.
- Approved-with-stipulations applications can be funded only when current policy allows it.
- Declined applications cannot be funded and return `409` with `application_not_fundable`.
- Manual-review applications cannot be funded and return `409` with `application_not_fundable`.
- Already funded applications return `409` with `application_already_funded`.
- Funding updates `decision_outcome`, preserves previous decision in the response, and updates `updated_at`.

### Persistence And Transactions

Validate:

- Create and fund operations commit exactly once when successful.
- Failed duplicate creates roll back without partial rows.
- Underwriting decision fields are persisted consistently with the API response.
- JSON fields such as `triggered_rules`, `dealer_overlay_result`, and `vehicle_eligibility_result` survive round trip storage.
- SQLite development behavior does not hide issues expected under PostgreSQL, especially decimal precision and JSON serialization.

## Underwriting Engine Tests

### Metric Calculation

Validate derived fields:

- Amount financed.
- Net trade equity.
- Loan-to-value ratio.
- Payment-to-income ratio.
- Debt-to-income ratio.
- Vehicle age.
- Applicant age.
- Combined monthly income with co-applicant data.

Use date-stable tests for age calculations so regressions are not hidden by the current calendar year.

### Hard Declines

Validate terminal decline reasons for:

- Applicant and co-applicant identity verification failure.
- Fraud, synthetic identity, sanctions, deceased tax ID, and invalid tax ID flags.
- Underage applicant.
- Ineligible applicant state.
- No verifiable income.
- Open bankruptcy.
- Credit score below minimum.
- Recent repossession, severe delinquency, and unresolved charge-off.
- Loan amount, term, payment-to-income, debt-to-income, and loan-to-value absolute maximums.
- Suspended, terminated, unlicensed, fraud-blocked, or ineligible dealer.

Expected result: final decision is `declined`, decline reasons include the specific policy reason, and hard-decline triggered rules are present.

### Risk Tiers

Validate:

- Credit score bands map to A+, A, B, C, D, and E.
- High DTI, high PTI, high LTV, short employment, short residence, recent delinquencies, thin credit file, recent inquiries, and negative equity downgrade tiers.
- Strong co-applicant, long employment, low DTI, low LTV, meaningful down payment, and prior positive lender relationship stabilize or improve tier only within allowed caps.
- Tier assignment never overrides hard declines or non-waivable vehicle failures.

### Vehicle Constraints

Validate:

- Non-clean titles decline unless configured as reviewable.
- Excessive vehicle age declines.
- Excessive mileage declines.
- High but not terminal mileage routes to manual review.
- Unsupported vehicle type declines.
- Prohibited vehicle use declines or routes to review according to product policy.
- Missing VIN decode creates stipulation or review outcome as specified.
- Unapproved valuation sources, dealer price variance, backend product cap, negative equity cap, and term limits trigger the expected reasons.

### Dealer Overlay

Validate:

- Standard dealers do not block automated approval.
- Watch dealers block automated approval and add required stipulations.
- Restricted dealers require manual review and stronger income verification.
- Suspended or terminated dealers produce declined outcomes.
- Dealer default rate, first-payment-default rate, defect rate, complaints, buybacks, and fraud flags map to the expected overlay level and actions.

### Final Decision Precedence

Validate precedence:

1. Any hard decline or non-waivable decline results in `declined`.
2. Reviewable but eligible failures result in `manual_review`.
3. Eligible applications with unresolved required documents result in `approved_with_stipulations`.
4. Clean eligible applications result in `approved`.
5. Funding transition changes only the persisted application decision to `funded`; underwriting policy evaluation should remain explainable from stored fields.

## Frontend Tests

### API Client

Validate:

- `listApplications()` calls `GET http://localhost:8000/applications`.
- `getApplication(id)` URL-encodes the identifier.
- `createApplication(payload)` sends JSON with the full typed payload.
- `fundApplication(id)` posts to the funding route.
- Non-2xx responses surface useful error messages from backend `detail` payloads.
- Network failures show a user-readable message.

### New Application Page

Validate:

- Form renders required applicant, vehicle, loan, and dealer fields.
- Default/sample values can submit successfully in local development.
- Numeric fields are converted to numbers before API submission.
- Submit button shows loading state and prevents duplicate submission while pending.
- Success notification appears after create.
- Backend validation errors render visibly.
- Returned underwriting summary displays decision, DTI, LTV, risk tier, reasons, and pricing adjustments.

### Applications List Page

Validate:

- Initial loading state appears.
- Empty state appears when no applications exist.
- Application rows render applicant, vehicle, dealer, loan, decision, and risk tier.
- Refresh button refetches data and shows a refreshing state.
- Expanding a row displays `UnderwritingSummary`.
- Funding button appears only for fundable applications.
- Funding success notification appears and list data refreshes.
- Funding errors render for declined, manual-review, or already-funded applications.

### Application Detail Page

Validate:

- Page can load by supplied prop, query string, or path-derived application ID.
- Loading and error states are visible.
- Application facts render accurately.
- Underwriting summary renders nested metrics, reasons, triggered rules, and pricing adjustments.
- Funding flow updates the page after success.

### Underwriting Summary Component

Validate:

- DTI and LTV format as percentages.
- Risk tier and decision badges match current decision state.
- Decline reasons, stipulations, manual-review reasons, and triggered rules render independently.
- Pricing adjustments are derived consistently from tier, LTV, DTI, dealer overlay, stipulations, and decline state.
- Missing optional underwriting fields do not crash rendering.

## End-to-End Browser Flows

Use Playwright or equivalent browser automation for these scenarios.

### Clean Approval Flow

1. Start backend on `http://127.0.0.1:8000`.
2. Start frontend through Vite or serve `frontend/dist` through FastAPI.
3. Open the application UI.
4. Submit a clean prime application.
5. Assert success notification.
6. Assert decision is `approved` and risk tier is A+ or expected tier.
7. Assert DTI and LTV are visible.
8. Assert the new application appears in the list.
9. Fund the application.
10. Assert funding success and final visible state is funded.

### Hard Decline Flow

1. Submit an application with a hard-decline condition such as fraud flag, open bankruptcy, or below-minimum credit score.
2. Assert the UI shows `declined`.
3. Assert the expected decline reason is visible.
4. Assert the funding action is unavailable or returns a controlled error.
5. Assert the declined application remains visible in the list for audit/review.

### Manual Review Flow

1. Submit an application with dealer watch or restricted overlay inputs.
2. Assert decision is `manual_review`.
3. Assert manual-review reasons and stipulations are visible.
4. Assert funding is blocked.
5. Assert list refresh preserves the manual-review state.

### Vehicle Constraint Flow

1. Submit applications for non-clean title, excessive mileage, invalid VIN decode, and unsupported vehicle type.
2. Assert each produces the expected decline, stipulation, or manual-review state.
3. Assert reasons appear in the underwriting summary.
4. Assert backend response and frontend display agree.

### Duplicate Application Flow

1. Submit an application with a known `application_id`.
2. Submit the same application ID again.
3. Assert the UI shows a duplicate-application error.
4. Assert only one row exists for that application ID.

### Static Hosting Flow

1. Run `npm run build` in `frontend/`.
2. Start FastAPI from the repository root.
3. Open `http://localhost:8000/`.
4. Assert the React application loads.
5. Assert `/applications` still returns JSON, not the frontend shell.

## Data Flow Validation Matrix

| Flow | Input | Backend Expected | Engine Expected | Database Expected | Frontend Expected |
| --- | --- | --- | --- | --- | --- |
| Clean create | Complete eligible payload | `201` application response | `approved`, metrics present | Row with decision fields | Success and approved summary |
| Hard decline | Fraud or bankruptcy flag | `201` application response | `declined`, reason present | Row with decline reasons | Declined summary, no funding |
| Manual review | Watch/restricted dealer | `201` application response | `manual_review` | Overlay fields persisted | Review reasons visible |
| Stipulation | VIN decode or document condition | `201` application response | `approved_with_stipulations` or review per rule | Stipulations persisted | Stipulations visible |
| Duplicate create | Existing application ID | `409` | No new evaluation required | No duplicate row | Error notification |
| Get list | Existing applications | `200` list | No re-evaluation | Read-only | Rows render sorted |
| Get detail | Existing ID | `200` application | No re-evaluation | Read-only | Detail facts and summary render |
| Fund approved | Approved application | `200` funding response | No new evaluation | Decision updated to funded | Success notification |
| Fund declined | Declined application | `409` | No new evaluation | Decision unchanged | Controlled error |

## Non-Functional Tests

### Accessibility

- Forms have labels associated with inputs.
- Buttons expose clear names.
- Loading, error, and success states are perceivable.
- Keyboard-only navigation can submit, refresh, expand summaries, and trigger funding where available.
- Decision and risk-tier status do not rely on color alone.

### Responsiveness

- Intake form remains usable at mobile, tablet, and desktop widths.
- List rows and expanded summaries do not overflow horizontally in common viewports.
- Action buttons and notifications remain visible and non-overlapping.

### Performance

- Application list returns quickly for seeded datasets of 10, 100, and 1,000 applications.
- Underwriting evaluation completes within an agreed local budget for single-application create.
- Frontend build size and initial load remain acceptable for operational workflows.

### Security And Data Handling

- Backend rejects unexpected payload fields.
- Client-side validation is treated as convenience only; backend remains authoritative.
- Error responses do not leak stack traces or sensitive implementation details.
- Synthetic tax ID tokens and applicant data are used in all tests.
- CORS policy should be tightened and validated before production.

## Automation Commands

Run backend unit tests from the repository root:

```powershell
& "C:/Users/debasishb/AppData/Local/Microsoft/WindowsApps/python3.12.exe" -m pytest backend\tests\underwriting\test_engine.py
```

Run a backend syntax check from the repository root:

```powershell
& "C:/Users/debasishb/AppData/Local/Microsoft/WindowsApps/python3.12.exe" -m py_compile backend\main.py backend\database.py backend\models.py backend\underwriting\engine.py
```

Start the backend locally:

```powershell
& "C:/Users/debasishb/AppData/Local/Microsoft/WindowsApps/python3.12.exe" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run frontend validation from `frontend/`:

```powershell
npm run lint
npm run build
```

Start the frontend development server from `frontend/`:

```powershell
npm run dev -- --host 127.0.0.1
```

Smoke-test the running local system:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri http://127.0.0.1:8000/applications -UseBasicParsing | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest -Uri http://127.0.0.1:5173/ -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

## CI Quality Gates

Minimum pull request gates:

- Backend underwriting tests pass.
- Backend API tests pass once added.
- Frontend lint passes.
- Frontend build passes.
- Playwright E2E smoke suite passes for clean approval, hard decline, manual review, and funding.
- Test data uses synthetic values only.
- Any underwriting rule change includes at least one positive and one negative regression test.

Release gates:

- Full backend test suite.
- Full frontend unit and integration suite.
- Full Playwright E2E suite.
- Database migration validation when migrations are introduced.
- Staging smoke tests against deployed URLs.
- Decision outcome counts and rule trigger telemetry verified when observability is implemented.

## Current Gaps And Next Test Work

- Add a backend API test module using FastAPI TestClient or httpx against a temporary test database.
- Add a frontend test runner, such as Vitest and React Testing Library.
- Add Mock Service Worker for frontend API success and error scenarios.
- Add Playwright for browser-level E2E flows.
- Add a Python dependency manifest so CI can install backend dependencies repeatably.
- Add deterministic date control for age-sensitive underwriting tests.
- Add database migration tests after Alembic migrations are introduced.
- Align docs and routes if the API is versioned under `/api/v1` later.

## Acceptance Criteria

The system is test-ready when:

- Every decision outcome has automated backend and E2E coverage.
- Every underwriting rule category has deterministic unit tests.
- Every public API route has success, validation-error, not-found, and conflict coverage where applicable.
- Frontend critical workflows have component tests and browser E2E coverage.
- Data created through the UI can be verified through API reads and persisted database state.
- CI can run all test layers from a clean checkout without relying on local machine state.