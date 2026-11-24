"""Add approved documents to the medical knowledge base, or list what is in it.

    python scripts/ingest_knowledge.py                 # ingest data/knowledge/manifest.yaml
    python scripts/ingest_knowledge.py --manifest PATH # another manifest
    python scripts/ingest_knowledge.py --list          # what is ingested (no passage text)

A manifest lists local files, each with its source details and the name of the person who approved it. See config/knowledge_manifest.example.yaml.
Nothing is downloaded: you save the document yourself after checking its licence. An entry that breaks a rule is rejected with the reasons, and the rest still run.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prana.ai import knowledge  # noqa: E402

if __name__ == "__main__":
    if "--list" in sys.argv:
        print(json.dumps(knowledge.stats(), indent=2))
    else:
        path = Path(sys.argv[sys.argv.index("--manifest") + 1]) if "--manifest" in sys.argv else None
        for row in knowledge.ingest(path):
            print(json.dumps(row))
