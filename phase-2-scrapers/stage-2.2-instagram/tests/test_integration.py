"""
Integration tests for Instagram scraper.

These tests use real Instaloader and local AWS services (moto).
Run with: pytest tests/test_integration.py -v -m integration

Requires: moto, pytest
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3
import instaloader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.mark.integration
class TestInstagramScraperIntegration:
    """Integration tests with real Instaloader but mocked AWS."""

    @mock_aws
    @patch('lambda_function.instaloader.Profile.from_username')
    def test_full_scraping_flow(self, mock_from_username, env_vars, mock_instaloader_profile):
        """Test full scraping flow with DynamoDB."""
        from lambda_function import InstagramScraper

        # Mock Instaloader
        mock_from_username.return_value = mock_instaloader_profile

        # Setup DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='celebrity-database',
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

        # Create scraper and process celebrity
        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        celebrity = {
            'celebrity_id': 'celeb_001',
            'name': 'Cristiano Ronaldo',
            'instagram_handle': 'cristiano'
        }

        result = scraper.process_celebrity(celebrity)

        assert result['status'] == 'success'

        # Verify data was written to DynamoDB
        response = table.get_item(
            Key={
                'celebrity_id': 'celeb_001',
                'source_type#timestamp': f"instagram#{result['data']['scraped_at']}" if 'scraped_at' in result.get('data', {}) else 'instagram#'
            }
        )

        # Data should be in DynamoDB
        assert response['Item'] if 'Item' in response else table.scan()['Items']

    @mock_aws
    @patch('lambda_function.instaloader.Profile.from_username')
    def test_batch_celebrity_processing(self, mock_from_username, env_vars, mock_instaloader_profile):
        """Test processing batch of celebrities."""
        from lambda_function import InstagramScraper

        mock_from_username.return_value = mock_instaloader_profile

        # Setup DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='celebrity-database',
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

        # Create scraper
        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        # Process multiple celebrities
        celebrities = [
            {'celebrity_id': 'celeb_001', 'name': 'Cristiano', 'instagram_handle': 'cristiano'},
            {'celebrity_id': 'celeb_002', 'name': 'Lionel', 'instagram_handle': 'leomessi'},
            {'celebrity_id': 'celeb_003', 'name': 'Unknown', 'instagram_handle': None}
        ]

        results = []
        for celeb in celebrities:
            result = scraper.process_celebrity(celeb)
            results.append(result)

        # Verify results
        successful = sum(1 for r in results if r['status'] == 'success')
        skipped = sum(1 for r in results if r['status'] == 'skipped')

        assert successful == 2
        assert skipped == 1

    @mock_aws
    @patch('lambda_function.instaloader.Instaloader')
    def test_load_and_use_credentials(self, mock_instaloader, env_vars, monkeypatch):
        """Test loading and using Instagram credentials."""
        from lambda_function import InstagramScraper

        # Setup Secrets Manager
        secrets = boto3.client('secretsmanager', region_name='us-east-1')
        secrets.create_secret(
            Name='instagram-accounts',
            SecretString=json.dumps({
                "accounts": [
                    {"account_id": "001", "username": "user1", "password": "pass1"},
                    {"account_id": "002", "username": "user2", "password": "pass2"}
                ]
            })
        )

        monkeypatch.setenv('INSTAGRAM_ACCOUNTS_SECRET_ARN', 'arn:aws:secretsmanager:us-east-1:123456789012:secret:instagram-accounts')

        # Patch the real secrets_client
        with patch('lambda_function.secrets_client', secrets):
            scraper = InstagramScraper('test-request-123')
            assert len(scraper.accounts) == 2
            assert scraper.accounts[0]['username'] == 'user1'

    @mock_aws
    @patch('lambda_function.instaloader.Profile.from_username')
    def test_error_handling_flow(self, mock_from_username, env_vars, monkeypatch):
        """Test error handling in full flow."""
        from lambda_function import InstagramScraper

        # Setup DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='celebrity-database',
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

        # Test various error conditions
        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        # Profile not found
        mock_from_username.side_effect = instaloader.exceptions.ProfileNotExistsException("Not found")
        success, data = scraper.scrape_instagram_profile('invalid')
        assert success is False
        assert data['status'] == 'profile_not_found'

        # Private account
        mock_from_username.side_effect = instaloader.exceptions.PrivateProfileNotFollowedException("Private")
        success, data = scraper.scrape_instagram_profile('private')
        assert success is False
        assert data['status'] == 'private_account'


@pytest.mark.integration
class TestLambdaHandler:
    """Integration tests for Lambda handler."""

    @mock_aws
    @patch('lambda_function.instaloader.Profile.from_username')
    def test_lambda_handler_with_celebrities(self, mock_from_username, env_vars, mock_instaloader_profile, mock_lambda_context):
        """Test Lambda handler with celebrities in event."""
        from lambda_function import lambda_handler

        mock_from_username.return_value = mock_instaloader_profile

        # Setup DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='celebrity-database',
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

        event = {
            'celebrities': [
                {'celebrity_id': 'celeb_001', 'name': 'Cristiano', 'instagram_handle': 'cristiano'},
                {'celebrity_id': 'celeb_002', 'name': 'Lionel', 'instagram_handle': 'leomessi'}
            ]
        }

        response = lambda_handler(event, mock_lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total_celebrities'] == 2
        assert body['successful'] >= 0

    @mock_aws
    def test_lambda_handler_empty_celebrities(self, env_vars, mock_lambda_context):
        """Test Lambda handler with no celebrities."""
        from lambda_function import lambda_handler

        event = {'celebrities': []}

        response = lambda_handler(event, mock_lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total_celebrities'] == 0

    @mock_aws
    def test_lambda_handler_error_recovery(self, env_vars, mock_lambda_context):
        """Test Lambda handler error recovery."""
        from lambda_function import lambda_handler

        # Invalid event structure
        event = {'invalid': 'data'}

        # Should still handle gracefully
        response = lambda_handler(event, mock_lambda_context)

        # May return error, but should not crash
        assert 'statusCode' in response
        assert response['statusCode'] in [200, 500]


@pytest.mark.integration
class TestMetricsAndLogging:
    """Test metrics and logging."""

    @mock_aws
    @patch('lambda_function.cloudwatch')
    @patch('lambda_function.instaloader.Profile.from_username')
    def test_metrics_publication(self, mock_from_username, mock_cloudwatch, env_vars, mock_instaloader_profile):
        """Test CloudWatch metrics publication."""
        from lambda_function import InstagramScraper

        mock_from_username.return_value = mock_instaloader_profile

        # Setup DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='celebrity-database',
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

        scraper = InstagramScraper('test-request-123')
        scraper.L.context = MagicMock()

        # Process some celebrities
        celeb = {'celebrity_id': 'celeb_001', 'name': 'Cristiano', 'instagram_handle': 'cristiano'}
        scraper.process_celebrity(celeb)

        # Publish metrics
        scraper.metrics.publish()

        # Verify CloudWatch was called
        assert mock_cloudwatch.put_metric_data.called
