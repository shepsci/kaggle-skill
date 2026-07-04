# Changelog

All notable changes to this project are documented in this file.

## 2.4.0 - 2026-07-04

Screencast and docs refresh:

- Re-rendered every demo GIF from its source `.cast` file (the previously
  committed renders were broken 1-frame images).
- Rebuilt the demo casts from verbatim live command output.
- Removed the dead VHS recording pipeline (`docs/demo/demo.tape`); asciinema
  is the only supported recording path.
- Added retrieval QC and a Vesuvius Challenge demo (PR #25): leaderboard
  writeup join/preview with a `--fallback-search` path, a badges self-test
  fix, live retrieval tests, and a Kaggle CLI 2.2.x live test suite.

## 2.3.0 (unreleased milestone)

- Truthfulness audit: dropped overstated claims and synced drifted counts.
- Reorganized modules by workflow instead of by resource type.
- Hardened docs validation.
- Updated platform compatibility documentation.
- Added Antigravity CLI install documentation.
- Added an affiliation disclaimer.
- Added an ARC-AGI writeups cast (later replaced by the Vesuvius demo).

## 2.2.0 (unreleased milestone)

- Refreshed Kaggle CLI docs and plugin distribution.
- Added a direct Claude marketplace install path.
- Added the first README demo casts.
