# Execution Plan - Subscription Platform API

## Context
- Django + DRF API with JWT auth, Stripe subscriptions, app limits, Dockerized; consumed by React SPA.
- User types basic/pro; app limits per plan; Stripe webhooks update Subscription and user_type.

## Objectives
- Ship secure auth flows with email verification, refresh-token cookie, and password reset.
- Integrate Stripe for subscription lifecycle while keeping user_type in sync.
- Enforce app limits per plan with clear API errors and admin controls.
- Provide documentation, logging, and health checks for operability.

## Workstreams
1) Foundation & Infra
   - Bootstrap Django project with DRF, SimpleJWT, CORS, CSRF/cookie settings.
   - Docker-compose for web (gunicorn), db (Postgres), optional worker; environment variable wiring.
   - Environment-specific settings (local/staging/prod) and secret management.
2) Auth & User Lifecycle
   - Endpoints: register, verify-email, login, token refresh (cookie), logout (clear cookie/blacklist), forgot-password, reset-password.
   - User model: email login, user_type default basic, is_active, is_disabled_by_admin.
   - Email token generation/validation for verification and reset; email templates/hooks.
   - Security: password hashing/policy, optional rate limiting, HTTPS flags on cookies.
3) Subscription & Billing (Stripe)
   - Configure plan_id to Stripe price mapping; ensure stripe_customer_id creation helper.
   - Endpoints: create Checkout Session, create Billing Portal session, get current subscription.
   - Webhook handler for checkout.session.completed, customer.subscription.* and invoice.* events; idempotent processing and signature verification.
   - Update Subscription model and user_type on status changes; handle cancel_at_period_end, trialing, past_due, canceled.
4) Apps & Limits
   - Models: App, AppUser (through) with roles; helper for owned app counts.
   - Endpoints: list/create/retrieve/update/delete; collaborator add/list/remove with permissions.
   - Enforce max apps per user_type before create; return 403 APP_LIMIT_REACHED with message.
5) Admin
   - Admin endpoints: list users with filters, retrieve detail with subscription/app counts, disable/enable via patch.
   - Ensure disabled users are blocked from login and authenticated actions.
6) Documentation & Observability
   - OpenAPI/Swagger via drf-spectacular; schema endpoint and swagger UI.
   - Structured logging for auth, subscription, and app limit events; health check endpoint.
   - Avoid logging tokens or secrets.
7) QA & Acceptance
   - Automated tests for auth (register/verify/login/refresh/logout), password reset, app limit enforcement, Stripe webhook flows (mocked).
   - Manual checklist aligned to PRD acceptance criteria: registration->verification->login, admin disable, checkout+webhook upgrade, cancel downgrade, APP_LIMIT_REACHED response.

## Key Decisions / Risks
- Downgrade timing on cancel: default downgrade at `current_period_end` unless `cancel_at_period_end` is false or an admin opts for immediate; keep config flag to switch to immediate if support load requires.
- Rate limiting: apply per-IP and per-email limits on auth endpoints (recommended defaults: login 5/min per email + 30/min per IP; register 3/min per IP; password reset 3/min per email + 10/min per IP); expose settings for ops tuning.
- Collaborator role scope limited to owner/editor/viewer in v1.
- Idempotency and retries on webhook processing to avoid duplicate subscription rows.
- Secure storage of JWT signing key and Stripe secrets per environment.

## Deliverables
- Running docker-compose stack with migration-ready database.
- Documented API with exposed OpenAPI schema and swagger UI.
- Test suite covering critical auth, billing, and app-limit flows.
