# IDE setup

## VS Code

1. Install [Visual Studio Code](https://code.visualstudio.com/) and Git.
2. Open the repository folder—not an individual subfolder—so the whole project is searchable.
3. Accept the recommended extensions when VS Code offers them. They support shared editor rules, formatting, Git history, and Markdown.
4. Use the Source Control panel to inspect changes, stage files, and resolve merge conflicts; learn the command-line workflow as well, since it is universal.

The repository's `.editorconfig` and `.vscode/settings.json` keep whitespace, line endings, and save behaviour consistent. Those settings are deliberately light until the team selects a stack.

## Before first code

- Clone the repository, then run `git status`; it should report a clean working tree.
- Confirm Git recognizes your author name and email with `git config --get user.name` and `git config --get user.email`.
- Create a test branch and PR that changes a line in a document. This is the team's lowest-risk workflow rehearsal.
