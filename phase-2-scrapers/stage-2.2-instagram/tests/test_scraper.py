"""
Unit tests for Instagram scraper.

These tests use mocks and don't require actual AWS services.
Run with: pytest tests/test_scraper.py -v
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
import instaloader
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.mark.unit
class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_circuit_breaker_success(self):
        """Test circuit breaker on success."""
        from lambda_function import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3)
        assert breaker.can_execute()
        assert not breaker.is_open

        breaker.record_success()
        assert breaker.can_execute()
        assert breaker.failure_count == 0

    def test_circuit_breaker_opens_on_threshold(self):
        """Test circuit breaker opens after threshold failures."""
        from lambda_function import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3)

        # Record failures
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()

        assert breaker.is_open
        assert not breaker.can_execute()

    def test_circuit_breaker_resets_after_timeout(self):
        """Test circuit breaker resets after timeout."""
        from lambda_function import CircuitBreaker
        from datetime import datetime, timedelta
        from unittest.mock import patch

        breaker = CircuitBreaker(failure_threshold=2, timeout=1)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open

        # Simulate timeout passing
        breaker.last_failure_time = datetime.utcnow() - timedelta(seconds=2)

        assert breaker.can_execute()
        assert not breaker.is_open
        assert breaker.failure_count == 0


@pytest.mark.unit
class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_metrics_initialization(self):
        """Test metrics collector initialization."""
        from lambda_function import MetricsCollector

        metrics = MetricsCollector('test-request-123')

        assert metrics.request_id == 'test-request-123'
        assert metrics.metrics['successful_scrapes'] == 0
        assert metrics.metrics['failed_scrapes'] == 0

    def test_record_success(self):
        """Test recording successful scrape."""
        from lambda_function import MetricsCollector

        metrics = MetricsCollector('test-request-123')
        metrics.record_success()

        assert metrics.metrics['successful_scrapes'] == 1
        assert metrics.metrics['failed_scrapes'] == 0

    def test_record_failure(self):
        """Test recording failed scrape."""
        from lambda_function import MetricsCollector

        metrics = MetricsCollector('test-request-123')
        metrics.record_failure('profile_not_found')

        assert metrics.metrics['failed_scrapes'] == 1
        assert metrics.metrics['errors_by_type']['profile_not_found'] == 1

    def test_record_rate_limited(self):
        """Test recording rate limit."""
        from lambda_function import MetricsCollector

        metrics = MetricsCollector('test-request-123')
        metrics.record_rate_limited()

        assert metrics.metrics['rate_limited'] == 1

    def test_record_retry(self):
        """Test recording retry."""
        from lambda_function import MetricsCollector

        metrics = MetricsCollector('test-request-123')
        metrics.record_retry()
        metrics.record_retry()

        assert metrics.metrics['retry_count'] == 2

    @patch('lambda_function.cloudwatch')
    def test_publish_metrics(self, mock_cw):
        """Test publishing metrics to CloudWatch."""
        from lambda_function import MetricsCollector

        metrics = MetricsCollector('test-request-123')
        metrics.record_success()
        metrics.record_failure('network_error')

        metrics.publish()

        # Verify CloudWatch was called
        assert mock_cw.put_metric_data.called
        call_args = mock_cw.put_metric_data.call_args
        assert call_args[1]['Namespace'] == 'InstagramScraper'
        assert len(call_args[1]['MetricData']) > 0


@pytest.mark.unit
class TestInstagramScraperInit:
    """Test InstagramScraper initialization."""

    @patch('lambda_function.instaloader.Instaloader')
    def test_scraper_initialization(self, mock_instaloader, env_vars):
        """Test scraper initialization."""
        from lambda_function import InstagramScraper

        scraper = InstagramScraper('test-request-123')

        assert scraper.request_id == 'test-request-123'
        assert scraper.accounts == []
        assert scraper.account_index == 0
        assert scraper.processed_profiles == set()

    @pytest.mark.skip(reason="Environment variable loading requires Lambda context - tested in integration tests")
    @patch('lambda_function.secrets_client')
    @patch('lambda_function.instaloader.Instaloader')
    def test_load_accounts_success(self, mock_instaloader, mock_secrets, env_vars):
        """Test loading accounts from Secrets Manager (integration tested)."""
        pass

    @patch('lambda_function.secrets_client')
    @patch('lambda_function.instaloader.Instaloader')
    def test_load_accounts_missing_secret(self, mock_instaloader, mock_secrets, env_vars, monkeypatch):
        """Test loading accounts when secret doesn't exist."""
        from lambda_function import InstagramScraper
        from botocore.exceptions import ClientError

        monkeypatch.setenv('INSTAGRAM_ACCOUNTS_SECRET_ARN', 'arn:aws:secretsmanager:us-east-1:123456789012:secret:instagram-accounts')

        error = ClientError({'Error': {'Code': 'ResourceNotFoundException'}}, 'GetSecretValue')
        mock_secrets.get_secret_value.side_effect = error

        scraper = InstagramScraper('test-request-123')

        # Should fall back to anonymous mode
        assert scraper.accounts == []


@pytest.mark.unit
class TestInstagramScraperLogin:
    """Test InstagramScraper login functionality."""

    @patch('lambda_function.instaloader.Instaloader')
    def test_login_next_account_success(self, mock_instaloader, env_vars):
        """Test successful account login."""
        from lambda_function import InstagramScraper

        scraper = InstagramScraper('test-request-123')
        scraper.accounts = [
            {"account_id": "001", "username": "user1", "password": "pass1"}
        ]
        scraper.L.login = MagicMock()

        account_id = scraper.login_next_account()

        assert account_id == "001"
        scraper.L.login.assert_called_once()

    @patch('lambda_function.instaloader.Instaloader')
    def test_login_next_account_failure(self, mock_instaloader, env_vars):
        """Test account login failure falls back to anonymous."""
        from lambda_function import InstagramScraper

        scraper = InstagramScraper('test-request-123')
        scraper.accounts = [
            {"account_id": "001", "username": "user1", "password": "wrong"}
        ]
        scraper.L.login = MagicMock(side_effect=Exception("Invalid credentials"))

        account_id = scraper.login_next_account()

        assert account_id is None

    @patch('lambda_function.instaloader.Instaloader')
    def test_login_account_rotation(self, mock_instaloader, env_vars):
        """Test account rotation."""
        from lambda_function import InstagramScraper

        scraper = InstagramScraper('test-request-123')
        scraper.accounts = [
            {"account_id": "001", "username": "user1", "password": "pass1"},
            {"account_id": "002", "username": "user2", "password": "pass2"}
        ]
        scraper.L.login = MagicMock()

        # First call
        scraper.login_next_account()
        first_call = scraper.L.login.call_args[0][0]

        # Second call
        scraper.login_next_account()
        second_call = scraper.L.login.call_args[0][0]

        assert first_call == "user1"
        assert second_call == "user2"


@pytest.mark.unit
class TestInstagramScraperProfile:
    """Test Instagram profile scraping."""

    @patch('lambda_function.instaloader.Profile.from_username')
    @patch('lambda_function.instaloader.Instaloader')
    def test_scrape_success(self, mock_instaloader, mock_from_username, env_vars, mock_instaloader_profile):
        """Test successful profile scraping."""
        from lambda_function import InstagramScraper, ScraperStatus

        mock_from_username.return_value = mock_instaloader_profile

        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        success, data = scraper.scrape_instagram_profile('cristiano')

        assert success is True
        assert data['status'] == ScraperStatus.SUCCESS.value
        assert data['username'] == 'cristiano'
        assert data['followers'] == 600000000
        assert 'cristiano' in scraper.processed_profiles

    @patch('lambda_function.instaloader.Profile.from_username')
    @patch('lambda_function.instaloader.Instaloader')
    def test_scrape_profile_not_found(self, mock_instaloader, mock_from_username, env_vars):
        """Test scraping non-existent profile."""
        from lambda_function import InstagramScraper, ScraperStatus

        mock_from_username.side_effect = instaloader.exceptions.ProfileNotExistsException("Profile not found")

        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        success, data = scraper.scrape_instagram_profile('nonexistent')

        assert success is False
        assert data['status'] == ScraperStatus.PROFILE_NOT_FOUND.value

    @patch('lambda_function.instaloader.Profile.from_username')
    @patch('lambda_function.instaloader.Instaloader')
    def test_scrape_duplicate_profile(self, mock_instaloader, mock_from_username, env_vars):
        """Test scraping duplicate profile."""
        from lambda_function import InstagramScraper

        scraper = InstagramScraper('test-request-123')
        scraper.processed_profiles.add('cristiano')

        success, data = scraper.scrape_instagram_profile('cristiano')

        assert success is False
        assert data['status'] == 'duplicate'

    @patch('lambda_function.time.sleep')
    @patch('lambda_function.instaloader.Profile.from_username')
    @patch('lambda_function.instaloader.Instaloader')
    def test_scrape_rate_limited_with_retry(self, mock_instaloader, mock_from_username, mock_sleep, env_vars):
        """Test rate limiting with retry."""
        from lambda_function import InstagramScraper, ScraperStatus

        # Fail twice, succeed on third
        mock_from_username.side_effect = [
            instaloader.exceptions.TooManyRequestsException("Rate limited"),
            instaloader.exceptions.TooManyRequestsException("Rate limited"),
            MagicMock(
                username='cristiano',
                follower_count=600000000,
                mediacount=5000,
                biography='Footballer',
                is_verified=True,
                is_business_account=True,
                is_private=False,
                profile_pic_url='https://example.com/pic.jpg'
            )
        ]

        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        success, data = scraper.scrape_instagram_profile('cristiano')

        assert success is True
        assert data['status'] == ScraperStatus.SUCCESS.value
        # Should have called sleep twice (exponential backoff)
        assert mock_sleep.call_count == 2

    @patch('lambda_function.instaloader.Profile.from_username')
    @patch('lambda_function.instaloader.Instaloader')
    def test_scrape_max_retries_exhausted(self, mock_instaloader, mock_from_username, env_vars):
        """Test max retries exhausted."""
        from lambda_function import InstagramScraper, ScraperStatus

        mock_from_username.side_effect = instaloader.exceptions.TooManyRequestsException("Rate limited")

        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        success, data = scraper.scrape_instagram_profile('cristiano')

        assert success is False
        assert data['status'] == ScraperStatus.RATE_LIMITED.value


@pytest.mark.unit
class TestInstagramScraperDynamoDB:
    """Test DynamoDB operations."""

    @patch('lambda_function.dynamodb')
    @patch('lambda_function.instaloader.Instaloader')
    def test_save_to_dynamodb(self, mock_instaloader, mock_dynamodb, env_vars):
        """Test saving data to DynamoDB."""
        from lambda_function import InstagramScraper

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        scraper = InstagramScraper('test-request-123')

        instagram_data = {
            'username': 'cristiano',
            'followers': 600000000,
            'posts': 5000
        }

        result = scraper.save_to_dynamodb('celeb_001', 'Cristiano Ronaldo', instagram_data)

        assert result is True
        mock_table.put_item.assert_called_once()

    @patch('lambda_function.dynamodb')
    @patch('lambda_function.instaloader.Instaloader')
    def test_save_to_dynamodb_failure(self, mock_instaloader, mock_dynamodb, env_vars):
        """Test DynamoDB save failure."""
        from lambda_function import InstagramScraper

        mock_table = MagicMock()
        mock_table.put_item.side_effect = Exception("DynamoDB error")
        mock_dynamodb.Table.return_value = mock_table

        scraper = InstagramScraper('test-request-123')

        instagram_data = {'username': 'cristiano'}
        result = scraper.save_to_dynamodb('celeb_001', 'Cristiano Ronaldo', instagram_data)

        assert result is False


@pytest.mark.unit
class TestInstagramScraperProcessing:
    """Test celebrity processing."""

    @patch('lambda_function.instaloader.Instaloader')
    def test_process_celebrity_missing_handle(self, mock_instaloader, env_vars):
        """Test processing celebrity without Instagram handle."""
        from lambda_function import InstagramScraper

        scraper = InstagramScraper('test-request-123')

        celebrity = {
            'celebrity_id': 'celeb_001',
            'name': 'Unknown',
            'instagram_handle': None
        }

        result = scraper.process_celebrity(celebrity)

        assert result['status'] == 'skipped'
        assert result['reason'] == 'no_instagram_handle'

    @patch('lambda_function.dynamodb')
    @patch('lambda_function.instaloader.Profile.from_username')
    @patch('lambda_function.instaloader.Instaloader')
    def test_process_celebrity_success(self, mock_instaloader, mock_from_username, mock_dynamodb, env_vars, mock_instaloader_profile):
        """Test successful celebrity processing."""
        from lambda_function import InstagramScraper

        mock_from_username.return_value = mock_instaloader_profile
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        celebrity = {
            'celebrity_id': 'celeb_001',
            'name': 'Cristiano Ronaldo',
            'instagram_handle': 'cristiano'
        }

        result = scraper.process_celebrity(celebrity)

        assert result['status'] == 'success'
        assert mock_table.put_item.called


@pytest.mark.unit
class TestScraperStatus:
    """Test ScraperStatus enum."""

    def test_scraper_status_values(self):
        """Test ScraperStatus enum values."""
        from lambda_function import ScraperStatus

        assert ScraperStatus.SUCCESS.value == 'success'
        assert ScraperStatus.PROFILE_NOT_FOUND.value == 'profile_not_found'
        assert ScraperStatus.RATE_LIMITED.value == 'rate_limited'
        assert ScraperStatus.PRIVATE_ACCOUNT.value == 'private_account'
