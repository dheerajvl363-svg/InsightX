# GitHub repository setup

## Create and publish the repository

1. On GitHub, create a repository named `insightx`. Do **not** add a README, `.gitignore`, or license there—the local repository already has them.
2. Decide whether it should be private while the team is building. Add teammates with the least access they need.
3. In this folder, set your Git author identity if it is not already configured, then create the initial checkpoint:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git add .
git commit -m "chore(setup): initialise InsightX Phase 0"
```

4. Replace the placeholder with the repository URL shown by GitHub and publish:

```bash
git remote add origin https://github.com/ORG_OR_USERNAME/insightx.git
git push -u origin main
```

## Recommended repository settings

After the first push, open **Settings → Branches** and protect `main`:

- Require a pull request before merging.
- Require one approval when the team size allows it.
- Require branches to be up to date before merging if CI is later enabled.
- Disable force pushes and direct deletion of `main`.

Use GitHub Issues for planned work and the included pull-request template for reviews. Add labels such as `frontend`, `backend`, `data`, `ml`, `documentation`, `good first issue`, and `blocked` once the team starts triage.

## Access safety

Use GitHub's personal access tokens or SSH keys only on your own machine. Never put credentials in this repository, issues, PRs, screenshots, or chat messages.
