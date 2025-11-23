# Task Backlog - Subscription Platform API

## Priority Legend
- P0 = critical path for MVP; P1 = high priority for launch; P2 = nice-to-have for v1; Owner default `Unassigned`; Target uses sprint label.

## Foundation & Infra
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Scaffold Django + DRF project; configure settings modules per environment.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Add docker-compose with web (gunicorn), db (Postgres), optional worker; env var defaults.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Configure CORS, security headers, and SimpleJWT settings (access TTL, refresh TTL, signing key).

## Auth & User Lifecycle
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Implement custom user model/email login with user_type default basic; flags is_active and is_disabled_by_admin.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Register endpoint creating inactive user and sending verification email with token.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Verify-email endpoint that activates user on valid token.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Login endpoint checking is_active and is_disabled_by_admin; returns access token JSON and sets refresh cookie (HttpOnly, Secure, SameSite config).
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Token refresh endpoint reading cookie and returning new access token.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Logout endpoint clearing refresh cookie and optionally blacklisting refresh token.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Forgot-password and reset-password endpoints with tokens and email delivery.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Rate limiting on auth endpoints per PLAN.md defaults.

## Subscription & Billing (Stripe)
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Define plan_id to Stripe price mapping in settings; helper to create stripe_customer_id.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Endpoint: POST /api/v1/subscriptions/stripe/checkout/ creating Checkout Session.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Endpoint: POST /api/v1/subscriptions/stripe/portal/ creating Billing Portal session.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Endpoint: GET /api/v1/subscriptions/me/ returning current subscription summary.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Webhook handler for checkout.session.completed, customer.subscription.* and invoice.* events; verify signature and process idempotently.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Update Subscription model and user_type on status changes; handle cancel_at_period_end, trialing, past_due, canceled; implement downgrade-at-period-end default with config for immediate.

## Apps & Limits
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Create models App and AppUser through table with roles (owner/editor/viewer).
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Implement list/create/retrieve/update/delete for apps with permissions for owners and collaborators.
- [ ] (P0, Owner: Unassigned, Target: Sprint 1) Enforce max owned apps per user_type before create; return 403 with code APP_LIMIT_REACHED and message.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Collaborator endpoints: list/add/remove with owner-only mutation.

## Admin
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Admin endpoints to list users with filters (email, user_type, is_disabled_by_admin, subscription_status).
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Admin user detail endpoint with subscription summary and owned app count.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Admin patch endpoint to disable/enable users; ensure disabled users are blocked from authenticated requests.

## Documentation & Observability
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Generate OpenAPI/Swagger via drf-spectacular; expose schema and swagger UI routes.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Add health check endpoint GET /health/ returning 200.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Logging for auth, subscription, and app limit events; avoid logging tokens or secrets.

## QA & Acceptance
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Automated tests for auth flows (register->verify->login->refresh->logout) and password reset.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Tests for app limit enforcement and collaborator permissions.
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Tests for Stripe checkout flow and webhook state transitions (mocked).
- [ ] (P1, Owner: Unassigned, Target: Sprint 2) Manual checklist aligned to PRD acceptance criteria including admin disable scenario and downgrade on cancel.
