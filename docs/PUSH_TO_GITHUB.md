# Push to GitHub

This folder is already initialized as a Git repository.

Local repository path:

```text
C:\Users\DELL\Documents\vispec-benchmark-demo
```

## Option A: Push to an Existing Empty GitHub Repo

Replace `<YOUR_GITHUB_REPO_URL>` with your GitHub repository URL:

```powershell
cd C:\Users\DELL\Documents\vispec-benchmark-demo
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

Example URL formats:

```text
https://github.com/<username>/vispec-benchmark-demo.git
git@github.com:<username>/vispec-benchmark-demo.git
```

## Option B: Upload Through GitHub Web UI

If command-line GitHub authentication is inconvenient:

1. Create a new GitHub repository named `vispec-benchmark-demo`.
2. Open the repository in GitHub web UI.
3. Upload the contents of this folder, or upload the generated zip archive.

## What Is Included

- Server benchmark runner.
- Minimal server setup script.
- Windows result-pull script.
- Operation manual Word document.
- Environment and asset checklist.
- Example JSON and PNG outputs.

## What Is Excluded

- Model weights.
- Datasets.
- SSH keys.
- Relay credentials.
- Generated logs and cache files.
