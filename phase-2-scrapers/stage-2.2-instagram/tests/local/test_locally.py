"""
Local testing script for Instagram scraper with DynamoDB Local.

This script tests the Lambda function against a local DynamoDB instance.

Prerequisites:
1. Docker and docker-compose installed
2. DynamoDB Local running: docker-compose up -d
3. Dependencies installed: pip install -r requirements.txt

Usage:
    python tests/local/test_locally.py

The script will:
1. Connect to local DynamoDB
2. Create the celebrity-database table
3. Invoke the scraper with sample data
4. Verify data was saved to DynamoDB
5. Display results
"""

import sys
import os
import json
import time
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import lambda_function
from unittest.mock import MagicMock, patch
import instaloader

# Configuration for local DynamoDB
LOCAL_DYNAMODB_ENDPOINT = 'http://localhost:8000'
AWS_REGION = 'us-east-1'
TABLE_NAME = 'celebrity-database'

# Set environment variables
os.environ['DYNAMODB_TABLE'] = TABLE_NAME
os.environ['AWS_REGION'] = AWS_REGION
os.environ['AWS_ACCESS_KEY_ID'] = 'local'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'local'


class LocalTestEnvironment:
    """Manage local testing environment."""

    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=LOCAL_DYNAMODB_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id='local',
            aws_secret_access_key='local'
        )
        self.table = None

    def setup(self):
        """Set up local DynamoDB table."""
        print("Setting up local DynamoDB...")

        try:
            # Delete existing table if it exists
            try:
                self.dynamodb.Table(TABLE_NAME).delete()
                print(f"  Deleted existing table: {TABLE_NAME}")
                time.sleep(2)
            except:
                pass

            # Create table
            self.table = self.dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {'AttributeName': 'celebrity_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'source_type#timestamp', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'celebrity_id', 'AttributeType': 'S'},
                    {'AttributeName': 'source_type#timestamp', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )

            # Wait for table to be created
            self.table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
            print(f"  ✓ Table created: {TABLE_NAME}")

            return True

        except Exception as e:
            print(f"  ✗ Failed to set up table: {str(e)}")
            print("\n  Make sure DynamoDB Local is running:")
            print("    docker-compose -f tests/local/docker-compose.yaml up -d")
            return False

    def cleanup(self):
        """Clean up local resources."""
        print("\nCleaning up...")
        try:
            self.table.delete()
            print(f"  ✓ Table deleted: {TABLE_NAME}")
        except:
            pass

    def scan_table(self) -> List[Dict]:
        """Scan all items in table."""
        response = self.table.scan()
        return response.get('Items', [])


class MockInstagram:
    """Mock Instagram data for testing."""

    @staticmethod
    def create_profile(username: str, followers: int = 100000):
        """Create mock profile."""
        profile = MagicMock()
        profile.username = username
        profile.follower_count = followers
        profile.mediacount = 1000
        profile.biography = f"Bio for {username}"
        profile.is_verified = username in ['cristiano', 'arianagrande', 'selenagomez']
        profile.is_business_account = True
        profile.is_private = False
        profile.profile_pic_url = f'https://example.com/{username}.jpg'
        return profile


def test_single_celebrity(env: LocalTestEnvironment):
    """Test scraping single celebrity."""
    print("\n" + "="*60)
    print("TEST 1: Single Celebrity Scraping")
    print("="*60)

    with patch('lambda_function.instaloader.Profile.from_username') as mock_from_username:
        mock_from_username.return_value = MockInstagram.create_profile('cristiano', 600000000)

        # Create Lambda event
        event = {
            'celebrities': [
                {
                    'celebrity_id': 'celeb_001',
                    'name': 'Cristiano Ronaldo',
                    'instagram_handle': 'cristiano'
                }
            ]
        }

        # Create mock context
        context = MagicMock()
        context.request_id = 'test-request-001'

        # Invoke handler
        print("\nInvoking Lambda handler...")
        response = lambda_function.lambda_handler(event, context)

        # Parse response
        status_code = response['statusCode']
        body = json.loads(response['body'])

        print(f"\nResponse Status: {status_code}")
        print(f"Successful: {body.get('successful', 0)}")
        print(f"Failed: {body.get('failed', 0)}")

        # Verify data in DynamoDB
        print("\nVerifying data in DynamoDB...")
        items = env.scan_table()
        print(f"  Items in table: {len(items)}")

        if items:
            for item in items:
                print(f"\n  ✓ Found entry:")
                print(f"    - Celebrity: {item.get('name')}")
                print(f"    - Source: {item.get('source')}")
                print(f"    - Timestamp: {item.get('timestamp')}")

            return True
        else:
            print(f"  ✗ No data found in DynamoDB")
            return False


def test_batch_scraping(env: LocalTestEnvironment):
    """Test scraping batch of celebrities."""
    print("\n" + "="*60)
    print("TEST 2: Batch Celebrity Scraping")
    print("="*60)

    with patch('lambda_function.instaloader.Profile.from_username') as mock_from_username:
        # Mock multiple profiles
        profiles = {
            'cristiano': MockInstagram.create_profile('cristiano', 600000000),
            'leomessi': MockInstagram.create_profile('leomessi', 500000000),
            'arianagrande': MockInstagram.create_profile('arianagrande', 300000000),
        }

        mock_from_username.side_effect = lambda context, handle: profiles.get(handle, MockInstagram.create_profile(handle))

        # Create Lambda event with multiple celebrities
        event = {
            'celebrities': [
                {'celebrity_id': 'celeb_001', 'name': 'Cristiano Ronaldo', 'instagram_handle': 'cristiano'},
                {'celebrity_id': 'celeb_002', 'name': 'Lionel Messi', 'instagram_handle': 'leomessi'},
                {'celebrity_id': 'celeb_003', 'name': 'Ariana Grande', 'instagram_handle': 'arianagrande'},
                {'celebrity_id': 'celeb_004', 'name': 'Unknown Celebrity', 'instagram_handle': None},
            ]
        }

        context = MagicMock()
        context.request_id = 'test-request-002'

        # Invoke handler
        print("\nInvoking Lambda handler with 4 celebrities...")
        response = lambda_function.lambda_handler(event, context)

        status_code = response['statusCode']
        body = json.loads(response['body'])

        print(f"\nResponse Status: {status_code}")
        print(f"Total Processed: {body.get('total_celebrities', 0)}")
        print(f"Successful: {body.get('successful', 0)}")
        print(f"Failed: {body.get('failed', 0)}")
        print(f"Skipped: {body.get('skipped', 0)}")

        # Verify data in DynamoDB
        print("\nVerifying data in DynamoDB...")
        items = env.scan_table()
        print(f"  Items in table: {len(items)}")

        if len(items) >= 3:  # Should have at least 3 successful entries
            print(f"  ✓ Batch processing successful")
            for item in items:
                print(f"    - {item.get('name')} (@{item.get('raw_text', {}).get('username', 'unknown')})")
            return True
        else:
            print(f"  ✗ Expected at least 3 items, got {len(items)}")
            return False


def test_error_handling(env: LocalTestEnvironment):
    """Test error handling."""
    print("\n" + "="*60)
    print("TEST 3: Error Handling")
    print("="*60)

    with patch('lambda_function.instaloader.Profile.from_username') as mock_from_username:
        # Simulate profile not found
        mock_from_username.side_effect = instaloader.exceptions.ProfileNotExistsException("Not found")

        event = {
            'celebrities': [
                {'celebrity_id': 'celeb_999', 'name': 'Invalid Celebrity', 'instagram_handle': 'nonexistent_user_12345'}
            ]
        }

        context = MagicMock()
        context.request_id = 'test-request-003'

        # Invoke handler
        print("\nInvoking Lambda handler with invalid profile...")
        response = lambda_function.lambda_handler(event, context)

        status_code = response['statusCode']
        body = json.loads(response['body'])

        print(f"\nResponse Status: {status_code}")
        print(f"Failed: {body.get('failed', 0)}")

        if body.get('failed', 0) > 0:
            print(f"  ✓ Error handling successful")
            return True
        else:
            print(f"  ✗ Error not handled properly")
            return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Instagram Scraper - Local Testing Suite")
    print("="*60)

    env = LocalTestEnvironment()

    # Setup
    if not env.setup():
        print("\n✗ Setup failed. Exiting.")
        return False

    results = {
        'Test 1: Single Celebrity': False,
        'Test 2: Batch Scraping': False,
        'Test 3: Error Handling': False,
    }

    try:
        # Run tests
        results['Test 1: Single Celebrity'] = test_single_celebrity(env)
        results['Test 2: Batch Scraping'] = test_batch_scraping(env)
        results['Test 3: Error Handling'] = test_error_handling(env)

    except Exception as e:
        print(f"\n✗ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

    # Cleanup
    env.cleanup()

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    return all(results.values())


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
