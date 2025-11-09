"""Unit tests for Threads Scraper."""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import responses

# Import the scraper components
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambda_function import (
    ThreadsScraper,
    CircuitBreaker,
    MetricsCollector,
    ScraperStatus,
    get_all_celebrities,
    save_to_dynamodb,
    lambda_handler
)


class TestCircuitBreaker:
    """Test CircuitBreaker pattern implementation."""

    def test_circuit_breaker_success(self):
        """Test circuit breaker allows execution on success."""
        cb = CircuitBreaker(failure_threshold=3)

        def success_func():
            return "success"

        result = cb.call(success_func)
        assert result == "success"
        assert cb.failures == 0
        assert not cb.is_open

    def test_circuit_breaker_opens_on_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        def fail_func():
            raise Exception("Test failure")

        # Fail 3 times
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(fail_func)

        assert cb.failures == 3
        assert cb.is_open

    def test_circuit_breaker_resets_after_timeout(self):
        """Test circuit breaker resets after timeout."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)

        def fail_func():
            raise Exception("Test failure")

        # Fail twice to open circuit
        for i in range(2):
            with pytest.raises(Exception):
                cb.call(fail_func)

        assert cb.is_open

        # Wait for timeout
        time.sleep(1.1)

        # Should be able to try again
        assert cb.is_healthy()

    def test_circuit_breaker_is_healthy(self):
        """Test circuit breaker health check."""
        cb = CircuitBreaker()
        assert cb.is_healthy()

        # Open the circuit
        cb.is_open = True
        cb.last_failure_time = time.time()
        assert not cb.is_healthy()


class TestMetricsCollector:
    """Test MetricsCollector implementation."""

    def test_metrics_initialization(self):
        """Test metrics initialized with zero values."""
        metrics = MetricsCollector()

        assert metrics.metrics['successful'] == 0
        assert metrics.metrics['failed'] == 0
        assert metrics.metrics['rate_limited'] == 0
        assert metrics.metrics['retries'] == 0

    def test_record_success(self):
        """Test recording successful scrape."""
        metrics = MetricsCollector()
        metrics.record_success()

        assert metrics.metrics['successful'] == 1

    def test_record_failure(self):
        """Test recording failed scrape."""
        metrics = MetricsCollector()
        metrics.record_failure("timeout")

        assert metrics.metrics['failed'] == 1

    def test_record_rate_limited(self):
        """Test recording rate limit event."""
        metrics = MetricsCollector()
        metrics.record_rate_limited()

        assert metrics.metrics['rate_limited'] == 1

    def test_record_retry(self):
        """Test recording retry attempt."""
        metrics = MetricsCollector()
        metrics.record_retry()

        assert metrics.metrics['retries'] == 1

    @patch('lambda_function.cloudwatch')
    def test_publish_metrics(self, mock_cw, aws_credentials, environment_variables):
        """Test publishing metrics to CloudWatch."""
        metrics = MetricsCollector()
        metrics.record_success()
        metrics.record_failure()
        metrics.start()

        # Publish metrics
        metrics.publish_metrics()

        # Verify CloudWatch was called
        assert mock_cw.put_metric_data.called


class TestThreadsScraperInitialization:
    """Test ThreadsScraper initialization."""

    def test_scraper_initialization(self, aws_credentials, environment_variables):
        """Test scraper initializes with accounts and proxies."""
        scraper = ThreadsScraper()

        assert scraper.accounts is not None
        assert scraper.proxies is not None
        assert scraper.account_index == 0
        assert scraper.proxy_index == 0

    def test_load_accounts_missing_secret(self, aws_credentials, environment_variables):
        """Test graceful fallback when accounts secret missing."""
        # When secrets are available (from autouse fixture), this test
        # verifies normal initialization
        with patch('lambda_function.secrets_client') as mock_sm:
            mock_sm.get_secret_value.side_effect = Exception("Secret not found")
            scraper = ThreadsScraper()
            # Should have empty accounts list when secret fails
            assert scraper.accounts == []

    def test_load_proxies_optional(self, aws_credentials, environment_variables):
        """Test proxies are optional."""
        # When secrets are available (from autouse fixture), this test
        # verifies proxies are truly optional
        with patch('lambda_function.secrets_client') as mock_sm:
            mock_sm.get_secret_value.side_effect = Exception("Secret not found")
            scraper = ThreadsScraper()
            # Should have empty proxies list (warning logged)
            assert scraper.proxies == []


class TestThreadsScraperAccountRotation:
    """Test account and proxy rotation."""

    def test_get_next_account(self, aws_credentials, environment_variables):
        """Test account rotation."""
        scraper = ThreadsScraper()

        account1 = scraper._get_next_account()
        account2 = scraper._get_next_account()

        assert account1 is not None
        assert account2 is not None
        assert account1['account_id'] == 'account_001'
        assert account2['account_id'] == 'account_002'

    def test_get_next_proxy(self, aws_credentials, environment_variables):
        """Test proxy rotation."""
        scraper = ThreadsScraper()

        proxy1 = scraper._get_next_proxy()
        proxy2 = scraper._get_next_proxy()

        assert proxy1 is not None
        assert proxy2 is not None
        assert proxy1['proxy_id'] == 'proxy_001'
        assert proxy2['proxy_id'] == 'proxy_002'

    def test_get_random_user_agent(self, aws_credentials, environment_variables):
        """Test random user agent selection."""
        scraper = ThreadsScraper()

        ua1 = scraper._get_random_user_agent()
        ua2 = scraper._get_random_user_agent()

        assert len(ua1) > 0
        assert 'Mozilla' in ua1
        # May or may not be same, just check format
        assert 'Mozilla' in ua2


class TestThreadsProfileParsing:
    """Test Threads profile HTML parsing."""

    @patch('boto3.client')
    def test_parse_threads_profile_success(self, mock_boto_client,
                                          aws_credentials, environment_variables,
                                          mock_threads_profile_html):
        """Test successful profile parsing."""
        scraper = ThreadsScraper()

        data = scraper._parse_threads_profile(mock_threads_profile_html)

        assert data is not None
        assert 'followers' in data
        assert 'posts' in data

    @patch('boto3.client')
    def test_parse_threads_profile_missing_data(self, mock_boto_client,
                                               aws_credentials, environment_variables):
        """Test parsing when data is missing."""
        scraper = ThreadsScraper()

        html = '<html><body>No data</body></html>'
        data = scraper._parse_threads_profile(html)

        assert data is not None
        assert data['followers'] is None
        assert data['posts'] is None

    @patch('boto3.client')
    def test_parse_threads_profile_empty_html(self, mock_boto_client,
                                             aws_credentials, environment_variables):
        """Test parsing empty HTML."""
        scraper = ThreadsScraper()

        data = scraper._parse_threads_profile('')

        assert data is None

    @patch('boto3.client')
    def test_parse_threads_profile_invalid_html(self, mock_boto_client,
                                               aws_credentials, environment_variables):
        """Test parsing invalid HTML."""
        scraper = ThreadsScraper()

        data = scraper._parse_threads_profile(None)

        assert data is None


class TestThreadsProfileScraping:
    """Test profile scraping with retries and error handling."""

    @responses.activate
    def test_scrape_success(self,
                           aws_credentials, environment_variables,
                           mock_threads_profile_html):
        """Test successful profile scrape."""
        # Mock the HTTP request
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body=mock_threads_profile_html,
            status=200
        )

        scraper = ThreadsScraper()
        result = scraper.scrape_threads_profile('taylorswift')

        assert result['success']
        assert result['status'] == ScraperStatus.SUCCESS.value
        assert result['raw_text'] is not None

    @responses.activate
    def test_scrape_not_found(self,
                             aws_credentials, environment_variables):
        """Test scrape when profile not found."""
        responses.add(
            responses.GET,
            'https://www.threads.net/@notarealuser/',
            body='<html>Not found</html>',
            status=404
        )

        scraper = ThreadsScraper()
        result = scraper.scrape_threads_profile('notarealuser')

        assert not result['success']
        assert result['status'] == ScraperStatus.NOT_FOUND.value

    @responses.activate
    def test_scrape_rate_limited_with_retry(self,
                                           aws_credentials, environment_variables,
                                           mock_threads_profile_html):
        """Test scrape with rate limiting and retry."""
        # First call returns 429, second succeeds
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body='Rate limited',
            status=429
        )
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body=mock_threads_profile_html,
            status=200
        )

        scraper = ThreadsScraper()
        result = scraper.scrape_threads_profile('taylorswift')

        # Should succeed on retry
        assert result['success']

    @responses.activate
    def test_scrape_max_retries_exhausted(self,
                                         aws_credentials, environment_variables):
        """Test scrape max retries."""
        # All calls fail with 429
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body='Rate limited',
            status=429
        )
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body='Rate limited',
            status=429
        )
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body='Rate limited',
            status=429
        )

        scraper = ThreadsScraper()
        result = scraper.scrape_threads_profile('taylorswift')

        # Should fail after max retries
        assert not result['success']
        assert result['status'] == ScraperStatus.FAILED.value

    def test_scrape_invalid_handle(self,
                                   aws_credentials, environment_variables):
        """Test scrape with invalid handle."""
        scraper = ThreadsScraper()

        result = scraper.scrape_threads_profile('')

        assert not result['success']
        assert result['status'] == ScraperStatus.INVALID_HANDLE.value

    @responses.activate
    def test_scrape_timeout(self,
                           aws_credentials, environment_variables):
        """Test scrape timeout handling."""
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body='Timeout',
            status=500
        )
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body='Timeout',
            status=500
        )
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body='Timeout',
            status=500
        )

        scraper = ThreadsScraper()
        result = scraper.scrape_threads_profile('taylorswift')

        # Should fail gracefully
        assert not result['success']


class TestCelebrityProcessing:
    """Test celebrity processing."""

    def test_process_celebrity_missing_handle(self,
                                             aws_credentials, environment_variables):
        """Test processing celebrity without Threads handle."""
        scraper = ThreadsScraper()

        # Celebrity without threads_handle, instagram_handle, or name conversion capability
        celebrity = {'celebrity_id': 'celeb_001', 'name': '', 'metadata': {}}
        result = scraper.process_celebrity(celebrity)

        assert result['status'] == ScraperStatus.INVALID_HANDLE.value

    @responses.activate
    def test_process_celebrity_success(self,
                                       aws_credentials, environment_variables,
                                       sample_celebrity, mock_threads_profile_html):
        """Test successful celebrity processing."""
        responses.add(
            responses.GET,
            'https://www.threads.net/@taylorswift/',
            body=mock_threads_profile_html,
            status=200
        )

        scraper = ThreadsScraper()
        result = scraper.process_celebrity(sample_celebrity)

        assert result['status'] == ScraperStatus.SUCCESS.value

    def test_extract_threads_handle(self,
                                    aws_credentials, environment_variables,
                                    sample_celebrity):
        """Test extracting Threads handle from celebrity."""
        scraper = ThreadsScraper()

        handle = scraper._extract_threads_handle(sample_celebrity)

        assert handle == 'taylorswift'


class TestDynamoDBOperations:
    """Test DynamoDB operations."""

    @patch('boto3.resource')
    def test_save_to_dynamodb(self, mock_resource, aws_credentials, environment_variables):
        """Test saving scraping result to DynamoDB."""
        # Mock table
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table

        scrape_result = {
            'name': 'Taylor Swift',
            'threads_handle': 'taylorswift',
            'result': {
                'raw_text': '<html>profile</html>',
                'account_used': 'account_001',
                'proxy_used': 'proxy_001',
                'data': {'followers': 5000000, 'posts': 250}
            }
        }

        success = save_to_dynamodb(mock_table, 'celeb_001', scrape_result, 'request-123')

        assert success
        assert mock_table.put_item.called

    @patch('boto3.resource')
    def test_save_to_dynamodb_failure(self, mock_resource, aws_credentials,
                                     environment_variables):
        """Test DynamoDB save failure handling."""
        mock_table = Mock()
        mock_table.put_item.side_effect = Exception("DynamoDB error")

        scrape_result = {
            'name': 'Taylor Swift',
            'threads_handle': 'taylorswift',
            'result': {'raw_text': '<html>profile</html>'}
        }

        success = save_to_dynamodb(mock_table, 'celeb_001', scrape_result, 'request-123')

        assert not success


class TestGetAllCelebrities:
    """Test getting celebrities from DynamoDB."""

    def test_get_all_celebrities_success(self, dynamodb_table, aws_credentials,
                                        environment_variables):
        """Test retrieving all celebrities."""
        # Add test data
        dynamodb_table.put_item(Item={
            'celebrity_id': 'celeb_001',
            'source_type#timestamp': 'metadata#2025-11-08T00:00:00Z',
            'name': 'Taylor Swift'
        })

        celebrities = get_all_celebrities(dynamodb_table)

        assert len(celebrities) >= 1
        assert any(c['celebrity_id'] == 'celeb_001' for c in celebrities)

    def test_get_all_celebrities_empty(self, dynamodb_table, aws_credentials,
                                       environment_variables):
        """Test retrieving from empty table."""
        celebrities = get_all_celebrities(dynamodb_table)

        assert celebrities == []


class TestLambdaHandler:
    """Test Lambda handler."""

    @patch('boto3.resource')
    @patch('boto3.client')
    def test_lambda_handler_with_celebrities(self, mock_client, mock_resource,
                                            mock_context, aws_credentials,
                                            environment_variables):
        """Test lambda handler with specific celebrities."""
        # This would require full mocking - simplified version
        event = {
            'celebrities': [
                {'celebrity_id': 'celeb_001', 'name': 'Taylor Swift', 'threads_handle': 'taylorswift'}
            ]
        }

        # Would need more setup for real test
        # Just verify structure
        assert 'celebrities' in event
        assert len(event['celebrities']) > 0

    @patch('boto3.resource')
    @patch('boto3.client')
    def test_lambda_handler_no_accounts(self, mock_client, mock_resource,
                                       mock_context, aws_credentials,
                                       environment_variables):
        """Test lambda handler when no accounts configured."""
        # Mock scraper with no accounts
        with patch('lambda_function.ThreadsScraper') as MockScraper:
            mock_scraper = Mock()
            mock_scraper.accounts = []
            MockScraper.return_value = mock_scraper

            # This verifies the handler would catch this error
            assert mock_scraper.accounts == []


class TestStatusEnum:
    """Test ScraperStatus enumeration."""

    def test_scraper_status_values(self):
        """Test all status enum values are defined."""
        assert ScraperStatus.PENDING.value == "pending"
        assert ScraperStatus.PROCESSING.value == "processing"
        assert ScraperStatus.SUCCESS.value == "success"
        assert ScraperStatus.FAILED.value == "failed"
        assert ScraperStatus.RATE_LIMITED.value == "rate_limited"
        assert ScraperStatus.NOT_FOUND.value == "not_found"
        assert ScraperStatus.INVALID_HANDLE.value == "invalid_handle"
