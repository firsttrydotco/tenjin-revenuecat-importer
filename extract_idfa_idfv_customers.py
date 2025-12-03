#!/usr/bin/env python3
"""
Script to extract attribution identifier combinations from RevenueCat Customers CSV file
and export them to a CSV file with two columns: idfa/idfv (iOS) or gaid/android_id (Android)

Note: Both identifiers are then sent simultaneously to Tenjin for each user.
"""

import csv
import sys
from collections import OrderedDict


def extract_idfa_idfv_customers(csv_file, output_file):
    """
    Extract unique attribution identifier combinations from Customers CSV file
    Supports iOS (IDFA/IDFV) and Android (GAID/Android ID)

    Args:
        csv_file: Path to input CSV file
        output_file: Path to output CSV file
    """
    # Use OrderedDict to keep order and avoid duplicates
    combinations = OrderedDict()

    total_rows = 0
    rows_with_data = 0

    print(f"Reading file {csv_file}...")

    with open(csv_file, 'r', encoding='utf-8') as f:
        # Use semicolon delimiter and handle quotes
        reader = csv.DictReader(f, delimiter=';', quotechar='"')

        for row in reader:
            total_rows += 1

            # Display progress every 50000 records (larger file)
            if total_rows % 50000 == 0:
                print(f"Processed {total_rows} lines, found {len(combinations)} unique combinations...")

            # Get IDFA and IDFV directly from columns
            idfa = row.get('idfa', '').strip()
            idfv = row.get('idfv', '').strip()

            # If at least one exists, add it
            if idfa or idfv:
                rows_with_data += 1
                # Use tuple as key to avoid duplicates
                key = (idfa, idfv)
                combinations[key] = True

    print(f"\nProcessing complete:")
    print(f"  - Total lines: {total_rows}")
    print(f"  - Lines with IDFA/IDFV: {rows_with_data}")
    print(f"  - Unique combinations: {len(combinations)}")

    # Write results to output file
    print(f"\nWriting results to {output_file}...")

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow(['idfa', 'idfv'])

        # Write all combinations
        for (idfa, idfv) in combinations.keys():
            writer.writerow([idfa, idfv])

    print(f"✓ Extraction complete! {len(combinations)} combinations exported.")


if __name__ == '__main__':
    # Input file
    input_file = 'idfv_not_null.csv'

    # Output file
    output_file = 'idfa_idfv_customers.csv'

    # Allow passing arguments via command line
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    try:
        extract_idfa_idfv_customers(input_file, output_file)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
