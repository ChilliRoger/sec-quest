"""
sec-quest/client.py

Python client for the SecQuest environment.
Extends openenv EnvClient — handles WebSocket connection to the server.

Usage (async):
    async with SecQuestEnv(base_url="https://your-space.hf.space") as env:
        result = await env.reset(task_id="easy")
        print(result.observation.diff)
        result = await env.step(ReviewAction(
            action_type="comment",
            line_number=5,
            issue_category="security",
            severity="critical",
            comment="Hardcoded password in source code.",
        ))
        print(result.reward)

Usage (sync):
    with SecQuestEnv(base_url="https://your-space.hf.space").sync() as env:
        result = env.reset(task_id="easy")
        result = env.step(ReviewAction(...))
"""

from openenv.core.env_client import EnvClient
from models import ReviewAction, ReviewObservation


class SecQuestEnv(EnvClient):
    """Client for the SecQuest PR Code Review environment."""

    action_class = ReviewAction
    observation_class = ReviewObservation

    async def reset(self, task_id: str = "easy"):
        """
        Start a new review episode.

        Parameters
        ----------
        task_id : str
            One of 'easy', 'medium', or 'hard'.
        """
        return await super().reset(task_id=task_id)