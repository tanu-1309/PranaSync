# ruff: noqa: E702
"""Split everything that is not committed yet into commits for each team member, in a safe push order, and build a bundle for each person.

    python scripts/team_commits.py            # writes docs/GIT_COMMITS_ROUND2.md and exports/team_bundles_round2/<Name>.zip

The team rule (docs/TEAM_GITHUB_PLAN.md) is that each person commits their own files from their own GitHub account, so authorship on GitHub is honest. This script only PLANS and PACKAGES:
it makes no commit and pushes nothing. Each bundle holds that person's files at their real paths plus PUSH_INSTRUCTIONS.md with the exact commands. Every path in `git status` must belong to exactly one
commit; the script stops and says so if one does not.
"""
import fnmatch
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
NEVER = ["results/*.log", "PranaSync_Week9_Package.zip", "data/raw/.gitkeep", "data/credentials*", ".env", "exports/*"]      # not committed: logs, an old zip, a file git thinks was deleted, passwords, keys, outputs

# order, person, branch, reviewer, then commits: (message, [path patterns])
PLAN = [
    (1, "Uday Kumar Reddy Yarradoddi", "round2/data-foundation", "Sindhu", [
        ("Add the document store, profiles, and the database helpers for uploads\n\nA separate sealed JSON document store (AES-256-GCM, a key per person), the profiles table, and the helpers for reviewing and replacing the values read from a document.",
         ["src/prana/data/db.py", "src/prana/data/docstore.py"]),
        ("Set up the project: dependencies, lint, CI and ignore rules\n\nAdds cryptography, OCR and PDF libraries, the lint settings, a CI workflow that runs the tests on every push, and ignore rules for keys, uploads and password sheets.",
         ["requirements.txt", ".gitignore", ".env.example", "ruff.toml", ".github/workflows/tests.yml", "scripts/team_commits.py", "scripts/git_guide.py"]),
    ]),
    (2, "Sindhu Padmaja Dudekula", "round2/risk-and-ai", "Sneha", [
        ("Add the explainable three-area risk model and its training data\n\nParameters, features, a per-area gradient-boosted model with exact per-value reasons, the service that merges documents into one picture, and the 900-record training table and trained model.",
         ["src/prana/risk/params.py", "src/prana/risk/features.py", "src/prana/risk/model.py", "src/prana/risk/service.py", "src/prana/risk/review.py", "models/risk_model.json", "data/risk/training_table.csv", "scripts/build_risk_table.py", "scripts/train_risk_model.py"]),
        ("Read uploaded documents: pattern reader, OCR for photos and scans, optional AI second reader\n\nUnits converted, ranges not mistaken for results, decimal commas, and an on-device OCR path. The Nemotron second reader only adds values it can prove from a real line, with identity removed first.",
         ["src/prana/risk/extract.py", "src/prana/risk/ocr.py", "src/prana/risk/extract_ai.py", "scripts/eval_extraction.py", "results/extraction_eval.json", "tests/test_extract_ai.py", "tests/test_extract_polish.py", "tests/test_ocr.py", "tests/test_range_before_result.py"]),
        ("Add the medical-insight pipeline, knowledge retrieval and the safeguard rails\n\nMedGemma insights with highlight marks, the approved-document knowledge base, a router between models, and thirteen numbered safeguard rails applied to every AI path, with a red-team script.",
         ["src/prana/ai/*.py", "scripts/redteam_ai.py", "scripts/check_medgemma.py", "scripts/pregenerate_ai.py", "scripts/export_ai_results.py", "results/redteam.json",
          "tests/test_ai.py", "tests/test_ai_first.py", "tests/test_analytics_ai.py", "tests/test_guardrails.py", "tests/test_knowledge.py", "tests/test_llm.py", "tests/test_medgemma.py",
          "tests/test_model_router.py", "tests/test_rerank.py", "tests/test_assessment_store_pg.py", "tests/test_shots.py"]),
        ("Add the fine-tuning dataset, scoring, and training recipe\n\n2,082 training and 224 validation examples built from our own data and rules, a scorer that applies the portal's rails, a LoRA recipe and a Colab notebook. Nothing is fine-tuned yet: no GPU.",
         ["finetune/*", "tests/test_finetune_dataset.py"]),
    ]),
    (3, "Uday Kumar Reddy Yarradoddi", "round2/portal-api", "Tanusree", [
        ("Add the portal API: register, upload, review, profile, export, clinical data and administrator reads\n\nRoutes for uploading and reviewing documents, editing personal details, downloading a person's data, the clinical view's data and read-only administrator access with an audit trail.",
         ["src/prana/api/server.py", "src/prana/api/risk_routes.py", "src/prana/api/account_routes.py", "src/prana/api/analytics.py", "src/prana/api/analytics_routes.py"]),
        ("Test the portal API, the document store and the browser flows\n\nAPI, security, document store, review and account tests, and rewritten browser tests for the five-place portal (they run with RUN_E2E=1).",
         ["tests/conftest.py", "tests/test_api.py", "tests/test_e2e.py", "tests/test_e2e_analytics.py", "tests/test_account.py", "tests/test_document_store.py", "tests/test_risk_documents.py",
          "tests/test_analytics.py", "tests/test_security_phase9.py", "tests/test_medical_workflows.py"]),
    ]),
    (4, "Gavinnolla Tanusree Reddy", "round2/portal-ui", "Uday", [
        ("Rebuild the portal into five places with tabs\n\nHome, Trends and labs, Analytics and outlook, How it works and Account; old addresses still open the right tab, with back links that name where you came from.",
         ["web/js/app.js", "web/js/hubs.js", "web/js/ui.js", "web/js/record.js", "web/js/glance.js", "web/js/hero.js", "web/js/homeparts.js", "web/js/outlook.js", "web/index.html", "web/css/theme.css", "web/css/home.css", "web/css/hubs.css"]),
        ("Add upload, review, account, clinical view and the architecture and models pages\n\nRegister and upload, a review page to correct each value, an editable Account, the clinical view, flow diagrams, the models page and the administrator viewer.",
         ["web/js/risk.js", "web/js/register.js", "web/js/review.js", "web/js/account.js", "web/js/login.js", "web/js/landing.js", "web/js/clinical.js", "web/js/architecture.js", "web/js/models.js", "web/js/method.js", "web/js/admin.js", "web/css/risk.css"]),
        ("Highlight key values and words, and tidy the analytics and chat pages\n\nA safe highlighter for values, measures and direction words; a redesigned insight card; the chat and AI status updates.",
         ["web/js/highlight.js", "web/js/analytics.js", "web/js/ai.js", "web/js/chat.js", "web/css/analytics.css"]),
    ]),
    (5, "Sneha Gunturu", "round2/docs-and-knowledge", "Tanusree", [
        ("Add the knowledge base sources and the helpers that fetch and ingest them\n\n23 approved WHO and MedlinePlus sources with licences and approvers recorded, and the scripts to fetch and ingest them.",
         ["config/knowledge_sources.yaml", "config/knowledge_manifest.example.yaml", "data/knowledge/manifest.yaml", "scripts/fetch_who_factsheets.py", "scripts/fetch_medical_sources.py", "scripts/ingest_knowledge.py"]),
        ("Add made-up sample documents and the data dictionary generator\n\nThirteen sample reports (PDF, Word, Excel, CSV, a photo and a scan) with a README, and a script that writes the data dictionary from the code.",
         ["sample_documents/*", "scripts/make_sample_documents.py", "scripts/make_data_dictionary.py", "scripts/visual_regression.py", "docs/DATA_DICTIONARY.md"]),
        ("Document the architecture, the safeguard rails, the gaps and the team tasks\n\nSite structure, the upload and OCR flow, the rails, what is still lacking, pitch questions, team tasks, the run guide and the earlier project documents.",
         ["docs/*", "README.md", "START_HERE.md"]),
    ]),
]
REVIEW_NOTE = "Each person should read their own files before committing: the commit carries their name."


def changed() -> list[str]:
    out = subprocess.run(["git", "status", "--short", "-uall"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    return sorted(line[3:].strip().strip('"') for line in out)


def match(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def main() -> int:
    files = [f for f in changed() if not match(f, NEVER)]
    owner: dict[str, tuple[int, int]] = {}
    for oi, (order, who, branch, reviewer, commits) in enumerate(PLAN):
        for ci, (msg, pats) in enumerate(commits):
            for f in files:
                if match(f, pats):
                    if f in owner:                                   # a more specific commit listed first wins; a later broad pattern must not take it
                        continue
                    owner[f] = (oi, ci)
    missing = [f for f in files if f not in owner]
    if missing:
        print("These paths belong to no commit; add them to PLAN:", *missing, sep="\n  "); return 1
    out = ["# Git commits for everyone (round 2)", "",
           "Everything that was not committed yet, split into commits per person in a safe order. **Nobody has committed or pushed yet.** The team rule (`TEAM_GITHUB_PLAN.md`) stands: **each person commits their own files from their own GitHub account**, so the history shows who did what. "
           + REVIEW_NOTE, "",
           "Repo: https://github.com/tanu-1309/PranaSync. Generated by `python scripts/team_commits.py`, which also writes one bundle per person in `exports/team_bundles_round2/`.", "",
           "| Order | Who | Branch | Reviewer | Commits | Files |", "|---|---|---|---|---|---|"]
    for oi, (order, who, branch, reviewer, commits) in enumerate(PLAN):
        n = sum(1 for v in owner.values() if v[0] == oi)
        out.append(f"| {order} | {who} | `{branch}` | {reviewer} | {len(commits)} | {n} |")
    out += ["", "**Merge in this order.** Pull requests 1 to 3 depend on each other (the API imports the risk and AI code, which import the database helpers), so continuous integration can be red until request 3 is merged: open all of 1 to 3, then merge them in one sitting. Requests 4 and 5 can be reviewed in parallel.", "",
            "**Do not commit** these (listed so nobody adds them by mistake): `results/*.log`, `PranaSync_Week9_Package.zip`, `exports/`, `data/credentials_*.csv` (plain-text passwords), `.env`, and `data/.docstore_key`. If git shows `data/raw/.gitkeep` as deleted, run `git restore data/raw/.gitkeep`.", "",
            "Every commit message ends with `" + TRAILER + "` because the work was written with Claude's help; keep it, it is honest.", ""]
    bundles: dict[str, list] = {}
    for oi, (order, who, branch, reviewer, commits) in enumerate(PLAN):
        sec = [f"## {order}. {who}: `{branch}` (reviewer: {reviewer})", "", "```bash", "git checkout main && git pull", f"git checkout -b {branch}", "# unzip your bundle into the project folder (say replace if asked), then:"]
        for ci, (msg, pats) in enumerate(commits):
            mine = [f for f in files if owner.get(f) == (oi, ci)]
            title = msg.split("\n")[0]
            sec += ["", f"# commit {ci + 1}: {len(mine)} files"]
            sec += [f'git add "{f}"' for f in mine] if len(mine) <= 12 else [f'git add "{p}"' for p in pats]
            body = msg.split("\n\n", 1)[1] if "\n\n" in msg else ""
            sec += [f'git commit -m "{title}" -m "{body}" -m "{TRAILER}"']
            bundles.setdefault(who, []).append((oi, mine))
        sec += ["", f"git push -u origin {branch}", "```", "", "Then on GitHub: Compare & pull request, base `main`, add the reviewer, and they merge it.", ""]
        out += sec
    path = ROOT / "docs" / "GIT_COMMITS_ROUND2.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    dest = ROOT / "exports" / "team_bundles_round2"
    dest.mkdir(parents=True, exist_ok=True)
    for who, parts in bundles.items():
        tag = "Tanusree" if who.startswith("Gavinnolla") else who.split()[0]
        mine_files = sorted({f for oi, fs in parts for f in fs})
        instr = [f"# Push instructions for {who}", "", "From the PranaSync repo folder, on your own computer and your own git identity:", "", "```bash", 'git config user.name "Your Name"', 'git config user.email "your-github-email"', "```", "",
                 "Then follow your section(s) of `docs/GIT_COMMITS_ROUND2.md` (included in this bundle): branch, `git add` lines, commit messages, push, pull request.", "", f"Files in this bundle: {len(mine_files)}.", "", REVIEW_NOTE]
        with zipfile.ZipFile(dest / f"{tag}_round2.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in mine_files:
                z.write(ROOT / f, f)
            if "docs/GIT_COMMITS_ROUND2.md" not in mine_files:
                z.write(path, "docs/GIT_COMMITS_ROUND2.md")
            z.writestr("PUSH_INSTRUCTIONS.md", "\n".join(instr) + "\n")
        print(f"{who}: {len(mine_files)} files -> {tag}_round2.zip")
    print(f"wrote {path} ({len(files)} files in {sum(len(c) for _, _, _, _, c in PLAN)} commits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
