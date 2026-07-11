"""
AutoSystem - Main Entry Point
Runs one pipeline cycle manually (for testing or single execution).
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config.settings as settings
from pipeline.orchestrator import PipelineOrchestrator


def setup_logging():
    """Configure logging for the application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "autosystem.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    """Run one pipeline cycle."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("AutoSystem - Starting Pipeline Cycle")
    logger.info("=" * 60)

    # Validate configuration
    missing = settings.validate_required_keys()
    if missing:
        logger.error(f"Missing required API keys: {missing}")
        logger.error("Copy .env.example to .env and fill in your API keys")
        sys.exit(1)

    # Run pipeline
    orchestrator = PipelineOrchestrator()
    orchestrator.run()

    logger.info("Pipeline cycle complete.")


if __name__ == "__main__":
    main()
