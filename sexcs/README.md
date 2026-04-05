---
title: sec-quest
emoji: 🔍
colorFrom: red
colorTo: orange
sdk: docker
pinned: false
license: apache-2.0
tags:
  - openenv
  - reinforcement-learning
  - code-review
  - security
  - agentic
---

# 🔍 sec-quest — PR Code Review RL Environment

**sec-quest** is an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) reinforcement learning environment where an AI agent acts as a **senior code reviewer**.

The agent is shown a code diff (Pull Request) containing **deliberately planted bugs** — security vulnerabilities, logic errors, race conditions, performance problems, and code smells. It must identify them, classify each one, and submit structured review comments. It is scored on **coverage** (did it find all bugs?) and **precision** (did it avoid false positives?).

> Built for the Meta × PyTorch × Hugging Face OpenEnv Hackathon.

---

## 🎯 Motivation

Code review is one of the highest-leverage activities in software engineering. Every team does it daily, and catching a critical security bug before it ships can prevent disasters. This environment trains and evaluates agents on the exact skill senior engineers use: reading diffs, spotting subtle bugs, and communicating findings clearly.

---

## 📁 Project Structure

```
sec-quest/
├── __init__.py              # Package exports
├── models.py                # Pydantic: ReviewAction, ReviewObservation
├── client.py                # SecQuestEnv(EnvClient) — connect from training code
├── inference.py             # ⭐ Mandatory baseline inference script
├── openenv.yaml             # Environment manifest
├── pyproject.toml           # Dependencies
├── Dockerfile               # Container definition
├── .dockerignore
├── .gitignore
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI app (via openenv create_app)
    ├── environment.py       # SecQuestEnvironment(Environment) — core logic
    ├── grader.py            # Deterministic scoring engine
    ├── tasks.py             # 3 tasks with diffs + bug manifests
    └── requirements.txt     # Docker dependencies
```

---

## 🗂️ Tasks

| Task | Name | Lines | Bugs Planted | Difficulty |
|------|------|-------|--------------|------------|
| `easy` | Rookie Review | ~30 | 2 | ⭐ Easy |
| `medium` | Mid-Level Review | ~80 | 4 | ⭐⭐ Medium |
| `hard` | Staff Engineer Review | ~130 | 5 | ⭐⭐⭐ Hard |

### Task 1 — Easy: Rookie Review
A simple Python utility file. Contains:
- **Hardcoded database password** in source code (`security / critical`)
- **Off-by-one error** in a loop starting at index 1 instead of 0 (`logic / major`)

### Task 2 — Medium: Mid-Level Review
A Flask REST API with search and delete endpoints. Contains:
- **Missing authentication check** on the search endpoint (`security / critical`)
- **SQL injection** via f-string interpolation of user input (`security / critical`)
- **N+1 query** — fetching orders per user inside a loop (`performance / major`)
- **Wrong HTTP status code** — returns 200 instead of 404 for missing user (`logic / major`)

### Task 3 — Hard: Staff Engineer Review
An async Python microservice with JWT auth and concurrent job processing. Contains:
- **Race condition** — shared `JOBS` dict mutated from concurrent coroutines without `asyncio.Lock` (`race_condition / critical`)
- **JWT `none` algorithm bypass** — allows forged unsigned tokens (`security / critical`)
- **Silent exception swallow** — catches all JWT errors and returns empty dict, hiding attacks (`logic / major`)
- **TOCTOU vulnerability** — `os.path.exists()` check and `open()` are not atomic (`security / major`)
- **Resource leak** — file handle opened without context manager; never closed on exception (`performance / major`)

---

## 🎮 Action Space

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `action_type` | string | ✅ | `comment`, `done`, `request_changes`, `approve` |
| `line_number` | int | For `comment` | Any line in the diff |
| `issue_category` | string | Recommended | `security`, `logic`, `race_condition`, `performance`, `style` |
| `severity` | string | Recommended | `critical`, `major`, `minor` |
| `comment` | string | Recommended | Free-text description of the bug |

**Action types:**
- `comment` — flag a bug on a specific line (can be called multiple times)
- `request_changes` — formally end the review, requesting fixes
- `approve` — approve the PR (heavy penalty if critical bugs remain!)
- `done` — signal review complete

---

## 👁️ Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `diff` | string | The full code diff to review |
| `task_id` | string | `easy`, `medium`, or `hard` |
| `task_description` | string | What the PR is supposed to do |
| `comments_so_far` | list[dict] | All comments submitted this episode |
| `steps_remaining` | int | Steps left before forced episode end |
| `feedback` | string | Feedback on the last action |
| `partial_score` | float | Running score estimate (0.0–1.0) |
| `done` | bool | Whether the episode has ended |

---

## 🏆 Reward Function

Rewards are given **at every step** (delta-based), not just at episode end.

**Per bug correctly found (within ±3 lines):**
| Component | Points |
|-----------|--------|
| Bug located (right line area) | +0.30 |
| Correct `issue_category` label | +0.10 |
| Correct `severity` label | +0.10 |
| **Max per bug** | **+0.50** |

**Bonuses & Penalties:**
| Event | Effect |
|-------|--------|
| All bugs found | +20% completion bonus |
| False positive (comment on clean code) | −0.15 per false positive |
| `approve` with critical bugs unfound | −50% penalty |
| Step budget exceeded (15 steps max) | Episode force-ended |

**Final score formula:**
```
coverage  = bugs_found / total_bugs_planted
precision = bugs_found / total_comments_made
score     = normalized((coverage × precision × weights) + bonuses − penalties)
           clamped to [0.0, 1.0]
```

---

## 🚀 Quick Start

### Option 1 — Use the Hugging Face Space (recommended)

```python
from client import SecQuestEnv
from models import ReviewAction

# Async
import asyncio

async def main():
    async with SecQuestEnv(base_url="https://YOUR-SPACE.hf.space") as env:
        result = await env.reset(task_id="easy")
        print(result.observation.diff)

        result = await env.step(ReviewAction(
            action_type="comment",
            line_number=5,
            issue_category="security",
            severity="critical",
            comment="Hardcoded database password in source code — use environment variables.",
        ))
        print(f"Reward: {result.reward}")
        print(f"Feedback: {result.observation.feedback}")

        result = await env.step(ReviewAction(action_type="request_changes"))
        print(f"Final score: {result.observation.partial_score}")

asyncio.run(main())

# Sync
with SecQuestEnv(base_url="https://YOUR-SPACE.hf.space").sync() as env:
    result = env.reset(task_id="medium")
    result = env.step(ReviewAction(
        action_type="comment",
        line_number=27,
        issue_category="security",
        severity="critical",
        comment="SQL injection via f-string interpolation of user input.",
    ))
    print(result.reward)
```

### Option 2 — Run locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR-USERNAME/sec-quest.git
cd sec-quest

# 2. Install dependencies
pip install openenv-core fastapi uvicorn pydantic websockets requests

# 3. Start the server
uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload

# 4. Test it
curl http://localhost:7860/health
```

### Option 3 — Docker

```bash
docker build -t sec-quest .
docker run -p 7860:7860 sec-quest
curl http://localhost:7860/health
```

---

## 🤖 Running the Baseline

```bash
# Set credentials
export API_BASE_URL="https://router.huggingface.co/v1"
export HF_TOKEN="hf_your_token_here"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"

# Run against the live HF Space
python inference.py --url https://YOUR-SPACE.hf.space

# Or run against local server
python inference.py --url http://localhost:7860
```

---

## 📊 Baseline Scores

| Agent | Easy | Medium | Hard | Average |
|-------|------|--------|------|---------|
| Oracle (ground truth) | 1.00 | 1.00 | 1.00 | 1.00 |
| Llama-3.1-8B | ~0.85 | ~0.55 | ~0.30 | ~0.57 |
| Random (no comments) | 0.00 | 0.00 | 0.00 | 0.00 |

---

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset` | POST | Start a new episode (`{"task_id": "easy"}`) |
| `/step` | POST | Submit a review action |
| `/state` | GET | Current episode metadata |
| `/health` | GET | Health check |
| `/docs` | GET | Auto-generated Swagger UI |
| `/web` | GET | Interactive web UI (when enabled) |

---

## 🔗 Links

- [OpenEnv GitHub](https://github.com/meta-pytorch/OpenEnv)
- [OpenEnv Docs](https://meta-pytorch.org/OpenEnv/)
- [Hackathon Page](https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/)