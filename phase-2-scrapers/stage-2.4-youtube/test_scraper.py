#!/usr/bin/env python3
"""
Test suite for YouTube Stage 2.4 scraper.

This file contains unit tests, integration tests, and documentation for testing protocols.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))


class TestYouTubeSearch(unittest.TestCase):
    """Test cases for YouTube channel search function."""

    def setUp(self):
        """Import the function to test."""
        from lambda_function import search_youtube_channel
        self.search_youtube_channel = search_youtube_channel

    @patch('lambda_function.requests.get')
    def test_successful_channel_search(self, mock_get):
        """Test successful YouTube channel search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'id': {'channelId': 'UC1234567890'},
                    'snippet': {'title': 'Test Channel'}
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.search_youtube_channel("Test Celebrity", "test_api_key")

        self.assertIsNotNone(result['channel_id'])
        self.assertEqual(result['channel_id'], 'UC1234567890')
        self.assertIsNone(result['error'])

    @patch('lambda_function.requests.get')
    def test_channel_not_found(self, mock_get):
        """Test when channel is not found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'items': []}
        mock_get.return_value = mock_response

        result = self.search_youtube_channel("Unknown Celebrity", "test_api_key")

        self.assertIsNone(result['channel_id'])
        self.assertIn('not found', result['error'].lower())

    @patch('lambda_function.requests.get')
    def test_timeout_handling(self, mock_get):
        """Test timeout error handling."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = self.search_youtube_channel("Test Celebrity", "test_api_key")

        self.assertIsNone(result['channel_id'])
        self.assertIn('timeout', result['error'].lower())

    @patch('lambda_function.requests.get')
    def test_api_error_in_response(self, mock_get):
        """Test API error in response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': {'message': 'Invalid API key'}
        }
        mock_get.return_value = mock_response

        result = self.search_youtube_channel("Test Celebrity", "invalid_key")

        self.assertIsNone(result['channel_id'])
        self.assertIn('error', result['error'].lower())


class TestYouTubeChannelFetch(unittest.TestCase):
    """Test cases for YouTube channel data fetch function."""

    def setUp(self):
        """Import the function to test."""
        from lambda_function import fetch_channel_data
        self.fetch_channel_data = fetch_channel_data

    @patch('lambda_function.requests.get')
    def test_successful_channel_fetch(self, mock_get):
        """Test successful channel data fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'id': 'UC1234567890',
                    'snippet': {'title': 'Test Channel'},
                    'statistics': {
                        'viewCount': '1000000',
                        'subscriberCount': '50000',
                        'videoCount': '100'
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.fetch_channel_data("UC1234567890", "test_api_key")

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['raw_text'])
        self.assertIsNotNone(result['channel_data'])

    @patch('lambda_function.requests.get')
    def test_quota_exceeded(self, mock_get):
        """Test quota exceeded error."""
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        result = self.fetch_channel_data("UC1234567890", "test_api_key")

        self.assertFalse(result['success'])
        self.assertTrue(result.get('quota_exceeded', False))

    @patch('lambda_function.requests.get')
    def test_timeout_handling(self, mock_get):
        """Test timeout error handling."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = self.fetch_channel_data("UC1234567890", "test_api_key")

        self.assertFalse(result['success'])
        self.assertIn('timeout', result['error'].lower())


class TestRetryLogic(unittest.TestCase):
    """Test cases for retry with backoff logic."""

    def setUp(self):
        """Import the function to test."""
        from lambda_function import retry_with_backoff
        self.retry_with_backoff = retry_with_backoff

    @patch('lambda_function.time.sleep')
    def test_retry_succeeds_on_second_attempt(self, mock_sleep):
        """Test that retry succeeds on second attempt."""
        call_count = [0]

        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 2:
                return {'success': False, 'error': 'Temporary error'}
            return {'success': True, 'data': 'success'}

        result = self.retry_with_backoff(flaky_function, max_retries=3)

        self.assertTrue(result['success'])
        self.assertEqual(call_count[0], 2)
        self.assertEqual(mock_sleep.call_count, 1)

    @patch('lambda_function.time.sleep')
    def test_retry_fails_after_max_attempts(self, mock_sleep):
        """Test that function gives up after max retries."""
        def always_fails():
            return {'success': False, 'error': 'Persistent error'}

        result = self.retry_with_backoff(always_fails, max_retries=3)

        self.assertFalse(result['success'])
        self.assertEqual(mock_sleep.call_count, 2)


class TestDynamoDBIntegration(unittest.TestCase):
    """Test cases for DynamoDB operations."""

    def setUp(self):
        """Import the function to test."""
        from lambda_function import write_scraper_entry_with_retry
        self.write_scraper_entry_with_retry = write_scraper_entry_with_retry

    @patch('lambda_function.time.sleep')
    def test_successful_write(self, mock_sleep):
        """Test successful DynamoDB write."""
        mock_table = MagicMock()
        mock_table.put_item.return_value = {}

        test_item = {
            'celebrity_id': 'celeb_001',
            'source_type#timestamp': 'youtube#2025-11-07T17:20:00Z',
            'id': 'test_uuid',
            'name': 'Test Celebrity',
            'raw_text': '{"test": "data"}',
        }

        result = self.write_scraper_entry_with_retry(mock_table, test_item)

        self.assertTrue(result)
        mock_table.put_item.assert_called_once()

    @patch('lambda_function.time.sleep')
    def test_write_retry_on_throttle(self, mock_sleep):
        """Test DynamoDB write retry on throttling."""
        from botocore.exceptions import ClientError

        mock_table = MagicMock()
        error = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException'}},
            'PutItem'
        )
        mock_table.put_item.side_effect = [error, {}]

        test_item = {
            'celebrity_id': 'celeb_001',
            'name': 'Test Celebrity',
        }

        result = self.write_scraper_entry_with_retry(mock_table, test_item, max_retries=3)

        self.assertTrue(result)
        self.assertEqual(mock_table.put_item.call_count, 2)


class TestLambdaHandler(unittest.TestCase):
    """Test cases for main Lambda handler."""

    @patch.dict(os.environ, {
        'DYNAMODB_TABLE': 'test-table',
        'YOUTUBE_API_KEY': 'test-key',
    })
    def test_missing_environment_variables(self):
        """Test handling of missing environment variables."""
        from lambda_function import lambda_handler

        with patch.dict(os.environ, {'YOUTUBE_API_KEY': ''}, clear=False):
            result = lambda_handler({}, None)

            self.assertEqual(result['total'], 0)
            self.assertGreater(result['errors'], 0)

    @patch('lambda_function.dynamodb')
    @patch.dict(os.environ, {
        'DYNAMODB_TABLE': 'test-table',
        'YOUTUBE_API_KEY': 'test-key',
    })
    def test_no_celebrities_found(self, mock_dynamodb):
        """Test when no celebrities are found in DynamoDB."""
        from lambda_function import lambda_handler

        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table

        result = lambda_handler({}, None)

        self.assertEqual(result['total'], 0)
        self.assertEqual(result['success'], 0)


# Testing Documentation
"""
TESTING PROTOCOL FOR STAGE 2.4
================================

Phase 2.4A: API Key Setup
-------------------------
Manual steps (cannot be automated):
1. Visit https://console.cloud.google.com
2. Create or select existing project
3. Enable YouTube Data API v3
4. Create API key (Credentials > Create Credentials > API Key)
5. Copy API key
6. Update .env file with key

Verification:
✓ API key format: starts with "AIza"
✓ .env file has the key


Phase 2.4B: Offline Test (Single Celebrity)
--------------------------------------------
Command: python3 lambda_function.py --test-mode

Expected output:
✓ Lambda handler function exists
✓ YouTube search function defined
✓ Channel data fetch function defined
✓ Error handling functions defined
✓ DynamoDB integration prepared
✓ Test mode completed


Phase 2.4C: Online Test (Single Celebrity)
-------------------------------------------
Requires:
- AWS credentials configured locally
- DynamoDB table exists with at least one celebrity
- .env file with valid YouTube API key

Commands:
export $(cat .env | xargs)
python3 -m unittest discover

Expected:
- No authentication errors
- All unit tests pass
- API call succeeds or logs meaningful error


Phase 2.4D: DynamoDB Verification
---------------------------------
Command:
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND source_type#timestamp BEGINS_WITH :prefix" \
  --expression-attribute-values \
    "{\":id\":{\"S\":\"celeb_001\"},\":prefix\":{\"S\":\"youtube#\"}}" \
  --region us-east-1

Expected fields in result:
✓ id: UUID string
✓ name: Celebrity name
✓ raw_text: Valid JSON from YouTube API
✓ source: "https://www.googleapis.com/youtube/v3/channels"
✓ timestamp: ISO 8601 format with Z suffix
✓ weight: null
✓ sentiment: null
✓ metadata.channel_id: YouTube channel ID


Phase 2.4E: Full Deployment
----------------------------
Steps:
1. Deploy lambda_function.py to AWS Lambda as "scraper-youtube"
2. Set environment variables in Lambda
3. Invoke with no limit (processes all celebrities)
4. Monitor CloudWatch logs

Verification:
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"youtube#\"}}" \
  --select COUNT \
  --region us-east-1

Expected:
- COUNT: 80-100 (most celebrities have YouTube channels)
- No quota exceeded errors (10K quota/day is generous)
- All scraper entries have required fields
"""


def run_tests():
    """Run all unit tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestYouTubeSearch))
    suite.addTests(loader.loadTestsFromTestCase(TestYouTubeChannelFetch))
    suite.addTests(loader.loadTestsFromTestCase(TestRetryLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestDynamoDBIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLambdaHandler))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
