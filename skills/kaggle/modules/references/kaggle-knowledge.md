# Kaggle Platform Notes

Last checked 2026-09-30.

This page holds what the official docs do not say, or say wrongly, and that
was confirmed by running the tools. For everything else, read the official
page. Do not answer from memory when a page below covers the question.

## Official docs

Every docs page is also served as Markdown: add `.md` to the address.
`https://www.kaggle.com/llms.txt` is an index of them.

| Topic | Page |
|---|---|
| Competitions: types, formats, teams, leaderboards | https://www.kaggle.com/docs/competitions.md |
| Hosting a competition | https://www.kaggle.com/docs/competitions-setup.md |
| Datasets: creating, versions, licenses | https://www.kaggle.com/docs/datasets.md |
| Notebooks: environment, hardware, saving | https://www.kaggle.com/docs/notebooks.md |
| Models: hierarchy, frameworks, publishing | https://www.kaggle.com/docs/models.md |
| Public API | https://www.kaggle.com/docs/api.md |
| MCP server | https://www.kaggle.com/docs/mcp.md |
| Benchmarks | https://www.kaggle.com/docs/benchmarks.md |
| Organizations | https://www.kaggle.com/docs/organizations.md |
| Kaggle Packages (Python packages built from notebooks with `nbdev`) | https://www.kaggle.com/docs/packages.md |
| TPU | https://www.kaggle.com/docs/tpu.md |
| Efficient GPU usage | https://www.kaggle.com/docs/efficient-gpu-usage.md |
| Progression tiers and medals | https://www.kaggle.com/progression |

Tools: [cli-reference.md](cli-reference.md) for the Kaggle CLI,
[mcp-reference.md](mcp-reference.md) for the MCP server.

## Submissions

- **Check the limit in two places.** The rules page and
  `kaggle competitions submission-limits <competition>` can disagree. In one
  competition the rules read "five (10) Submissions per day" and the API
  allowed ten; in another the rules said two and the API said five. Plan on
  the smaller number unless the host has confirmed the larger one.
- **A submission that errors can still use a slot.** The docs do not promise
  otherwise, and at least one host has confirmed that an invalid file counted
  against the daily limit. Validate the file locally first: row count,
  columns, ids, value ranges, and any format rule in the evaluation page.
- **The limit is per team**, not per member.
- **Which submissions count as final** is chosen on the website. No API or
  MCP tool shows or sets the selection.
- **Simulation competitions keep only your latest two submissions in play.**
  A new submission replaces the older of the two instead of adding a third,
  so a weak upload removes a strong agent.
- **Code competitions** score a notebook, not a file. Push the notebook, wait
  for the run, read its log, then submit that version
  (`kaggle competitions submit <competition> -f submission.csv -k
  owner/notebook -v <version> -m "message"`). See
  [competition-operations.md](../competitions/references/competition-operations.md).
- There is no command to accept competition rules. It is done on kaggle.com,
  and until it is done, downloads and submissions are refused.

## Notebooks and quota

- **The GPU quota is for the whole account.** The weekly hours shown by
  `kaggle quota` are shared by every project that uses the account. Check
  before a long run.
- **Two GPU batch runs at a time.** A third push fails with `Kernel push
  error: Maximum batch GPU session count of 2 reached.`, and the CLI still
  exits with status 0.
- **Pushing runs.** With CLI 2.2.4 there is no way to save a version without
  running it.
- **A notebook's public score, best score, runtime, and license are on its
  web page only.** `kaggle kernels list --sort-by scoreDescending` orders by
  score, and the order matches the website, but the score value is not in the
  CLI output, the API, or the MCP `search_notebooks` tool.
- Accelerator ids for `kaggle kernels push --accelerator`, from the CLI docs
  in September 2026: `NvidiaTeslaT4` (two T4s, the default GPU),
  `NvidiaTeslaA100`, `NvidiaL4`, `NvidiaL4X1`, `NvidiaH100`,
  `NvidiaRtxPro6000`, `TpuV5E8` (the default TPU), `TpuV6E8`. Retired:
  `NvidiaTeslaP100`, `TpuV38`, `Tpu1VmV38`. Availability depends on the
  account and the competition.
- Hardware sizes, session lengths, and weekly hours change. Read the
  notebooks page and `kaggle quota` instead of quoting numbers.

## Models

- Four parts name a variation: `owner/model/framework/variation`. A fifth
  part is the version number.
- `kagglehub.model_download` takes four parts (latest version) or five.
  `kaggle models variations versions download` needs all five.
- Creating a variation uploads the files as its version 1.
- In a notebook, an attached model is under
  `/kaggle/input/<model>/<framework>/<variation>/<version>/`.

## kagglehub

Checked with `kagglehub` 1.0.2 (Python 3.10 or later).

| Function | Arguments |
|---|---|
| `dataset_download`, `model_download`, `competition_download`, `notebook_output_download` | `handle`, `path=None`, `force_download=False`, `output_dir=None` |
| `dataset_upload` | `handle`, `local_dataset_dir`, `version_notes=""`, `ignore_patterns=None` |
| `model_upload` | `handle`, `local_model_dir`, `license_name=None`, `version_notes=""`, `ignore_patterns=None`, `sigstore=False` |
| `dataset_load` | `adapter`, `handle`, `path`, plus adapter options |
| `package_import` | `handle`, `force_download=False`, `bypass_confirmation=False` |
| `utility_script_install` | `handle`, `force_download=False` |
| `login`, `whoami` | sign in, show the account |

- `dataset_upload` has no `license_name` argument. Passing one raises
  `TypeError`. Set the license in the dataset's settings on kaggle.com.
- Uploads send everything in the folder except `ignore_patterns`. Check the
  folder for credential files first. `.git` is left out at any depth; `.cache`
  and `.huggingface` only at the top of the folder.
- With `output_dir`, a repeated download with `force_download=True` first
  deletes everything in that folder. Never point it at a folder that holds
  other files.
- kagglehub cannot push or run notebooks, submit to a competition, or work
  with benchmarks. Use the Kaggle CLI for those.
- Public datasets and models download without a credential.
- Releases before 1.0.2 extracted tar archives without a path check. Use
  1.0.2 or later.

## Credentials and OAuth

- Token kinds: an API token starts with `KGAT_`; an OAuth refresh token
  starts with `KGRT_`; OAuth access tokens have no fixed prefix. A legacy key
  is 32 hex characters and comes with a username.
- Kaggle's OAuth server advertises one scope, `resources.admin:*`, at
  `https://www.kaggle.com/.well-known/oauth-authorization-server`. There is
  no narrower or broader scope to ask for. Clients can register themselves at
  the registration endpoint listed there.
- A credential that exists is not always valid. A revoked key still sits in
  `kaggle.json`, and `kaggle config view` still accepts it. `kaggle quota`
  fails for it, because that call needs a signed-in account.
- With a revoked key, calls that also work anonymously return empty results
  instead of an error.
- With `VERBOSE` or `VERBOSE_OUTPUT` set, the CLI prints request headers,
  including the bearer token.

## Account checks done on kaggle.com

- Phone verification unlocks GPU, TPU, and internet access in notebooks.
- Some competitions require identity verification before prizes or
  submissions.
- Accepting competition rules, joining a team, and choosing final
  submissions.

None of these has an API. Tell the user what to do on the website.

## Writeups

- No tool creates or edits a Kaggle Writeup. That is done in the browser.
- Published writeups are public: `get_writeup` needs no credential.
- A hackathon's roster of writeups is limited to its hosts, judges, and
  teammates.
