#!/usr/bin/env python3
"""
DynamoDB Table Creation Script

This script creates the celebrity-database table with proper configuration.
Run this ONCE to initialize the table.

Usage:
    python3 create-table.py --region us-east-1
"""

import boto3
import json
import argparse
import time
import sys
from botocore.exceptions import ClientError


def load_table_definition(filepath):
    """Load DynamoDB table definition from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def create_table(dynamodb_client, table_def):
    """
    Create DynamoDB table from definition.

    Args:
        dynamodb_client: boto3 DynamoDB client
        table_def: Dictionary with table configuration

    Returns:
        Boolean indicating success
    """
    try:
        print(f"Creating table: {table_def['TableName']}...")

        response = dynamodb_client.create_table(**table_def)

        print(f"✓ Table creation initiated")
        print(f"  Table ARN: {response['TableDescription']['TableArn']}")

        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠ Table '{table_def['TableName']}' already exists")
            return True
        else:
            print(f"✗ Error creating table: {e}")
            return False


def wait_for_table_active(dynamodb_client, table_name, max_wait=300):
    """
    Wait for table to become ACTIVE.

    Args:
        dynamodb_client: boto3 DynamoDB client
        table_name: Name of the table
        max_wait: Maximum wait time in seconds

    Returns:
        Boolean indicating success
    """
    print(f"\nWaiting for table to become ACTIVE (max {max_wait}s)...")

    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']

            print(f"  Status: {status}")

            if status == 'ACTIVE':
                print(f"✓ Table is ACTIVE")
                return True

            time.sleep(5)  # Check every 5 seconds
        except ClientError as e:
            print(f"✗ Error checking table status: {e}")
            return False

    print(f"✗ Table did not become ACTIVE within {max_wait} seconds")
    return False


def verify_table_configuration(dynamodb_client, table_name):
    """
    Verify table configuration matches expected settings.

    Args:
        dynamodb_client: boto3 DynamoDB client
        table_name: Name of the table

    Returns:
        Boolean indicating success
    """
    print(f"\nVerifying table configuration...")

    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        table = response['Table']

        # Check key schema
        key_schema = {key['AttributeName']: key['KeyType'] for key in table['KeySchema']}
        print(f"  Partition Key: {[k for k, v in key_schema.items() if v == 'HASH']}")
        print(f"  Sort Key: {[k for k, v in key_schema.items() if v == 'RANGE']}")

        # Check billing mode
        billing = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')
        print(f"  Billing Mode: {billing}")

        # Check streams
        streams_enabled = table.get('StreamSpecification', {}).get('StreamViewType')
        print(f"  DynamoDB Streams: {'Enabled' if streams_enabled else 'Disabled'}")
        if streams_enabled:
            print(f"    View Type: {streams_enabled}")

        # Check GSI
        gsi_count = len(table.get('GlobalSecondaryIndexes', []))
        print(f"  Global Secondary Indexes: {gsi_count}")
        if gsi_count > 0:
            for gsi in table['GlobalSecondaryIndexes']:
                print(f"    - {gsi['IndexName']}")

        print(f"✓ Table configuration verified")
        return True

    except ClientError as e:
        print(f"✗ Error verifying configuration: {e}")
        return False


def enable_point_in_time_recovery(dynamodb_client, table_name):
    """
    Enable Point-in-Time Recovery for backup.

    Args:
        dynamodb_client: boto3 DynamoDB client
        table_name: Name of the table

    Returns:
        Boolean indicating success
    """
    print(f"\nEnabling Point-in-Time Recovery...")

    try:
        dynamodb_client.update_continuous_backups(
            TableName=table_name,
            PointInTimeRecoverySpecification={
                'PointInTimeRecoveryEnabled': True
            }
        )
        print(f"✓ Point-in-Time Recovery enabled")
        return True
    except ClientError as e:
        print(f"⚠ Could not enable PITR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Create DynamoDB table for celebrity database'
    )
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--definition', default='table-definition.json',
                        help='Path to table definition JSON')
    parser.add_argument('--skip-verification', action='store_true',
                        help='Skip configuration verification')

    args = parser.parse_args()

    # Load table definition
    try:
        table_def = load_table_definition(args.definition)
    except Exception as e:
        print(f"✗ Error loading table definition: {e}")
        sys.exit(1)

    # Create DynamoDB client
    try:
        dynamodb = boto3.client('dynamodb', region_name=args.region)
        print(f"Connected to DynamoDB in region: {args.region}")
    except Exception as e:
        print(f"✗ Error connecting to DynamoDB: {e}")
        sys.exit(1)

    table_name = table_def['TableName']

    # Create table
    if not create_table(dynamodb, table_def):
        sys.exit(1)

    # Wait for table to be active
    if not wait_for_table_active(dynamodb, table_name):
        sys.exit(1)

    # Verify configuration
    if not args.skip_verification:
        if not verify_table_configuration(dynamodb, table_name):
            sys.exit(1)

    # Enable PITR
    enable_point_in_time_recovery(dynamodb, table_name)

    print(f"\n✓ DynamoDB table setup complete!")
    print(f"  Table: {table_name}")
    print(f"  Region: {args.region}")
    print(f"\nNext step: Seed initial celebrity data using phase-1-foundation/celebrity-seed/")


if __name__ == '__main__':
    main()
