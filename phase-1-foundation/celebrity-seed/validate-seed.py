#!/usr/bin/env python3
"""
Celebrity Seed Data Validation Script
Validates the integrity and completeness of seeded celebrity data in DynamoDB.
"""

import boto3
import argparse
import sys
from datetime import datetime
import json
import re

class CelebirtySeedValidator:
    """Validates seeded celebrity data"""

    def __init__(self, table_name, region):
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        self.region = region
        self.validation_results = {
            'total_records': 0,
            'valid_records': 0,
            'errors': [],
            'warnings': [],
            'details': {}
        }

    def scan_all_items(self):
        """Scan all items from the table"""
        items = []
        try:
            response = self.table.scan()
            items.extend(response.get('Items', []))

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))

            return items
        except Exception as e:
            self.validation_results['errors'].append(f"Scan error: {str(e)}")
            return []

    def validate_item(self, item, index):
        """Validate a single item"""
        errors = []
        warnings = []

        # Check required fields
        required_fields = ['celebrity_id', 'name', 'birth_date', 'nationality', 'occupation']
        for field in required_fields:
            if field not in item:
                errors.append(f"Item {index}: Missing required field '{field}'")

        # Validate celebrity_id format
        if 'celebrity_id' in item:
            celeb_id = item['celebrity_id']
            if not re.match(r'^celeb_\d{3}$', celeb_id):
                warnings.append(f"Item {index}: Celebrity ID '{celeb_id}' doesn't match expected format 'celeb_NNN'")

        # Validate birth_date format (ISO 8601)
        if 'birth_date' in item:
            birth_date = item['birth_date']
            try:
                datetime.strptime(birth_date, '%Y-%m-%d')
            except ValueError:
                errors.append(f"Item {index}: Invalid birth_date format '{birth_date}' (expected YYYY-MM-DD)")

        # Validate nationality is not empty
        if 'nationality' in item and not item['nationality']:
            errors.append(f"Item {index}: Nationality cannot be empty")

        # Validate occupation is a list/array
        if 'occupation' in item:
            if not isinstance(item['occupation'], list):
                errors.append(f"Item {index}: Occupation should be an array")
            elif len(item['occupation']) == 0:
                warnings.append(f"Item {index}: Occupation array is empty")

        # Check for is_active field
        if 'is_active' not in item:
            warnings.append(f"Item {index}: Missing 'is_active' field")
        elif item.get('is_active') != True:
            warnings.append(f"Item {index}: is_active is not True (value: {item.get('is_active')})")

        return errors, warnings

    def check_duplicates(self, items):
        """Check for duplicate celebrity IDs"""
        duplicates = []
        celeb_ids = [item.get('celebrity_id') for item in items if 'celebrity_id' in item]

        seen = set()
        for celeb_id in celeb_ids:
            if celeb_id in seen:
                duplicates.append(celeb_id)
            seen.add(celeb_id)

        return duplicates

    def run_validation(self):
        """Run complete validation"""
        print("\n" + "="*70)
        print("Celebrity Seed Data Validation")
        print(f"Table: {self.table_name}")
        print(f"Region: {self.region}")
        print("="*70 + "\n")

        # Scan all items
        print("Scanning table...")
        items = self.scan_all_items()
        self.validation_results['total_records'] = len(items)

        if len(items) == 0:
            print("✗ No records found in table!")
            return False

        print(f"✓ Found {len(items)} records\n")

        # Validate each item
        print("Validating individual records...")
        for idx, item in enumerate(items, 1):
            errors, warnings = self.validate_item(item, idx)

            if errors:
                self.validation_results['errors'].extend(errors)
            if warnings:
                self.validation_results['warnings'].extend(warnings)

            if not errors:
                self.validation_results['valid_records'] += 1

        # Check for duplicates
        print("Checking for duplicates...")
        duplicates = self.check_duplicates(items)
        if duplicates:
            self.validation_results['errors'].append(f"Found duplicate celebrity IDs: {duplicates}")
        else:
            print("✓ No duplicates found")

        # Count records by type
        print("Analyzing data...")
        metadata_records = sum(1 for item in items if 'source_type#timestamp' in item and item['source_type#timestamp'].startswith('metadata#'))
        scraper_records = sum(1 for item in items if 'source_type#timestamp' in item and not item['source_type#timestamp'].startswith('metadata#'))

        self.validation_results['details'] = {
            'metadata_records': metadata_records,
            'scraper_records': scraper_records,
            'total_valid': self.validation_results['valid_records'],
            'total_errors': len(self.validation_results['errors']),
            'total_warnings': len(self.validation_results['warnings'])
        }

        # Print results
        self.print_summary()

        # Return success if no errors and all records valid
        return len(self.validation_results['errors']) == 0

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*70)
        print("Validation Summary")
        print("="*70)

        details = self.validation_results['details']
        print(f"\n✓ Total Records: {self.validation_results['total_records']}")
        print(f"✓ Valid Records: {self.validation_results['valid_records']}")
        print(f"  - Metadata records: {details.get('metadata_records', 0)}")
        print(f"  - Scraper records: {details.get('scraper_records', 0)}")

        if self.validation_results['errors']:
            print(f"\n✗ Errors ({len(self.validation_results['errors'])}):")
            for error in self.validation_results['errors'][:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.validation_results['errors']) > 10:
                print(f"  ... and {len(self.validation_results['errors']) - 10} more")

        if self.validation_results['warnings']:
            print(f"\n⚠ Warnings ({len(self.validation_results['warnings'])}):")
            for warning in self.validation_results['warnings'][:10]:  # Show first 10
                print(f"  - {warning}")
            if len(self.validation_results['warnings']) > 10:
                print(f"  ... and {len(self.validation_results['warnings']) - 10} more")

        print("\n" + "="*70)
        if len(self.validation_results['errors']) == 0:
            print("✓ VALIDATION PASSED: All data integrity checks successful!")
        else:
            print("✗ VALIDATION FAILED: Please review errors above")
        print("="*70 + "\n")

    def export_report(self, filename='validation-report.json'):
        """Export validation report to JSON"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
            print(f"✓ Validation report exported to {filename}")
        except Exception as e:
            print(f"✗ Failed to export report: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Validate celebrity seed data in DynamoDB')
    parser.add_argument('--table', default='celebrity-database', help='Table name (default: celebrity-database)')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--export', action='store_true', help='Export validation report to JSON')
    parser.add_argument('--report-file', default='validation-report.json', help='Report file name')

    args = parser.parse_args()

    validator = CelebirtySeedValidator(args.table, args.region)
    success = validator.run_validation()

    if args.export:
        validator.export_report(args.report_file)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
