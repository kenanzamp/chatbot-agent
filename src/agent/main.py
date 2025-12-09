"""
Application entry point.
"""

import uvicorn
import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.transport.server import app
from agent.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    """Start the agent server."""
    uvicorn.run(
        "agent.transport.server:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
