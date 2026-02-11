from typing import Optional
"""Registry of all 59 Kaggle badges with metadata.

Each badge has:
  - id: unique identifier
  - name: display name
  - tier: bronze/silver/gold/platinum or None
  - category: notebooks/datasets/models/competitions/community/account
  - phase: which automation phase can earn it (1-5, or None if not automatable)
  - description: how to earn it
  - automatable: whether the badge collector can earn it
"""

from dataclasses import dataclass


@dataclass
class Badge:
    id: str
    name: str
    category: str
    phase: Optional[int]
    description: str
    automatable: bool
    tier: Optional[str] = None


# fmt: off
ALL_BADGES: list[Badge] = [
    # ── Phase 1: Instant API badges (~20) ──────────────────────────────────

    # Notebooks
    Badge("python_coder", "Python Coder", "notebooks", 1,
          "Push a Python notebook via API", True),
    Badge("r_coder", "R Coder", "notebooks", 1,
          "Push an R notebook via API", True),
    Badge("api_notebook_creator", "API Notebook Creator", "notebooks", 1,
          "Create a notebook using the Kaggle API", True),
    Badge("utility_scripter", "Utility Scripter", "notebooks", 1,
          "Push a utility script (not a notebook) via API", True),
    Badge("code_uploader", "Code Uploader", "notebooks", 1,
          "Upload code to Kaggle", True),
    Badge("code_forker", "Code Forker", "notebooks", 1,
          "Fork an existing public notebook", True),
    Badge("code_tagger", "Code Tagger", "notebooks", 1,
          "Add tags to a notebook", True),

    # Datasets
    Badge("dataset_creator", "Dataset Creator", "datasets", 1,
          "Create a new dataset", True),
    Badge("api_dataset_creator", "API Dataset Creator", "datasets", 1,
          "Create a dataset using the Kaggle API", True),
    Badge("dataset_tagger", "Dataset Tagger", "datasets", 1,
          "Add tags to a dataset", True),
    Badge("dataset_documenter", "Dataset Documenter", "datasets", 1,
          "Achieve usability score 10/10 on a dataset", True),

    # Models
    Badge("model_creator", "Model Creator", "models", 1,
          "Create a new model", True),
    Badge("api_model_creator", "API Model Creator", "models", 1,
          "Create a model using the Kaggle API", True),
    Badge("model_variation_creator", "Model Variation Creator", "models", 1,
          "Create a model variation/instance", True),
    Badge("model_tagger", "Model Tagger", "models", 1,
          "Add tags to a model", True),
    Badge("model_documenter", "Model Documenter", "models", 1,
          "Achieve usability score 10/10 on a model", True),

    # ── Phase 2: Competition badges (~7) ───────────────────────────────────

    Badge("competitor", "Competitor", "competitions", 2,
          "Submit to any competition", True),
    Badge("getting_started_competitor", "Getting Started Competitor", "competitions", 2,
          "Submit to a Getting Started competition", True),
    Badge("playground_competitor", "Playground Competitor", "competitions", 2,
          "Submit to a Playground competition", True),
    Badge("community_competitor", "Community Competitor", "competitions", 2,
          "Submit to a Community competition", True),
    Badge("code_submitter", "Code Submitter", "competitions", 2,
          "Make a code-based submission to a competition", True),
    Badge("notebook_modeler", "Notebook Modeler", "competitions", 2,
          "Create a notebook that generates a competition submission", True),
    Badge("competition_modeler", "Competition Modeler", "competitions", 2,
          "Use a model in a competition notebook", True),

    # ── Phase 3: Pipeline badges (~3) ──────────────────────────────────────

    Badge("dataset_pipeline_creator", "Dataset Pipeline Creator", "datasets", 3,
          "Create a dataset from notebook output", True),
    Badge("model_pipeline_creator", "Model Pipeline Creator", "models", 3,
          "Create a model from notebook output", True),
    Badge("r_markdown_coder", "R Markdown Coder", "notebooks", 3,
          "Push and execute an R Markdown notebook on KKB", True),

    # ── Phase 4: Browser badges (~8) ──────────────────────────────────────

    Badge("stylish", "Stylish", "account", 4,
          "Fill out your Kaggle profile (bio, location, etc.)", True),
    Badge("vampire", "Vampire", "account", 4,
          "Switch to dark theme", True),
    Badge("bookmarker", "Bookmarker", "community", 4,
          "Bookmark a notebook, dataset, or competition", True),
    Badge("collector", "Collector", "community", 4,
          "Add an item to a collection", True),
    Badge("github_coder", "GitHub Coder", "notebooks", 4,
          "Link a GitHub repo to a notebook", True),
    Badge("colab_coder", "Colab Coder", "notebooks", 4,
          "Open a Kaggle notebook in Google Colab", True),
    Badge("linked_dataset_creator", "Linked Dataset Creator", "datasets", 4,
          "Create a dataset linked to a URL source", True),
    Badge("linked_model_creator", "Linked Model Creator", "models", 4,
          "Create a model linked to an external source", True),

    # ── Phase 5: Streak badges (~4) ───────────────────────────────────────

    Badge("seven_day_login_streak", "7-Day Login Streak", "account", 5,
          "Log in for 7 consecutive days", True),
    Badge("thirty_day_login_streak", "30-Day Login Streak", "account", 5,
          "Log in for 30 consecutive days", True),
    Badge("submission_streak", "Submission Streak", "competitions", 5,
          "Submit to competitions for 7 consecutive days", True),
    Badge("super_submission_streak", "Super Submission Streak", "competitions", 5,
          "Submit to competitions for 30 consecutive days", True),

    # ── Not automatable badges (~17) ──────────────────────────────────────

    Badge("contributor", "Contributor", "community", None,
          "Reach Contributor progression tier", False),
    Badge("expert", "Expert", "community", None,
          "Reach Expert progression tier", False),
    Badge("master", "Master", "community", None,
          "Reach Master progression tier", False),
    Badge("grandmaster", "Grandmaster", "community", None,
          "Reach Grandmaster progression tier", False),
    Badge("discussion_starter", "Discussion Starter", "community", None,
          "Start a discussion that gets upvoted", False),
    Badge("commentator", "Commentator", "community", None,
          "Post a comment that gets upvoted", False),
    Badge("voter", "Voter", "community", None,
          "Upvote content on Kaggle", False),
    Badge("sharer", "Sharer", "community", None,
          "Share a notebook or dataset externally", False),
    Badge("course_completer", "Course Completer", "community", None,
          "Complete a Kaggle Learn course", False),
    Badge("certificate_earner", "Certificate Earner", "community", None,
          "Earn a Kaggle Learn certificate", False),
    Badge("competition_medal", "Competition Medal", "competitions", None,
          "Earn a medal in a competition", False),
    Badge("dataset_medal", "Dataset Medal", "datasets", None,
          "Earn a medal on a dataset", False),
    Badge("notebook_medal", "Notebook Medal", "notebooks", None,
          "Earn a medal on a notebook", False),
    Badge("team_player", "Team Player", "competitions", None,
          "Join a competition team", False),
    Badge("competition_host", "Competition Host", "competitions", None,
          "Host a competition", False),
    Badge("simulations_competitor", "Simulations Competitor", "competitions", None,
          "Submit to a Simulations competition", False),
    Badge("featured_competitor", "Featured Competitor", "competitions", None,
          "Submit to a Featured competition", False),
]
# fmt: on


def get_badges_by_phase(phase: int) -> list[Badge]:
    """Get all badges for a specific phase."""
    return [b for b in ALL_BADGES if b.phase == phase]


def get_automatable_badges() -> list[Badge]:
    """Get all badges that can be automated."""
    return [b for b in ALL_BADGES if b.automatable]


def get_badge_by_id(badge_id: str) -> Optional['Badge']:
    """Look up a badge by ID."""
    for b in ALL_BADGES:
        if b.id == badge_id:
            return b
    return None
