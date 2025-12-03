#!/usr/bin/env python3
"""
Script to send attributions to Tenjin Import Attribution API

Sends simultaneously advertising_id (IDFA/GAID) + developer_device_id (IDFV/Android ID)
for each user, enabling better attribution even if one identifier is missing.
"""

import csv
import requests
import time
import sys
import os
from requests.auth import HTTPBasicAuth


class TenjinImporter:
    """Client to send attributions to Tenjin"""

    def __init__(self, sdk_key, bundle_id, platform='ios', batch_size=100, delay=0.1):
        """
        Initialize Tenjin client

        Args:
            sdk_key: Tenjin SDK key for authentication
            bundle_id: Application bundle ID
            platform: Platform (ios, android, etc.)
            batch_size: Number of requests before pause
            delay: Delay between requests (in seconds)
        """
        self.sdk_key = sdk_key
        self.bundle_id = bundle_id
        self.platform = platform
        self.batch_size = batch_size
        self.delay = delay
        self.api_url = 'https://track.tenjin.io/v0/import_attribution'

        # Statistics
        self.total_sent = 0
        self.total_success = 0
        self.total_errors = 0
        self.errors = []

    def send_attribution(self, advertising_id, developer_device_id):
        """
        Send attribution to Tenjin
        Sends both identifiers simultaneously (advertising_id + developer_device_id)

        Args:
            advertising_id: IDFA (iOS) or GAID (Android) - can be empty or None
            developer_device_id: IDFV (iOS) or Android ID (Android) - required

        Returns:
            tuple: (success: bool, status_code: int, response_text: str)
        """
        # Prepare parameters
        params = {
            'bundle_id': self.bundle_id,
            'platform': self.platform,
        }

        # Add advertising_id only if not empty
        if advertising_id:
            params['advertising_id'] = advertising_id

        # Add developer_device_id (required for iOS)
        if developer_device_id:
            params['developer_device_id'] = developer_device_id

        try:
            # Send request with Basic Auth authentication
            response = requests.post(
                self.api_url,
                params=params,
                auth=HTTPBasicAuth(self.sdk_key, ''),
                timeout=10
            )

            success = response.status_code in [200, 201, 204]
            return success, response.status_code, response.text

        except requests.exceptions.RequestException as e:
            return False, 0, str(e)

    def import_from_csv(self, csv_file, start_line=1, max_lines=None, dry_run=False):
        """
        Import attributions from CSV file

        Args:
            csv_file: Path to CSV file
            start_line: Start line (1 = first line after header)
            max_lines: Maximum number of lines to process (None = all)
            dry_run: If True, simulates sending without making real requests
        """
        print(f"\n{'='*70}")
        print(f"📤 Importing attributions to Tenjin")
        print(f"{'='*70}")
        print(f"File: {csv_file}")
        print(f"Bundle ID: {self.bundle_id}")
        print(f"Platform: {self.platform}")
        print(f"Start line: {start_line}")
        print(f"Max lines: {max_lines if max_lines else 'All'}")
        print(f"Mode: {'DRY RUN (simulation)' if dry_run else 'PRODUCTION'}")
        print(f"{'='*70}\n")

        if dry_run:
            print("⚠️  DRY RUN MODE - No requests will be sent\n")

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            current_line = 0
            processed = 0

            for row in reader:
                current_line += 1

                # Ignore lines before start_line
                if current_line < start_line:
                    continue

                # Stop if max_lines reached
                if max_lines and processed >= max_lines:
                    print(f"\n✓ Limit of {max_lines} lines reached")
                    break

                advertising_id = row.get('advertising_id', '').strip()
                developer_device_id = row.get('developer_device_id', '').strip()

                # Validate we have at least one identifier
                if not advertising_id and not developer_device_id:
                    print(f"⚠️  Line {current_line}: No identifier found, skipped")
                    continue

                processed += 1

                if dry_run:
                    # Simulation mode
                    print(f"[DRY RUN] Line {current_line}: "
                          f"IDFA={advertising_id[:8] if advertising_id else 'empty'}..., "
                          f"IDFV={developer_device_id[:8]}...")
                    self.total_success += 1
                else:
                    # Real send
                    success, status_code, response = self.send_attribution(
                        advertising_id,
                        developer_device_id
                    )

                    self.total_sent += 1

                    if success:
                        self.total_success += 1
                        if processed % 10 == 0:
                            print(f"✓ Line {current_line}: Sent successfully "
                                  f"({self.total_success}/{self.total_sent})")
                    else:
                        self.total_errors += 1
                        error_msg = f"Line {current_line}: Error {status_code} - {response}"
                        print(f"✗ {error_msg}")
                        self.errors.append(error_msg)

                        # If too many consecutive errors, stop
                        if self.total_errors >= 10 and self.total_success == 0:
                            print("\n❌ Too many consecutive errors, stopping import")
                            break

                    # Pause between requests to avoid rate limiting
                    if processed % self.batch_size == 0:
                        print(f"⏸  Pause after {processed} requests...")
                        time.sleep(1)
                    else:
                        time.sleep(self.delay)

        # Display final statistics
        self.print_summary()

    def print_summary(self):
        """Display summary of results"""
        print(f"\n{'='*70}")
        print(f"📊 Import summary")
        print(f"{'='*70}")
        print(f"Total sent: {self.total_sent}")
        print(f"✓ Success: {self.total_success}")
        print(f"✗ Errors: {self.total_errors}")

        if self.total_sent > 0:
            success_rate = (self.total_success / self.total_sent) * 100
            print(f"Success rate: {success_rate:.1f}%")

        if self.errors:
            print(f"\n⚠️  First errors:")
            for error in self.errors[:5]:
                print(f"  - {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} other errors")

        print(f"{'='*70}\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Send IDFA/IDFV attributions to Tenjin API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:

  # Test with 10 lines only (dry run)
  python3 send_to_tenjin.py --dry-run --max-lines 10

  # Real test with 10 lines
  python3 send_to_tenjin.py --max-lines 10

  # Send all data
  python3 send_to_tenjin.py

  # Resume from line 1000
  python3 send_to_tenjin.py --start-line 1000

  # Use different file
  python3 send_to_tenjin.py --file tenjin_formatted_transactions.csv
        """
    )

    parser.add_argument(
        '--file',
        default='tenjin_formatted.csv',
        help='CSV file to import (default: tenjin_formatted.csv)'
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
        default=100,
        help='Number of requests before long pause (default: 100)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.1,
        help='Delay between requests in seconds (default: 0.1)'
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

    # Validate bundle ID
    if not args.bundle_id:
        print("❌ Error: Bundle ID is required.")
        print("   Use --bundle-id argument")
        sys.exit(1)

    # Create importer
    importer = TenjinImporter(
        sdk_key=args.sdk_key,
        bundle_id=args.bundle_id,
        platform=args.platform,
        batch_size=args.batch_size,
        delay=args.delay
    )

    # Ask for confirmation if not dry-run and many lines
    if not args.dry_run and not args.max_lines:
        print("⚠️  You are about to send ALL data to Tenjin.")
        response = input("Are you sure you want to continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    try:
        # Launch import
        importer.import_from_csv(
            csv_file=args.file,
            start_line=args.start_line,
            max_lines=args.max_lines,
            dry_run=args.dry_run
        )
    except FileNotFoundError:
        print(f"❌ Error: The file '{args.file}' does not exist.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Import interrupted by user")
        importer.print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
