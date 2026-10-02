"""Phase 2: Competition badges (7 badges).

Earns badges by submitting to various competition types:
  - Competitor, Getting Started Competitor, Playground Competitor
  - Community Competitor, Code Submitter
  - Notebook Modeler, Competition Modeler

Uses pre-built submission_titanic.csv and finds active competitions via CLI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from badge_tracker import set_status, should_attempt
from utils import (
    TEMPLATES_DIR,
    make_temp_dir,
    resource_name,
    run_kaggle_cli,
    show_cli_output,
)

from shared.safe_extract import safe_extract  # utils puts the skill root on sys.path


def _safe_extract(zf_path: Path, dest: Path) -> None:
    """Extract ``zf_path`` into ``dest`` with the shared zip-slip check.

    Raises ValueError, and writes nothing, if a member would land outside
    ``dest`` or is a symlink. Kaggle archives are untrusted input.
    """
    safe_extract(zf_path, dest)


def _parse_competition_slugs(stdout: str) -> list[str]:
    """Competition slugs from `kaggle competitions list --format json` output.

    The CLI can print a "Next Page Token" line around the JSON, and prints
    "No competitions found" when the list is empty, so only the JSON array is
    read. Anything else yields no slugs.
    """
    start, end = stdout.find("["), stdout.rfind("]")
    if start < 0 or end < start:
        return []
    try:
        rows = json.loads(stdout[start : end + 1])
    except ValueError:
        return []
    slugs = []
    for row in rows if isinstance(rows, list) else []:
        ref = str(row.get("ref", "")) if isinstance(row, dict) else ""
        slug = ref.rstrip("/").split("/")[-1]
        if slug:
            slugs.append(slug)
    return slugs


def _find_competition(*filter_args: str) -> Optional[str]:
    """First competition the CLI lists for the given filter, or None."""
    result = run_kaggle_cli(
        ["competitions", "list", *filter_args, "--sort-by", "latestDeadline", "--format", "json"],
        check=False,
    )
    if result.returncode != 0:
        return None
    slugs = _parse_competition_slugs(result.stdout)
    return slugs[0] if slugs else None


def _find_competition_by_category(category: str) -> Optional[str]:
    """Find an active competition by category (playground, research, ...)."""
    return _find_competition("--category", category)


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

        run_kaggle_cli(
            [
                "competitions",
                "submit",
                "-c",
                "titanic",
                "-f",
                str(submission_file),
                "-m",
                "Badge Collector automated submission",
            ]
        )
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
        dl_result = run_kaggle_cli(
            [
                "competitions",
                "download",
                comp,
                "--path",
                str(tmp),
            ],
            check=False,
        )
        if dl_result.returncode != 0:
            print(f"  [SKIP] Could not download {comp}; accept its rules on kaggle.com first")
            set_status("playground_competitor", "skipped", f"could not download {comp}")
            return False

        # Find and unzip if needed (zip-slip-safe)
        for zf in tmp.glob("*.zip"):
            _safe_extract(zf, tmp)

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

        result = run_kaggle_cli(
            [
                "competitions",
                "submit",
                "-c",
                comp,
                "-f",
                str(submission_file),
                "-m",
                "Badge Collector playground submission",
            ],
            check=False,
        )

        if result.returncode == 0:
            print(f"  [OK] Submitted to Playground: {comp}")
            set_status("playground_competitor", "earned", f"competition={comp}")
            return True
        else:
            print(f"  [FAIL] Playground submission failed for {comp}:")
            show_cli_output(result)
            set_status("playground_competitor", "failed", f"submit failed for {comp}")
            return False

    except Exception as e:
        print(f"  [FAIL] Playground submission: {e}")
        set_status("playground_competitor", "failed", str(e))
        return False


def _submit_community(username: str) -> bool:
    """Submit to a Community competition to earn Community Competitor.

    Community competitions are listed with `kaggle competitions list --group community`.
    """
    if not should_attempt("community_competitor"):
        return True

    set_status("community_competitor", "attempting")
    try:
        comp = _find_competition("--group", "community")
        if not comp:
            print("  [SKIP] No active community competition found")
            set_status("community_competitor", "skipped", "no active community competition")
            return False

        print(f"  Found community competition: {comp}")

        # Download sample submission
        tmp = make_temp_dir("-community")
        run_kaggle_cli(["competitions", "download", comp, "--path", str(tmp)], check=False)

        for zf in tmp.glob("*.zip"):
            _safe_extract(zf, tmp)

        submission_file = None
        for pattern in ["sample_submission*.csv", "sample*.csv"]:
            matches = list(tmp.glob(pattern))
            if matches:
                submission_file = matches[0]
                break

        if not submission_file:
            set_status("community_competitor", "skipped", f"no sample_submission for {comp}")
            return False

        result = run_kaggle_cli(
            [
                "competitions",
                "submit",
                "-c",
                comp,
                "-f",
                str(submission_file),
                "-m",
                "Badge Collector community submission",
            ],
            check=False,
        )

        if result.returncode == 0:
            print(f"  [OK] Submitted to community competition: {comp}")
            set_status("community_competitor", "earned", f"competition={comp}")
            return True
        else:
            print("  [FAIL] Submission failed:")
            show_cli_output(result)
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
            "keywords": ["kaggle-badges", "titanic", "competition"],
            "competition_sources": ["titanic"],
            "dataset_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }
        (tmp / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))

        run_kaggle_cli(["kernels", "push", "-p", str(tmp)])
        print(f"  [OK] Code submission notebook pushed: {nb_slug}")
        print("  [MANUAL] The badges need a submission made from this notebook.")
        print(f"           When `kaggle kernels status {username}/{nb_slug}` shows COMPLETE,")
        print("           open the notebook on kaggle.com and choose Submit to competition.")

        # Pushing the notebook is not a submission, so nothing is earned yet.
        for bid in actionable:
            set_status(
                bid, "skipped", f"notebook={nb_slug} pushed; submit it from the notebook page"
            )
        return False

    except Exception as e:
        print(f"  [FAIL] Code submission: {e}")
        for bid in actionable:
            set_status(bid, "failed", str(e))
        return False


def _competition_modeler(username: str) -> bool:
    """Competition Modeler needs a competition notebook that uses a Kaggle model.

    Choosing and attaching a model is the user's decision (many need a licence
    to be accepted first), so nothing is pushed here.
    """
    if not should_attempt("competition_modeler"):
        return True

    print("  [MANUAL] Competition Modeler: in a notebook for any competition, use")
    print("           Add Input > Models to attach a model, then save a version.")
    set_status("competition_modeler", "skipped", "needs a model attached in the notebook editor")
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
