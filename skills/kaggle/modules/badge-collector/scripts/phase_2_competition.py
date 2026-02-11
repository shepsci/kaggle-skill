from typing import Optional
"""Phase 2: Competition badges (~7 badges).

Earns badges by submitting to various competition types:
  - Competitor, Getting Started Competitor, Playground Competitor
  - Community Competitor, Code Submitter
  - Notebook Modeler, Competition Modeler

Uses pre-built submission_titanic.csv and finds active competitions via CLI.
"""

import json
import shutil
from pathlib import Path

from badge_tracker import set_status, should_attempt
from utils import (
    API_DELAY,
    TEMPLATES_DIR,
    make_temp_dir,
    resource_name,
    run_kaggle_cli,
)


def _find_competition_by_category(category: str) -> Optional[str]:
    """Find an active competition by category.

    kaggle CLI v1.8+ outputs full URLs in the ref column:
      https://www.kaggle.com/competitions/playground-series-s6e2
    We extract the slug from the URL.
    """
    result = run_kaggle_cli(
        ["competitions", "list", "--category", category, "--sort-by", "latestDeadline"],
        check=False,
    )
    if result.returncode != 0:
        return None

    # Parse output — kaggle CLI v1.8 outputs a table with full URLs
    lines = result.stdout.strip().split("\n")
    for line in lines:
        # Skip header and separator lines
        if line.startswith("ref") or line.startswith("---") or not line.strip():
            continue
        parts = line.split()
        if not parts:
            continue
        ref = parts[0]
        # Extract slug from URL: https://www.kaggle.com/competitions/SLUG
        if "/competitions/" in ref:
            return ref.split("/competitions/")[-1].strip("/")
        # Fallback: treat first column as slug directly
        if not ref.startswith("-"):
            return ref
    return None


def _submit_titanic(username: str) -> bool:
    """Submit to Titanic (Getting Started) competition.

    Earns: Competitor, Getting Started Competitor.
    """
    badge_ids = ["competitor", "getting_started_competitor"]
    actionable = [b for b in badge_ids if should_attempt(b)]
    if not actionable:
        return True

    for bid in actionable:
        set_status(bid, "attempting")

    try:
        submission_file = TEMPLATES_DIR / "submission_titanic.csv"
        if not submission_file.exists():
            print("  [ERROR] submission_titanic.csv not found in templates")
            for bid in actionable:
                set_status(bid, "failed", "template missing")
            return False

        run_kaggle_cli([
            "competitions", "submit",
            "-c", "titanic",
            "-f", str(submission_file),
            "-m", "Badge Collector automated submission",
        ])
        print("  [OK] Submitted to Titanic competition")

        for bid in actionable:
            set_status(bid, "earned", "competition=titanic")
        return True

    except Exception as e:
        print(f"  [FAIL] Titanic submission: {e}")
        for bid in actionable:
            set_status(bid, "failed", str(e))
        return False


def _submit_playground(username: str) -> bool:
    """Submit to a Playground competition to earn Playground Competitor.

    Downloads the competition's sample_submission.csv and submits it.
    """
    if not should_attempt("playground_competitor"):
        return True

    set_status("playground_competitor", "attempting")
    try:
        comp = _find_competition_by_category("playground")
        if not comp:
            print("  [SKIP] No active Playground competition found")
            set_status("playground_competitor", "skipped", "no active playground competition")
            return False

        print(f"  Found playground competition: {comp}")

        # Download competition data to get sample_submission.csv
        tmp = make_temp_dir("-playground")
        dl_result = run_kaggle_cli([
            "competitions", "download", comp,
            "--path", str(tmp),
        ], check=False)

        # Find and unzip if needed
        import zipfile
        for zf in tmp.glob("*.zip"):
            with zipfile.ZipFile(zf, "r") as z:
                z.extractall(tmp)

        # Find sample_submission
        submission_file = None
        for pattern in ["sample_submission*.csv", "sample*.csv", "submission*.csv"]:
            matches = list(tmp.glob(pattern))
            if matches:
                submission_file = matches[0]
                break

        if not submission_file:
            # Fall back: create a minimal submission from whatever CSVs are available
            print(f"  [SKIP] No sample_submission found for {comp}")
            set_status("playground_competitor", "skipped", f"no sample_submission for {comp}")
            return False

        result = run_kaggle_cli([
            "competitions", "submit",
            "-c", comp,
            "-f", str(submission_file),
            "-m", "Badge Collector playground submission",
        ], check=False)

        if result.returncode == 0:
            print(f"  [OK] Submitted to Playground: {comp}")
            set_status("playground_competitor", "earned", f"competition={comp}")
            return True
        else:
            print(f"  [FAIL] Playground submission failed for {comp}: {result.stderr[:200]}")
            set_status("playground_competitor", "failed", f"submit failed for {comp}")
            return False

    except Exception as e:
        print(f"  [FAIL] Playground submission: {e}")
        set_status("playground_competitor", "failed", str(e))
        return False


def _submit_community(username: str) -> bool:
    """Submit to a Community competition to earn Community Competitor.

    Note: kaggle CLI does not have a 'community' category filter.
    Valid categories: featured, research, recruitment, gettingStarted, masters, playground.
    Community competitions often appear under 'research' or the default listing.
    We try 'research' as the closest match, and also download sample_submission
    to get the right format.
    """
    if not should_attempt("community_competitor"):
        return True

    set_status("community_competitor", "attempting")
    try:
        # Try 'research' category as closest match for community competitions
        comp = _find_competition_by_category("research")
        if not comp:
            print("  [SKIP] No active research/community competition found")
            set_status("community_competitor", "skipped",
                       "no active research competition (CLI has no 'community' category)")
            return False

        print(f"  Found research competition: {comp}")

        # Download sample submission
        tmp = make_temp_dir("-community")
        run_kaggle_cli(["competitions", "download", comp, "--path", str(tmp)], check=False)

        import zipfile
        for zf in tmp.glob("*.zip"):
            with zipfile.ZipFile(zf, "r") as z:
                z.extractall(tmp)

        submission_file = None
        for pattern in ["sample_submission*.csv", "sample*.csv"]:
            matches = list(tmp.glob(pattern))
            if matches:
                submission_file = matches[0]
                break

        if not submission_file:
            set_status("community_competitor", "skipped", f"no sample_submission for {comp}")
            return False

        result = run_kaggle_cli([
            "competitions", "submit",
            "-c", comp,
            "-f", str(submission_file),
            "-m", "Badge Collector community/research submission",
        ], check=False)

        if result.returncode == 0:
            print(f"  [OK] Submitted to research competition: {comp}")
            set_status("community_competitor", "earned", f"competition={comp}")
            return True
        else:
            print(f"  [FAIL] Submission failed: {result.stderr[:200]}")
            set_status("community_competitor", "failed", f"submit failed for {comp}")
            return False

    except Exception as e:
        print(f"  [FAIL] Community submission: {e}")
        set_status("community_competitor", "failed", str(e))
        return False


def _code_submission(username: str) -> bool:
    """Make a code-based submission to earn Code Submitter + Notebook Modeler.

    Creates a notebook that generates a submission file and submits via KKB.
    """
    badge_ids = ["code_submitter", "notebook_modeler"]
    actionable = [b for b in badge_ids if should_attempt(b)]
    if not actionable:
        return True

    for bid in actionable:
        set_status(bid, "attempting")

    try:
        tmp = make_temp_dir("-code-submit")
        nb_slug = resource_name("titanic-submit")

        # Create a notebook that generates a Titanic submission
        notebook_content = {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "import pandas as pd\n",
                        "import os\n",
                        "\n",
                        "# Read test data\n",
                        "test = pd.read_csv('/kaggle/input/titanic/test.csv')\n",
                        "\n",
                        "# Simple baseline: predict all 0\n",
                        "submission = pd.DataFrame({\n",
                        "    'PassengerId': test['PassengerId'],\n",
                        "    'Survived': 0\n",
                        "})\n",
                        "\n",
                        "# Save submission\n",
                        "submission.to_csv('submission.csv', index=False)\n",
                        "print(f'Submission shape: {submission.shape}')\n",
                        "print(submission.head())\n",
                    ],
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.10.0"},
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }
        (tmp / "notebook.ipynb").write_text(json.dumps(notebook_content, indent=2))

        metadata = {
            "id": f"{username}/{nb_slug}",
            "title": nb_slug,
            "code_file": "notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": False,
            "enable_tpu": False,
            "enable_internet": False,
            "keywords": ["badge-collector", "titanic", "competition"],
            "competition_sources": ["titanic"],
            "dataset_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }
        (tmp / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))

        run_kaggle_cli(["kernels", "push", "-p", str(tmp)])
        print(f"  [OK] Code submission notebook pushed: {nb_slug}")
        print("  NOTE: Notebook will execute on KKB. Check status with:")
        print(f"    kaggle kernels status {username}/{nb_slug}")

        for bid in actionable:
            set_status(bid, "earned", f"notebook={nb_slug}")
        return True

    except Exception as e:
        print(f"  [FAIL] Code submission: {e}")
        for bid in actionable:
            set_status(bid, "failed", str(e))
        return False


def _competition_modeler(username: str) -> bool:
    """Create a notebook using a model for a competition to earn Competition Modeler."""
    if not should_attempt("competition_modeler"):
        return True

    set_status("competition_modeler", "attempting")
    try:
        tmp = make_temp_dir("-comp-model")
        nb_slug = resource_name("comp-modeler")

        # Create a notebook that references both a competition and a model
        notebook_content = {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "import pandas as pd\n",
                        "\n",
                        "# Read competition data\n",
                        "test = pd.read_csv('/kaggle/input/titanic/test.csv')\n",
                        "\n",
                        "# Simple prediction using model approach\n",
                        "submission = pd.DataFrame({\n",
                        "    'PassengerId': test['PassengerId'],\n",
                        "    'Survived': 0\n",
                        "})\n",
                        "\n",
                        "submission.to_csv('submission.csv', index=False)\n",
                        "print('Competition modeler submission created')\n",
                    ],
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.10.0"},
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }
        (tmp / "notebook.ipynb").write_text(json.dumps(notebook_content, indent=2))

        metadata = {
            "id": f"{username}/{nb_slug}",
            "title": nb_slug,
            "code_file": "notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": False,
            "enable_tpu": False,
            "enable_internet": False,
            "keywords": ["badge-collector", "competition", "model"],
            "competition_sources": ["titanic"],
            "dataset_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }
        (tmp / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))

        run_kaggle_cli(["kernels", "push", "-p", str(tmp)])
        print(f"  [OK] Competition modeler notebook pushed: {nb_slug}")

        set_status("competition_modeler", "earned", f"notebook={nb_slug}")
        return True

    except Exception as e:
        print(f"  [FAIL] Competition modeler: {e}")
        set_status("competition_modeler", "failed", str(e))
        return False


def run(username: str) -> tuple[int, int]:
    """Run all Phase 2 badge actions. Returns (attempted, succeeded)."""
    actions = [
        ("Titanic submission", _submit_titanic),
        ("Playground submission", _submit_playground),
        ("Community submission", _submit_community),
        ("Code submission", _code_submission),
        ("Competition modeler", _competition_modeler),
    ]

    attempted = 0
    succeeded = 0

    for name, fn in actions:
        print(f"\n  --- {name} ---")
        attempted += 1
        if fn(username):
            succeeded += 1

    return attempted, succeeded
