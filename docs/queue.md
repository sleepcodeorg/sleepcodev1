# SleepCode Task Queue & Night Runner Guide

SleepCode allows you to queue coding tasks throughout the day and execute them overnight while you sleep.

---

## 1. Task Queue Management

The task queue is stored safely in a local SQLite database at `~/.sleepcode/sleepcode.db`.

### Adding a Task
```bash
sleepcode queue add "Fix failing unit tests in test_auth.py" --repo ~/projects/myapp --budget-usd 1.50
```
- **Repository check:** The target `--repo` must exist, be a valid Git repository, and have a clean working tree (`git status` clean).

### Listing Queued Tasks
```bash
sleepcode queue list
sleepcode queue list --status queued
```

### Displaying Task Details
```bash
sleepcode queue show 1
```

### Cancelling a Task
```bash
sleepcode queue cancel 1
```
*Note: Only `queued` tasks can be cancelled. Running or finished tasks cannot be cancelled from the queue command.*

### Retrying Failed Tasks
```bash
sleepcode queue retry 1
```
*Note: Retry works on `failed` or `needs_review` tasks by creating a new run entry without editing historical run records.*

---

## 2. Overnight Execution (`sleepcode night start`)

Run the overnight runner during your sleep window:

```bash
sleepcode night start --window 23:00-07:00 --budget-usd 5.00
```

### Safety and Isolation Controls
- **Branch Isolation:** Every task executes on a dedicated git task branch (`sleepcode/<slug>-<timestamp>`). SleepCode **never** commits directly to `main` or `master`.
- **Zero Push:** SleepCode never pushes code to remote repositories.
- **Secret Guards:** Before staging changes, SleepCode blocks commits if forbidden secret files (e.g. `.env`, `*.pem`, `*.key`, `*secret*`) are modified.
- **Branch Restoration:** After completing or pausing a task, SleepCode restores your original git working branch.
- **Budget Limits:** Stops execution when the task budget or night total budget is reached.

---

## 3. Morning Reports

Review the outcome of the overnight session every morning:

```bash
sleepcode report --latest
```

Reports are saved to `~/.sleepcode/reports/YYYY-MM-DD.md` in plain English, summarizing completed work, file changes, test results, and next steps for review.
