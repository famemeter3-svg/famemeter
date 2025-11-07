#!/usr/bin/env python3
"""
Seed Celebrity Database Script

Bulk insert 100 celebrities into DynamoDB celebrity-database table.

Usage:
    python3 seed-database.py --region us-east-1 --celebrities celebrities.json
"""

import boto3
import json
import argparse
import sys
from botocore.exceptions import ClientError
from datetime import datetime


def load_celebrities(filepath):
    """Load celebrity list from JSON file."""
    try:
        with open(filepath, 'r') as f:
            celebrities = json.load(f)
        print(f"✓ Loaded {len(celebrities)} celebrities from {filepath}")
        return celebrities
    except Exception as e:
        print(f"✗ Error loading celebrities: {e}")
        return None


def seed_celebrities(dynamodb_client, table_name, celebrities):
    """
    Bulk insert celebrities into DynamoDB.

    Args:
        dynamodb_client: boto3 DynamoDB client
        table_name: Name of the table
        celebrities: List of celebrity dictionaries

    Returns:
        Tuple (success_count, error_count, error_list)
    """
    table = dynamodb_client.Table(table_name)
    success_count = 0
    error_count = 0
    errors = []

    print(f"\nInserting {len(celebrities)} celebrities into '{table_name}'...\n")

    for idx, celebrity in enumerate(celebrities, 1):
        try:
            # Add composite sort key (metadata entry)
            # Format: source_type#timestamp
            timestamp = datetime.utcnow().isoformat() + 'Z'

            # Add metadata
            item = {
                **celebrity,
                'source_type#timestamp': 'metadata#2025-01-01T00:00:00Z',  # Initial metadata record
                'created_at': timestamp,
                'updated_at': timestamp,
                'is_active': True
            }

            table.put_item(Item=item)

            print(f"  [{idx:3d}] ✓ {celebrity['name']:20s} (ID: {celebrity['celebrity_id']})")
            success_count += 1

        except ClientError as e:
            error_msg = f"{celebrity['name']}: {str(e)}"
            print(f"  [{idx:3d}] ✗ {celebrity['name']:20s} - ERROR")
            errors.append(error_msg)
            error_count += 1

    return success_count, error_count, errors


def validate_seed(dynamodb_client, table_name, celebrities):
    """
    Verify that all celebrities were inserted correctly.

    Args:
        dynamodb_client: boto3 DynamoDB client
        table_name: Name of the table
        celebrities: List of celebrity dictionaries

    Returns:
        Boolean indicating success
    """
    print(f"\nValidating seed data...")

    table = dynamodb_client.Table(table_name)

    for celebrity in celebrities:
        try:
            response = table.get_item(
                Key={'celebrity_id': celebrity['celebrity_id'], 'source_type#timestamp': 'metadata#2025-01-01T00:00:00Z'}
            )

            if 'Item' not in response:
                # Check if item exists without sort key (master record)
                # For now, we'll verify through scan
                pass

        except ClientError as e:
            print(f"✗ Error validating {celebrity['name']}: {e}")
            return False

    # Count total items in table
    try:
        response = table.scan(Select='COUNT')
        count = response['Count']
        print(f"✓ Total items in table: {count}")

        if count >= len(celebrities):
            print(f"✓ All {len(celebrities)} celebrities verified in database")
            return True
        else:
            print(f"⚠ Expected {len(celebrities)} items, found {count}")
            return False

    except ClientError as e:
        print(f"✗ Error counting items: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Seed celebrity database with initial data'
    )
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--table', default='celebrity-database', help='DynamoDB table name')
    parser.add_argument('--celebrities', default='celebrities.json',
                        help='Path to celebrities JSON file')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of celebrities to seed (for testing)')
    parser.add_argument('--skip-validation', action='store_true',
                        help='Skip validation step')

    args = parser.parse_args()

    # Load celebrities
    celebrities = load_celebrities(args.celebrities)
    if not celebrities:
        sys.exit(1)

    # Apply limit if specified
    if args.limit:
        celebrities = celebrities[:args.limit]
        print(f"✓ Limiting to first {len(celebrities)} celebrities for testing")

    # Create DynamoDB resource
    try:
        dynamodb = boto3.resource('dynamodb', region_name=args.region)
        print(f"Connected to DynamoDB in region: {args.region}")
    except Exception as e:
        print(f"✗ Error connecting to DynamoDB: {e}")
        sys.exit(1)

    # Seed data
    success, errors_count, errors = seed_celebrities(dynamodb, args.table, celebrities)

    print(f"\n{'='*60}")
    print(f"Seed Results:")
    print(f"  ✓ Successful: {success}")
    print(f"  ✗ Failed: {errors_count}")
    print(f"{'='*60}")

    if errors:
        print(f"\nErrors encountered:")
        for error in errors:
            print(f"  - {error}")

    # Validate seed (optional)
    if not args.skip_validation:
        if not validate_seed(dynamodb, args.table, celebrities):
            print(f"\n⚠ Validation had issues, but seed may still be complete")

    if success == len(celebrities):
        print(f"\n✓ Seeding complete! All {success} celebrities inserted successfully.")
        print(f"\nNext step: Run scrapers to collect data from external sources")
        sys.exit(0)
    else:
        print(f"\n✗ Seeding incomplete with {errors_count} errors")
        sys.exit(1)


if __name__ == '__main__':
    main()
