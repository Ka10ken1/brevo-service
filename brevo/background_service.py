#!/usr/bin/env python3

import time
import logging
import schedule
import os
import platform
from datetime import datetime, timedelta
from pathlib import Path
from .brevo_service import get_existing_contacts, send_info_email, handle_csv

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

        self.csv_base_path = os.getenv("CSV_BASE_PATH", "")
        self.csv_filename_pattern = os.getenv(
            "CSV_FILENAME_PATTERN", "applications_{date}_past_1days"
        )
        self.csv_file_extension = os.getenv("CSV_FILE_EXTENSION", ".csv")

        if not self.csv_base_path:
            logger.error("CSV_BASE_PATH is required! Please set it in your .env file.")
            raise ValueError("CSV_BASE_PATH environment variable is required")

        self._setup_directories()
        self._log_configuration()

    def _setup_directories(self):
        if self.platform == "Windows":
            logs_dir = Path("logs")
            if not logs_dir.exists():
                logs_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {logs_dir}")

    def _log_configuration(self):
        logger.info("Dynamic CSV Path Configuration:")
        logger.info(f"  - Base Path: {self.csv_base_path}")
        logger.info(f"  - Filename Pattern: {self.csv_filename_pattern}")
        logger.info(f"  - File Extension: {self.csv_file_extension}")

        today = datetime.now()
        example_path = self._generate_csv_path(today)
        logger.info(f"  - Today's Expected Path: {example_path}")

    def _generate_csv_path(self, date: datetime) -> Path:
        """Generate the CSV file path for a given date"""
        date_str = date.strftime("%Y%m%d")
        filename = self.csv_filename_pattern.format(date=date_str)
        filename += self.csv_file_extension

        return Path(self.csv_base_path) / filename

    def _find_csv_file_for_date(self, date: datetime) -> Path:
        """Find CSV file for a specific date"""
        expected_path = self._generate_csv_path(date)

        if expected_path.exists():
            logger.info(f"Found CSV file: {expected_path}")
            return expected_path
        else:
            logger.warning(f"Expected CSV file not found: {expected_path}")

            # Show available CSV files in the base directory for debugging
            base_path = Path(self.csv_base_path)
            if base_path.exists():
                all_csv_files = list(base_path.glob("*.csv"))
                if all_csv_files:
                    logger.info(f"Available CSV files in {base_path}:")
                    for file in sorted(all_csv_files[-5:]):  # Show last 5 files
                        logger.info(f"  - {file.name}")
                    if len(all_csv_files) > 5:
                        logger.info(f"  ... and {len(all_csv_files) - 5} more files")
                else:
                    logger.warning(f"No CSV files found in base directory: {base_path}")
            else:
                logger.error(f"Base CSV directory does not exist: {base_path}")

            return None

    def test_dynamic_path_configuration(self):
        logger.info("=== Testing Dynamic Path Configuration ===")

        logger.info("Configuration:")
        logger.info(f"  - Base Path: {self.csv_base_path}")
        logger.info(f"  - Filename Pattern: {self.csv_filename_pattern}")
        logger.info(f"  - File Extension: {self.csv_file_extension}")

        # Test for today and yesterday
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        for test_date in [today, yesterday]:
            date_str = test_date.strftime("%Y-%m-%d")
            logger.info(f"\nTesting for {date_str}:")

            expected_path = self._generate_csv_path(test_date)
            logger.info(f"  - Expected file: {expected_path}")

            if expected_path.exists():
                logger.info(f"  - ✅ File exists!")
                file_size = expected_path.stat().st_size
                modified_time = datetime.fromtimestamp(expected_path.stat().st_mtime)
                logger.info(f"  - File size: {file_size:,} bytes")
                logger.info(
                    f"  - Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                logger.info(f"  - ❌ File not found")

        base_path = Path(self.csv_base_path)
        if base_path.exists():
            all_csv_files = list(base_path.glob("*.csv"))
            if all_csv_files:
                logger.info(f"\nAll CSV files in {base_path}:")
                for file in sorted(all_csv_files):
                    file_size = file.stat().st_size
                    modified_time = datetime.fromtimestamp(file.stat().st_mtime)
                    logger.info(
                        f"  - {file.name} ({file_size:,} bytes, modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')})"
                    )
            else:
                logger.warning(f"No CSV files found in {base_path}")
        else:
            logger.error(f"Base directory does not exist: {base_path}")

        logger.info("=== End Configuration Test ===")
        return True

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

    def daily_csv_processing(self):
        """Process CSV files for today's date and optionally yesterday's if today's is missing"""
        try:
            today = datetime.now()
            logger.info(
                f"Starting daily CSV processing for {today.strftime('%Y-%m-%d')}"
            )

            csv_file = self._find_csv_file_for_date(today)

            if not csv_file:
                yesterday = today - timedelta(days=1)
                logger.info(
                    f"No file found for today, trying yesterday ({yesterday.strftime('%Y-%m-%d')})"
                )
                csv_file = self._find_csv_file_for_date(yesterday)

            if not csv_file:
                logger.warning("No CSV file found for processing")
                return

            logger.info(f"Processing CSV file: {csv_file}")
            self._process_csv_file(csv_file)

            logger.info("Daily CSV processing completed")

        except Exception as e:
            logger.error(f"Error during daily CSV processing: {str(e)}")

    def manual_csv_processing_for_date(self, date_str: str):
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            logger.info(f"Manual CSV processing for {date_str}")

            csv_file = self._find_csv_file_for_date(target_date)

            if not csv_file:
                logger.warning(f"No CSV file found for date: {date_str}")
                return

            logger.info(f"Processing CSV file: {csv_file}")
            self._process_csv_file(csv_file)

            logger.info(f"Manual CSV processing completed for {date_str}")

        except ValueError:
            logger.error(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
        except Exception as e:
            logger.error(f"Error during manual CSV processing for {date_str}: {str(e)}")

    def _process_csv_file(self, csv_file: Path):
        """Process a single CSV file"""
        try:
            logger.info(f"Processing CSV file: {csv_file.name}")

            with open(csv_file, "rb") as f:
                csv_content = f.read()

            results = handle_csv(csv_content)

            total_processed = len(results.get("added_contacts", [])) + len(
                results.get("info_sent", [])
            )
            total_errors = len(results.get("errors", []))

            logger.info(f"CSV processing completed for {csv_file.name}:")
            logger.info(f"  - Successfully processed: {total_processed} contacts")
            logger.info(
                f"  - New contacts added: {len(results.get('added_contacts', []))}"
            )
            logger.info(f"  - Info emails sent: {len(results.get('info_sent', []))}")
            logger.info(f"  - Errors: {total_errors} contacts")

            if total_errors > 0:
                logger.warning(f"Some contacts failed to process in {csv_file.name}")
                for error in results.get("errors", [])[:5]:  # Show first 5 errors
                    logger.warning(
                        f"  - {error.get('email', 'Unknown')}: {error.get('error', 'Unknown error')}"
                    )
                if total_errors > 5:
                    logger.warning(f"  ... and {total_errors - 5} more errors")

            logger.info(f"File processed successfully: {csv_file}")

        except Exception as e:
            logger.error(f"Error processing CSV file {csv_file.name}: {str(e)}")
            raise

    def cleanup_logs(self):
        try:
            log_files = [
                Path("brevo_service.log"),
                Path("api_service.log"),
                Path("background_service.log"),
            ]

            for log_file in log_files:
                if log_file.exists():
                    if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
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
        try:
            uptime = datetime.now() - self.start_time
            logger.info(f"Daily report: Service uptime {uptime}")

            today = datetime.now()
            expected_path = self._generate_csv_path(today)
            if expected_path.exists():
                file_size = expected_path.stat().st_size
                modified_time = datetime.fromtimestamp(expected_path.stat().st_mtime)
                logger.info(f"Daily report: Today's CSV file exists at {expected_path}")
                logger.info(
                    f"Daily report: File size: {file_size:,} bytes, modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                logger.warning(
                    f"Daily report: Today's CSV file not found at {expected_path}"
                )

            logger.info("Daily service report completed")

        except Exception as e:
            logger.error(f"Error sending daily report: {str(e)}")

    def manual_csv_processing(self):
        logger.info("Manual CSV processing triggered")
        self.daily_csv_processing()

    def start(self):
        self.running = True
        logger.info("Starting Brevo Background Service...")

        schedule.every(5).minutes.do(self.health_check)
        schedule.every().hour.do(self.cleanup_logs)
        schedule.every().day.at("09:00").do(self.send_daily_report)
        schedule.every().day.at("02:00").do(
            self.daily_csv_processing
        )  # Run at 2 AM daily

        logger.info("Background service started successfully")
        logger.info("Scheduled tasks:")
        logger.info("  - Health check: Every 5 minutes")
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
        self.running = False
        logger.info("Brevo Background Service stopped")


def main():
    try:
        service = BrevoBackgroundService()
        service.start()
    except Exception as e:
        logger.error(f"Critical error in background service: {str(e)}")
        return 1

    return 0


def test_configuration():
    try:
        service = BrevoBackgroundService()
        service.test_dynamic_path_configuration()
    except Exception as e:
        logger.error(f"Configuration test failed: {str(e)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_configuration()
    else:
        exit(main())
