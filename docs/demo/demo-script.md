# Demo Script for the README Screencast

The README demo is recorded after the documentation has been refreshed.
Re-record after material install, credential, or workflow changes.

## Goal of the demo

Show the current v2.3.0 experience in 60-90 seconds:

1. Install `kaggle@shepsci` from the Claude marketplace command surface.
2. Verify Kaggle credentials without displaying secrets.
3. Summarize the Titanic competition pages.
4. Retrieve recent Kaggle discussion/writeup content.

## Setup before recording

```bash
# Fresh Claude Code local plugin state with no kaggle plugin installed.
# Have a valid Kaggle API token available before recording, but do not paste
# or print the token during the cast.
# Use at least 100 columns x 30 rows for legibility.
asciinema --version
```

If credentials are already present in `~/.kaggle/access_token` or
`KAGGLE_API_TOKEN`, the demo should show only the verification result.

## Recording commands used in the cast

These are the commands shown in the cast:

```bash
claude plugin marketplace add shepsci/claude-marketplace --scope local
claude plugin marketplace update shepsci
claude plugin install kaggle@shepsci --scope local

python3 skills/kaggle/shared/check_all_credentials.py

python3 skills/kaggle/modules/kllm/scripts/list_competition_pages.py \
  --competition titanic --summary

export PATH="<kaggle-2.2.3-venv>/bin:$PATH"
kaggle --version
python3 skills/kaggle/modules/kllm/scripts/cli_forums.py forum-topics \
  --category competition_write_ups --sort-by recent --page-size 3 --format json
```

Keep the terminal focused on confirmations, summaries, and short wrapped
Kaggle-supplied snippets. Do not scroll through full forum/writeup bodies in
the cast.

## Recording with asciinema

```bash
cd ~/work/kaggle-skill
bash docs/demo/record.sh
```

After recording:

```bash
asciinema cat docs/demo/install-and-demo.cast
asciinema upload docs/demo/install-and-demo.cast
```

Use the returned cast id in the README demo badge:

```markdown
[![asciicast](https://asciinema.org/a/<cast-id>.svg)](https://asciinema.org/a/<cast-id>)
```

Use an authenticated asciinema CLI for a permanent public URL. Anonymous
uploads may expire; the source `.cast` file should still be committed so the
demo can be replayed or re-uploaded.

Before committing the cast, scan it for secrets:

```bash
rg -n "KGAT_|KAGGLE_API_TOKEN|access_token|kaggle\\.json|\"key\"|\"username\"" \
  docs/demo/install-and-demo.cast
```

The scan should return no credential material. Mentions of safe file names in
documentation text are acceptable only outside the committed cast.

## Recording with vhs

VHS is retained as an optional future GIF/MP4 path. The issue #7 artifact is
the asciinema cast.

```bash
cd ~/work/kaggle-skill/docs/demo
vhs demo.tape
```
