"""Phase 4: Badges earned in the Kaggle web UI (8 badges).

These badges come from actions on kaggle.com: filling in a profile, switching
theme, bookmarking, and so on. They need a browser that is signed in to
Kaggle, which API credentials do not give, so this phase prints the steps and
marks each badge as skipped. Nothing here changes the account.
"""

from __future__ import annotations

from badge_tracker import set_status, should_attempt

MANUAL = "manual step on kaggle.com"

# (badge id, badge name, what to do)
MANUAL_STEPS: list[tuple[str, str, str]] = [
    (
        "stylish",
        "Stylish",
        "Go to https://www.kaggle.com/settings and fill in your bio, location, "
        "occupation, and organization.",
    ),
    ("vampire", "Vampire", "Go to https://www.kaggle.com/settings and switch to the dark theme."),
    (
        "bookmarker",
        "Bookmarker",
        "Open any notebook, dataset, or competition and click the bookmark icon.",
    ),
    (
        "collector",
        "Collector",
        "Open any notebook or dataset, open the '...' menu, and choose 'Add to collection'.",
    ),
    (
        "github_coder",
        "GitHub Coder",
        "Create a notebook on Kaggle and link a GitHub repository in its settings.",
    ),
    (
        "colab_coder",
        "Colab Coder",
        "Open any notebook, open the '...' menu, and choose 'Open in Google Colab'.",
    ),
    (
        "linked_dataset_creator",
        "Linked Dataset Creator",
        "Go to https://www.kaggle.com/datasets/new and create a dataset from a URL "
        "instead of uploading files.",
    ),
    (
        "linked_model_creator",
        "Linked Model Creator",
        "Go to https://www.kaggle.com/models/new and create a model linked to an external source.",
    ),
]


def run(username: str) -> tuple[int, int]:
    """Print the manual step for each badge. Returns (attempted, succeeded)."""
    attempted = 0
    for badge_id, name, steps in MANUAL_STEPS:
        if not should_attempt(badge_id):
            continue
        attempted += 1
        print(f"\n  [MANUAL] {name}:")
        print(f"  {steps}")
        set_status(badge_id, "skipped", MANUAL)
    return attempted, 0
