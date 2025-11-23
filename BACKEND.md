# Backend API Reference (Sandbox)

This backend runs in Stripe test mode only. All keys in `.env.example` are test keys. Use these endpoints from the UI; keep refresh tokens in cookies as implemented by the API.

## Auth
- `POST /api/v1/auth/register/` — body `{email, password, first_name?, last_name?}`; creates inactive basic user, sends verification email. Responses: `201` with `{detail}`. Errors: validation `400`; throttled `429` (scope `register`).
- `POST /api/v1/auth/verify-email/` — body `{uid, token}`; activates user. `200 {detail}` or `400` invalid/expired token.
- `POST /api/v1/auth/login/` — body `{email, password}`; returns `{access}` and sets `refresh_token` HttpOnly cookie. Blocks inactive/disabled with `400`. Throttled scope `login`.
- `POST /api/v1/auth/token/refresh/` — reads `refresh_token` cookie or body `refresh`; returns new `{access}` and rotates cookie.
- `POST /api/v1/auth/logout/` — clears refresh cookie and blacklists token if provided. `204` always (ignores bad token).
- `POST /api/v1/auth/forgot-password/` — body `{email}`; sends reset email if user exists. `200` generic detail. Throttled scope `password_reset`.
- `POST /api/v1/auth/reset-password/` — body `{uid, token, new_password}`; resets password. `200 {detail}` or `400` invalid token.

Error codes: `APP_LIMIT_REACHED` (from apps create). Admin-disabled users get `400` on login/verify/reset/register validation.

## Subscriptions (Stripe test)
- `POST /api/v1/subscriptions/stripe/checkout/` — body `{plan_id: basic|pro}`; returns `{checkout_url}` for Stripe Checkout (subscription mode). Creates customer if missing.
- `POST /api/v1/subscriptions/stripe/portal/` — returns `{portal_url}` for Stripe Billing Portal.
- `GET /api/v1/subscriptions/me/` — returns `{subscription: {status, plan_id, price_id, cancel_at_period_end, current_period_end, current_period_start, trial_end, stripe_subscription_id}}` or `{subscription: null}`.
- `POST /api/v1/subscriptions/stripe/webhook/` — Stripe webhook (no auth); verifies signature. Handles `checkout.session.completed` and `customer.subscription.*` updates (status, price, cancel flag, period dates) and syncs `user_type` (active/trialing -> plan, canceled/incomplete/unpaid -> basic). Always `200` if processed; `400` on invalid payload/signature.

Env mapping: `PLAN_PRICE_MAP` from `STRIPE_PRICE_BASIC_ID` / `STRIPE_PRICE_PRO_ID`; limits `PLAN_LIMITS` basic=3, pro=50. Success/cancel/portal return URLs from env.

## Apps & Collaborators
- `GET /api/v1/apps/` — list apps where user is a member (owner/editor/viewer). Each item includes `role`.
- `POST /api/v1/apps/` — create app `{name, description?}` as owner; enforces owned count vs `PLAN_LIMITS`. Success `201` with app; error `403` `{detail, code: "APP_LIMIT_REACHED"}`.
- `GET /api/v1/apps/{id}/` — retrieve app if member.
- `PATCH/PUT /api/v1/apps/{id}/` — owner/editor only. Viewer forbidden `403`.
- `DELETE /api/v1/apps/{id}/` — owner only.
- `GET /api/v1/apps/{app_id}/collaborators/` — owner only; list collaborators `{user, email, role, invited_at}`.
- `POST /api/v1/apps/{app_id}/collaborators/` — owner only; body `{email, role}`; adds existing user. `400` if already collaborator or user missing.
- `DELETE /api/v1/apps/{app_id}/collaborators/{user_id}/` — owner only; cannot remove owner (`400`).

Permissions: membership enforced on app routes; non-members receive `403`.

## Admin (staff only)
- `GET /api/v1/admin/users/` — list users with optional filters `email`, `user_type`, `is_disabled_by_admin` (true/false), `subscription_status`. Each item: `id, email, first_name, last_name, user_type, is_active, is_disabled_by_admin, subscription_status, subscription_plan, owned_app_count`.
- `GET /api/v1/admin/users/{user_id}/` — user detail (fields above).
- `PATCH /api/v1/admin/users/{user_id}/` — body `{is_disabled_by_admin: bool}` to disable/enable. `404` if not found.

## Docs & Health
- `GET /api/v1/health/` — `{status: "ok"}`.
- `GET /api/schema/` — OpenAPI schema (Spectacular).
- `GET /api/docs/` — Swagger UI.

## Auth & Tokens
- Default permissions: authenticated required unless endpoint marked AllowAny.
- Auth header: `Authorization: Bearer <access>`.
- Refresh tokens stored in cookie `refresh_token` (configurable name) with `HttpOnly`, `Secure` (toggle via env), `SameSite` (env), path `/`, optional domain. Blacklisting enabled.

## Throttling (defaults)
- User: `1000/day`, Anon: `100/day`.
- Login: `30/minute`; Register: `3/minute`; Password reset: `10/minute`. Configure via env `DRF_THROTTLE_*`.

## Error Patterns
- Validation errors: `400` with field messages or `{detail, code}`.
- Auth failures: `401` unauthenticated; `403` forbidden for permission failures (e.g., non-member, non-owner).
- Stripe webhook signature errors: `400`.
- App limit enforcement: `403` with `code: APP_LIMIT_REACHED`.

## Required Environment (test)
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` (test keys), `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_BASIC_ID`, `STRIPE_PRICE_PRO_ID`.
- URLs: `CHECKOUT_SUCCESS_URL`, `CHECKOUT_CANCEL_URL`, `PORTAL_RETURN_URL`, `FRONTEND_URL`.
- JWT/refresh cookie config: `ACCESS_TOKEN_LIFETIME_MINUTES`, `REFRESH_TOKEN_LIFETIME_DAYS`, `REFRESH_COOKIE_*`.
- CORS/CSRF origins and DB settings as in `.env.example`.
