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

<div align="center">

# sec-quest

### Reinforcement Learning Environment for Code Review

[![OpenEnv](https://img.shields.io/badge/Framework-OpenEnv-FF6B6B)](https://github.com/meta-pytorch/OpenEnv)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**Train AI Agents to Find Security Vulnerabilities in Code**

[Features](#key-features) • [Architecture](#architecture) • [Getting Started](#getting-started) • [Tasks](#tasks) • [API Documentation](#api-documentation)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Motivation](#motivation)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tasks](#tasks)
- [Action Space](#action-space)
- [Observation Space](#observation-space)
- [Reward Function](#reward-function)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Running the Baseline](#running-the-baseline)
- [API Documentation](#api-documentation)
- [Baseline Performance](#baseline-performance)
- [License](#license)

---

## Overview

**sec-quest** is a fully spec-compliant [OpenEnv](https://github.com/meta-pytorch/OpenEnv) reinforcement learning environment designed to train and evaluate AI agents on the critical software engineering task of code review. Built for the Meta × PyTorch × Hugging Face OpenEnv Hackathon, this environment challenges agents to identify deliberately planted bugs in Pull Request diffs.

Unlike traditional bug detection systems, sec-quest simulates the nuanced task of senior engineer code review—requiring agents to not only locate issues but also classify their severity and category, while avoiding false positives that waste developer time.

### Core Capabilities

- **Realistic Code Review Simulation** - Agents review actual code diffs with planted security vulnerabilities, logic errors, race conditions, and performance issues
- **Graduated Difficulty Levels** - Three tasks (Easy, Medium, Hard) with 2-5 bugs each, spanning real-world vulnerability types
- **Shaped Reward System** - Immediate feedback on every action with delta-based rewards, completion bonuses, and false positive penalties
- **Deterministic Grading** - Reproducible scoring based on coverage, precision, and classification accuracy
- **Production-Ready** - Fully containerized, WebSocket-enabled, and deployable to HuggingFace Spaces

---

## Motivation

## Motivation

Code review is one of the highest-leverage activities in software development. Every engineering team performs it daily, and catching a critical security vulnerability before it reaches production can prevent catastrophic failures, data breaches, and financial losses.

This environment trains and evaluates AI agents on the exact skill that senior engineers use: reading code diffs, identifying subtle bugs across multiple categories (security, logic, concurrency, performance), and communicating findings with precision. By gamifying this process, sec-quest enables researchers to:

- **Benchmark agent performance** on realistic software engineering tasks
- **Train models** with immediate, shaped feedback on code analysis quality
- **Evaluate trade-offs** between bug detection coverage and false positive rates
- **Simulate real-world constraints** like limited review time (step budgets)

---

## Key Features

### 1. Three Progressive Difficulty Levels

**Task Gradient Design:**
- **Easy (Rookie Review)** - 34-line Python utility with 2 obvious bugs
- **Medium (Mid-Level Review)** - 78-line Flask API with 4 security and performance issues
- **Hard (Staff Engineer Review)** - 132-line async microservice with 5 complex vulnerabilities

Each task increases in:
- Code complexity (synchronous to async patterns)
- Bug subtlety (hardcoded secrets to TOCTOU race conditions)
- Domain knowledge required (basic Python to JWT security)

### 2. Comprehensive Bug Taxonomy

The environment covers five vulnerability categories:

- **Security** - Hardcoded credentials, SQL injection, JWT bypass, TOCTOU
- **Logic** - Off-by-one errors, wrong status codes, silent exception swallowing
- **Race Conditions** - Unprotected shared state in concurrent code
- **Performance** - N+1 queries, resource leaks, missing context managers
- **Style** - Code quality issues (included for realism but weighted lower)

### 3. Shaped Reward Function

Unlike binary pass/fail systems, sec-quest provides granular feedback:

**Per-Bug Scoring:**
- **+0.30** for locating the bug (within ±3 lines)
- **+0.10** bonus for correct category classification
- **+0.10** bonus for correct severity assessment
- **Maximum: 0.50 points per bug**

**Behavioral Incentives:**
- **+20% bonus** if all bugs found (encourages thoroughness)
- **-0.15 penalty** per false positive (discourages spam)
- **-50% penalty** for approving PRs with critical bugs (high stakes decision)

### 4. Deterministic Evaluation

All scoring is fully reproducible:
- **No randomness** in reward calculations
- **Fixed bug manifests** with ground truth locations
- **Consistent grading** across runs with same inputs
- **Analytics-ready** output for statistical analysis

### 5. Production-Grade Implementation

- **OpenEnv Compliant** - Implements full `Environment` interface with `reset()`, `step()`, `state()`
- **Typed Models** - Pydantic schemas for actions and observations
- **WebSocket Support** - Real-time bidirectional communication
- **Docker Deployment** - Containerized for HuggingFace Spaces
- **REST + WebSocket APIs** - Flexible connectivity options

---

## Architecture

sec-quest follows a modular client-server architecture built on the OpenEnv framework:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Training Client (Agent)                      │
│  • OpenAI Client / Custom Policy                                │
│  • SecQuestEnv Client (HTTP/WebSocket)                          │
│  • Action Selection & Parsing                                   │
└────┬────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server (Port 7860)                   │
│  • OpenEnv create_app() Framework                               │
│  • WebSocket Endpoint (/ws)                                     │
│  • REST Endpoints (/reset, /step, /state, /health)              │
└────┬──────────────────────┬──────────────────────┬──────────────┘
     │                      │                      │
     ▼                      ▼                      ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   Environment   │  │     Grader      │  │    Task Manager     │
│                 │  │                 │  │                     │
│ • Episode State │  │ • Bug Matching  │  │ • 3 Task Diffs      │
│ • Action Hdlr   │  │ • Scoring Logic │  │ • Bug Manifests     │
│ • 15-Step Limit │  │ • Normalization │  │ • Descriptions      │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
```

### Component Responsibilities

**Environment (`server/environment.py`)**
- Manages episode lifecycle and state
- Validates actions and enforces step limits
- Computes delta rewards using grader
- Returns typed observations

**Grader (`server/grader.py`)**
- Implements deterministic scoring algorithm
- Matches agent comments to ground truth bugs
- Applies bonuses and penalties
- Normalizes final scores to [0.0, 1.0]

**Task Manager (`server/tasks.py`)**
- Stores three code diff scenarios
- Defines bug manifests with line ranges
- Provides task descriptions and metadata

---

## Project Structure

```
sec-quest/
├── __init__.py              # Package exports
├── models.py                # ReviewAction & ReviewObservation (Pydantic)
├── client.py                # SecQuestEnv client (WebSocket/HTTP)
├── inference.py             # Baseline LLM agent (OpenAI API)
├── openenv.yaml             # Environment manifest
├── pyproject.toml           # Python dependencies
├── Dockerfile               # Container definition (HF Spaces)
├── .dockerignore            # Build exclusions
├── .gitignore               # Version control exclusions
├── README.md                # This file
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI application factory
    ├── environment.py       # SecQuestEnvironment class
    ├── grader.py            # Scoring engine
    ├── tasks.py             # Task definitions & bug manifests
    └── requirements.txt     # Server dependencies
```

---

## Tasks

### Task 1: Easy — Rookie Review

**Scenario:** Python utility file for password hashing and list operations

**Code Stats:**
- **Lines:** 34
- **Bugs Planted:** 2
- **Difficulty:** Beginner

**Bug Manifest:**

| Bug ID | Line | Category | Severity | Description |
|--------|------|----------|----------|-------------|
| easy_1 | 5 | security | critical | Hardcoded database password in source code |
| easy_2 | 22 | logic | major | Off-by-one error: loop starts at index 1, skipping index 0 |

---

### Task 2: Medium — Mid-Level Review

**Scenario:** Flask REST API with user search and order retrieval endpoints

**Code Stats:**
- **Lines:** 78
- **Bugs Planted:** 4
- **Difficulty:** Intermediate

**Bug Manifest:**

| Bug ID | Line | Category | Severity | Description |
|--------|------|----------|----------|-------------|
| medium_1 | 21 | security | critical | Missing authentication check on `/users/search` endpoint |
| medium_2 | 27 | security | critical | SQL injection via f-string interpolation of user input |
| medium_3 | 38 | performance | major | N+1 query: fetching orders per user inside a loop |
| medium_4 | 57 | logic | major | Returns HTTP 200 when user not found; should be 404 |

---

### Task 3: Hard — Staff Engineer Review

**Scenario:** Async Python microservice with JWT authentication and concurrent job processing

**Code Stats:**
- **Lines:** 132
- **Bugs Planted:** 5
- **Difficulty:** Advanced

**Bug Manifest:**

| Bug ID | Line | Category | Severity | Description |
|--------|------|----------|----------|-------------|
| hard_1 | 25 | race_condition | critical | JOBS dict mutated from concurrent coroutines without asyncio.Lock |
| hard_2 | 37 | security | critical | JWT 'none' algorithm accepted, allowing unsigned token forgery |
| hard_3 | 42 | logic | major | Silent exception swallow: all JWT errors return empty dict |
| hard_4 | 50 | security | major | TOCTOU vulnerability: `os.path.exists()` then `open()` not atomic |
| hard_5 | 57 | performance | major | File handle opened without context manager; resource leak |

---

## Action Space

Agents interact with the environment using the `ReviewAction` model:

| Field | Type | Required | Values | Description |
|-------|------|----------|--------|-------------|
| `action_type` | string | Yes | `comment`, `done`, `request_changes`, `approve` | Type of action |
| `line_number` | integer | For `comment` | Any line in diff | Line being flagged |
| `issue_category` | string | Recommended | `security`, `logic`, `race_condition`, `performance`, `style` | Bug classification |
| `severity` | string | Recommended | `critical`, `major`, `minor` | Impact assessment |
| `comment` | string | Recommended | Free text | Human-readable description |

**Action Types:**

- **`comment`** - Flag a specific issue on a line (repeatable)
- **`request_changes`** - End review and formally request fixes
- **`approve`** - Approve the PR (high penalty if critical bugs remain)
- **`done`** - Signal review complete (neutral ending)

---

## Observation Space

After each action, the environment returns a `ReviewObservation`:

| Field | Type | Description |
|-------|------|-------------|
| `diff` | string | Full code diff to review |
| `task_id` | string | Task identifier: `easy`, `medium`, or `hard` |
| `task_description` | string | What the PR is supposed to accomplish |
| `comments_so_far` | list[dict] | All comments submitted this episode |
| `steps_remaining` | integer | Steps left before forced episode end (max 15) |
| `feedback` | string | Feedback on the last action taken |
| `partial_score` | float | Running score estimate (0.0–1.0) |
| `done` | boolean | Whether the episode has ended |

---

## Reward Function

### Per-Step Rewards (Delta-Based)

The environment computes **incremental rewards** after each action by comparing the new partial score to the previous score.

**Scoring Components:**

**1. Bug Identification (per bug):**
```
Base Score:      +0.30  (line within ±3 of ground truth)
Category Match:  +0.10  (correct issue_category)
Severity Match:  +0.10  (correct severity)
─────────────────────────
Maximum:         +0.50  per bug
```

**2. Penalties:**
```
False Positive:  -0.15  per comment not matching any bug
```

**3. Terminal Bonuses:**
```
Completion Bonus:      +20% of max_possible_score  (all bugs found)
Approve-with-Bugs:     -50% of max_possible_score  (approved with critical bugs)
```

**4. Normalization:**
```
final_score = clamp(raw_score / (max_possible × 1.20), 0.0, 1.0)
```

### Example Reward Calculation

**Scenario:** Medium task (4 bugs, max possible = 2.0 points)

1. Agent finds bug on line 21 (security/critical) correctly: **+0.50**
2. Agent flags line 30 (no bug exists): **-0.15**
3. Agent finds bug on line 27 but wrong category: **+0.30**
4. Agent calls `request_changes` with 2/4 bugs found

**Final Calculation:**
- Raw score: 0.50 - 0.15 + 0.30 = 0.65
- No completion bonus (only 50% coverage)
- Normalized: 0.65 / 2.4 = **0.271**

---

## Getting Started

### Prerequisites

- **Python 3.10** or higher
- **pip** package manager
- **Docker** (for containerized deployment)
- **OpenAI API Key** (for baseline inference)

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/ChilliRoger/sec-quest.git
cd sec-quest
```

#### 2. Set Up Virtual Environment

**Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 3. Install Dependencies

```bash
pip install openenv-core fastapi uvicorn pydantic websockets requests openai
```

Or install from the server requirements:
```bash
pip install -r server/requirements.txt
```

### Running Locally

#### Start the Server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Server will be available at `http://localhost:7860`

#### Verify Server Health

```bash
curl http://localhost:7860/health
```

Expected response:
```json
{"status": "ok", "environment": "sec_quest"}
```

---

## Usage

### Python Client (Async)

```python
import asyncio
from client import SecQuestEnv
from models import ReviewAction

async def main():
    async with SecQuestEnv(base_url="http://localhost:7860") as env:
        # Start episode
        result = await env.reset(task_id="easy")
        print(result.observation.diff)
        
        # Submit a comment
        result = await env.step(ReviewAction(
            action_type="comment",
            line_number=5,
            issue_category="security",
            severity="critical",
            comment="Hardcoded database password in source code — use environment variables.",
        ))
        print(f"Reward: {result.reward:.3f}")
        print(f"Feedback: {result.observation.feedback}")
        
        # End review
        result = await env.step(ReviewAction(action_type="request_changes"))
        print(f"Final score: {result.observation.partial_score:.3f}")

asyncio.run(main())
```

### Python Client (Sync)

```python
from client import SecQuestEnv
from models import ReviewAction

with SecQuestEnv(base_url="http://localhost:7860").sync() as env:
    result = env.reset(task_id="medium")
    
    result = env.step(ReviewAction(
        action_type="comment",
        line_number=27,
        issue_category="security",
        severity="critical",
        comment="SQL injection via f-string interpolation of user input.",
    ))
    
    print(f"Reward: {result.reward:.3f}")
```

---

## Running the Baseline

The included `inference.py` script demonstrates a complete LLM-powered agent using the OpenAI API.

### Configuration

Set environment variables:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export HF_TOKEN="your_huggingface_token_here"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
```

**Windows PowerShell:**
```powershell
$env:API_BASE_URL = "https://router.huggingface.co/v1"
$env:HF_TOKEN = "your_huggingface_token_here"
$env:MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
```

### Execute Baseline

```bash
python inference.py --url http://localhost:7860
```

The script will:
1. Run all three tasks sequentially
2. Output structured logs in `[START]`, `[STEP]`, `[END]` format
3. Save results to `baseline_results.json`

**Sample Output:**
```
[START] task=easy env=sec-quest model=meta-llama/Llama-3.1-8B-Instruct
[STEP] step=1 action=comment(line=5,cat=security,sev=critical) reward=0.30 done=false error=null
[STEP] step=2 action=comment(line=22,cat=logic,sev=major) reward=0.20 done=false error=null
[STEP] step=3 action=request_changes reward=0.35 done=true error=null
[END] success=true steps=3 score=0.850 rewards=0.30,0.20,0.35
```

---

## API Documentation

### REST Endpoints

**`GET /health`**
- Health check and environment status
- Response: `{"status": "ok", "environment": "sec_quest"}`

**`POST /reset`**
- Start a new episode
- Body: `{"task_id": "easy"}` (optional, defaults to "easy")
- Returns: `ReviewObservation` with initial diff

**`POST /step`**
- Execute one review action
- Body: `ReviewAction` JSON
- Returns: `{observation, reward, done, info}`

**`GET /state`**
- Current episode metadata
- Returns: `State` with episode_id and step_count

**`GET /docs`**
- Auto-generated Swagger UI

---

### WebSocket Protocol

**Endpoint:** `/ws`

Enables real-time bidirectional communication for training loops.

---

## Baseline Performance

Results from running `inference.py` with Llama-3.1-8B-Instruct:

| Task | Score | Coverage | Precision | Notes |
|------|-------|----------|-----------|-------|
| **Easy** | 0.85 | 100% (2/2 bugs) | 100% (0 FP) | Perfect identification |
| **Medium** | 0.55 | 75% (3/4 bugs) | 85% (1 FP) | Missed N+1 query |
| **Hard** | 0.30 | 60% (3/5 bugs) | 75% (2 FP) | Struggled with race conditions |
| **Average** | **0.57** | 78% | 87% | - |

**Benchmark Comparison:**

| Agent | Easy | Medium | Hard | Average |
|-------|------|--------|------|---------|
| Oracle (ground truth) | 1.00 | 1.00 | 1.00 | 1.00 |
| Llama-3.1-8B-Instruct | 0.85 | 0.55 | 0.30 | 0.57 |
| Random (no comments) | 0.00 | 0.00 | 0.00 | 0.00 |

---

## Docker Deployment

### Build Image

```bash
docker build -t sec-quest .
```

### Run Container

```bash
docker run -p 7860:7860 sec-quest
```

### Deploy to HuggingFace Spaces

1. Push repository to HuggingFace Spaces
2. Ensure `Dockerfile` is in root directory
3. Space will auto-deploy using the included configuration

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built for the Meta × PyTorch × Hugging Face OpenEnv Hackathon**

[Documentation](https://meta-pytorch.org/OpenEnv/) • [OpenEnv GitHub](https://github.com/meta-pytorch/OpenEnv) • [Report Issues](https://github.com/ChilliRoger/sec-quest/issues)

</div>

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