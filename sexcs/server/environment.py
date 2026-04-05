"""
sec-quest/server/environment.py

Core SecQuest environment implementing the OpenEnv Environment base class.
Manages episode state, step logic, and reward computation.
"""

from uuid import uuid4
from typing import Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ReviewAction, ReviewObservation
from server.tasks import ALL_TASKS
from server.grader import grade, partial_grade

MAX_STEPS = 15   # max comments per episode before force-end


class SecQuestEnvironment(Environment):
    """
    PR Code Review RL environment.

    Episode flow:
      1. reset(task_id='easy'|'medium'|'hard') → agent receives the diff
      2. agent calls step(ReviewAction(action_type='comment', ...)) repeatedly
      3. agent calls step(ReviewAction(action_type='done'|'request_changes'|'approve'))
      4. episode ends, final grade computed

    Reward shaping:
      - Per-step: delta reward (improvement in partial_score since last step)
      - Terminal: full grader result (coverage × precision + bonuses/penalties)
    """

    # Mark as concurrency-safe (each WebSocket gets its own instance)
    concurrency_safe = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task = None
        self._comments = []
        self._done = False
        self._last_partial_score = 0.0
        self._steps_used = 0

    # ------------------------------------------------------------------
    # OpenEnv required methods
    # ------------------------------------------------------------------

    def state(self) -> State:
        return self._state

    def reset(self, task_id: str = "easy") -> ReviewObservation:
        """Start a new episode. task_id: 'easy', 'medium', or 'hard'."""
        if task_id not in ALL_TASKS:
            task_id = "easy"

        self._task = ALL_TASKS[task_id]
        self._comments = []
        self._done = False
        self._last_partial_score = 0.0
        self._steps_used = 0
        self._state = State(episode_id=str(uuid4()), step_count=0)

        return ReviewObservation(
            diff=self._task["diff"],
            task_id=self._task["task_id"],
            task_description=self._task["task_description"],
            comments_so_far=[],
            steps_remaining=MAX_STEPS,
            feedback="Episode started. Review the diff and submit comments.",
            partial_score=0.0,
            done=False,
        )

    def step(self, action: ReviewAction):
        """
        Execute one review action.

        Returns (observation, reward, done, info)
        """
        if self._done:
            obs = self._make_obs("Episode already ended.", self._last_partial_score)
            obs.done = True
            return obs, 0.0, True, {"error": "Episode already ended"}

        self._state.step_count += 1
        self._steps_used += 1

        action_type = action.action_type.lower().strip()

        # --- Handle terminal actions ---
        if action_type in ("done", "request_changes", "approve"):
            self._done = True
            result = grade(
                self._comments,
                self._task["bug_manifest"],
                final_action=action_type,
            )
            final_score = result["score"]
            reward = final_score - self._last_partial_score  # terminal delta
            self._last_partial_score = final_score

            obs = ReviewObservation(
                diff=self._task["diff"],
                task_id=self._task["task_id"],
                task_description=self._task["task_description"],
                comments_so_far=list(self._comments),
                steps_remaining=0,
                feedback=result["feedback"],
                partial_score=final_score,
                done=True,
            )
            info = {
                "final_score": final_score,
                "bugs_found": result["bugs_found"],
                "bugs_missed": result["bugs_missed"],
                "false_positives": result["false_positives"],
                "coverage": result["coverage"],
                "precision": result["precision"],
                "breakdown": result["breakdown"],
            }
            return obs, round(reward, 4), True, info

        # --- Handle comment action ---
        if action_type == "comment":
            valid_categories = {"security", "logic", "race_condition", "performance", "style"}
            valid_severities = {"critical", "major", "minor"}

            feedback_parts = []

            # Validate fields
            if action.line_number is None:
                feedback_parts.append("⚠️  line_number is required for 'comment' actions.")

            if action.issue_category and action.issue_category not in valid_categories:
                feedback_parts.append(
                    f"⚠️  Unknown category '{action.issue_category}'. "
                    f"Valid: {sorted(valid_categories)}"
                )

            if action.severity and action.severity not in valid_severities:
                feedback_parts.append(
                    f"⚠️  Unknown severity '{action.severity}'. "
                    f"Valid: {sorted(valid_severities)}"
                )

            # Record the comment
            comment_dict = {
                "line_number": action.line_number,
                "issue_category": action.issue_category,
                "severity": action.severity,
                "comment": action.comment or "",
            }
            self._comments.append(comment_dict)

            # Compute partial score delta for reward signal
            new_partial = partial_grade(self._comments, self._task["bug_manifest"])
            reward = new_partial - self._last_partial_score
            self._last_partial_score = new_partial

            if reward > 0:
                feedback_parts.append(f"✅ Good catch! Score improved by +{reward:.3f}.")
            elif reward < 0:
                feedback_parts.append(f"❌ False positive detected. Score dropped by {reward:.3f}.")
            else:
                feedback_parts.append("ℹ️  Comment recorded. No score change yet.")

            steps_left = MAX_STEPS - self._steps_used
            if steps_left <= 3:
                feedback_parts.append(f"⏰ Only {steps_left} step(s) remaining!")

            # Force-end if budget exhausted
            force_done = steps_left <= 0
            if force_done:
                self._done = True
                result = grade(self._comments, self._task["bug_manifest"], final_action="done")
                final_score = result["score"]
                reward = final_score - new_partial
                self._last_partial_score = final_score
                feedback_parts.append("🛑 Step budget exhausted — episode ended automatically.")
                obs = ReviewObservation(
                    diff=self._task["diff"],
                    task_id=self._task["task_id"],
                    task_description=self._task["task_description"],
                    comments_so_far=list(self._comments),
                    steps_remaining=0,
                    feedback=" | ".join(feedback_parts),
                    partial_score=final_score,
                    done=True,
                )
                return obs, round(reward, 4), True, {"forced_end": True, "final_score": final_score}

            obs = ReviewObservation(
                diff=self._task["diff"],
                task_id=self._task["task_id"],
                task_description=self._task["task_description"],
                comments_so_far=list(self._comments),
                steps_remaining=steps_left,
                feedback=" | ".join(feedback_parts),
                partial_score=new_partial,
                done=False,
            )
            return obs, round(reward, 4), False, {}

        # Unknown action_type
        obs = self._make_obs(
            f"Unknown action_type '{action_type}'. "
            "Use: 'comment', 'done', 'request_changes', or 'approve'.",
            self._last_partial_score,
        )
        return obs, -0.05, False, {"warning": "unknown action_type"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_obs(self, feedback: str, partial_score: float) -> ReviewObservation:
        return ReviewObservation(
            diff=self._task["diff"] if self._task else "",
            task_id=self._task["task_id"] if self._task else "",
            task_description=self._task["task_description"] if self._task else "",
            comments_so_far=list(self._comments),
            steps_remaining=max(0, MAX_STEPS - self._steps_used),
            feedback=feedback,
            partial_score=partial_score,
            done=self._done,
        )

    def get_metadata(self) -> dict:
        return {
            "name": "sec-quest",
            "description": "PR Code Review RL environment — find planted bugs in code diffs",
            "tasks": list(ALL_TASKS.keys()),
            "max_steps": MAX_STEPS,
            "action_types": ["comment", "done", "request_changes", "approve"],
            "issue_categories": ["security", "logic", "race_condition", "performance", "style"],
            "severities": ["critical", "major", "minor"],
        }