"""Shared utilities for the badge collector."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Rate limiting: seconds between API calls
API_DELAY = 5

# Prefix for all created resources
RESOURCE_PREFIX = "badge-collector-"

# Skill root: 3 levels up from modules/badge-collector/scripts/utils.py
SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
KLLM_SCRIPTS = SKILL_ROOT / "modules" / "kllm" / "scripts"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def get_username() -> str:
    """Get the Kaggle username from env or kaggle.json."""
    username = os.getenv("KAGGLE_USERNAME")
    if username:
        return username
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        creds = json.loads(kaggle_json.read_text())
        return creds.get("username", "")
    return ""


def get_kaggle_cli() -> str:
    """Find the kaggle CLI binary."""
    # Check common locations
    for path in [
        shutil.which("kaggle"),
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/kaggle",
        str(Path.home() / ".local" / "bin" / "kaggle"),
    ]:
        if path and Path(path).exists():
            return path
    return "kaggle"  # fallback, hope it's on PATH


def run_kaggle_cli(args: list[str], check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a kaggle CLI command with rate limiting."""
    cli = get_kaggle_cli()
    cmd = [cli] + args
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        print(f"  [STDERR] {result.stderr.strip()}")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    time.sleep(API_DELAY)
    return result


def make_temp_dir(suffix: str = "") -> Path:
    """Create a temporary directory under badge-tmp/."""
    tmp_base = SKILL_ROOT / "badge-tmp"
    tmp_base.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=RESOURCE_PREFIX, suffix=suffix, dir=tmp_base))


def check_credentials() -> bool:
    """Verify Kaggle credentials are configured."""
    script = KLLM_SCRIPTS / "check_credentials.py"
    if script.exists():
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
        )
        print(result.stdout.strip())
        return result.returncode == 0
    # Fallback: check credential sources directly (priority order)
    access_token = Path.home() / ".kaggle" / "access_token"
    if access_token.exists():
        return True
    if os.getenv("KAGGLE_API_TOKEN"):
        return True
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return True
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    return kaggle_json.exists()


def resource_name(kind: str, suffix: str = "") -> str:
    """Generate a unique resource name with prefix."""
    ts = int(time.time())
    name = f"{RESOURCE_PREFIX}{kind}-{ts}"
    if suffix:
        name += f"-{suffix}"
    return name


def slug(name: str) -> str:
    """Convert a name to a Kaggle-compatible slug."""
    return name.lower().replace(" ", "-").replace("_", "-")
