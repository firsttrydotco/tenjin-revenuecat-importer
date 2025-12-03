#!/usr/bin/env python3
"""
Script to format IDFA/IDFV (iOS) or GAID/Android ID (Android) combinations for Tenjin API
Required format: lowercase without dashes

Note: Both identifiers (advertising_id + developer_device_id) are sent simultaneously to Tenjin
for each user, enabling better attribution even if one identifier is missing.
"""

import csv
import sys


def format_uuid_for_tenjin(uuid_str):
    """
    Convert UUID to Tenjin format (lowercase, without dashes)

    Args:
        uuid_str: UUID in standard format (ex: F024E65F-3DD9-4F16-9837-26BCEF192D68)

    Returns:
        UUID formatted for Tenjin (ex: f024e65f3dd94f16983726bcef192d68)
    """
    if not uuid_str:
        return ""

    # Remove dashes and convert to lowercase
    return uuid_str.replace("-", "").lower()


def format_csv_for_tenjin(input_file, output_file, skip_zero_idfa=True):
    """
    Format CSV file of IDFA/IDFV combinations for Tenjin API

    Args:
        input_file: Input CSV file with idfa,idfv columns
        output_file: Output CSV file formatted for Tenjin
        skip_zero_idfa: If True, ignore lines with zero IDFA (default: True)
    """
    total_rows = 0
    formatted_rows = 0
    skipped_zero_idfa = 0

    print(f"Reading file {input_file}...")

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:

        reader = csv.DictReader(infile)
        writer = csv.writer(outfile)

        # Write header with column names for Tenjin API
        writer.writerow(['advertising_id', 'developer_device_id'])

        for row in reader:
            total_rows += 1

            # Display progress every 50000 records
            if total_rows % 50000 == 0:
                print(f"Processed {total_rows} lines, formatted {formatted_rows} lines...")

            idfa = row.get('idfa', '').strip()
            idfv = row.get('idfv', '').strip()

            # Check if IDFA is zero
            if skip_zero_idfa and idfa == '00000000-0000-0000-0000-000000000000':
                skipped_zero_idfa += 1
                continue

            # Format UUIDs for Tenjin (lowercase, without dashes)
            advertising_id = format_uuid_for_tenjin(idfa)
            developer_device_id = format_uuid_for_tenjin(idfv)

            # Write formatted line
            writer.writerow([advertising_id, developer_device_id])
            formatted_rows += 1

    print(f"\n✓ Formatting complete!")
    print(f"  - Total lines read: {total_rows}")
    print(f"  - Formatted lines: {formatted_rows}")
    if skip_zero_idfa:
        print(f"  - Zero IDFAs ignored: {skipped_zero_idfa}")
    print(f"\nOutput file: {output_file}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Format IDFA/IDFV for Tenjin Import Attribution API'
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default='idfa_idfv_customers.csv',
        help='Input CSV file (default: idfa_idfv_customers.csv)'
    )
    parser.add_argument(
        'output_file',
        nargs='?',
        default='tenjin_formatted.csv',
        help='Output CSV file (default: tenjin_formatted.csv)'
    )
    parser.add_argument(
        '--keep-zero-idfa',
        action='store_true',
        help='Keep zero IDFAs (default: ignore them)'
    )

    args = parser.parse_args()

    try:
        format_csv_for_tenjin(
            args.input_file,
            args.output_file,
            skip_zero_idfa=not args.keep_zero_idfa
        )
    except FileNotFoundError:
        print(f"Error: The file '{args.input_file}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
