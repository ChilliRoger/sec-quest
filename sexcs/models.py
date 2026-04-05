"""
sec-quest/models.py
Typed Pydantic models for the SecQuest PR Code Review environment.
"""

from typing import List, Optional
from pydantic import Field
from openenv.core.env_server.types import Action, Observation


class ReviewComment(object):
    """A single review comment made by the agent."""

    def __init__(
        self,
        line_number: int,
        issue_category: str,
        severity: str,
        comment: str,
    ):
        self.line_number = line_number
        self.issue_category = issue_category
        self.severity = severity
        self.comment = comment

    def dict(self):
        return {
            "line_number": self.line_number,
            "issue_category": self.issue_category,
            "severity": self.severity,
            "comment": self.comment,
        }


class ReviewAction(Action):
    """
    Action the agent can take in the SecQuest environment.

    action_type:
        'comment'         - Leave a review comment on a specific line
        'request_changes' - Formally request changes (ends episode, all comments evaluated)
        'approve'         - Approve the PR (ends episode, penalized if bugs remain)
        'done'            - Signal review is complete (ends episode)

    line_number:
        The line in the diff being commented on (1-indexed).
        Required when action_type is 'comment'.

    issue_category:
        One of: 'security', 'logic', 'race_condition', 'performance', 'style'

    severity:
        One of: 'critical', 'major', 'minor'

    comment:
        Free-text description of the issue found.
    """

    action_type: str = Field(
        ...,
        description="One of: 'comment', 'request_changes', 'approve', 'done'",
    )
    line_number: Optional[int] = Field(
        None,
        description="Line number in the diff being flagged (required for 'comment')",
    )
    issue_category: Optional[str] = Field(
        None,
        description="One of: 'security', 'logic', 'race_condition', 'performance', 'style'",
    )
    severity: Optional[str] = Field(
        None,
        description="One of: 'critical', 'major', 'minor'",
    )
    comment: Optional[str] = Field(
        None,
        description="Free-text description of the issue found",
    )


class ReviewObservation(Observation):
    """
    Observation returned by the SecQuest environment after each step.

    diff:
        The full code diff the agent must review (shown on reset, repeated each step).

    task_id:
        Which task is active: 'easy', 'medium', or 'hard'.

    task_description:
        Human-readable description of what the PR is supposed to accomplish.

    comments_so_far:
        List of all comments the agent has made this episode (as dicts).

    steps_remaining:
        How many more steps the agent may take before the episode is force-ended.

    feedback:
        Feedback on the last action taken (e.g. "Good catch!", "False positive").

    partial_score:
        Running score estimate based on bugs found so far (0.0 – 1.0).

    done:
        Whether the episode has ended.
    """

    diff: str = Field(..., description="The full code diff to review")
    task_id: str = Field(..., description="Task difficulty: 'easy', 'medium', or 'hard'")
    task_description: str = Field(..., description="What this PR is supposed to do")
    comments_so_far: List[dict] = Field(
        default_factory=list,
        description="All review comments submitted so far this episode",
    )
    steps_remaining: int = Field(..., description="Steps left before forced episode end")
    feedback: str = Field(..., description="Feedback on the last action")
    partial_score: float = Field(..., description="Running score estimate (0.0–1.0)")
    done: bool = Field(default=False, description="Whether the episode has ended")