# Kaggle Badge Catalog (55 badges)

Reference for the 55 badges the module tracks: how each is earned and what the
scripts do about it. 38 belong to a phase; the other 17 cannot be scripted.

"Earned" in the progress table means the action that earns the badge completed.
The scripts cannot see your Kaggle profile, so check there for the badge itself.

## Phase 1: Instant API (16 badges, 5-10 min)

| Badge | Category | How to Earn | Method |
|-------|----------|-------------|--------|
| Python Coder | Notebooks | Push a Python notebook via API | `kaggle kernels push` |
| R Coder | Notebooks | Push an R notebook via API | `kaggle kernels push` (language=r) |
| API Notebook Creator | Notebooks | Create a notebook using the Kaggle API | `kaggle kernels push` |
| Utility Scripter | Notebooks | Push a utility script (kernel_type=script) | `kaggle kernels push` |
| Code Uploader | Notebooks | Upload code to Kaggle | `kaggle kernels push` |
| Code Forker | Notebooks | Fork an existing public notebook | `kaggle kernels pull` + `push` |
| Code Tagger | Notebooks | Add tags/keywords to a notebook | keywords in kernel-metadata.json |
| Dataset Creator | Datasets | Create a new dataset | `kaggle datasets create` |
| API Dataset Creator | Datasets | Create a dataset via API | `kaggle datasets create` |
| Dataset Tagger | Datasets | Add tags to a dataset | keywords in dataset-metadata.json |
| Dataset Documenter | Datasets | Achieve usability score 10/10 | Full metadata + schema + README |
| Model Creator | Models | Create a new model | `kaggle models create` |
| API Model Creator | Models | Create a model via API | `kaggle models create` |
| Model Variation Creator | Models | Create a model variation | `kaggle models variations create` |
| Model Tagger | Models | Add tags to a model | Manual (model page); the script prints the step |
| Model Documenter | Models | Achieve usability score 10/10 | Full metadata + description + README |

## Phase 2: Competition (7 badges, 10-15 min)

| Badge | Category | How to Earn | Method |
|-------|----------|-------------|--------|
| Competitor | Competitions | Submit to any competition | `kaggle competitions submit` |
| Getting Started Competitor | Competitions | Submit to Getting Started comp | Submit to Titanic |
| Playground Competitor | Competitions | Submit to Playground comp | Find + submit to active playground |
| Community Competitor | Competitions | Submit to Community comp | `kaggle competitions list --group community`, then submit |
| Code Submitter | Competitions | Code-based submission | The script pushes the notebook; submit it from the notebook page |
| Notebook Modeler | Competitions | Notebook that generates submission | Same notebook; submit it from the notebook page |
| Competition Modeler | Competitions | Use model in competition notebook | Manual (attach a model in the notebook editor) |

## Phase 3: Pipeline (3 badges, 15-30 min)

| Badge | Category | How to Earn | Method |
|-------|----------|-------------|--------|
| Dataset Pipeline Creator | Datasets | Create dataset from notebook output | Push notebook → wait → create dataset from output |
| Model Pipeline Creator | Models | Create model from notebook output | Push notebook → wait → create model from output |
| R Markdown Coder | Notebooks | Push R Markdown notebook | `kaggle kernels push` (language=rmarkdown) |

## Phase 4: Browser (8 badges, 5-10 min, manual)

These are earned in the Kaggle web UI. The script prints the steps and marks
each badge as skipped; it does not drive a browser, because it has no
signed-in Kaggle session.

| Badge | Category | How to Earn | Method |
|-------|----------|-------------|--------|
| Stylish | Account | Fill out profile (bio, location) | Manual (profile page) |
| Vampire | Account | Switch to dark theme | Manual (settings) |
| Bookmarker | Community | Bookmark content | Manual (any notebook or dataset page) |
| Collector | Community | Add item to collection | Manual (any notebook or dataset page) |
| GitHub Coder | Notebooks | Link GitHub repo to notebook | Manual (notebook settings) |
| Colab Coder | Notebooks | Open notebook in Colab | Manual (notebook menu) |
| Linked Dataset Creator | Datasets | Create URL-linked dataset | Manual (dataset creation UI) |
| Linked Model Creator | Models | Create externally-linked model | Manual (model creation UI) |

## Phase 5: Streaks (4 badges, multi-day)

The script does today's actions and writes a daily script you can schedule
yourself. The badges stay "attempting" until the streak is complete; run the
orchestrator with `--resume` to do the next day.

| Badge | Category | How to Earn | Duration |
|-------|----------|-------------|----------|
| 7-Day Login Streak | Account | Log in 7 consecutive days | 7 days |
| 30-Day Login Streak | Account | Log in 30 consecutive days | 30 days |
| Submission Streak | Competitions | Submit 7 consecutive days | 7 days |
| Super Submission Streak | Competitions | Submit 30 consecutive days | 30 days |

## Not Automatable (17 badges)

| Badge | Category | Why Not Automatable |
|-------|----------|---------------------|
| Contributor | Community | Requires progression tier (needs community engagement) |
| Expert | Community | Requires progression tier |
| Master | Community | Requires progression tier |
| Grandmaster | Community | Requires progression tier |
| Discussion Starter | Community | Requires upvoted discussion |
| Commentator | Community | Requires upvoted comment |
| Voter | Community | Requires voting on content |
| Sharer | Community | Requires external sharing |
| Course Completer | Community | Requires completing Kaggle Learn course |
| Certificate Earner | Community | Requires earning Kaggle Learn certificate |
| Competition Medal | Competitions | Requires earning a medal (performance-based) |
| Dataset Medal | Datasets | Requires earning a medal (community votes) |
| Notebook Medal | Notebooks | Requires earning a medal (community votes) |
| Team Player | Competitions | Requires joining a competition team |
| Competition Host | Competitions | Requires hosting a competition |
| Simulations Competitor | Competitions | Requires active Simulations competition |
| Featured Competitor | Competitions | Requires Featured competition (often $$$) |

## Summary

| Phase | Badges | Done by the scripts | Time |
|-------|--------|---------------------|------|
| 1 — Instant API | 16 | 15 (Model Tagger is manual) | 5-10 min |
| 2 — Competition | 7 | 4 (three need a step on kaggle.com) | 10-15 min |
| 3 — Pipeline | 3 | 3 | 15-30 min |
| 4 — Browser | 8 | 0 (steps are printed) | 5-10 min |
| 5 — Streaks | 4 | 4, one day at a time | 7-30 days |
| Not automatable | 17 | 0 | — |
| **Total** | **55** | **26** | — |
