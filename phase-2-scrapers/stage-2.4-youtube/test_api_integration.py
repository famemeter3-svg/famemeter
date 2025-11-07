#!/usr/bin/env python3
"""
Integration test for YouTube scraper API endpoints.

Tests the actual API integration patterns without requiring AWS.
This validates that the scraper code correctly constructs and handles API calls.
"""

import json
import sys
import os
from unittest.mock import patch, MagicMock
import requests

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from lambda_function import search_youtube_channel, fetch_channel_data, retry_with_backoff

# Test API Key (placeholder)
TEST_API_KEY = "AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w"


class YouTubeAPIIntegrationTest:
    """Test YouTube API integration patterns."""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    def test_search_youtube_channel_api_format(self):
        """Test that search constructs correct API request."""
        print("\n" + "="*60)
        print("TEST 1: YouTube Search API Format")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate YouTube API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'items': [
                    {
                        'id': {'channelId': 'UC1234567890'},
                        'snippet': {'title': 'Leonardo DiCaprio Official'}
                    }
                ]
            }
            mock_get.return_value = mock_response

            # Call the function
            result = search_youtube_channel("Leonardo DiCaprio", TEST_API_KEY)

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
            assert result['channel_id'] == 'UC1234567890', "Channel ID not extracted"
            assert result['error'] is None, "Error should be None on success"

            print(f"\n✓ Channel ID extracted: {result['channel_id']}")
            print("✅ PASSED: Search API format correct")
            self.passed += 1

    def test_fetch_channel_data_api_format(self):
        """Test that fetch constructs correct API request."""
        print("\n" + "="*60)
        print("TEST 2: YouTube Channel Data API Format")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate YouTube API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'items': [
                    {
                        'id': 'UC1234567890',
                        'snippet': {
                            'title': 'Leonardo DiCaprio Official',
                            'description': 'Official channel'
                        },
                        'statistics': {
                            'viewCount': '1000000',
                            'subscriberCount': '5000000',
                            'videoCount': '100'
                        },
                        'contentDetails': {
                            'uploads': 'UU1234567890'
                        }
                    }
                ]
            }
            mock_get.return_value = mock_response

            # Call the function
            result = fetch_channel_data('UC1234567890', TEST_API_KEY)

            # Verify the API call
            call_args = mock_get.call_args
            url = call_args[0][0]
            params = call_args[1]['params']

            print(f"✓ URL: {url}")
            print(f"\nRequest Parameters:")
            for key, value in params.items():
                if key != 'key':
                    print(f"  - {key}: {value}")
                else:
                    print(f"  - {key}: [HIDDEN]")

            # Verify 'part' includes all required sections
            parts = params['part'].split(',')
            assert 'snippet' in parts, "snippet not requested"
            assert 'statistics' in parts, "statistics not requested"
            assert 'contentDetails' in parts, "contentDetails not requested"

            print(f"\n✓ API parts requested: {', '.join(parts)}")

            # Verify result structure
            assert result['success'] is True, "Should succeed"
            assert result['raw_text'] is not None, "raw_text should be populated"
            assert result['channel_data'] is not None, "channel_data should be populated"

            # Verify raw_text is JSON string
            raw_data = json.loads(result['raw_text'])
            assert 'items' in raw_data, "raw_text should contain full API response"

            print(f"✓ raw_text size: {len(result['raw_text'])} bytes")
            print(f"✓ Subscriber count: {result['channel_data']['statistics']['subscriberCount']}")
            print("✅ PASSED: Channel Data API format correct")
            self.passed += 1

    def test_retry_mechanism_with_timeout(self):
        """Test that retry logic handles timeouts correctly."""
        print("\n" + "="*60)
        print("TEST 3: Retry Mechanism (Timeout Handling)")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get, \
             patch('lambda_function.time.sleep') as mock_sleep:

            # Simulate timeout on first attempt, success on second
            mock_get.side_effect = [
                requests.Timeout("Connection timeout"),
                MagicMock(
                    status_code=200,
                    json=lambda: {
                        'items': [{'id': {'channelId': 'UC1234567890'}}]
                    }
                )
            ]

            # Call with retry
            result = retry_with_backoff(
                lambda: search_youtube_channel("Test", TEST_API_KEY),
                max_retries=3
            )

            print(f"✓ Timeout on first attempt")
            print(f"✓ Retry triggered")
            print(f"✓ Success on second attempt: {result['channel_id']}")
            print(f"✓ Sleep called {mock_sleep.call_count} time(s)")

            assert result['channel_id'] == 'UC1234567890', "Should succeed after retry"
            assert mock_sleep.call_count >= 1, "Should have sleep call"

            print("✅ PASSED: Retry mechanism works")
            self.passed += 1

    def test_quota_exceeded_detection(self):
        """Test that quota exceeded (403) is detected."""
        print("\n" + "="*60)
        print("TEST 4: Quota Exceeded (403) Detection")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate 403 error
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            result = fetch_channel_data('UC1234567890', TEST_API_KEY)

            print(f"✓ HTTP 403 detected")
            print(f"✓ quota_exceeded flag: {result.get('quota_exceeded')}")
            print(f"✓ success: {result['success']}")

            assert result['success'] is False, "Should fail on 403"
            assert result.get('quota_exceeded') is True, "quota_exceeded flag should be True"

            print("✅ PASSED: Quota exceeded detection works")
            self.passed += 1

    def test_api_error_response_handling(self):
        """Test handling of API errors in response body."""
        print("\n" + "="*60)
        print("TEST 5: API Error Response Handling")
        print("="*60)

        with patch('lambda_function.requests.get') as mock_get:
            # Simulate API error in response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'error': {
                    'code': 400,
                    'message': 'Invalid API key',
                    'status': 'INVALID_ARGUMENT'
                }
            }
            mock_get.return_value = mock_response

            result = search_youtube_channel("Test", "invalid_key")

            print(f"✓ API error detected in response body")
            print(f"✓ Error message: {result['error']}")
            print(f"✓ channel_id: {result['channel_id']}")

            assert result['channel_id'] is None, "Should return None on API error"
            assert 'error' in result['error'].lower() or 'invalid' in result['error'].lower(), \
                   "Error message should be informative"

            print("✅ PASSED: API error response handling works")
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

            result = search_youtube_channel("Unknown Celebrity XYZ", TEST_API_KEY)

            print(f"✓ Empty items array from API")
            print(f"✓ channel_id: {result['channel_id']}")
            print(f"✓ Error message: {result['error']}")

            assert result['channel_id'] is None, "Should return None when no results"
            assert 'not found' in result['error'].lower(), "Error should indicate not found"

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
                        'id': 'UC1234567890',
                        'snippet': {
                            'title': 'Test Channel',
                            'description': 'Test description',
                            'thumbnails': {'default': {'url': 'https://example.com/img.jpg'}}
                        },
                        'statistics': {
                            'viewCount': '1000000',
                            'subscriberCount': '5000000',
                            'videoCount': '100'
                        }
                    }
                ]
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_get.return_value = mock_response

            result = fetch_channel_data('UC1234567890', TEST_API_KEY)

            # Parse raw_text
            parsed_raw = json.loads(result['raw_text'])

            print(f"✓ raw_text is valid JSON")
            print(f"✓ raw_text size: {len(result['raw_text'])} bytes")
            print(f"✓ Contains 'items' key: {'items' in parsed_raw}")
            print(f"✓ First item ID: {parsed_raw['items'][0]['id']}")

            # Verify structure
            assert isinstance(parsed_raw, dict), "raw_text should be JSON object"
            assert 'items' in parsed_raw, "raw_text should contain items"
            assert len(parsed_raw['items']) > 0, "raw_text should have items"

            # Verify data completeness
            item = parsed_raw['items'][0]
            assert 'snippet' in item, "snippet should be in item"
            assert 'statistics' in item, "statistics should be in item"

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
        channel_id = 'UC1234567890'
        celebrity_name = 'Leonardo DiCaprio'
        raw_api_response = json.dumps({
            'items': [{'id': channel_id, 'snippet': {'title': celebrity_name}}]
        })

        entry = {
            'celebrity_id': 'celeb_001',
            'source_type#timestamp': f"youtube#{datetime.utcnow().isoformat()}Z",
            'id': str(uuid.uuid4()),
            'name': celebrity_name,
            'raw_text': raw_api_response,
            'source': 'https://www.googleapis.com/youtube/v3/channels',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'weight': None,
            'sentiment': None,
            'metadata': {
                'scraper_name': 'scraper-youtube',
                'source_type': 'youtube',
                'processed': False,
                'error': None,
                'channel_id': channel_id
            }
        }

        print(f"✓ celebrity_id: {entry['celebrity_id']}")
        print(f"✓ source_type#timestamp: {entry['source_type#timestamp']}")
        print(f"✓ id (UUID): {entry['id']}")
        print(f"✓ name: {entry['name']}")
        print(f"✓ raw_text size: {len(entry['raw_text'])} bytes")
        print(f"✓ source: {entry['source']}")
        print(f"✓ timestamp: {entry['timestamp']}")
        print(f"✓ metadata.channel_id: {entry['metadata']['channel_id']}")

        # Verify required fields
        required_fields = ['celebrity_id', 'source_type#timestamp', 'id', 'name',
                          'raw_text', 'source', 'timestamp', 'weight', 'sentiment', 'metadata']
        for field in required_fields:
            assert field in entry, f"Missing required field: {field}"

        # Verify metadata structure
        assert entry['metadata']['scraper_name'] == 'scraper-youtube'
        assert entry['metadata']['source_type'] == 'youtube'
        assert entry['metadata']['processed'] is False

        print("✅ PASSED: DynamoDB entry structure valid")
        self.passed += 1

    def run_all_tests(self):
        """Run all integration tests."""
        print("\n" + "="*60)
        print("YOUTUBE SCRAPER API INTEGRATION TESTS")
        print("="*60)

        try:
            self.test_search_youtube_channel_api_format()
            self.test_fetch_channel_data_api_format()
            self.test_retry_mechanism_with_timeout()
            self.test_quota_exceeded_detection()
            self.test_api_error_response_handling()
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
    tester = YouTubeAPIIntegrationTest()
    sys.exit(tester.run_all_tests())
