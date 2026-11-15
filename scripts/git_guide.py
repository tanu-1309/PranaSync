# ruff: noqa: E702
"""Write a dated, step-by-step Git guide for every team member, and the routine that keeps the repository up to date.

    python scripts/team_commits.py                    # first: the commit plan and the bundles
    python scripts/git_guide.py                       # then: docs/GIT_GUIDE_BY_PERSON.md and a guide inside each bundle
    python scripts/git_guide.py --start 2026-12-01    # move every date (the first working day of the push week)

The dates are a PROPOSAL (working days only, one pull request a day with a day for review), not a deadline anyone set: change --start if the team's week is different. Nothing here commits or pushes.
"""
import argparse
import importlib.util
import subprocess
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("team_commits", ROOT / "scripts" / "team_commits.py")
tc = importlib.util.module_from_spec(spec)
sys.modules["team_commits"] = tc
spec.loader.exec_module(tc)


def workdays(start: date, n: int) -> list[date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def next_workday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def fmt(d: date) -> str:
    return d.strftime("%a %d %b %Y")


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=(date.today() + timedelta(days=1)).isoformat(), help="first working day of the push week (YYYY-MM-DD)")
    a = ap.parse_args()
    D = workdays(date.fromisoformat(a.start), 7)           # D[0] .. D[6]
    when = {1: D[0], 2: D[1], 3: D[2], 4: D[3], 5: D[4]}   # the day each pull request is opened
    merge_123, merge_45, tag_day = D[3], D[5], D[6]          # the three dependent pull requests are merged on the morning after the last one is opened, then pull request 4 is opened
    files = [f for f in tc.changed() if not tc.match(f, tc.NEVER)]
    owner: dict[str, tuple[int, int]] = {}
    for oi, (_o, _w, _b, _r, commits) in enumerate(tc.PLAN):
        for ci, (_m, pats) in enumerate(commits):
            for f in files:
                if tc.match(f, pats) and f not in owner:
                    owner[f] = (oi, ci)
    reviewer_of = {name: [] for name in ("Uday", "Sindhu", "Sneha", "Tanusree")}
    short = {"Uday Kumar Reddy Yarradoddi": "Uday", "Sindhu Padmaja Dudekula": "Sindhu", "Sneha Gunturu": "Sneha", "Gavinnolla Tanusree Reddy": "Tanusree"}
    for order, who, branch, reviewer, _c in tc.PLAN:
        reviewer_of[reviewer].append((order, short[who], branch))

    log = git("log", "-12", "--date=short", "--format=%ad | %an | %s")
    me = git("branch", "--show-current") or "(detached)"
    dirty = len([line for line in git("status", "--short", "-uall").splitlines() if line.strip()])
    md = ["# Git guide for the team, with dates", "",
          f"Written {date.today():%a %d %b %Y}. The repository is https://github.com/tanu-1309/PranaSync. Everyone commits **their own files from their own GitHub account**. Nobody has committed or pushed the new work yet.", "",
          "The dates below are a **proposal**: one pull request a day, working days only, with the day after for review, then one merge sitting. If your week is different, run `python scripts/git_guide.py --start YYYY-MM-DD` and the guide is rewritten.", "",
          "## The week at a glance", "", "| Date | Who | What |", "|---|---|---|"]
    for order, who, branch, reviewer, _c in tc.PLAN:
        md.append(f"| {fmt(when[order])} | {short[who]} | Open pull request {order} `{branch}`; {reviewer} reviews |")
    md += [f"| {fmt(merge_123)} (morning) | Uday + the reviewers | **Merge pull requests 1, 2 and 3 together**, in order, then everyone runs the sync routine. Tanusree opens pull request 4 after that |",
           f"| {fmt(merge_45)} | Uday, Tanusree | Merge pull requests 4 and 5 |",
           f"| {fmt(tag_day)} | everyone | Final sync, run the tests once, **Uday tags `round2-complete`** |", "",
           "Pull requests 1 to 3 depend on each other (the API imports the risk and AI code, which import the database helpers), so the automatic checks can be red until pull request 3 is merged.", "",
           "## Where the repository stands today", "", f"- Branch you are on in this folder: `{me}`", f"- Paths with uncommitted changes: {dirty}", "- Latest commits (date | author | message):", "", "```", log, "```", "",
           "## Everyone, once (setup)", "", "```bash", "git clone https://github.com/tanu-1309/PranaSync.git      # skip if you already have the folder", "cd PranaSync",
           'git config user.name "Your Name"                            # so the commit shows YOUR name',
           'git config user.email "the-email-of-your-github-account"', "git config pull.rebase true                                 # keeps history straight when you pull", "```", "",
           "## Everyone, every working morning (keeps your copy up to date)", "", "| Date | Command | What it does |", "|---|---|---|"]
    for d in D:
        md.append(f"| {fmt(d)} | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |")
    md += ["", "Before you push anything, on your branch: `git fetch origin && git rebase origin/main` (if it stops on a conflict, see Troubleshooting).", "",
           "Every Friday: `git log --since=\"7 days ago\" --date=short --format=\"%ad %an %s\"` shows what the team did this week.", ""]
    for oi, (order, who, branch, reviewer, commits) in enumerate(tc.PLAN):
        pass
    persons = {}
    for oi, (order, who, branch, reviewer, commits) in enumerate(tc.PLAN):
        persons.setdefault(who, []).append((oi, order, branch, reviewer, commits))
    guides: dict[str, list[str]] = {}
    for who, prs in persons.items():
        s = short[who]
        g = [f"# {who}: your Git steps, with dates", "", f"Follow these in order. Every step says the day it is meant for ({fmt(D[0])} to {fmt(tag_day)}). Read the files in your bundle before you commit: the commit carries your name.", ""]
        n = 0
        for oi, order, branch, reviewer, commits in prs:
            day = when[order]
            nfiles = sum(1 for v in owner.values() if v[0] == oi)
            g += [f"## Pull request {order}: `{branch}` ({nfiles} files, {len(commits)} commits)", ""]
            steps = [
                (day - timedelta(days=0), "Sync with main", "```bash\ngit fetch --all --prune\ngit switch main\ngit pull --ff-only\n```", "Your main matches GitHub. If `git pull` complains about local changes, stop and ask: do not discard anything."),
                (day, "Make your branch", f"```bash\ngit switch -c {branch}\n```", "A branch keeps your work apart until it is reviewed."),
                (day, "Unpack your bundle", "Extract `" + ("Tanusree" if s == "Tanusree" else s) + "_round2.zip` over the project folder (choose **replace** if asked). In PowerShell: `Expand-Archive -Path <path to the zip> -DestinationPath . -Force`", "Your files land at their real paths. Nothing else changes."),
                (day, "Check only your files changed", "```bash\ngit status --short\n```", "You should see only files from your bundle. If you see `.env`, `data/credentials_*.csv`, `data/.docstore_key` or a `*.log`, **do not add them**."),
                (day, "Run the tests and the lint", "```bash\nPYTHONPATH=src python -m pytest -q\npython -m ruff check src scripts tests finetune\n```", "On Windows PowerShell: `$env:PYTHONPATH = \"src\"` first. Red tests before pull request 3 is merged can be expected for some parts; tell the team which ones fail."),
            ]
            for ci, (msg, pats) in enumerate(commits):
                mine = [f for f in files if owner.get(f) == (oi, ci)]
                title, body = msg.split("\n")[0], (msg.split("\n\n", 1)[1] if "\n\n" in msg else "")
                adds = "\n".join(f'git add "{f}"' for f in mine) if len(mine) <= 12 else "\n".join(f'git add "{p}"' for p in pats)
                steps.append((day, f"Commit {ci + 1} of {len(commits)}: {title}", f"```bash\n{adds}\ngit commit -m \"{title}\" -m \"{body}\" -m \"{tc.TRAILER}\"\n```", f"{len(mine)} files. Check with `git show --stat HEAD` that it holds what you expect."))
            steps += [(day, "Push and open the pull request", f"```bash\ngit push -u origin {branch}\n```", f"On GitHub press **Compare & pull request**, base `main`, add **{reviewer}** as reviewer, and paste the commit titles as the description."),
                      (merge_123 if order <= 3 else merge_45, "After it is merged", f"```bash\ngit switch main\ngit pull --ff-only\ngit branch -d {branch}\n```", "Your branch has done its job. The merge sitting is described at the top of this guide.")]
            for d, title, cmd, note in steps:
                n += 1
                g += [f"**Step {n} ({fmt(d)}): {title}**", "", cmd, "", note, ""]
        rev = reviewer_of[s]
        if rev:
            g += ["## You also review", ""]
            for order, author, branch in rev:
                d = next_workday(when[order])
                g += [f"- **{fmt(d)}**: pull request {order} `{branch}` by {author}. On GitHub open **Files changed**, read it, run it if you can (`git fetch origin {branch} && git switch {branch}`, then the tests), leave comments, and press **Approve**. Uday presses **Merge** at the merge sitting.", ""]
        g += [f"## {fmt(tag_day)}: final sync (everyone)", "", "```bash\ngit fetch --all --prune\ngit switch main\ngit pull --ff-only\nPYTHONPATH=src python -m pytest -q\n```", "", "Uday only, once everything is merged and the tests pass:", "", "```bash\ngit tag -a round2-complete -m \"Risk model, uploads, document store, clinical view, safeguard rails\"\ngit push origin round2-complete\n```", ""]
        guides[who] = g
    md += ["## Each person's steps", "", "Each person's full step-by-step guide is below, and the same text is inside their bundle in `exports/team_bundles_round2/`.", ""]
    for who, g in guides.items():
        md += g[:]
        md.append("---")
        md.append("")
    md += ["## Troubleshooting (everyone)", "",
           "| Problem | What to do |", "|---|---|",
           "| `git push` is rejected | `git fetch origin && git rebase origin/main`, then `git push --force-with-lease` (only on your own branch). Never force-push `main`. |",
           "| A rebase stops on a conflict | Open the files git lists, keep the right lines, remove the `<<<<` `====` `>>>>` marks, then `git add <file>` and `git rebase --continue`. To give up: `git rebase --abort`. |",
           "| You added the wrong file | Before you push: `git reset --soft HEAD~1` (undoes the last commit, keeps your files staged), unstage with `git restore --staged <file>`, commit again. |",
           "| You committed a password or key | **Do not push.** `git reset --soft HEAD~1`, remove it, commit again. If it was already pushed: change that password or key now, and tell Uday. |",
           "| Git shows `data/raw/.gitkeep` deleted | `git restore data/raw/.gitkeep` |",
           "| Your changes look wrong after a pull | `git status` and `git log --oneline -5` first. Ask before using `git reset --hard`: it throws work away. |",
           "| You are on the wrong branch | `git branch --show-current`; to move your uncommitted work: `git stash`, `git switch <right branch>`, `git stash pop`. |", "",
           "## What never goes in git", "", "`.env`, `data/.docstore_key`, `data/.session_secret`, `data/credentials_*.csv` (plain-text passwords), the databases and uploaded files (`data/*.db`, `data/uploads/`), `results/*.log`, and `exports/`. `.gitignore` already blocks most of these; check `git status` before every commit.", ""]
    out = ROOT / "docs" / "GIT_GUIDE_BY_PERSON.md"
    out.write_text("\n".join(md), encoding="utf-8")
    dest = ROOT / "exports" / "team_bundles_round2"
    for who, g in guides.items():
        z = dest / f"{short[who]}_round2.zip"
        if z.exists():
            with zipfile.ZipFile(z, "a", zipfile.ZIP_DEFLATED) as zz:
                if "YOUR_GIT_GUIDE.md" not in zz.namelist():
                    zz.writestr("YOUR_GIT_GUIDE.md", "\n".join(g) + "\n")
    print(f"wrote {out} ({len(md)} lines); dates {fmt(D[0])} to {fmt(tag_day)}; guides added to {len(guides)} bundles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
