# InsightX

Phase 0 foundation for the Smart India Hackathon 2026 project **InsightX** (Problem Statement 26152: Social Media Analytics).

InsightX will turn social-media data into usable insights through an analytics pipeline and a decision-focused dashboard. This repository deliberately starts technology-neutral: select the final stack after the team agrees on data sources, scope, and deployment constraints.

## Repository map

| Location | Purpose |
| --- | --- |
| `apps/web` | Future user-facing dashboard |
| `apps/api` | Future API and analytics-service entry point |
| `packages/shared` | Shared types, utilities, and domain logic |
| `packages/ui` | Reusable interface components |
| `data` | Local data staging only; source datasets stay untracked |
| `infra` | Deployment and infrastructure configuration |
| `docs` | Product, architecture, and decision records |
| `tests` | Cross-application tests |

## Start here

1. Read [the project brief](docs/planning/project-brief.md).
2. Record stack and architecture choices as short ADRs in `docs/decisions`.
3. Create a GitHub repository, add it as `origin`, then push `main` (commands are in [GitHub setup](docs/github-setup.md)).
4. Create the first issue from the discovery checklist and work on a short-lived branch.

## Phase 0 outcomes

- A predictable home for application, data, infrastructure, and planning work.
- Safe handling of local data and secrets through `.gitignore`.
- A branch, review, and commit convention suitable for a student team.
- Shared VS Code defaults without forcing extensions or a programming language.

See [IDE setup](docs/ide-setup.md) and [Git workflow](docs/git-workflow.md) for the practical setup.
