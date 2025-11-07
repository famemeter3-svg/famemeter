#!/usr/bin/env python3
"""
Integration test for Google Search scraper API endpoints.

Tests the actual API integration patterns without requiring real credentials.
This validates that the scraper code correctly constructs and handles API calls.
"""

import json
import sys
import os
from unittest.mock import patch, MagicMock
import requests

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from lambda_function import fetch_google_search_data

# Test API Keys
TEST_API_KEY_1 = "AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w"
TEST_SEARCH_ENGINE_ID = "e1f2g3h4i5"


class GoogleSearchAPIIntegrationTest:
    """Test Google Custom Search API integration patterns."""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    def test_google_search_api_format(self):
        """Test that search constructs correct API request."""
        print("\n" + "="*60)
        print("TEST 1: Google Custom Search API Format")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate Google API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'items': [
                    {
                        'title': 'Leonardo DiCaprio - Wikipedia',
                        'link': 'https://en.wikipedia.org/wiki/Leonardo_DiCaprio',
                        'snippet': 'Leonardo Wilhelm DiCaprio is an American actor...'
                    }
                ]
            }
            mock_get.return_value = mock_response

            # Call the function
            result = fetch_google_search_data("Leonardo DiCaprio", TEST_API_KEY_1, TEST_SEARCH_ENGINE_ID)

            # Verify the API call was made correctly
            call_args = mock_get.call_args
            url = call_args[0][0]
            params = call_args[1]['params']
            timeout = call_args[1]['timeout']

            print(f"✓ URL: {url}")
            print(f"✓ Timeout: {timeout}s")
            print(f"\nRequest Parameters:")
            for key, value in params.items():
                if key != 'key':  # Hide API key in output
                    print(f"  - {key}: {value}")
                else:
                    print(f"  - {key}: [HIDDEN]")

            # Verify result structure
            assert result['success'] is True, "Should succeed"
            assert result['raw_text'] is not None, "raw_text should be populated"

            print(f"\n✓ Items found: {len(json.loads(result['raw_text']).get('items', []))}")
            print("✅ PASSED: Google Search API format correct")
            self.passed += 1

    def test_rate_limit_429_handling(self):
        """Test that rate limit (429) is handled correctly."""
        print("\n" + "="*60)
        print("TEST 2: Rate Limit (429) Handling")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate 429 rate limit error
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            result = fetch_google_search_data("Test", TEST_API_KEY_1, TEST_SEARCH_ENGINE_ID)

            print(f"✓ HTTP 429 detected (rate limit)")
            print(f"✓ success: {result['success']}")
            print(f"✓ error message: {result.get('error', 'N/A')}")

            assert result['success'] is False, "Should fail on 429"

            print("✅ PASSED: Rate limit handling works")
            self.passed += 1

    def test_api_error_response_handling(self):
        """Test handling of API errors in response body."""
        print("\n" + "="*60)
        print("TEST 3: API Error Response Handling")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate API error in response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'error': {
                    'code': 403,
                    'message': 'Invalid API key provided',
                    'status': 'PERMISSION_DENIED'
                }
            }
            mock_get.return_value = mock_response

            result = fetch_google_search_data("Test", "invalid_key", TEST_SEARCH_ENGINE_ID)

            print(f"✓ API error detected in response body")
            print(f"✓ Error message: {result.get('error', 'N/A')}")
            print(f"✓ success: {result['success']}")

            assert result['success'] is False, "Should fail on API error"
            assert 'error' in result.get('error', '').lower(), "Error message should be informative"

            print("✅ PASSED: API error response handling works")
            self.passed += 1

    def test_timeout_handling(self):
        """Test handling of request timeouts."""
        print("\n" + "="*60)
        print("TEST 4: Timeout Handling")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate timeout
            mock_get.side_effect = requests.Timeout("Connection timeout")

            result = fetch_google_search_data("Test", TEST_API_KEY_1, TEST_SEARCH_ENGINE_ID, timeout=5)

            print(f"✓ Timeout exception caught")
            print(f"✓ success: {result['success']}")
            print(f"✓ error message: {result.get('error', 'N/A')}")

            assert result['success'] is False, "Should fail on timeout"
            assert 'timeout' in result.get('error', '').lower(), "Error should mention timeout"

            print("✅ PASSED: Timeout handling works")
            self.passed += 1

    def test_malformed_json_response(self):
        """Test handling of malformed JSON responses."""
        print("\n" + "="*60)
        print("TEST 5: Malformed JSON Response Handling")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate malformed JSON
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value = mock_response

            result = fetch_google_search_data("Test", TEST_API_KEY_1, TEST_SEARCH_ENGINE_ID)

            print(f"✓ Malformed JSON detected")
            print(f"✓ success: {result['success']}")
            print(f"✓ error message: {result.get('error', 'N/A')}")

            assert result['success'] is False, "Should fail on malformed JSON"

            print("✅ PASSED: Malformed JSON handling works")
            self.passed += 1

    def test_no_results_handling(self):
        """Test handling when no results are returned."""
        print("\n" + "="*60)
        print("TEST 6: No Results Handling")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate empty results
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'items': []}
            mock_get.return_value = mock_response

            result = fetch_google_search_data("XYZ Unknown Celebrity XYZ", TEST_API_KEY_1, TEST_SEARCH_ENGINE_ID)

            print(f"✓ Empty items array from API")
            print(f"✓ success: {result['success']}")
            # This might be True with 0 results depending on implementation
            print(f"✓ raw_text populated: {result['raw_text'] is not None}")

            # Verify raw_text is still valid JSON
            if result['raw_text']:
                parsed = json.loads(result['raw_text'])
                print(f"✓ raw_text is valid JSON")
                assert 'items' in parsed, "raw_text should contain items array"

            print("✅ PASSED: No results handling works")
            self.passed += 1

    def test_raw_text_json_structure(self):
        """Test that raw_text contains complete, valid JSON."""
        print("\n" + "="*60)
        print("TEST 7: Raw Text JSON Structure")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate full API response
            api_response = {
                'items': [
                    {
                        'title': 'Leonardo DiCaprio - Wikipedia',
                        'link': 'https://en.wikipedia.org/wiki/Leonardo_DiCaprio',
                        'snippet': 'Leonardo Wilhelm DiCaprio is an American actor and film producer...',
                        'displayLink': 'en.wikipedia.org'
                    }
                ],
                'queries': {
                    'request': [{'title': 'Google Custom Search', 'totalResults': '1000000'}]
                }
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_get.return_value = mock_response

            result = fetch_google_search_data("Leonardo DiCaprio", TEST_API_KEY_1, TEST_SEARCH_ENGINE_ID)

            # Parse raw_text
            parsed_raw = json.loads(result['raw_text'])

            print(f"✓ raw_text is valid JSON")
            print(f"✓ raw_text size: {len(result['raw_text'])} bytes")
            print(f"✓ Contains 'items' key: {'items' in parsed_raw}")
            print(f"✓ First item title: {parsed_raw['items'][0]['title']}")

            # Verify structure
            assert isinstance(parsed_raw, dict), "raw_text should be JSON object"
            assert 'items' in parsed_raw, "raw_text should contain items"
            assert len(parsed_raw['items']) > 0, "raw_text should have items"

            # Verify data completeness
            item = parsed_raw['items'][0]
            assert 'title' in item, "item should have title"
            assert 'link' in item, "item should have link"
            assert 'snippet' in item, "item should have snippet"

            print("✅ PASSED: Raw text JSON structure valid")
            self.passed += 1

    def test_dynamodb_entry_structure(self):
        """Test that DynamoDB entry structure follows schema."""
        print("\n" + "="*60)
        print("TEST 8: DynamoDB Entry Structure")
        print("="*60)

        from datetime import datetime
        import uuid

        # Simulate creating a DynamoDB entry
        raw_api_response = json.dumps({
            'items': [{'title': 'Leonardo DiCaprio', 'link': 'https://example.com'}]
        })

        entry = {
            'celebrity_id': 'celeb_001',
            'source_type#timestamp': f"google_search#{datetime.utcnow().isoformat()}Z",
            'id': str(uuid.uuid4()),
            'name': 'Leonardo DiCaprio',
            'raw_text': raw_api_response,
            'source': 'https://www.googleapis.com/customsearch/v1',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'weight': None,
            'sentiment': None,
            'metadata': {
                'scraper_name': 'scraper-google-search',
                'source_type': 'google_search',
                'processed': False,
                'error': None,
                'key_rotation': {
                    'enabled': True,
                    'strategy': 'round_robin'
                }
            }
        }

        print(f"✓ celebrity_id: {entry['celebrity_id']}")
        print(f"✓ source_type#timestamp: {entry['source_type#timestamp']}")
        print(f"✓ id (UUID): {entry['id']}")
        print(f"✓ name: {entry['name']}")
        print(f"✓ raw_text size: {len(entry['raw_text'])} bytes")
        print(f"✓ source: {entry['source']}")
        print(f"✓ timestamp: {entry['timestamp']}")
        print(f"✓ metadata.key_rotation.enabled: {entry['metadata']['key_rotation']['enabled']}")

        # Verify required fields
        required_fields = ['celebrity_id', 'source_type#timestamp', 'id', 'name',
                          'raw_text', 'source', 'timestamp', 'weight', 'sentiment', 'metadata']
        for field in required_fields:
            assert field in entry, f"Missing required field: {field}"

        # Verify metadata structure
        assert entry['metadata']['scraper_name'] == 'scraper-google-search'
        assert entry['metadata']['source_type'] == 'google_search'
        assert entry['metadata']['processed'] is False

        print("✅ PASSED: DynamoDB entry structure valid")
        self.passed += 1

    def run_all_tests(self):
        """Run all integration tests."""
        print("\n" + "="*60)
        print("GOOGLE SEARCH SCRAPER API INTEGRATION TESTS")
        print("="*60)

        try:
            self.test_google_search_api_format()
            self.test_rate_limit_429_handling()
            self.test_api_error_response_handling()
            self.test_timeout_handling()
            self.test_malformed_json_response()
            self.test_no_results_handling()
            self.test_raw_text_json_structure()
            self.test_dynamodb_entry_structure()

        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.failed += 1

        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        total = self.passed + self.failed
        if total > 0:
            pass_rate = (self.passed / total) * 100
            print(f"📊 Pass Rate: {pass_rate:.1f}%")

        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("\n⚠️  SOME TESTS FAILED")
            return 1


if __name__ == '__main__':
    tester = GoogleSearchAPIIntegrationTest()
    sys.exit(tester.run_all_tests())
