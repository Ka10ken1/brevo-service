#!/usr/bin/env python3

import time
import logging
import schedule
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path
from .brevo_service import get_existing_contacts, send_info_email, handle_csv

# Setup cross-platform logging
log_file = Path("brevo_service.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class BrevoBackgroundService:
    def __init__(self):
        self.running = False
        self.start_time = datetime.now()
        self.platform = platform.system()
        logger.info(f"Brevo Background Service initialized on {self.platform}")

        self.csv_input_dir = Path(os.getenv("CSV_INPUT_DIR", "csv_input"))
        self.csv_processed_dir = Path(os.getenv("CSV_PROCESSED_DIR", "csv_processed"))
        self.csv_failed_dir = Path(os.getenv("CSV_FAILED_DIR", "csv_failed"))

        self._setup_directories()

    def _setup_directories(self):
        directories = [
            Path("pending_csv"),
            self.csv_input_dir,
            self.csv_processed_dir,
            self.csv_failed_dir,
            Path("logs") if self.platform == "Windows" else None,
        ]

        for directory in directories:
            if directory and not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")

        logger.info("CSV Processing Directories:")
        logger.info(
            f"  - Input (place CSV files here): {self.csv_input_dir.absolute()}"
        )
        logger.info(f"  - Processed (successful): {self.csv_processed_dir.absolute()}")
        logger.info(f"  - Failed (errors): {self.csv_failed_dir.absolute()}")

    def health_check(self):
        try:
            api_key = os.getenv("BREVO_API_KEY")
            if not api_key:
                logger.warning("BREVO_API_KEY not configured")
                return False

            contacts = get_existing_contacts()
            logger.info(f"Health check passed - {len(contacts)} contacts found")
            return True

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def process_pending_tasks(self):
        try:
            pending_dir = Path("pending_csv")
            if pending_dir.exists():
                csv_files = list(pending_dir.glob("*.csv"))
                if csv_files:
                    logger.info(f"Found {len(csv_files)} pending CSV files to process")
                    for csv_file in csv_files:
                        self._process_single_csv(csv_file, source="pending")
                else:
                    logger.debug("No pending CSV files found")

            logger.info("Pending tasks check completed")

        except Exception as e:
            logger.error(f"Error processing pending tasks: {str(e)}")

    def daily_csv_processing(self):
        try:
            if not self.csv_input_dir.exists():
                logger.warning(
                    f"CSV input directory does not exist: {self.csv_input_dir}"
                )
                return

            csv_files = list(self.csv_input_dir.glob("*.csv"))
            if not csv_files:
                logger.info(f"No CSV files found in {self.csv_input_dir}")
                return

            logger.info(f"Starting daily CSV processing - found {len(csv_files)} files")

            for csv_file in csv_files:
                self._process_single_csv(csv_file, source="daily")

            logger.info("Daily CSV processing completed")

        except Exception as e:
            logger.error(f"Error during daily CSV processing: {str(e)}")

    def _process_single_csv(self, csv_file: Path, source: str = "unknown"):
        """Process a single CSV file"""
        try:
            logger.info(f"Processing CSV file: {csv_file.name} (source: {source})")

            # Read and process the CSV file
            with open(csv_file, "rb") as f:
                csv_content = f.read()

            # Process with the existing handle_csv function
            results = handle_csv(csv_content)

            # Log results
            total_processed = len(results.get("added_contacts", [])) + len(
                results.get("info_sent", [])
            )
            total_errors = len(results.get("errors", []))

            logger.info(f"CSV processing completed for {csv_file.name}:")
            logger.info(f"  - Successfully processed: {total_processed} contacts")
            logger.info(f"  - Errors: {total_errors} contacts")

            if total_errors > 0:
                logger.warning(f"Some contacts failed to process in {csv_file.name}")
                for error in results.get("errors", []):
                    logger.warning(
                        f"  - {error.get('email', 'Unknown')}: {error.get('error', 'Unknown error')}"
                    )

            # Move file to appropriate directory
            if total_errors == 0:
                destination = (
                    self.csv_processed_dir
                    / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{csv_file.name}"
                )
                shutil.move(str(csv_file), str(destination))
                logger.info(f"Moved successful file to: {destination}")
            else:
                destination = (
                    self.csv_failed_dir
                    / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{csv_file.name}"
                )
                shutil.move(str(csv_file), str(destination))
                logger.warning(f"Moved file with errors to: {destination}")

        except Exception as e:
            logger.error(f"Error processing CSV file {csv_file.name}: {str(e)}")
            try:
                # Move failed file to failed directory
                destination = (
                    self.csv_failed_dir
                    / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_ERROR_{csv_file.name}"
                )
                shutil.move(str(csv_file), str(destination))
                logger.error(f"Moved failed file to: {destination}")
            except Exception as move_error:
                logger.error(f"Failed to move error file: {move_error}")

    def cleanup_logs(self):
        """Clean up old log files"""
        try:
            log_files = [
                Path("brevo_service.log"),
                Path("api_service.log"),
                Path("background_service.log"),
            ]

            for log_file in log_files:
                if log_file.exists():
                    if log_file.stat().st_size > 10 * 1024 * 1024:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_name = f"{log_file.stem}_{timestamp}.log"

                        if self.platform == "Windows" and Path("logs").exists():
                            backup_path = Path("logs") / backup_name
                        else:
                            backup_path = Path(backup_name)

                        log_file.rename(backup_path)
                        logger.info(f"Log file rotated to {backup_path}")

        except Exception as e:
            logger.error(f"Error during log cleanup: {str(e)}")

    def send_daily_report(self):
        """Send daily service report"""
        try:
            uptime = datetime.now() - self.start_time
            logger.info(f"Daily report: Service uptime {uptime}")
            logger.info("Daily service report completed")

        except Exception as e:
            logger.error(f"Error sending daily report: {str(e)}")

    def manual_csv_processing(self):
        """Manually trigger CSV processing (for testing/immediate processing)"""
        logger.info("Manual CSV processing triggered")
        self.daily_csv_processing()

    def start(self):
        """Start the background service"""
        self.running = True
        logger.info("Starting Brevo Background Service...")

        # Schedule tasks
        schedule.every(5).minutes.do(self.health_check)
        schedule.every(10).minutes.do(self.process_pending_tasks)
        schedule.every().hour.do(self.cleanup_logs)
        schedule.every().day.at("09:00").do(self.send_daily_report)
        schedule.every().day.at("11:00").do(
            self.daily_csv_processing
        )  # Run at 11 AM daily

        logger.info("Background service started successfully")
        logger.info("Scheduled tasks:")
        logger.info("  - Health check: Every 5 minutes")
        logger.info("  - Process pending tasks: Every 10 minutes")
        logger.info("  - Log cleanup: Every hour")
        logger.info("  - Daily report: 09:00 daily")
        logger.info("  - Daily CSV processing: 11:00 daily")

        self.health_check()

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(30)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()

    def stop(self):
        """Stop the background service"""
        self.running = False
        logger.info("Brevo Background Service stopped")


def main():
    """Main entry point for background service"""
    service = BrevoBackgroundService()

    try:
        service.start()
    except Exception as e:
        logger.error(f"Critical error in background service: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
