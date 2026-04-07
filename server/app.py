"""
sec-quest/server/app.py

FastAPI app for the SecQuest environment.
Uses openenv.core.env_server.create_app to handle WebSocket sessions,
reset/step/state routing, and the optional web UI.
"""

import os
import sys

# Make sure the package root is on the path when running inside Docker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server import create_app

from models import ReviewAction, ReviewObservation
from server.environment import SecQuestEnvironment

app = create_app(
    SecQuestEnvironment,
    ReviewAction,
    ReviewObservation,
    env_name="sec_quest",
)


def main():
    """Main entry point for running the server."""
    import uvicorn
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=7860,
        reload=False
    )


if __name__ == "__main__":
    main()
