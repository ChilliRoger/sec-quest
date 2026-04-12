"""
inference.py — SecQuest Baseline Inference Script
==================================================

Runs an LLM agent against all 3 SecQuest tasks using the OpenAI client.

Required environment variables:
    API_BASE_URL   The API endpoint (e.g. https://router.huggingface.co/v1)
    MODEL_NAME     The model identifier
    HF_TOKEN       Your Hugging Face / API key

Usage:
    python inference.py
    python inference.py --url https://your-space.hf.space

STDOUT FORMAT:
    [START] task=<task_name> env=sec-quest model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import os
import re
import json
import argparse
from typing import List, Optional
from openai import OpenAI

# ── Configuration ────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME   = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

BENCHMARK    = "sec-quest"
MAX_STEPS    = 12
TEMPERATURE  = 0.2
MAX_TOKENS   = 600
SUCCESS_SCORE_THRESHOLD = 0.5  # normalized score in [0, 1]
STRICT_MIN_SCORE = 0.001
STRICT_MAX_SCORE = 0.999

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


def _strict_score(value: float) -> float:
    """Clamp any score to the strict open interval (0, 1)."""
    return max(STRICT_MIN_SCORE, min(STRICT_MAX_SCORE, float(value)))

# ── Logging Functions ────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    """Log episode start in required format."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    """Log step in required format."""
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Log episode end in required format."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert senior software engineer performing a code review.
You will be shown a code diff (a Pull Request). Your job is to find all security vulnerabilities,
logic bugs, race conditions, performance issues, and code smells planted in the diff.

At each step you must respond with EXACTLY one JSON object (no markdown, no explanation outside the JSON).

To flag a bug:
{
  "action_type": "comment",
  "line_number": <int>,
  "issue_category": "<security|logic|race_condition|performance|style>",
  "severity": "<critical|major|minor>",
  "comment": "<your description of the bug>"
}

When you have found all bugs or have no more to report:
{
  "action_type": "request_changes"
}

If you believe the PR is clean:
{
  "action_type": "approve"
}

Rules:
- Only flag real bugs — false positives cost you points.
- You may submit multiple comments (one per response turn).
- Be precise about line numbers.
- Always respond with valid JSON only.
"""


def build_user_prompt(obs: dict) -> str:
    comments_str = ""
    if obs.get("comments_so_far"):
        comments_str = "\n\nComments you have submitted so far:\n"
        for c in obs["comments_so_far"]:
            comments_str += (
                f"  Line {c['line_number']} [{c['issue_category']}/{c['severity']}]: "
                f"{c['comment']}\n"
            )

    return f"""Task: {obs['task_description']}
Steps remaining: {obs['steps_remaining']}
Current partial score: {obs['partial_score']:.3f}
Last feedback: {obs['feedback']}
{comments_str}
=== CODE DIFF ===
{obs['diff']}
=================

Respond with exactly one JSON action object."""


def call_llm(messages: list) -> dict:
    """Call the LLM and parse a JSON action from its response."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        action = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                action = json.loads(match.group())
            except Exception:
                action = {"action_type": "done"}
        else:
            action = {"action_type": "done"}

    return action


def run_task_sync(env_url: str, task_id: str) -> dict:
    """Run a single task using the HTTP REST endpoints."""
    import requests

    base = env_url.rstrip("/")
    session = requests.Session()

    rewards: List[float] = []
    steps_taken = 0
    score = STRICT_MIN_SCORE
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset
        resp = session.post(f"{base}/reset", json={"task_id": task_id}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get("observation", data)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        done = obs.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            user_msg = build_user_prompt(obs)
            messages.append({"role": "user", "content": user_msg})

            action_dict = call_llm(messages)
            messages.append({"role": "assistant", "content": json.dumps(action_dict)})

            # Step
            resp = session.post(f"{base}/step", json=action_dict, timeout=30)
            resp.raise_for_status()
            step_data = resp.json()

            reward = step_data.get("reward", 0.0)
            rewards.append(reward)
            obs = step_data.get("observation", step_data)
            done = step_data.get("done", obs.get("done", False))
            error = step_data.get("info", {}).get("error", None)
            steps_taken = step

            # Format action as string for logging
            action_type = action_dict.get("action_type", "unknown")
            if action_type == "comment":
                action_str = f"comment(line={action_dict.get('line_number')},cat={action_dict.get('issue_category')},sev={action_dict.get('severity')})"
            else:
                action_str = action_type

            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            if done:
                break

        score = _strict_score(obs.get("partial_score", STRICT_MIN_SCORE))
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        error_msg = str(e)
        log_step(step=steps_taken + 1, action="error", reward=0.0, done=True, error=error_msg)
        score = STRICT_MIN_SCORE
        success = False

    finally:
        score = _strict_score(score)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return {
        "task_id": task_id,
        "final_score": score,
        "total_reward": round(sum(rewards), 4),
        "steps": steps_taken,
        "success": success,
    }


def main():
    parser = argparse.ArgumentParser(description="SecQuest baseline inference script")
    parser.add_argument(
        "--url",
        default=os.getenv("ENV_URL", "http://localhost:7860"),
        help="SecQuest environment URL (default: http://localhost:7860)",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  SecQuest Baseline Inference")
    print(f"  Model : {MODEL_NAME}")
    print(f"  URL   : {args.url}")
    print(f"{'='*60}\n")

    results = []
    for task_id in ["easy", "medium", "hard"]:
        try:
            result = run_task_sync(args.url, task_id)
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Task {task_id} failed: {e}", flush=True)
            results.append({
                "task_id": task_id,
                "final_score": STRICT_MIN_SCORE,
                "error": str(e),
                "success": False,
            })

    avg = sum(_strict_score(r.get("final_score", STRICT_MIN_SCORE)) for r in results) / len(results) if results else STRICT_MIN_SCORE

    print(f"\n{'='*60}")
    print("  BASELINE RESULTS")
    print(f"{'='*60}")
    for r in results:
        score = _strict_score(r.get("final_score", STRICT_MIN_SCORE))
        success_icon = "✅" if r.get("success", False) else "❌"
        print(f"  {success_icon} {r['task_id']:8s}  score={score:.3f}")
    print(f"\n  AVERAGE SCORE: {avg:.3f}")
    print(f"{'='*60}\n")

    # Write results to file for reproducibility
    with open("baseline_results.json", "w") as f:
        json.dump({
            "model": MODEL_NAME,
            "results": results,
            "average_score": round(avg, 4),
        }, f, indent=2)
    
    print("  Results saved to baseline_results.json\n")


if __name__ == "__main__":
    main()
