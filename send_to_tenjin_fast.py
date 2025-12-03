#!/usr/bin/env python3
"""
Script to send les attributions à l'API Tenjin Import Attribution
Optimized version avec requêtes asynchrones parallèles pour vitesse maximale

Sends simultaneously advertising_id (IDFA/GAID) + developer_device_id (IDFV/Android ID)
for each user, enabling better attribution even if one identifier is missing.
"""

import csv
import asyncio
import aiohttp
import time
import sys
import os
import logging
from datetime import datetime
from aiohttp import BasicAuth


class TenjinImporter:
    """Client to send des attributions à Tenjin with parallel requests"""

    def __init__(self, sdk_key, bundle_id, platform='ios', batch_size=1000, concurrency=50, log_file=None):
        """
        Initialize Tenjin client

        Args:
            sdk_key: Tenjin SDK key for authentication
            bundle_id: Application bundle ID
            platform: Platform (ios, android, etc.)
            batch_size: Number of requests before progress report
            concurrency: Number of concurrent requests (default: 50)
            log_file: Log file (None = no file)
        """
        self.sdk_key = sdk_key
        self.bundle_id = bundle_id
        self.platform = platform
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.api_url = 'https://track.tenjin.io/v0/import_attribution'

        # Statistiques
        self.total_sent = 0
        self.total_success = 0
        self.total_errors = 0
        self.errors = []
        self.start_time = None
        self.lock = None  # Sera créé dans la boucle d'événements

        # Configuration du logging
        self.setup_logging(log_file)

    def setup_logging(self, log_file):
        """Configure logging system"""
        # Log format
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

        # Root logger
        self.logger = logging.getLogger('TenjinImporter')
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(log_format, datefmt=date_format)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(log_format, datefmt=date_format)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    async def send_attribution(self, session, advertising_id, developer_device_id, line_number):
        """
        Send attribution to Tenjin asynchronously
        Sends simultaneously les deux identifiants (advertising_id + developer_device_id)

        Args:
            session: Session aiohttp
            advertising_id: IDFA (iOS) ou GAID (Android) - can be empty or None
            developer_device_id: IDFV (iOS) ou Android ID (Android) - required
            line_number: Line number for error logs

        Returns:
            tuple: (success: bool, status_code: int, response_text: str, line_number: int)
        """
        # Prepare parameters
        params = {
            'bundle_id': self.bundle_id,
            'platform': self.platform,
        }

        # Add advertising_id only if not empty
        if advertising_id:
            params['advertising_id'] = advertising_id

        # Add developer_device_id (required pour iOS)
        if developer_device_id:
            params['developer_device_id'] = developer_device_id

        try:
            # Send request with Basic Auth authentication
            async with session.post(
                self.api_url,
                params=params,
                auth=BasicAuth(self.sdk_key, ''),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                status_code = response.status
                response_text = await response.text()
                success = status_code in [200, 201, 204]
                return success, status_code, response_text, line_number

        except Exception as e:
            return False, 0, str(e), line_number

    async def process_batch(self, session, tasks, lock):
        """Process a batch of tasks in parallel"""
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        async with lock:
            for result in results:
                if isinstance(result, Exception):
                    self.total_sent += 1
                    self.total_errors += 1
                    error_msg = f"Exception: {str(result)[:100]}"
                    self.errors.append(error_msg)
                else:
                    success, status_code, response, line_number = result
                    self.total_sent += 1
                    
                    if success:
                        self.total_success += 1
                    else:
                        self.total_errors += 1
                        error_msg = f"Line {line_number}: HTTP {status_code} - {response[:100]}"
                        if self.total_errors <= 10:  # Limit error logs
                            self.logger.error(f"✗ {error_msg}")
                        self.errors.append(error_msg)

    async def import_from_csv_async(self, csv_file, start_line=1, max_lines=None, dry_run=False):
        """
        Import attributions from CSV file asynchronously

        Args:
            csv_file: Path to CSV file
            start_line: Start line (1 = first line after header)
            max_lines: Maximum number of lines to process (None = all)
            dry_run: If True, simulates sending without making real requests
        """
        self.start_time = time.time()

        self.logger.info("="*70)
        self.logger.info("📤 STARTING TENJIN IMPORT (ASYNC MODE)")
        self.logger.info("="*70)
        self.logger.info(f"File: {csv_file}")
        self.logger.info(f"Bundle ID: {self.bundle_id}")
        self.logger.info(f"Platform: {self.platform}")
        self.logger.info(f"Start line: {start_line}")
        self.logger.info(f"Max lines: {max_lines if max_lines else 'All'}")
        self.logger.info(f"Batch size: {self.batch_size}")
        self.logger.info(f"Concurrent requests: {self.concurrency}")
        self.logger.info(f"Mode: {'DRY RUN (simulation)' if dry_run else 'PRODUCTION'}")
        self.logger.info("="*70)

        if dry_run:
            self.logger.warning("⚠️  DRY RUN MODE - No requests will be sent")

        # Read all lines to process
        rows_to_process = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            current_line = 0
            
            for row in reader:
                current_line += 1
                
                # Ignore lines before start_line
                if current_line < start_line:
                    continue
                
                # Stop if max_lines reached
                if max_lines and len(rows_to_process) >= max_lines:
                    break
                
                advertising_id = row.get('advertising_id', '').strip()
                developer_device_id = row.get('developer_device_id', '').strip()
                
                # Validate we have at least one identifier
                if not advertising_id and not developer_device_id:
                    self.logger.warning(f"⚠️  Line {current_line}: No identifier, skipped")
                    continue
                
                rows_to_process.append((current_line, advertising_id, developer_device_id))
        
        total_rows = len(rows_to_process)
        self.logger.info(f"📋 {total_rows:,} lines to process")
        
        if dry_run:
            self.total_success = total_rows
            self.print_summary()
            return

        # Create reusable HTTP session
        connector = aiohttp.TCPConnector(limit=self.concurrency, limit_per_host=self.concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            semaphore = asyncio.Semaphore(self.concurrency)
            lock = asyncio.Lock()
            last_report_time = time.time()
            processed = 0
            
            async def send_with_semaphore(line_num, adv_id, dev_id):
                async with semaphore:
                    return await self.send_attribution(session, adv_id, dev_id, line_num)
            
            # Process in batches for progress reports
            for i in range(0, total_rows, self.batch_size):
                batch = rows_to_process[i:i + self.batch_size]
                tasks = [send_with_semaphore(line_num, adv_id, dev_id) 
                        for line_num, adv_id, dev_id in batch]
                
                await self.process_batch(session, tasks, lock)
                processed += len(batch)
                
                # Progress report
                elapsed = time.time() - last_report_time
                rate = len(batch) / elapsed if elapsed > 0 else 0
                total_elapsed = time.time() - self.start_time
                
                # Estimate remaining time
                if self.total_sent > 0:
                    avg_time_per_request = total_elapsed / self.total_sent
                    remaining = (total_rows - processed) * avg_time_per_request
                    eta = self.format_time(remaining)
                else:
                    eta = "calculating..."
                
                success_rate = (self.total_success / self.total_sent * 100) if self.total_sent > 0 else 100
                current_line = batch[-1][0] if batch else 0
                
                self.logger.info(
                    f"📊 Line {current_line:,} | "
                    f"Sent: {self.total_sent:,} | "
                    f"Success: {self.total_success:,} ({success_rate:.1f}%) | "
                    f"Errors: {self.total_errors} | "
                    f"Speed: {rate:.1f} req/s | "
                    f"ETA: {eta}"
                )
                
                last_report_time = time.time()
                
                # Stop if too many errors at start
                if self.total_errors >= 10 and self.total_success == 0:
                    self.logger.error("❌ Too many consecutive errors, stopping import")
                    break

        # Display final statistics
        self.print_summary()

    def import_from_csv(self, csv_file, start_line=1, max_lines=None, dry_run=False):
        """Synchronous wrapper for async import"""
        asyncio.run(self.import_from_csv_async(csv_file, start_line, max_lines, dry_run))

    def format_time(self, seconds):
        """Format time in seconds to readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def print_summary(self):
        """Display summary of results"""
        total_time = time.time() - self.start_time if self.start_time else 0

        self.logger.info("")
        self.logger.info("="*70)
        self.logger.info("📊 IMPORT SUMMARY")
        self.logger.info("="*70)
        self.logger.info(f"Total duration: {self.format_time(total_time)}")
        self.logger.info(f"Total sent: {self.total_sent:,}")
        self.logger.info(f"✓ Success: {self.total_success:,}")
        self.logger.info(f"✗ Errors: {self.total_errors:,}")

        if self.total_sent > 0:
            success_rate = (self.total_success / self.total_sent) * 100
            avg_rate = self.total_sent / total_time if total_time > 0 else 0
            self.logger.info(f"Success rate: {success_rate:.2f}%")
            self.logger.info(f"Average speed: {avg_rate:.2f} req/s")

        if self.errors:
            self.logger.warning(f"\n⚠️  First errors ({min(5, len(self.errors))} out of {len(self.errors)}):")
            for error in self.errors[:5]:
                self.logger.warning(f"  - {error}")
            if len(self.errors) > 5:
                self.logger.warning(f"  ... et {len(self.errors) - 5} other errors")

        self.logger.info("="*70)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Envoie les attributions IDFA/IDFV à l\'API Tenjin (fast version with logs)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:

  # Test with 10 lines
  python3 send_to_tenjin_fast.py --max-lines 10

  # Full import with logs in file
  python3 send_to_tenjin_fast.py --log-file import.log

  # Ultra-fast import (100 concurrent requests)
  python3 send_to_tenjin_fast.py --concurrency 100 --batch-size 5000

  # Resume from line 50000
  python3 send_to_tenjin_fast.py --start-line 50001 --log-file import.log
        """
    )

    parser.add_argument(
        '--file',
        default='tenjin_formatted_all.csv',
        help='File CSV à importer (default: tenjin_formatted_all.csv)'
    )
    parser.add_argument(
        '--log-file',
        help='Log file pour sauvegarder la progression'
    )
    parser.add_argument(
        '--sdk-key',
        default=os.environ.get('TENJIN_SDK_KEY', ''),
        help='Tenjin SDK Key (or set TENJIN_SDK_KEY environment variable)'
    )
    parser.add_argument(
        '--bundle-id',
        default='',
        help='Application bundle ID (required)'
    )
    parser.add_argument(
        '--platform',
        default='ios',
        choices=['ios', 'android'],
        help='Platform (default: ios)'
    )
    parser.add_argument(
        '--start-line',
        type=int,
        default=1,
        help='Start line (default: 1)'
    )
    parser.add_argument(
        '--max-lines',
        type=int,
        help='Maximum number of lines to process'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Display progress every N sends (default: 1000)'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        default=50,
        help='Number of concurrent requests (default: 50, recommended: 50-100)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulation without real sending (test)'
    )

    args = parser.parse_args()

    # Validate SDK key
    if not args.sdk_key:
        print("❌ Error: Tenjin SDK Key is required.")
        print("   Set TENJIN_SDK_KEY environment variable or use --sdk-key argument")
        sys.exit(1)

    # Create importer
    importer = TenjinImporter(
        sdk_key=args.sdk_key,
        bundle_id=args.bundle_id,
        platform=args.platform,
        batch_size=args.batch_size,
        concurrency=args.concurrency,
        log_file=args.log_file
    )

    try:
        # Launch import
        importer.import_from_csv(
            csv_file=args.file,
            start_line=args.start_line,
            max_lines=args.max_lines,
            dry_run=args.dry_run
        )
    except FileNotFoundError:
        importer.logger.error(f"❌ Error: The file '{args.file}' does not exist.")
        sys.exit(1)
    except KeyboardInterrupt:
        importer.logger.warning("\n\n⚠️  Import interrupted by user (Ctrl+C)")
        importer.print_summary()
        sys.exit(1)
    except Exception as e:
        importer.logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
