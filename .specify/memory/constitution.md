<!--
Sync Impact Report
- Version change: [TEMPLATE] → 1.0.0 (initial ratification)
- Modified principles: n/a (first concrete adoption from placeholder template)
- Added sections: Core Principles I–VI (Role Separation & Least Privilege; Vendor Approval Gate;
  Data & Payment Security; Real Core, Mocked Edges; Spec-Driven, Staged Delivery; Simplicity
  Within a Load-Bearing Domain Model); Security & Non-Functional Requirements; Development
  Workflow; Governance
- Removed sections: none (template had no prior content)
- Deferred TODOs: none — all placeholders resolved from the source SRS/diagrams and the
  user's confirmed decisions on tech stack, vendor role, and staged/reviewed build process
- Templates requiring follow-up: none pending; plan-template.md, spec-template.md,
  tasks-template.md, checklist-template.md already reference the constitution generically
  and need no edits for this ratification
-->

# E-Mall Constitution

## Core Principles

### I. Role Separation & Least Privilege
The system MUST recognize exactly three roles — Customer, Vendor, Administrator — and every
capability MUST be scoped to the role(s) the source requirements grant it to (per the SRS use-case
diagram and the project's confirmed addition of the Vendor role). Role checks MUST be enforced
server-side on every request; any client-side role check (route guards, hidden UI) is a UX
convenience only and MUST NOT be relied upon for authorization. Rationale: this is a marketplace
handling other people's money and shops — authorization bugs here are data breaches or fraud, not
cosmetic issues.

### II. Vendor Approval Gate (NON-NEGOTIABLE)
A Vendor's shop MUST carry an explicit status (PENDING / APPROVED / REJECTED, set only by an
Administrator) and MUST NOT be able to create, publish, or modify catalog listings, nor receive
orders, while not APPROVED. This gate MUST be enforced in the same server-side authorization layer
as Principle I, not as a UI-only restriction, a seed-data convenience, or a default left open
during development. Rationale: unapproved-seller gating is the one requirement the original SRS
calls out explicitly ("approve/reject shop creation requests") — it is the feature, not an
incidental check.

### III. Data & Payment Security
Passwords MUST be hashed (never stored/logged in plaintext). Payment methods MUST NEVER persist
raw card numbers or CVV/CVC, including in mocked or development payment flows — store only
non-sensitive references (method, status, amount, an opaque transaction reference). Authentication
tokens MUST follow least-exposure storage: short-lived access tokens held in memory on the
frontend only, refresh tokens set as httpOnly/Secure/SameSite cookies. Secrets (DB credentials,
signing keys) MUST come from environment variables, never committed to the repository. Rationale:
"secure access to consumer's confidential data" is a named non-functional requirement in the
source SRS, and payment data is the highest-consequence category to get wrong.

### IV. Real Core, Mocked Edges
The parts of the system that define correctness — the PostgreSQL schema and migrations,
authentication, server-side permission enforcement, and the cart→checkout→order lifecycle
(including stock decrement) — MUST be fully real, never mocked or stubbed. External integrations
with no bearing on this project's own logic — the payment gateway, outbound email transport,
shipping-carrier tracking — MAY be stubbed for the MVP, but MUST be implemented as a real,
swappable service interface (e.g. a payment service class with one mock and one future real
backend) rather than hardcoded fake branches inlined into business logic. Rationale: keeps the MVP
buildable without third-party accounts while ensuring swapping in a real Stripe/SMTP/carrier
integration later is a config change, not a rewrite.

### V. Spec-Driven, Staged Delivery
Every feature area MUST move through the Spec Kit workflow in order — specify → (clarify) → plan →
tasks → (analyze) → implement — with each generated artifact reviewed before the next stage
begins. Implementation MUST proceed in reviewable chunks (e.g. one task group at a time), each
verified as actually working (migrations run, API exercised, UI walked through) before moving to
the next chunk. Large, unreviewed, all-at-once generation is prohibited even when a tool (e.g.
`/speckit-implement`) is technically capable of it. Rationale: this project is explicitly being
built as a step-by-step learning exercise — the staged, reviewed process is a project goal, not
just a quality nicety.

### VI. Simplicity Within a Load-Bearing Domain Model
Prefer the simplest implementation that satisfies a requirement (YAGNI) for everything not named
below. However, three structural elements MUST NOT be simplified away, deferred, or collapsed,
because the multi-vendor requirement depends on them: (1) the three-role model (Customer / Vendor /
Administrator), (2) the shop approval state machine (Principle II), and (3) per-line-item order
fulfillment status (because a single Customer order can span multiple vendors' shops, each
fulfilling and shipping independently). Rationale: these three are where the original single-shop
SRS/UML model diverges from the confirmed multi-vendor scope — cutting corners here breaks the
actual product, not just its polish.

## Security & Non-Functional Requirements
<!-- Derived from the SRS's non-functional requirements list: security, reliability,
     maintainability, portability, extensibility, reusability, compatibility, resource
     utilization; reframed as concrete engineering commitments for this stack. -->

- **Security**: enforced per Principles I–III; additionally, all list/detail endpoints returning
  another user's data MUST filter by ownership/role at the queryset level, not only in serializers.
- **Reliability**: destructive or state-changing operations (checkout, cancellation, shop
  approval, stock decrement) MUST be wrapped in database transactions so partial failures cannot
  leave inconsistent state (e.g. stock decremented without an Order row, or vice versa).
- **Maintainability**: the backend MUST stay organized as the Django app boundaries established in
  planning (accounts, vendors, catalog, cart, orders, payments, feedback, core) — cross-app logic
  belongs in a shared `core` app, not duplicated per-app.
- **Portability / Compatibility**: configuration (database, secrets, CORS origins, email backend)
  MUST be environment-driven so the same codebase runs in local dev and any future deployment
  target without code changes.
- **Extensibility / Reusability**: domain logic (pricing, stock adjustment, order-total
  calculation) belongs in model methods or service functions callable from multiple entry points
  (API views, management commands, admin actions), not duplicated inline in view functions.
- **Resource Utilization**: list endpoints MUST be paginated; product/category queries MUST avoid
  N+1 queries (use `select_related`/`prefetch_related` where relations are traversed in serializers).

## Development Workflow
<!-- How the staged, reviewed process from Principle V actually runs day to day. -->

- Each feature/phase of work follows: `/speckit-specify` (or an equivalent spec update) →
  optional `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → optional `/speckit-analyze` →
  `/speckit-implement` in reviewable chunks.
- A chunk is not considered done until it has been run for real: `python manage.py migrate`
  against Postgres succeeds, the relevant endpoints are exercised (DRF browsable API or an actual
  frontend flow), and any new UI is walked through in the running Next.js dev server.
- Every model, endpoint, and page added MUST be traceable back to a requirement in the spec (which
  itself traces back to the source SRS/diagrams or an explicitly confirmed project decision, such
  as the added Vendor role) — no speculative features beyond what's specified.

## Governance

This constitution supersedes ad hoc technical decisions; where a plan or task conflicts with a
Principle above, the plan/task MUST be revised, not the principle silently ignored. Amendments are
made by re-running the constitution workflow, MUST increment the version per semantic versioning
(MAJOR: incompatible principle removal/redefinition; MINOR: new principle or materially expanded
guidance; PATCH: wording/clarification only), and MUST update `Last Amended`. Every `/speckit-plan`
and `/speckit-implement` stage MUST be checked against these principles as part of its own review
step described in Principle V, rather than deferring compliance review to a separate audit.

**Version**: 1.0.0 | **Ratified**: 2026-09-14 | **Last Amended**: 2026-09-14
