# How each of us pushes the checkpoint into `main`

Repo: https://github.com/tanu-1309/PranaChain · Each person commits **their own files from their own GitHub account**.
Use the bundle with your name (`Tanusree_...zip` etc.); each contains only your files, already at the right paths, plus
`PUSH_INSTRUCTIONS.md`. **Push in this order** so the tests pass after every merge:

| # | Who | Branch | What | Reviewer |
|---|---|---|---|---|
| 1 | Tanusree | `chore/repo-setup` | README, requirements, gitignore, config helper, run guide | Uday |
| 2 | Sneha | `feature/data-pipeline` | column map, generator, loader & cleaning, timeline, DB, profiling + tests | Sindhu |
| 3 | Sindhu | `feature/analysis` | scenario config, baselines, trend & change point, patterns + tests | Sneha |
| 4 | Uday | `feature/insight` | history linking, evidence, missing data, explanation, pipeline + tests, architecture doc | Tanusree |
| 5 | Tanusree | `feature/dashboard-ci` | dashboard, CI, one-command demo scripts, screenshots | Sneha |
| 6 | all four | `feature/validation-checkpoint` | validate.py (Sindhu), VALIDATION.md (Sneha), plan/limits/demo docs (Uday), results + this file (Tanusree) | Uday merges |

After PR 6: `git tag checkpoint-1 && git push origin checkpoint-1`.

## Steps for each person (same every time)
```bash
# once
git clone https://github.com/tanu-1309/PranaChain.git
cd PranaChain
git config user.name "Your Name"            # so the commit shows YOUR name
git config user.email "you@uwindsor.ca"     # the email of your GitHub account

# for your PR (after the previous PR is merged)
git checkout main
git pull
git checkout -b <your-branch>
# unzip YOUR bundle into this folder (say "replace" if asked); PUSH_INSTRUCTIONS.md lists the exact git add line
git add <your files>
git commit -m "<message from PUSH_INSTRUCTIONS.md>"
git push -u origin <your-branch>
```
Then on GitHub: **Compare & pull request** → base `main` → add the reviewer → reviewer clicks **Merge**.

**No pull requests set up?** Same steps but skip the branch: `git checkout main && git pull`, add and commit your files,
`git push origin main`. Still go in the order above; if the push is rejected, run `git pull --rebase` and push again.

## Rules
* Never commit `data/raw/`, `data/synthetic/`, `*.db`, `results/insights/`, `results/summary.csv` or `.env` (all git-ignored; check `git status` before committing).
* Before pushing (from PR 4 on): `python -m pytest -q` shows `18 passed`.
* Everyone must be able to explain every file they push (each file starts with a short description of its job).
