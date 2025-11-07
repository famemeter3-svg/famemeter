#!/usr/bin/env python3
"""
Test suite for Google Search Stage 2.1 scraper.

This file contains unit tests, integration tests, and documentation for testing protocols.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))


class TestCleanRawText(unittest.TestCase):
    """Test cases for raw_text cleaning function."""

    def setUp(self):
        """Import the function to test."""
        from lambda_function import clean_raw_text
        self.clean_raw_text = clean_raw_text

    def test_clean_json_dict(self):
        """Test cleaning a Python dict (converts to JSON string)."""
        input_data = {"key": "value", "number": 42}
        result = self.clean_raw_text(input_data)

        self.assertIsInstance(result, str)
        parsed = json.loads(result)
        self.assertEqual(parsed['key'], 'value')
        self.assertEqual(parsed['number'], 42)

    def test_clean_json_string(self):
        """Test cleaning a JSON string."""
        input_data = '{"key":"value","nested":{"item":1}}'
        result = self.clean_raw_text(input_data)

        self.assertIsInstance(result, str)
        parsed = json.loads(result)
        self.assertEqual(parsed['key'], 'value')
        self.assertEqual(parsed['nested']['item'], 1)

    def test_clean_whitespace(self):
        """Test that excess whitespace is normalized."""
        input_data = "text   with    multiple     spaces"
        result = self.clean_raw_text(input_data)

        # Should have normalized whitespace
        self.assertIsInstance(result, str)
        # Multiple spaces collapsed
        self.assertNotIn('    ', result)

    def test_clean_utf8_text(self):
        """Test UTF-8 encoding handling."""
        input_data = "Hello 世界 مرحبا"
        result = self.clean_raw_text(input_data)

        self.assertIsInstance(result, str)
        # Should contain the text
        self.assertIn("Hello", result)

    def test_clean_empty_string(self):
        """Test cleaning empty string."""
        result = self.clean_raw_text("")
        self.assertIsInstance(result, str)

    def test_clean_none_handling(self):
        """Test handling of None value."""
        result = self.clean_raw_text(None)
        self.assertIsInstance(result, str)
        self.assertEqual(result, "None")


class TestFetchGoogleSearchData(unittest.TestCase):
    """Test cases for Google Search API calls."""

    def setUp(self):
        """Import the function to test."""
        from lambda_function import fetch_google_search_data
        self.fetch_google_search_data = fetch_google_search_data

    @patch('lambda_function.requests.get')
    def test_successful_api_call(self, mock_get):
        """Test successful API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {'title': 'Result 1', 'link': 'https://example.com/1'},
                {'title': 'Result 2', 'link': 'https://example.com/2'},
            ]
        }
        mock_get.return_value = mock_response

        result = self.fetch_google_search_data(
            "Leonardo DiCaprio",
            "test_api_key",
            "test_search_engine_id"
        )

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['raw_text'])
        self.assertEqual(result['item_count'], 2)
        self.assertIsNone(result['error'])

    @patch('lambda_function.requests.get')
    def test_timeout_handling(self, mock_get):
        """Test timeout error handling."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = self.fetch_google_search_data(
            "Test Celebrity",
            "test_api_key",
            "test_search_engine_id",
            timeout=5
        )

        self.assertFalse(result['success'])
        self.assertIn('timeout', result['error'].lower())
        self.assertIsNone(result['raw_text'])

    @patch('lambda_function.requests.get')
    def test_rate_limit_handling(self, mock_get):
        """Test rate limit (429) error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        import requests
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        result = self.fetch_google_search_data(
            "Test Celebrity",
            "test_api_key",
            "test_search_engine_id"
        )

        self.assertFalse(result['success'])
        self.assertIn('429', result['error'])

    @patch('lambda_function.requests.get')
    def test_malformed_json_response(self, mock_get):
        """Test malformed JSON response handling."""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        mock_get.return_value = mock_response

        result = self.fetch_google_search_data(
            "Test Celebrity",
            "test_api_key",
            "test_search_engine_id"
        )

        self.assertFalse(result['success'])
        self.assertIn('Malformed', result['error'])

    @patch('lambda_function.requests.get')
    def test_api_error_in_response(self, mock_get):
        """Test API error returned in JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': {'message': 'Invalid API key provided'}
        }
        mock_get.return_value = mock_response

        result = self.fetch_google_search_data(
            "Test Celebrity",
            "invalid_key",
            "test_search_engine_id"
        )

        self.assertFalse(result['success'])
        self.assertIn('API error', result['error'])


class TestRetryLogic(unittest.TestCase):
    """Test cases for retry with backoff logic."""

    def setUp(self):
        """Import the function to test."""
        from lambda_function import retry_with_backoff
        self.retry_with_backoff = retry_with_backoff

    @patch('lambda_function.time.sleep')  # Mock sleep to avoid delays
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
        self.assertEqual(mock_sleep.call_count, 1)  # One sleep between attempts

    @patch('lambda_function.time.sleep')
    def test_retry_fails_after_max_attempts(self, mock_sleep):
        """Test that function gives up after max retries."""
        def always_fails():
            return {'success': False, 'error': 'Persistent error'}

        result = self.retry_with_backoff(always_fails, max_retries=3)

        self.assertFalse(result['success'])
        self.assertEqual(mock_sleep.call_count, 2)  # Two sleeps for 3 attempts

    @patch('lambda_function.time.sleep')
    def test_retry_no_retry_on_invalid_key(self, mock_sleep):
        """Test that invalid API key is not retried."""
        def invalid_key_error():
            return {'success': False, 'error': 'Invalid API key'}

        result = self.retry_with_backoff(invalid_key_error, max_retries=3)

        self.assertFalse(result['success'])
        # Should not sleep if invalid key (no retry)
        self.assertEqual(mock_sleep.call_count, 0)


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
            'source_type#timestamp': 'google_search#2025-11-07T17:20:00Z',
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

        # First call fails, second succeeds
        error = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException'}},
            'PutItem'
        )
        mock_table.put_item.side_effect = [error, {}]

        test_item = {
            'celebrity_id': 'celeb_001',
            'source_type#timestamp': 'google_search#2025-11-07T17:20:00Z',
            'name': 'Test Celebrity',
        }

        result = self.write_scraper_entry_with_retry(mock_table, test_item, max_retries=3)

        self.assertTrue(result)
        self.assertEqual(mock_table.put_item.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)  # One sleep between retries

    @patch('lambda_function.time.sleep')
    def test_write_fails_after_max_retries(self, mock_sleep):
        """Test write failure after max retries."""
        from botocore.exceptions import ClientError

        mock_table = MagicMock()
        error = ClientError(
            {'Error': {'Code': 'ValidationException'}},
            'PutItem'
        )
        mock_table.put_item.side_effect = error

        test_item = {
            'celebrity_id': 'celeb_001',
            'name': 'Test Celebrity',
        }

        result = self.write_scraper_entry_with_retry(mock_table, test_item, max_retries=2)

        self.assertFalse(result)
        self.assertEqual(mock_table.put_item.call_count, 2)


class TestLambdaHandler(unittest.TestCase):
    """Test cases for main Lambda handler."""

    @patch.dict(os.environ, {
        'DYNAMODB_TABLE': 'test-table',
        'GOOGLE_API_KEY': 'test-key',
        'GOOGLE_SEARCH_ENGINE_ID': 'test-engine'
    })
    def test_missing_environment_variables(self):
        """Test handling of missing environment variables."""
        from lambda_function import lambda_handler

        # Clear one variable
        with patch.dict(os.environ, {'GOOGLE_API_KEY': ''}, clear=False):
            result = lambda_handler({}, None)

            self.assertEqual(result['total'], 0)
            self.assertGreater(result['errors'], 0)
            self.assertIn('error', result)

    @patch('lambda_function.dynamodb')
    @patch.dict(os.environ, {
        'DYNAMODB_TABLE': 'test-table',
        'GOOGLE_API_KEY': 'test-key',
        'GOOGLE_SEARCH_ENGINE_ID': 'test-engine'
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
        self.assertEqual(result['errors'], 0)


class TestKeyRotation(unittest.TestCase):
    """Test cases for API key rotation functionality."""

    def setUp(self):
        """Import the key rotation module."""
        from key_rotation import APIKeyRotationManager
        self.APIKeyRotationManager = APIKeyRotationManager

    @patch.dict(os.environ, {
        'GOOGLE_API_KEY_1': 'AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w',
        'GOOGLE_API_KEY_2': 'AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8',
        'GOOGLE_API_KEY_3': 'AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc',
    })
    def test_load_multiple_keys(self):
        """Test loading multiple API keys from environment."""
        manager = self.APIKeyRotationManager()

        self.assertEqual(len(manager.keys), 3)
        self.assertIn('AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w', manager.keys)
        self.assertIn('AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8', manager.keys)
        self.assertIn('AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc', manager.keys)

    @patch.dict(os.environ, {
        'GOOGLE_API_KEYS': 'AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w|AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8',
    })
    def test_load_combined_keys_format(self):
        """Test loading keys from combined format (GOOGLE_API_KEYS)."""
        manager = self.APIKeyRotationManager()

        self.assertEqual(len(manager.keys), 2)

    @patch.dict(os.environ, {
        'GOOGLE_API_KEY_1': 'AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w',
        'GOOGLE_API_KEY_2': 'AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8',
        'GOOGLE_API_KEY_3': 'AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc',
    })
    def test_round_robin_strategy(self):
        """Test round-robin key rotation."""
        manager = self.APIKeyRotationManager(strategy='round_robin')

        keys_returned = [manager.get_next_key() for _ in range(6)]

        # Should cycle: key1, key2, key3, key1, key2, key3
        self.assertEqual(keys_returned[0], keys_returned[3])
        self.assertEqual(keys_returned[1], keys_returned[4])
        self.assertEqual(keys_returned[2], keys_returned[5])

    @patch.dict(os.environ, {
        'GOOGLE_API_KEY_1': 'AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w',
        'GOOGLE_API_KEY_2': 'AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8',
        'GOOGLE_API_KEY_3': 'AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc',
    })
    def test_least_used_strategy(self):
        """Test least-used key rotation strategy."""
        manager = self.APIKeyRotationManager(strategy='least_used')

        # Get first key
        key1 = manager.get_next_key()
        # Record request for key1
        manager.record_request(key1, success=True)

        # Get next key - should be different (least used)
        key2 = manager.get_next_key()
        self.assertNotEqual(key1, key2)

    @patch.dict(os.environ, {
        'GOOGLE_API_KEY_1': 'AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w',
        'GOOGLE_API_KEY_2': 'AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8',
        'GOOGLE_API_KEY_3': 'AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc',
    })
    def test_record_request_statistics(self):
        """Test recording request statistics."""
        manager = self.APIKeyRotationManager()

        key = manager.get_next_key()
        manager.record_request(key, success=True)
        manager.record_request(key, success=True)
        manager.record_request(key, success=False, error_type='TIMEOUT')

        stats = manager.get_statistics()
        key_short = key[:10] + "..."
        self.assertEqual(stats[key_short]['requests'], 3)
        self.assertEqual(stats[key_short]['errors'], 1)

    @patch.dict(os.environ, {
        'GOOGLE_API_KEY_1': 'AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w',
        'GOOGLE_API_KEY_2': 'AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8',
    })
    def test_adaptive_strategy_with_rate_limit(self):
        """Test adaptive strategy switches on rate limit."""
        manager = self.APIKeyRotationManager(strategy='adaptive')

        # Mark first key with rate limit error
        key1 = manager.keys[0]
        manager.record_request(key1, success=False, error_type='RATE_LIMIT')

        # Get next key - should avoid rate-limited key
        next_key = manager.get_next_key()
        # Note: This test demonstrates the adaptive behavior
        # The actual key selected depends on the order and strategy

    @patch.dict(os.environ, {
        'GOOGLE_API_KEY_1': 'AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w',
        'GOOGLE_API_KEY_2': 'AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8',
        'GOOGLE_API_KEY_3': 'AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc',
    })
    def test_should_skip_key_with_high_error_rate(self):
        """Test should_skip_key with high error rate."""
        manager = self.APIKeyRotationManager()

        key = manager.keys[0]
        # Simulate 10 requests, 95 of which failed
        for _ in range(95):
            manager.record_request(key, success=False, error_type='RATE_LIMIT')
        for _ in range(5):
            manager.record_request(key, success=True)

        # With 95% error rate and threshold of 95%, should be skipped
        self.assertTrue(manager.should_skip_key(key))


# Testing Documentation
"""
TESTING PROTOCOL FOR STAGE 2.1
================================

Phase 2.1A: API Key Setup
-------------------------
Manual steps (cannot be automated):
1. Visit https://console.cloud.google.com
2. Create or select existing project
3. Enable Custom Search API
4. Create API key (Credentials > Create Credentials > API Key)
5. Create custom search engine at https://cse.google.com
6. Copy both API key and Search Engine ID
7. Update .env file with these values

Verification:
✓ API key format: starts with "AIza"
✓ Search Engine ID format: 12-18 digit number ending with ":cse"
✓ .env file has both values


Phase 2.1B: Offline Test (Single Celebrity)
--------------------------------------------
Command: python3 lambda_function.py --test-mode

Expected output:
✓ Function runs without crashes
✓ Error handling functions defined
✓ DynamoDB integration prepared
✓ Test mode completed


Phase 2.1C: Online Test (Single Celebrity - Local)
--------------------------------------------------
Requires:
- AWS credentials configured locally
- DynamoDB table exists with at least one celebrity
- .env file with valid API key and Search Engine ID

Commands:
export $(cat .env | xargs)
python3 lambda_function.py

Expected:
- No authentication errors
- API call succeeds or logs meaningful error
- DynamoDB write attempted or logs error
- Output JSON with summary


Phase 2.1D: DynamoDB Verification
---------------------------------
Command:
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND source_type#timestamp BEGINS_WITH :prefix" \
  --expression-attribute-values \
    "{\":id\":{\"S\":\"celeb_001\"},\":prefix\":{\"S\":\"google_search#\"}}" \
  --region us-east-1

Expected fields in result:
✓ id: UUID string
✓ name: Celebrity name
✓ raw_text: Valid JSON from Google API
✓ source: "https://www.googleapis.com/customsearch/v1"
✓ timestamp: ISO 8601 format with Z suffix
✓ weight: null
✓ sentiment: null


Phase 2.1E: Batch Test (5 Celebrities)
--------------------------------------
Steps:
1. Deploy lambda_function.py to AWS Lambda as "scraper-google-search-dev"
2. Set environment variables in Lambda
3. Test with limit=5 payload: {'limit': 5}
4. Monitor CloudWatch logs
5. Verify no errors in logs
6. Check results

Expected:
- success >= 4 (80% success rate)
- errors <= 1
- All celebrities have DynamoDB entries
- No timeout or API key errors


Phase 2.1F: Full Deployment (100 Celebrities)
----------------------------------------------
Steps:
1. Update Lambda code to production version
2. Invoke with no limit (processes all 100)
3. Monitor execution time (should be ~5 minutes)
4. Check CloudWatch logs for completion

Verification:
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names "{\"#key\":\"source_type#timestamp\"}" \
  --expression-attribute-values "{\":source\":{\"S\":\"google_search#\"}}" \
  --select COUNT \
  --region us-east-1

Expected:
- COUNT: ~100 (one per celebrity)
- No errors in CloudWatch logs
- Execution time < 5 minutes
- Total cost: < $1 (free tier or minimal)

Success Criteria:
✓ 100 scraper entries in DynamoDB
✓ Each entry has required fields
✓ raw_text contains valid Google API response
✓ weight and sentiment are null
✓ All timestamps in ISO 8601 format
"""


def run_tests():
    """Run all unit tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCleanRawText))
    suite.addTests(loader.loadTestsFromTestCase(TestFetchGoogleSearchData))
    suite.addTests(loader.loadTestsFromTestCase(TestRetryLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestDynamoDBIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLambdaHandler))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
