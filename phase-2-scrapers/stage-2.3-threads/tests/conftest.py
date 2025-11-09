"""Pytest configuration and fixtures for Threads Scraper tests."""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def environment_variables():
    """Set up environment variables."""
    env_vars = {
        'DYNAMODB_TABLE': 'celebrity-database',
        'INSTAGRAM_ACCOUNTS_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:instagram-accounts',
        'PROXY_LIST_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:proxy-list',
        'LOG_LEVEL': 'INFO',
        'INSTAGRAM_TIMEOUT': '20'
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def dynamodb_table(aws_credentials, environment_variables):
    """Create mock DynamoDB table."""
    import boto3
    with mock_aws():
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
        yield table


@pytest.fixture
def mock_accounts():
    """Mock Instagram accounts data."""
    return {
        'accounts': [
            {
                'account_id': 'account_001',
                'username': 'test_account_1',
                'password': 'password_1'
            },
            {
                'account_id': 'account_002',
                'username': 'test_account_2',
                'password': 'password_2'
            }
        ]
    }


@pytest.fixture
def mock_proxies():
    """Mock proxy list data."""
    return {
        'proxies': [
            {
                'proxy_id': 'proxy_001',
                'url': 'http://proxy1.example.com:8080'
            },
            {
                'proxy_id': 'proxy_002',
                'url': 'http://proxy2.example.com:8080'
            }
        ]
    }


@pytest.fixture(autouse=True)
def mock_secrets_manager(mock_accounts, mock_proxies):
    """Mock Secrets Manager for account and proxy loading (auto-used)."""
    def mock_get_secret(SecretId):
        response = {}
        if 'instagram-accounts' in SecretId:
            response['SecretString'] = json.dumps(mock_accounts)
        elif 'proxy-list' in SecretId:
            response['SecretString'] = json.dumps(mock_proxies)
        return response

    with patch('lambda_function.secrets_client') as mock_sm:
        mock_sm.get_secret_value = mock_get_secret
        yield mock_sm


@pytest.fixture
def sample_celebrity():
    """Sample celebrity data from DynamoDB."""
    return {
        'celebrity_id': 'celeb_001',
        'name': 'Taylor Swift',
        'threads_handle': 'taylorswift',
        'instagram_handle': 'taylorswift',
        'source_type#timestamp': 'metadata#2025-11-08T00:00:00Z',
        'metadata': {
            'threads_handle': 'taylorswift'
        }
    }


@pytest.fixture
def sample_celebrities():
    """Multiple sample celebrities."""
    return [
        {
            'celebrity_id': 'celeb_001',
            'name': 'Taylor Swift',
            'threads_handle': 'taylorswift'
        },
        {
            'celebrity_id': 'celeb_002',
            'name': 'Dwayne Johnson',
            'threads_handle': 'therock'
        },
        {
            'celebrity_id': 'celeb_003',
            'name': 'Ariana Grande',
            'threads_handle': 'arianagrande'
        }
    ]


@pytest.fixture
def mock_threads_profile_html():
    """Mock HTML response from Threads profile."""
    return '''
    <html>
        <head><title>Taylor Swift on Threads</title></head>
        <body>
            <script type="application/json">
            {
                "edge_followed_by": {"count": 5000000},
                "edge_owner_to_timeline_media": {"count": 250},
                "biography": "Singer-Songwriter"
            }
            </script>
        </body>
    </html>
    '''


@pytest.fixture
def mock_404_html():
    """Mock 404 response."""
    return '<html><body>User not found</body></html>'


@pytest.fixture
def mock_context():
    """Mock Lambda context."""
    context = Mock()
    context.request_id = 'test-request-123'
    context.function_name = 'scraper-threads'
    context.memory_limit_in_mb = 1024
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:scraper-threads'
    context.aws_request_id = 'test-request-123'
    return context


@pytest.fixture
def mock_responses():
    """Mock requests responses."""
    import responses
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging after each test."""
    import logging
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    yield
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
