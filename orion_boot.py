#!/usr/bin/env python3
"""
ORION Boot Script
==================
Runs on computer startup to process pending tasks.

This script is registered with Windows Task Scheduler
to run at system startup. It:
1. Starts the ORION daemon
2. Processes any pending tasks
3. Runs the task scheduler in background
4. Stops after processing or after max runtime

Usage:
    python orion_boot.py
    
Register with Windows:
    python orion_boot.py --install
    
Unregister:
    python orion_boot.py --uninstall
"""

import sys
import os
import time
import signal
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[ORION BOOT] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "boot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("orion_boot")


def install_boot_task():
    """Register ORION to run at Windows startup"""
    try:
        python_path = sys.executable
        script_path = str(Path(__file__).resolve())
        
        # Create schtasks command
        cmd = (
            f'schtasks /create '
            f'/tn "ORION_Boot" '
            f'/tr "{python_path} {script_path}" '
            f'/sc ONSTART '
            f'/ru SYSTEM '
            f'/rl HIGHEST '
            f'/f'
        )
        
        result = os.popen(cmd).read()
        
        if "SUCCESS" in result:
            logger.info("ORION boot task installed successfully")
            return True
        else:
            logger.warning(f"Install result: {result}")
            return False
    except Exception as e:
        logger.error(f"Error installing boot task: {e}")
        return False


def uninstall_boot_task():
    """Remove ORION from Windows startup"""
    try:
        cmd = 'schtasks /delete /tn "ORION_Boot" /f'
        result = os.popen(cmd).read()
        logger.info("ORION boot task removed")
        return True
    except Exception as e:
        logger.error(f"Error uninstalling boot task: {e}")
        return False


def run_orion_boot(max_runtime_minutes: int = 30):
    """
    Main boot function.
    Starts ORION and processes pending tasks.
    """
    logger.info("=" * 60)
    logger.info("ORION BOOT STARTED")
    logger.info("=" * 60)
    
    try:
        # Import ORION components
        from orion.daemon import ORIONDaemon
        from orion.task_scheduler import get_task_scheduler
        
        # Initialize daemon
        logger.info("Initializing ORION daemon...")
        daemon = ORIONDaemon()
        daemon.run_background()
        
        # Get task scheduler (already started by daemon)
        scheduler = get_task_scheduler()
        
        # Process pending tasks
        logger.info("Processing pending tasks...")
        processed = scheduler.process_pending_tasks()
        logger.info(f"Processed {processed} pending tasks")
        
        # Keep running for max_runtime_minutes to handle any scheduled tasks
        start_time = time.time()
        max_runtime = max_runtime_minutes * 60
        
        logger.info(f"Running for up to {max_runtime_minutes} minutes...")
        
        while time.time() - start_time < max_runtime:
            # Check for new tasks
            processed = scheduler.process_pending_tasks()
            if processed > 0:
                logger.info(f"Processed {processed} tasks")
            
            # Check for shutdown signal
            if daemon.should_stop:
                logger.info("Shutdown signal received")
                break
            
            time.sleep(30)  # Check every 30 seconds
        
        # Cleanup
        logger.info("Boot processing completed")
        daemon.should_stop = True
        
    except Exception as e:
        logger.error(f"Error during boot: {e}")
        raise


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--install":
            install_boot_task()
            return
        elif sys.argv[1] == "--uninstall":
            uninstall_boot_task()
            return
        elif sys.argv[1] == "--help":
            print(__doc__)
            return
    
    # Run boot processing
    run_orion_boot()


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received, exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    main()
