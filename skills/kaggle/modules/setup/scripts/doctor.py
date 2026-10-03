#!/usr/bin/env python3
"""Check what is installed, signed in and reachable, and say what works now.

    doctor.py
    doctor.py --verify      also ask Kaggle whether the credential is accepted
    doctor.py --json

Looks at the Python version, the `kaggle` and `kagglehub` packages, the Kaggle
CLI, which credential is configured, and whether Kaggle's hosts and its MCP
server answer. It only reads: nothing is installed, written or changed, and
no credential value is printed.

Run this first when something does not work. Public reads need nothing but
Python and the network; the report says what each missing piece is needed for.

Exit status: 0 every host and the MCP server answer, 1 one of them does not,
2 with --verify when the configured credential is not accepted.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from importlib import metadata
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, kaggle_cli, mcp_client, net, script  # noqa: E402

HOSTS = {
    "www.kaggle.com": "the MCP server and web pages",
    "api.kaggle.com": "the Kaggle CLI and kagglehub",
    "storage.googleapis.com": "file downloads",
}
MINIMUM = {"kaggle": (2, 2, 4), "kagglehub": (1, 0, 2)}
NEEDED_FOR = {
    "kaggle": "downloads, submissions, notebooks and publishing with the Kaggle CLI",
    "kagglehub": "dataset and model download and publishing (the default tool for them)",
}
LABELS = {"api_token": "API token", "legacy_key": "legacy API key", "oauth": "OAuth login"}
NETWORK_TIMEOUT = 10


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _numbers(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_packages() -> dict:
    found = {}
    for name, minimum in MINIMUM.items():
        version = package_version(name)
        found[name] = {
            "version": version,
            "ok": version is not None and _numbers(version) >= minimum,
            "needs": script.PACKAGES[name],
        }
    return found


def check_host(host: str) -> dict:
    """Any HTTP answer means the host can be reached."""
    try:
        response = net.request("GET", f"https://{host}/", timeout=NETWORK_TIMEOUT)
    except net.RequestError as exc:
        return {"ok": False, "detail": exc.detail or exc.kind, "kind": exc.kind}
    return {"ok": True, "detail": f"HTTP {response.status}"}


def check_mcp() -> dict:
    response = mcp_client.mcp_list_tools(timeout=NETWORK_TIMEOUT * 2)
    tools = (response.get("result") or {}).get("tools") if isinstance(response, dict) else None
    if mcp_client.is_error(response) or not isinstance(tools, list):
        return {"ok": False, "detail": "no answer"}
    return {"ok": True, "detail": f"{len(tools)} tools"}


def collect(verify: bool, network: bool) -> dict:
    found = credentials.discover()
    report: dict = {
        "python": {
            "version": ".".join(str(n) for n in sys.version_info[:3]),
            "ok": sys.version_info >= (3, 11),
        },
        "packages": check_packages(),
        "cli": {"path": shutil.which("kaggle") if kaggle_cli.installed() else None},
        "credential": (
            {"kind": found[0].kind, "source": found[0].source, "label": LABELS[found[0].kind]}
            if found
            else None
        ),
        "verified": None,
        "account": None,
        "hosts": None,
        "mcp": None,
    }
    if verify and found:
        ok, account = credentials.verify()
        report["verified"] = ok
        report["account"] = account or None
    if network:
        report["hosts"] = {host: check_host(host) for host in HOSTS}
        report["mcp"] = check_mcp()

    # The commands run the CLI found on PATH, whichever Python it was installed for.
    cli_ready = bool(report["cli"]["path"])
    signed_in = bool(found) and report["verified"] is not False
    # The account reads send a token in credentials.bearer_token's order: the
    # override, an API token or an OAuth login before a legacy key. A legacy key
    # found first does not hide an OAuth login found later.
    has_token = bool(os.environ.get("KAGGLE_MCP_TOKEN", "").strip()) or any(
        credential.kind != "legacy_key" for credential in found
    )
    token_ready = signed_in and has_token
    report["other_credentials"] = [LABELS[c.kind] for c in found[1:]]

    def up(host: str) -> bool:
        return not network or bool(report["hosts"][host]["ok"])

    reachable = not network or bool(report["mcp"] and report["mcp"]["ok"])
    report["works"] = {
        "public_reads": reachable,
        "account_reads": reachable and token_ready,
        # Downloads and the files a submission or an upload sends go through storage.
        "cli_commands": cli_ready
        and signed_in
        and up("api.kaggle.com")
        and up("storage.googleapis.com"),
        "kagglehub_downloads": report["packages"]["kagglehub"]["ok"]
        and up("api.kaggle.com")
        and up("storage.googleapis.com"),
    }
    return report


def _mark(ok: bool | None) -> str:
    return {True: "ok", False: "MISSING", None: "not checked"}[ok]


def print_report(report: dict) -> None:
    rows: list[tuple[str, str, str]] = []
    python = report["python"]
    rows.append(("Python", python["version"], "ok" if python["ok"] else "needs 3.11 or newer"))
    cli = report["cli"]["path"]
    for name, info in report["packages"].items():
        if info["version"] is None and name == "kaggle" and cli:
            state = "not in this Python; the CLI on PATH is what the commands use"
        elif info["version"] is None:
            state = f"not installed: python3 -m pip install '{info['needs']}'"
        elif not info["ok"]:
            state = f"too old: python3 -m pip install --upgrade '{info['needs']}'"
        else:
            state = "ok"
        rows.append((f"{name} package", info["version"] or "-", state))
    rows.append(("Kaggle CLI", cli or "-", "ok" if cli else "not on PATH (comes with kaggle)"))

    credential = report["credential"]
    if credential is None:
        rows.append(("credential", "-", "none found"))
    else:
        if report["verified"] is True:
            who = f" as {report['account']}" if report["account"] else ""
            state = f"accepted by Kaggle{who}"
        elif report["verified"] is False:
            state = "NOT accepted by Kaggle"
        else:
            state = "found; add --verify to ask Kaggle"
        rows.append(("credential", f"{credential['label']} from {credential['source']}", state))
        if report.get("other_credentials"):
            rows.append(("also found", ", ".join(report["other_credentials"]), ""))

    if report["hosts"] is not None:
        for host, result in report["hosts"].items():
            state = "ok" if result["ok"] else f"NOT reachable ({result['detail']})"
            rows.append((host, HOSTS[host], state))
        mcp = report["mcp"]
        rows.append(("Kaggle MCP server", mcp["detail"], "ok" if mcp["ok"] else "NOT reachable"))

    left = max(len(row[0]) for row in rows)
    middle = min(max(len(row[1]) for row in rows), 48)
    for label, value, state in rows:
        print(f"  {label:<{left}}  {value:<{middle}}  {state}")

    works = report["works"]
    print()
    print("What works now:")
    print(
        f"  {_yes(works['public_reads'])}  public reads: brief, pages, solutions, topics, writeup"
    )
    print(
        f"  {_yes(works['account_reads'])}  reads on your account: status, leaderboard, "
        "competitions, details"
    )
    print(
        f"  {_yes(works['cli_commands'])}  downloads, submissions, notebooks, publishing "
        "(Kaggle CLI)"
    )
    print(f"  {_yes(works['kagglehub_downloads'])}  dataset and model downloads with kagglehub")

    hints = []
    if credential is None:
        hints.append(
            "No credential: sign in with `kaggle auth login`, or create an API token at "
            "https://www.kaggle.com/settings and save it in ~/.kaggle/access_token."
        )
    elif credential["kind"] == "legacy_key" and not works["account_reads"]:
        hints.append(
            "The credential is a legacy API key. The Kaggle CLI takes it; Kaggle's MCP server "
            "takes an API token or an OAuth login, so the reads on your account need one of those."
        )
    if report["hosts"] is not None and any(
        result.get("kind") == "certificate" for result in report["hosts"].values()
    ):
        hints.append(net.CERTIFICATE_HINT)
    elif report["hosts"] is not None and not all(r["ok"] for r in report["hosts"].values()):
        hints.append(
            "A host is unreachable: behind a proxy or firewall, allow outbound HTTPS to the "
            "three hosts above."
        )
    for hint in hints:
        print()
        print(hint)


def _yes(value: bool) -> str:
    return "yes" if value else "no "


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check what is installed, signed in and reachable, and say what works now.",
        epilog="Reads only. No credential value is printed.",
    )
    parser.add_argument(
        "--verify", action="store_true", help="Ask Kaggle whether the credential is accepted"
    )
    parser.add_argument("--skip-network", action="store_true", help="Do not contact Kaggle")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args(argv)

    credentials.load_configured_env_file()
    report = collect(args.verify, not args.skip_network)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    if args.verify and report["verified"] is False:
        return script.EXIT_NO_CREDENTIAL
    if report["hosts"] is not None:
        hosts_up = all(result["ok"] for result in report["hosts"].values())
        if not hosts_up or not report["works"]["public_reads"]:
            return script.EXIT_FAILED
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
