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
"""

import os
import re
import json
import argparse
from openai import OpenAI

# ── Configuration ────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME   = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

MAX_STEPS    = 12
TEMPERATURE  = 0.2
MAX_TOKENS   = 600

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

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
    """Run a single task using the HTTP REST endpoints (sync, no WebSocket needed for baseline)."""
    import requests

    base = env_url.rstrip("/")
    session = requests.Session()

    # Reset
    resp = session.post(f"{base}/reset", json={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    obs = data.get("observation", data)

    # Structured logging - START
    print(json.dumps({
        "type": "START",
        "task_id": task_id,
        "timestamp": str(os.times()),
    }))

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    total_reward = 0.0
    steps = 0
    done = obs.get("done", False)

    while not done and steps < MAX_STEPS:
        user_msg = build_user_prompt(obs)
        messages.append({"role": "user", "content": user_msg})

        action = call_llm(messages)
        messages.append({"role": "assistant", "content": json.dumps(action)})

        # Step
        resp = session.post(f"{base}/step", json=action, timeout=30)
        resp.raise_for_status()
        step_data = resp.json()

        reward = step_data.get("reward", 0.0)
        total_reward += reward
        obs = step_data.get("observation", step_data)
        done = step_data.get("done", obs.get("done", False))
        info = step_data.get("info", {})
        steps += 1

        # Structured logging - STEP
        print(json.dumps({
            "type": "STEP",
            "task_id": task_id,
            "step": steps,
            "action": action,
            "reward": reward,
            "total_reward": round(total_reward, 4),
            "done": done,
            "observation": {
                "partial_score": obs.get("partial_score", 0.0),
                "feedback": obs.get("feedback", ""),
                "steps_remaining": obs.get("steps_remaining", 0),
            }
        }))

        if done:
            break

    final_score = obs.get("partial_score", 0.0)
    
    # Structured logging - END
    print(json.dumps({
        "type": "END",
        "task_id": task_id,
        "final_score": final_score,
        "total_reward": round(total_reward, 4),
        "steps": steps,
        "timestamp": str(os.times()),
    }))

    return {
        "task_id": task_id,
        "final_score": final_score,
        "total_reward": round(total_reward, 4),
        "steps": steps,
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
            print(json.dumps({
                "type": "ERROR",
                "task_id": task_id,
                "error": str(e),
            }))
            results.append({"task_id": task_id, "final_score": 0.0, "error": str(e)})

    avg = sum(r.get("final_score", 0) for r in results) / len(results)

    # Summary structured log
    print(json.dumps({
        "type": "SUMMARY",
        "results": results,
        "average_score": round(avg, 4),
        "model": MODEL_NAME,
    }))

    # Write results to file for reproducibility
    with open("baseline_results.json", "w") as f:
        json.dump({
            "model": MODEL_NAME,
            "results": results,
            "average_score": round(avg, 4),
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print("  Results saved to baseline_results.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()