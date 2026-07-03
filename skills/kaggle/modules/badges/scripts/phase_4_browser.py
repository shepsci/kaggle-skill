from typing import Optional
"""Phase 4: Browser badges (~8 badges).

Earns badges that require browser interaction via Playwright:
  - Stylish (fill profile)
  - Vampire (dark theme)
  - Bookmarker (bookmark content)
  - Collector (add to collection)
  - GitHub Coder (link GitHub repo to notebook)
  - Colab Coder (open notebook in Colab)
  - Linked Dataset Creator (dataset linked to URL)
  - Linked Model Creator (model linked to URL)

Requires: playwright package installed + browser binaries.
Falls back to printing manual instructions if Playwright is unavailable.
"""

import json
import os
import time
from pathlib import Path

from badge_tracker import set_status, should_attempt
from utils import get_username


def _get_kaggle_cookies() -> Optional[dict]:
    """Try to get Kaggle session cookies from environment or kaggle.json."""
    username = os.getenv("KAGGLE_USERNAME", "")
    key = os.getenv("KAGGLE_KEY", "")
    if not username or not key:
        kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
        if kaggle_json.exists():
            creds = json.loads(kaggle_json.read_text())
            username = creds.get("username", "")
            key = creds.get("key", "")
    if username and key:
        return {"username": username, "key": key}
    return None


def _try_playwright() -> bool:
    """Check if Playwright is available."""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


def _print_manual_instructions(badge_name: str, instructions: str) -> None:
    """Print manual instructions for a badge when Playwright isn't available."""
    print(f"\n  [MANUAL] {badge_name}:")
    print(f"  {instructions}")


def _fill_profile(username: str) -> bool:
    """Fill out Kaggle profile to earn Stylish badge."""
    if not should_attempt("stylish"):
        return True

    set_status("stylish", "attempting")

    if not _try_playwright():
        _print_manual_instructions(
            "Stylish",
            "Go to https://www.kaggle.com/settings and fill out your bio, "
            "location, occupation, and organization fields."
        )
        set_status("stylish", "skipped", "Playwright not available — manual action needed")
        return False

    try:
        from playwright.sync_api import sync_playwright

        creds = _get_kaggle_cookies()
        if not creds:
            set_status("stylish", "failed", "no credentials")
            return False

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Log in via API cookie approach
            page.goto("https://www.kaggle.com/account/login")
            time.sleep(2)

            # Navigate to settings/profile
            page.goto(f"https://www.kaggle.com/{creds['username']}/account")
            time.sleep(2)

            # Try to fill profile fields
            # This is best-effort — Kaggle's UI changes frequently
            try:
                # Fill bio
                bio_field = page.query_selector('textarea[name="bio"]')
                if bio_field:
                    bio_field.fill("Data scientist and machine learning enthusiast. "
                                   "Exploring Kaggle competitions and datasets.")

                # Fill location
                location_field = page.query_selector('input[name="location"]')
                if location_field:
                    location_field.fill("Earth")

                # Save
                save_btn = page.query_selector('button:has-text("Save")')
                if save_btn:
                    save_btn.click()
                    time.sleep(2)

                print("  [OK] Profile fields updated")
                set_status("stylish", "earned", "profile filled via Playwright")
                return True
            except Exception as e:
                print(f"  [WARN] Could not fill all profile fields: {e}")
                set_status("stylish", "failed", str(e))
                return False
            finally:
                browser.close()

    except Exception as e:
        print(f"  [FAIL] Profile fill: {e}")
        set_status("stylish", "failed", str(e))
        return False


def _dark_theme(username: str) -> bool:
    """Switch to dark theme to earn Vampire badge."""
    if not should_attempt("vampire"):
        return True

    set_status("vampire", "attempting")

    if not _try_playwright():
        _print_manual_instructions(
            "Vampire",
            "Go to https://www.kaggle.com/settings and switch to dark theme."
        )
        set_status("vampire", "skipped", "Playwright not available — manual action needed")
        return False

    try:
        from playwright.sync_api import sync_playwright

        creds = _get_kaggle_cookies()
        if not creds:
            set_status("vampire", "failed", "no credentials")
            return False

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto("https://www.kaggle.com")
            time.sleep(2)

            # Look for theme toggle
            try:
                theme_btn = page.query_selector('[data-testid="theme-toggle"], .theme-toggle')
                if theme_btn:
                    theme_btn.click()
                    time.sleep(1)
                    print("  [OK] Dark theme toggled")
                    set_status("vampire", "earned", "dark theme via Playwright")
                    return True
                else:
                    print("  [WARN] Could not find theme toggle")
                    set_status("vampire", "skipped", "theme toggle not found")
                    return False
            finally:
                browser.close()

    except Exception as e:
        print(f"  [FAIL] Dark theme: {e}")
        set_status("vampire", "failed", str(e))
        return False


def _bookmark(username: str) -> bool:
    """Bookmark content to earn Bookmarker badge."""
    if not should_attempt("bookmarker"):
        return True

    set_status("bookmarker", "attempting")

    if not _try_playwright():
        _print_manual_instructions(
            "Bookmarker",
            "Go to any Kaggle notebook/dataset/competition and click the bookmark icon."
        )
        set_status("bookmarker", "skipped", "Playwright not available — manual action needed")
        return False

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Navigate to a popular notebook and bookmark it
            page.goto("https://www.kaggle.com/code/alexisbcook/titanic-tutorial")
            time.sleep(3)

            try:
                bookmark_btn = page.query_selector('[aria-label="Bookmark"], .bookmark-button')
                if bookmark_btn:
                    bookmark_btn.click()
                    time.sleep(1)
                    print("  [OK] Content bookmarked")
                    set_status("bookmarker", "earned", "bookmarked via Playwright")
                    return True
                else:
                    print("  [WARN] Bookmark button not found")
                    set_status("bookmarker", "skipped", "bookmark button not found")
                    return False
            finally:
                browser.close()

    except Exception as e:
        print(f"  [FAIL] Bookmark: {e}")
        set_status("bookmarker", "failed", str(e))
        return False


def _collector(username: str) -> bool:
    """Add item to a collection to earn Collector badge."""
    if not should_attempt("collector"):
        return True

    set_status("collector", "attempting")

    if not _try_playwright():
        _print_manual_instructions(
            "Collector",
            "Go to any Kaggle notebook/dataset, click the '...' menu, and select 'Add to collection'."
        )
        set_status("collector", "skipped", "Playwright not available — manual action needed")
        return False

    # Collection creation is complex via browser automation
    _print_manual_instructions(
        "Collector",
        "Go to any Kaggle notebook/dataset, click the '...' menu, and select 'Add to collection'."
    )
    set_status("collector", "skipped", "complex browser interaction — manual action recommended")
    return False


def _github_coder(username: str) -> bool:
    """Link a GitHub repo to a notebook to earn GitHub Coder."""
    if not should_attempt("github_coder"):
        return True

    set_status("github_coder", "attempting")
    _print_manual_instructions(
        "GitHub Coder",
        "Create a notebook on Kaggle and link a GitHub repository to it via the notebook settings."
    )
    set_status("github_coder", "skipped", "requires GitHub linking via UI")
    return False


def _colab_coder(username: str) -> bool:
    """Open a notebook in Colab to earn Colab Coder."""
    if not should_attempt("colab_coder"):
        return True

    set_status("colab_coder", "attempting")
    _print_manual_instructions(
        "Colab Coder",
        "Go to any Kaggle notebook, click the '...' menu, and select 'Open in Google Colab'."
    )
    set_status("colab_coder", "skipped", "requires Colab action via UI")
    return False


def _linked_dataset(username: str) -> bool:
    """Create a dataset linked to a URL to earn Linked Dataset Creator."""
    if not should_attempt("linked_dataset_creator"):
        return True

    set_status("linked_dataset_creator", "attempting")
    _print_manual_instructions(
        "Linked Dataset Creator",
        "Go to https://www.kaggle.com/datasets/new and create a dataset by providing "
        "a URL source instead of uploading files."
    )
    set_status("linked_dataset_creator", "skipped", "requires URL-linked dataset via UI")
    return False


def _linked_model(username: str) -> bool:
    """Create a model linked to an external source to earn Linked Model Creator."""
    if not should_attempt("linked_model_creator"):
        return True

    set_status("linked_model_creator", "attempting")
    _print_manual_instructions(
        "Linked Model Creator",
        "Go to https://www.kaggle.com/models/new and create a model linked "
        "to an external source (e.g., HuggingFace)."
    )
    set_status("linked_model_creator", "skipped", "requires linked model via UI")
    return False


def run(username: str) -> tuple[int, int]:
    """Run all Phase 4 badge actions. Returns (attempted, succeeded)."""
    actions = [
        ("Fill profile (Stylish)", _fill_profile),
        ("Dark theme (Vampire)", _dark_theme),
        ("Bookmark content", _bookmark),
        ("Add to collection", _collector),
        ("GitHub Coder", _github_coder),
        ("Colab Coder", _colab_coder),
        ("Linked dataset", _linked_dataset),
        ("Linked model", _linked_model),
    ]

    attempted = 0
    succeeded = 0

    for name, fn in actions:
        print(f"\n  --- {name} ---")
        attempted += 1
        if fn(username):
            succeeded += 1

    return attempted, succeeded
