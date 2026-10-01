"""Shared utilities for the badges workflow."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Rate limiting: seconds between API calls
API_DELAY = 5

# Prefix for all created resources
RESOURCE_PREFIX = "kaggle-badges-"

# Skill root: skills/kaggle
SKILL_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = SKILL_ROOT.parent.parent
SETUP_SCRIPTS = SKILL_ROOT / "modules" / "setup" / "scripts"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Where progress and scratch files go. The default is the skill folder, as in
# earlier releases. Set KAGGLE_BADGES_STATE_DIR to keep them somewhere else,
# for example when the skill is installed in a read-only plugin cache.
_STATE_OVERRIDE = os.environ.get("KAGGLE_BADGES_STATE_DIR", "")
STATE_DIR = Path(_STATE_OVERRIDE).expanduser() if _STATE_OVERRIDE else SKILL_ROOT

sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, kaggle_cli, untrusted  # noqa: E402

credentials.load_configured_env_file()


def get_username() -> str:
    """Kaggle username from the shared credential resolver."""
    return credentials.username()


def get_kaggle_cli() -> str:
    """Path of the kaggle CLI binary."""
    return kaggle_cli.kaggle_bin()


def run_kaggle_cli(
    args: list[str], check: bool = True, timeout: int = 120
) -> subprocess.CompletedProcess:
    """Run a kaggle CLI command with rate limiting.

    The CLI runs through the shared runner, so a failure it reports with exit
    status 0 ("Kernel push error: ...") comes back as a non-zero return code
    and raises when ``check`` is set. A badge is never recorded from a command
    that did not succeed.
    """
    print(f"  $ kaggle {' '.join(args)}")
    result = kaggle_cli.run(args, timeout=timeout)
    if check and result.returncode != 0:
        show_cli_output(result)
        raise subprocess.CalledProcessError(
            result.returncode, ["kaggle", *args], result.stdout, result.stderr
        )
    time.sleep(API_DELAY)
    return result


def show_cli_output(result: subprocess.CompletedProcess) -> None:
    """Print what the CLI said about a failure. The text comes from Kaggle, so it is wrapped."""
    message = (
        result.stderr.strip() or kaggle_cli.find_failure(result.stdout) or result.stdout.strip()
    )
    with untrusted.Block(source="kaggle-cli", tool="badges") as block:
        block.write(message[:500] or "(no output)")


def kernel_status(kernel: str) -> str:
    """Status word of a notebook run, e.g. COMPLETE, RUNNING, ERROR. '' if unknown."""
    result = kaggle_cli.run(["kernels", "status", kernel], timeout=120)
    if result.returncode != 0:
        return ""
    marker = ' has status "'
    for line in reversed(result.stdout.splitlines()):
        if marker in line:
            status = line.split(marker, 1)[1].split('"', 1)[0]
            return status.rsplit(".", 1)[-1].upper()
    return ""


def make_temp_dir(suffix: str = "") -> Path:
    """Create a temporary directory under badge-tmp/."""
    tmp_base = STATE_DIR / "badge-tmp"
    tmp_base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=RESOURCE_PREFIX, suffix=suffix, dir=tmp_base))


def check_credentials() -> bool:
    """True when a Kaggle credential is configured. Reads only; writes nothing."""
    found = credentials.discover()
    if not found:
        print("No Kaggle credentials found.")
        return False
    print(f"Kaggle credentials found: {found[0].kind} from {found[0].source}")
    return True


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
