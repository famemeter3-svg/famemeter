"""
Pytest fixtures for Instagram scraper tests.
"""

import pytest
import boto3
import json
import os
from unittest.mock import Mock, MagicMock, patch
from moto import mock_aws
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table."""
    with mock_aws():
        client = boto3.resource('dynamodb', region_name='us-east-1')
        table = client.create_table(
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
def secrets_manager(aws_credentials):
    """Create a mock Secrets Manager."""
    with mock_aws():
        client = boto3.client('secretsmanager', region_name='us-east-1')
        yield client


@pytest.fixture
def instagram_accounts_secret(secrets_manager):
    """Create mock Instagram accounts secret."""
    secret_data = {
        "accounts": [
            {
                "account_id": "account_001",
                "username": "test_account_1",
                "password": "test_password_1",
                "status": "active"
            },
            {
                "account_id": "account_002",
                "username": "test_account_2",
                "password": "test_password_2",
                "status": "active"
            }
        ]
    }
    secrets_manager.create_secret(
        Name='instagram-accounts',
        SecretString=json.dumps(secret_data)
    )
    return secret_data


@pytest.fixture
def mock_instaloader_context():
    """Mock Instaloader context."""
    mock_context = MagicMock()
    return mock_context


@pytest.fixture
def sample_instagram_profile():
    """Sample Instagram profile data."""
    return {
        'username': 'cristiano',
        'follower_count': 600000000,
        'mediacount': 5000,
        'biography': 'Professional footballer',
        'is_verified': True,
        'is_business_account': True,
        'is_private': False,
        'profile_pic_url': 'https://example.com/pic.jpg'
    }


@pytest.fixture
def sample_celebrities():
    """Sample celebrities for testing."""
    return [
        {
            'celebrity_id': 'celeb_001',
            'name': 'Cristiano Ronaldo',
            'instagram_handle': 'cristiano'
        },
        {
            'celebrity_id': 'celeb_002',
            'name': 'Lionel Messi',
            'instagram_handle': 'leomessi'
        },
        {
            'celebrity_id': 'celeb_003',
            'name': 'Unknown Celebrity',
            'instagram_handle': None  # Missing handle
        },
        {
            'celebrity_id': 'celeb_004',
            'name': 'Private Account User',
            'instagram_handle': 'private_account'
        }
    ]


@pytest.fixture
def mock_lambda_context():
    """Mock AWS Lambda context."""
    context = MagicMock()
    context.request_id = 'test-request-12345'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:scraper-instagram'
    context.get_remaining_time_in_millis = MagicMock(return_value=300000)
    return context


@pytest.fixture
def env_vars(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv('DYNAMODB_TABLE', 'celebrity-database')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('INSTAGRAM_TIMEOUT', '30')
    monkeypatch.setenv('INSTAGRAM_MAX_RETRIES', '3')


@pytest.fixture
def mock_instaloader_profile():
    """Mock Instaloader Profile object."""
    mock_profile = MagicMock()
    mock_profile.username = 'cristiano'
    mock_profile.follower_count = 600000000
    mock_profile.mediacount = 5000
    mock_profile.biography = 'Professional footballer'
    mock_profile.is_verified = True
    mock_profile.is_business_account = True
    mock_profile.is_private = False
    mock_profile.profile_pic_url = 'https://example.com/pic.jpg'
    return mock_profile


@pytest.fixture
def mock_boto3_clients(monkeypatch):
    """Mock boto3 clients."""
    mock_dynamodb = MagicMock()
    mock_secrets = MagicMock()
    mock_cloudwatch = MagicMock()

    monkeypatch.setattr('lambda_function.dynamodb', mock_dynamodb)
    monkeypatch.setattr('lambda_function.secrets_client', mock_secrets)
    monkeypatch.setattr('lambda_function.cloudwatch', mock_cloudwatch)

    return {
        'dynamodb': mock_dynamodb,
        'secrets': mock_secrets,
        'cloudwatch': mock_cloudwatch
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires AWS services)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (uses mocks)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
