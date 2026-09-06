# Git and GitHub workflow

## The mental model

Git records project history on your computer. A **commit** is a small saved checkpoint. A **branch** is a safe lane for one piece of work. GitHub hosts the shared copy. A **pull request (PR)** is the review step that merges a branch into `main`.

Keep `main` stable and releasable. Do ordinary work on a short-lived branch; merge it through a PR after at least one teammate reviews it when possible.

## One-time local setup

Set the name and email that will appear on your commits (use the email linked to GitHub):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

After creating an empty GitHub repository named `insightx`, connect this local repository and publish it:

```bash
git remote add origin https://github.com/ORG_OR_USERNAME/insightx.git
git push -u origin main
```

The `-u` links local `main` with GitHub's `main`, so later `git push` and `git pull` are enough.

## Everyday contribution loop

```bash
git switch main
git pull --ff-only
git switch -c feat/sentiment-baseline
# edit and test
git status
git add path/to/changed-file
git commit -m "feat(analytics): add sentiment baseline"
git push -u origin feat/sentiment-baseline
```

Then open a PR on GitHub from `feat/sentiment-baseline` into `main`. Describe the user-facing outcome, test evidence, and any data/privacy impact. After review and merge, update local `main` and delete the merged local branch:

```bash
git switch main
git pull --ff-only
git branch -d feat/sentiment-baseline
```

## Naming and commit conventions

- Branches: `feat/…`, `fix/…`, `docs/…`, `chore/…`; use lowercase hyphenated words.
- Commits: `type(scope): imperative summary`, for example `docs(setup): add team Git workflow`.
- Useful types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.
- Keep a commit focused. Do not mix formatting, unrelated cleanup, and a feature in one commit.

## Commands worth memorising

| Command | Meaning |
| --- | --- |
| `git status` | Shows what changed and what will be committed. Run this often. |
| `git diff` | Shows unstaged line-by-line changes. |
| `git add <file>` | Selects a change for the next commit. |
| `git commit -m "…"` | Creates a named checkpoint from staged changes. |
| `git log --oneline --graph --all` | Shows a compact history map. |
| `git pull --ff-only` | Updates without silently creating a merge commit. |
| `git restore <file>` | Discards unstaged edits to a file—use carefully. |

Never commit `.env` files, API keys, tokens, or raw social-media exports. If a secret is exposed, revoke or rotate it immediately; deleting it in a later commit does not erase it from Git history.
