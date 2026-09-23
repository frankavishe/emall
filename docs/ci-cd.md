# CI/CD pipeline

Single workflow: `.github/workflows/ci.yml`. It runs on every PR and push to
`development`, `staging`, and `main`, and each branch's push acts as one stage of the
promotion pipeline below.

## 1. feature/* -> development

- Open a PR into `development`.
- `backend-test` (ruff + pytest) and `frontend-check` (eslint, prettier, vitest, build)
  run for whichever of `backend/`/`frontend/` changed.
- `enable-auto-merge` flags the PR for GitHub's native auto-merge. Once the required
  status checks pass **and** the PR has the required approval (branch protection on
  `development`), GitHub completes the merge automatically - no extra polling job needed.

## 2. development -> staging

- The merge above pushes to `development`, which re-triggers this workflow scoped to
  that branch: `backend-image`/`frontend-image` build and push `dev-*`-tagged images to
  GHCR, then `promote-to-staging` fast-forwards `staging` to `development` and pushes it
  using the `PROMOTION_PAT` secret (the default `GITHUB_TOKEN` can't trigger a further
  workflow run, so a PAT is required to chain into the next stage).

## 3. staging: deploy + E2E

- The push to `staging` triggers a fresh run scoped to `staging`: images get rebuilt and
  tagged `staging-*`/`staging-latest`, then `staging-e2e` stands up
  `docker-compose.staging.yml` using the `staging-latest` images and runs the Playwright
  smoke suite (`frontend/e2e/`) against it.
- **This "staging" is a placeholder** - a docker-compose stack on the runner itself, since
  no dedicated staging host exists yet. Once one does, swap the "Deploy staging-simulation
  stack" step in `staging-e2e` for a real deploy (SSH/PaaS), and point
  `PLAYWRIGHT_BASE_URL` at that host instead of `localhost`.

## 4. staging -> main

- If `staging-e2e` passes, `promote-to-main` fast-forwards `main` to `staging` and pushes
  it directly with `PROMOTION_PAT` - no PR, no approval. The E2E pass on staging is the
  gate.
- The push to `main` triggers one final run: tests re-run and images are rebuilt tagged
  `prod-*` and `latest`.

## Image tags

| Branch      | Backend/frontend image tags        |
|-------------|-------------------------------------|
| development | `dev-<sha>`, `dev-latest`           |
| staging     | `staging-<sha>`, `staging-latest`   |
| main        | `prod-<sha>`, `latest`              |

## Required repo configuration

- **Secret `PROMOTION_PAT`**: a token (classic PAT with `repo`+`workflow` scope, or a
  fine-grained token with `Contents: write` + `Workflows: write` on this repo) used by
  `promote-to-staging`/`promote-to-main` to push in a way that triggers the next stage.
- **Repo setting**: "Allow auto-merge" enabled.
- **Branch protection on `development`**: require the `backend-test`/`frontend-check`
  status checks and at least 1 approving review before merging.
- `staging`/`main` intentionally do *not* require a PR - they're only ever updated by the
  promotion jobs above pushing directly with `PROMOTION_PAT`.
