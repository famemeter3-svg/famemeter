#!/usr/bin/env python3
"""
DynamoDB Table Validation Script
Tests and validates the structure, indexes, and operational capabilities of the celebrity-database table.
"""

import boto3
import argparse
import sys
from datetime import datetime
import json

class DynamoDBTableValidator:
    """Validates DynamoDB table structure and operations"""

    def __init__(self, table_name, region):
        self.dynamodb = boto3.client('dynamodb', region_name=region)
        self.table_name = table_name
        self.region = region
        self.test_results = []

    def log_test(self, test_name, passed, message=""):
        """Log test results"""
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"  → {message}")
        self.test_results.append({"test": test_name, "passed": passed, "message": message})
        return passed

    def test_table_exists(self):
        """Test 1: Verify table exists"""
        try:
            response = self.dynamodb.describe_table(TableName=self.table_name)
            self.log_test(
                "Table Exists",
                True,
                f"Table '{self.table_name}' is {response['Table']['TableStatus']}"
            )
            return response['Table']
        except self.dynamodb.exceptions.ResourceNotFoundException:
            self.log_test("Table Exists", False, f"Table '{self.table_name}' not found")
            return None
        except Exception as e:
            self.log_test("Table Exists", False, str(e))
            return None

    def test_table_active(self, table_info):
        """Test 2: Verify table is ACTIVE"""
        if not table_info:
            return False
        status = table_info['TableStatus']
        passed = status == 'ACTIVE'
        self.log_test(
            "Table Status",
            passed,
            f"Current status: {status}" if not passed else "Table is ACTIVE"
        )
        return passed

    def test_billing_mode(self, table_info):
        """Test 3: Verify billing mode is ON_DEMAND"""
        if not table_info:
            return False
        billing_mode = table_info['BillingModeSummary']['BillingMode']
        passed = billing_mode == 'PAY_PER_REQUEST'
        self.log_test(
            "Billing Mode",
            passed,
            f"Billing mode: {billing_mode}"
        )
        return passed

    def test_partition_key(self, table_info):
        """Test 4: Verify partition key is celebrity_id"""
        if not table_info:
            return False
        key_schema = table_info['KeySchema']
        pk = next((k['AttributeName'] for k in key_schema if k['KeyType'] == 'HASH'), None)
        passed = pk == 'celebrity_id'
        self.log_test(
            "Partition Key",
            passed,
            f"Partition key: {pk}"
        )
        return passed

    def test_sort_key(self, table_info):
        """Test 5: Verify sort key is source_type#timestamp"""
        if not table_info:
            return False
        key_schema = table_info['KeySchema']
        sk = next((k['AttributeName'] for k in key_schema if k['KeyType'] == 'RANGE'), None)
        passed = sk == 'source_type#timestamp'
        self.log_test(
            "Sort Key",
            passed,
            f"Sort key: {sk}"
        )
        return passed

    def test_gsi_name_index(self, table_info):
        """Test 6: Verify name-index GSI exists and is ACTIVE"""
        if not table_info:
            return False
        gsi_list = table_info.get('GlobalSecondaryIndexes', [])
        name_index = next((g for g in gsi_list if g['IndexName'] == 'name-index'), None)

        if not name_index:
            self.log_test("GSI name-index Exists", False, "name-index not found")
            return False

        status = name_index.get('IndexStatus', 'UNKNOWN')
        passed = status == 'ACTIVE'
        self.log_test(
            "GSI name-index Status",
            passed,
            f"Status: {status}"
        )
        return passed

    def test_gsi_source_index(self, table_info):
        """Test 7: Verify source-index GSI exists and is ACTIVE"""
        if not table_info:
            return False
        gsi_list = table_info.get('GlobalSecondaryIndexes', [])
        source_index = next((g for g in gsi_list if g['IndexName'] == 'source-index'), None)

        if not source_index:
            self.log_test("GSI source-index Exists", False, "source-index not found")
            return False

        status = source_index.get('IndexStatus', 'UNKNOWN')
        passed = status == 'ACTIVE'
        self.log_test(
            "GSI source-index Status",
            passed,
            f"Status: {status}"
        )
        return passed

    def test_streams_enabled(self, table_info):
        """Test 8: Verify DynamoDB Streams are enabled"""
        if not table_info:
            return False
        stream_spec = table_info.get('StreamSpecification', {})
        enabled = stream_spec.get('StreamViewType') == 'NEW_AND_OLD_IMAGES'
        self.log_test(
            "DynamoDB Streams",
            enabled,
            f"View type: {stream_spec.get('StreamViewType', 'Not enabled')}"
        )
        return enabled

    def test_stream_arn(self, table_info):
        """Test 9: Verify Stream ARN exists"""
        if not table_info:
            return False
        stream_arn = table_info.get('LatestStreamArn')
        passed = bool(stream_arn)
        self.log_test(
            "Stream ARN",
            passed,
            f"ARN: {stream_arn}" if stream_arn else "No stream ARN"
        )
        return passed

    def test_pitr_enabled(self, table_info):
        """Test 10: Verify Point-in-Time Recovery is enabled"""
        if not table_info:
            return False
        try:
            pitr = self.dynamodb.describe_continuous_backups(TableName=self.table_name)
            status = pitr['ContinuousBackupsDescription']['PointInTimeRecoveryDescription']['PointInTimeRecoveryStatus']
            passed = status == 'ENABLED'
            self.log_test(
                "Point-in-Time Recovery",
                passed,
                f"PITR Status: {status}"
            )
            return passed
        except Exception as e:
            self.log_test("Point-in-Time Recovery", False, str(e))
            return False

    def test_write_read_operations(self):
        """Test 11: Test basic write and read operations"""
        try:
            test_item = {
                'celebrity_id': {'S': 'celeb_test_validation'},
                'source_type#timestamp': {'S': 'test#2025-11-07T00:00:00Z'},
                'name': {'S': '測試名人'},
                'birth_date': {'S': '1980-01-01'},
                'nationality': {'S': '台灣'},
                'occupation': {'L': [{'S': '演員'}]},
                'created_at': {'S': datetime.utcnow().isoformat() + 'Z'},
                'updated_at': {'S': datetime.utcnow().isoformat() + 'Z'},
                'is_active': {'BOOL': True}
            }

            # Write
            self.dynamodb.put_item(TableName=self.table_name, Item=test_item)

            # Read
            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={
                    'celebrity_id': {'S': 'celeb_test_validation'},
                    'source_type#timestamp': {'S': 'test#2025-11-07T00:00:00Z'}
                }
            )

            # Verify
            passed = 'Item' in response
            self.log_test(
                "Write and Read Operations",
                passed,
                "Successfully wrote and retrieved test item"
            )

            # Cleanup
            self.dynamodb.delete_item(
                TableName=self.table_name,
                Key={
                    'celebrity_id': {'S': 'celeb_test_validation'},
                    'source_type#timestamp': {'S': 'test#2025-11-07T00:00:00Z'}
                }
            )

            return passed
        except Exception as e:
            self.log_test("Write and Read Operations", False, str(e))
            return False

    def test_query_by_name_index(self):
        """Test 12: Test query using name-index GSI"""
        try:
            response = self.dynamodb.query(
                TableName=self.table_name,
                IndexName='name-index',
                KeyConditionExpression='#name = :name',
                ExpressionAttributeNames={'#name': 'name'},
                ExpressionAttributeValues={':name': {'S': '周潤發'}},
                Limit=1
            )

            # Index may be empty initially, just verify query succeeds
            passed = 'Items' in response
            count = response.get('Count', 0)
            self.log_test(
                "Query by name-index GSI",
                passed,
                f"Query successful (Found {count} items)"
            )
            return passed
        except Exception as e:
            self.log_test("Query by name-index GSI", False, str(e))
            return False

    def run_all_tests(self):
        """Run all validation tests"""
        print("\n" + "="*60)
        print("DynamoDB Table Validation Tests")
        print(f"Table: {self.table_name}")
        print(f"Region: {self.region}")
        print("="*60 + "\n")

        # Get table info
        table_info = self.test_table_exists()
        if not table_info:
            print("\n✗ CRITICAL: Table does not exist. Cannot continue testing.")
            return False

        # Run tests
        self.test_table_active(table_info)
        self.test_billing_mode(table_info)
        self.test_partition_key(table_info)
        self.test_sort_key(table_info)
        self.test_gsi_name_index(table_info)
        self.test_gsi_source_index(table_info)
        self.test_streams_enabled(table_info)
        self.test_stream_arn(table_info)
        self.test_pitr_enabled(table_info)
        self.test_write_read_operations()
        self.test_query_by_name_index()

        # Summary
        passed = sum(1 for t in self.test_results if t['passed'])
        total = len(self.test_results)

        print("\n" + "="*60)
        print(f"Test Results: {passed}/{total} passed")
        print("="*60)

        if passed == total:
            print("✓ All tests passed! Table is ready for operation.")
            return True
        else:
            print("✗ Some tests failed. Please review the output above.")
            return False


def main():
    parser = argparse.ArgumentParser(description='Validate DynamoDB table structure and operations')
    parser.add_argument('--table', default='celebrity-database', help='Table name (default: celebrity-database)')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')

    args = parser.parse_args()

    validator = DynamoDBTableValidator(args.table, args.region)
    success = validator.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
