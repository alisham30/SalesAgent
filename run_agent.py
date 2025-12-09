"""
Main entry point for tender agent
Runs the agent automatically without user input
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.main import TenderAgent
from backend.utils.logger import logger

def main():
    """Main entry point"""
    try:
        logger.info("=" * 60)
        logger.info("Tender Agent - Starting Automatic Processing")
        logger.info("=" * 60)
        
        agent = TenderAgent()
        agent.run()
        
        logger.info("=" * 60)
        logger.info("Tender Agent - Processing Complete")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

