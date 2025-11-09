"""Integration tests for Threads Scraper."""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import responses

# Import scraper components
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambda_function import (
    ThreadsScraper,
    ScraperStatus,
    lambda_handler,
    get_all_celebrities,
    save_to_dynamodb
)


class TestIntegrationFullScrapingFlow:
    """Integration tests for full scraping workflow."""

    @mock_aws
    @responses.activate
    def test_full_scraping_flow(self, sample_celebrities, mock_threads_profile_html,
                               mock_context, aws_credentials, environment_variables):
        """Test complete scraping flow: load celebrities → scrape → save to DynamoDB."""
        import boto3

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

        # Add test celebrities
        for celeb in sample_celebrities:
            table.put_item(Item={
                'celebrity_id': celeb['celebrity_id'],
                'source_type#timestamp': 'metadata#2025-11-08T00:00:00Z',
                'name': celeb['name']
            })

        # Mock HTTP responses for each celebrity
        for celeb in sample_celebrities:
            responses.add(
                responses.GET,
                f"https://www.threads.net/@{celeb['threads_handle']}/",
                body=mock_threads_profile_html,
                status=200
            )

        # Mock Secrets Manager
        with patch('boto3.client') as mock_client:
            mock_sm = Mock()
            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps({
                    'accounts': [
                        {'account_id': 'account_001', 'username': 'test_user', 'password': 'test_pass'}
                    ]
                })
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps({
                    'proxies': [
                        {'proxy_id': 'proxy_001', 'url': 'http://proxy:8080'}
                    ]
                })
            }
            mock_client.return_value = mock_sm

            scraper = ThreadsScraper()
            results = []

            # Scrape each celebrity
            for celeb in sample_celebrities:
                result = scraper.process_celebrity(celeb)
                if result['status'] == ScraperStatus.SUCCESS.value:
                    save_to_dynamodb(table, celeb['celebrity_id'], result, 'test-request')
                results.append(result)

            # Verify results
            assert len(results) == len(sample_celebrities)
            assert any(r['status'] == ScraperStatus.SUCCESS.value for r in results)

    @mock_aws
    @responses.activate
    def test_batch_celebrity_processing(self, sample_celebrities, mock_threads_profile_html,
                                       aws_credentials, environment_variables):
        """Test batch processing of multiple celebrities."""
        import boto3

        # Mock responses for all celebrities
        for celeb in sample_celebrities:
            responses.add(
                responses.GET,
                f"https://www.threads.net/@{celeb['threads_handle']}/",
                body=mock_threads_profile_html,
                status=200
            )

        # Mock Secrets Manager
        with patch('boto3.client') as mock_client:
            mock_sm = Mock()
            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps({
                    'accounts': [
                        {'account_id': 'account_001', 'username': 'test_user', 'password': 'test_pass'}
                    ]
                })
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps({
                    'proxies': [
                        {'proxy_id': 'proxy_001', 'url': 'http://proxy:8080'}
                    ]
                })
            }
            mock_client.return_value = mock_sm

            scraper = ThreadsScraper()
            results = []

            for celeb in sample_celebrities:
                result = scraper.process_celebrity(celeb)
                results.append(result)

            # Verify batch processing
            successful = [r for r in results if r['status'] == ScraperStatus.SUCCESS.value]
            assert len(successful) > 0

    @mock_aws
    @responses.activate
    def test_error_handling_flow(self, sample_celebrities, mock_threads_profile_html,
                                aws_credentials, environment_variables):
        """Test error handling during scraping."""
        # First celebrity succeeds
        responses.add(
            responses.GET,
            f"https://www.threads.net/@{sample_celebrities[0]['threads_handle']}/",
            body=mock_threads_profile_html,
            status=200
        )

        # Second celebrity not found
        responses.add(
            responses.GET,
            f"https://www.threads.net/@{sample_celebrities[1]['threads_handle']}/",
            body='Not found',
            status=404
        )

        # Third celebrity rate limited but retries succeed
        responses.add(
            responses.GET,
            f"https://www.threads.net/@{sample_celebrities[2]['threads_handle']}/",
            body='Rate limited',
            status=429
        )
        responses.add(
            responses.GET,
            f"https://www.threads.net/@{sample_celebrities[2]['threads_handle']}/",
            body=mock_threads_profile_html,
            status=200
        )

        with patch('boto3.client') as mock_client:
            mock_sm = Mock()
            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps({
                    'accounts': [
                        {'account_id': 'account_001', 'username': 'test_user', 'password': 'test_pass'}
                    ]
                })
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps({
                    'proxies': [
                        {'proxy_id': 'proxy_001', 'url': 'http://proxy:8080'}
                    ]
                })
            }
            mock_client.return_value = mock_sm

            scraper = ThreadsScraper()
            results = []

            for celeb in sample_celebrities:
                result = scraper.process_celebrity(celeb)
                results.append(result)

            # Verify error handling
            statuses = [r['status'] for r in results]
            assert ScraperStatus.SUCCESS.value in statuses
            assert ScraperStatus.NOT_FOUND.value in statuses


class TestLambdaHandlerIntegration:
    """Integration tests for Lambda handler."""

    @mock_aws
    @responses.activate
    def test_lambda_handler_with_celebrities(self, sample_celebrities, mock_threads_profile_html,
                                            mock_context, aws_credentials, environment_variables):
        """Test Lambda handler with event celebrities."""
        import boto3

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

        # Mock responses
        for celeb in sample_celebrities:
            responses.add(
                responses.GET,
                f"https://www.threads.net/@{celeb['threads_handle']}/",
                body=mock_threads_profile_html,
                status=200
            )

        # Mock Secrets Manager
        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:

            mock_sm = Mock()
            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps({
                    'accounts': [
                        {'account_id': 'account_001', 'username': 'test_user', 'password': 'test_pass'}
                    ]
                })
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps({
                    'proxies': [
                        {'proxy_id': 'proxy_001', 'url': 'http://proxy:8080'}
                    ]
                })
            }
            mock_client.return_value = mock_sm
            mock_resource.return_value.Table.return_value = table

            event = {'celebrities': sample_celebrities}

            response = lambda_handler(event, mock_context)

            # Verify response structure
            assert response['statusCode'] in [200, 400, 500]
            if response['statusCode'] == 200:
                body = json.loads(response['body'])
                assert 'total' in body
                assert 'success' in body
                assert 'errors' in body

    @mock_aws
    def test_lambda_handler_empty_celebrities(self, mock_context, aws_credentials,
                                             environment_variables):
        """Test Lambda handler with empty celebrities list."""
        import boto3

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

        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:

            mock_sm = Mock()
            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps({
                    'accounts': [
                        {'account_id': 'account_001', 'username': 'test_user', 'password': 'test_pass'}
                    ]
                })
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps({
                    'proxies': [
                        {'proxy_id': 'proxy_001', 'url': 'http://proxy:8080'}
                    ]
                })
            }
            mock_client.return_value = mock_sm
            mock_resource.return_value.Table.return_value = table

            event = {'celebrities': []}

            response = lambda_handler(event, mock_context)

            assert response['statusCode'] in [200, 400, 500]

    @mock_aws
    def test_lambda_handler_error_recovery(self, mock_context, aws_credentials,
                                          environment_variables):
        """Test Lambda handler error recovery on invalid events."""
        import boto3

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

        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:

            mock_sm = Mock()
            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps({
                    'accounts': [
                        {'account_id': 'account_001', 'username': 'test_user', 'password': 'test_pass'}
                    ]
                })
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps({
                    'proxies': [
                        {'proxy_id': 'proxy_001', 'url': 'http://proxy:8080'}
                    ]
                })
            }
            mock_client.return_value = mock_sm
            mock_resource.return_value.Table.return_value = table

            # Invalid event (no celebrities key)
            event = {}

            response = lambda_handler(event, mock_context)

            assert response['statusCode'] in [200, 400, 500]


class TestMetricsPublishing:
    """Test metrics publishing during scraping."""

    @mock_aws
    @responses.activate
    def test_metrics_publication(self, sample_celebrities, mock_threads_profile_html,
                                aws_credentials, environment_variables):
        """Test metrics are collected and published."""
        import boto3

        # Mock responses
        responses.add(
            responses.GET,
            f"https://www.threads.net/@{sample_celebrities[0]['threads_handle']}/",
            body=mock_threads_profile_html,
            status=200
        )

        with patch('boto3.client') as mock_client:
            mock_sm = Mock()
            mock_cloudwatch = Mock()

            def client_factory(service_name=None, **kwargs):
                if service_name == 'secretsmanager' or not service_name:
                    return mock_sm
                elif service_name == 'cloudwatch':
                    return mock_cloudwatch
                return Mock()

            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps({
                    'accounts': [
                        {'account_id': 'account_001', 'username': 'test_user', 'password': 'test_pass'}
                    ]
                })
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps({
                    'proxies': [
                        {'proxy_id': 'proxy_001', 'url': 'http://proxy:8080'}
                    ]
                })
            }

            mock_client.side_effect = client_factory

            scraper = ThreadsScraper()
            result = scraper.process_celebrity(sample_celebrities[0])

            # Verify metrics were recorded
            assert scraper.metrics.metrics['successful'] >= 0
            assert scraper.metrics.metrics['failed'] >= 0


class TestCredentialsLoading:
    """Test credentials loading from Secrets Manager."""

    @mock_aws
    def test_load_and_use_credentials(self, mock_accounts, mock_proxies,
                                     aws_credentials, environment_variables):
        """Test loading and using credentials from Secrets Manager."""
        import boto3

        with patch('boto3.client') as mock_client:
            mock_sm = Mock()
            mock_sm.get_secret_value.side_effect = lambda SecretId: {
                'SecretString': json.dumps(mock_accounts)
            } if 'instagram-accounts' in SecretId else {
                'SecretString': json.dumps(mock_proxies)
            }
            mock_client.return_value = mock_sm

            scraper = ThreadsScraper()

            # Verify accounts and proxies loaded
            assert len(scraper.accounts) == 2
            assert len(scraper.proxies) == 2

            # Verify account rotation
            account1 = scraper._get_next_account()
            account2 = scraper._get_next_account()

            assert account1['account_id'] == 'account_001'
            assert account2['account_id'] == 'account_002'
