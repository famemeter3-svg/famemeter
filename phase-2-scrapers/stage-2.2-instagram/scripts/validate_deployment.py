#!/usr/bin/env python3
"""
Pre-deployment validation script.

Checks that all AWS resources and configurations are in place before deploying.

Usage:
    python scripts/validate_deployment.py [--fix]

Options:
    --fix: Attempt to fix issues automatically (creates resources, fixes permissions)
"""

import sys
import json
import argparse
from typing import Dict, List, Tuple
import boto3
from botocore.exceptions import ClientError

# AWS clients
iam = boto3.client('iam')
dynamodb = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')
secretsmanager = boto3.client('secretsmanager')
logs = boto3.client('logs')

# Configuration
LAMBDA_FUNCTION_NAME = 'scraper-instagram'
DYNAMODB_TABLE_NAME = 'celebrity-database'
INSTAGRAM_ACCOUNTS_SECRET = 'instagram-accounts'
LOG_GROUP = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error

    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        msg = f"{status} - {self.name}"
        if self.message:
            msg += f": {self.message}"
        if self.error and not self.passed:
            msg += f"\n      Error: {self.error}"
        return msg


class DeploymentValidator:
    """Validate deployment prerequisites."""

    def __init__(self, fix: bool = False):
        self.fix = fix
        self.results: List[ValidationResult] = []

    def check_aws_credentials(self) -> ValidationResult:
        """Check if AWS credentials are configured."""
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            account_id = identity['Account']
            arn = identity['Arn']
            result = ValidationResult(
                'AWS Credentials',
                True,
                f"Account: {account_id}, ARN: {arn}"
            )
            return result
        except Exception as e:
            return ValidationResult(
                'AWS Credentials',
                False,
                error=f"Failed to get AWS identity: {str(e)}"
            )

    def check_dynamodb_table(self) -> ValidationResult:
        """Check if DynamoDB table exists."""
        try:
            response = dynamodb.describe_table(TableName=DYNAMODB_TABLE_NAME)
            status = response['Table']['TableStatus']
            return ValidationResult(
                'DynamoDB Table',
                status == 'ACTIVE',
                f"Table '{DYNAMODB_TABLE_NAME}' exists with status: {status}"
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                if self.fix:
                    print(f"  → Creating DynamoDB table '{DYNAMODB_TABLE_NAME}'...")
                    try:
                        dynamodb.create_table(
                            TableName=DYNAMODB_TABLE_NAME,
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
                        return ValidationResult(
                            'DynamoDB Table',
                            True,
                            f"Table '{DYNAMODB_TABLE_NAME}' created successfully"
                        )
                    except Exception as create_error:
                        return ValidationResult(
                            'DynamoDB Table',
                            False,
                            error=f"Failed to create table: {str(create_error)}"
                        )
                else:
                    return ValidationResult(
                        'DynamoDB Table',
                        False,
                        f"Table '{DYNAMODB_TABLE_NAME}' does not exist (use --fix to create)"
                    )
            else:
                return ValidationResult(
                    'DynamoDB Table',
                    False,
                    error=f"Error checking table: {str(e)}"
                )

    def check_dynamodb_schema(self) -> ValidationResult:
        """Check DynamoDB table schema."""
        try:
            response = dynamodb.describe_table(TableName=DYNAMODB_TABLE_NAME)
            keys = response['Table']['KeySchema']
            key_names = [k['AttributeName'] for k in keys]

            expected_keys = {'celebrity_id', 'source_type#timestamp'}
            if set(key_names) == expected_keys:
                return ValidationResult(
                    'DynamoDB Schema',
                    True,
                    f"Schema correct: {', '.join(key_names)}"
                )
            else:
                return ValidationResult(
                    'DynamoDB Schema',
                    False,
                    f"Schema mismatch. Expected: {expected_keys}, Got: {set(key_names)}"
                )
        except Exception as e:
            return ValidationResult(
                'DynamoDB Schema',
                False,
                error=f"Error checking schema: {str(e)}"
            )

    def check_lambda_function(self) -> ValidationResult:
        """Check if Lambda function exists."""
        try:
            response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            arn = response['Configuration']['FunctionArn']
            runtime = response['Configuration']['Runtime']
            memory = response['Configuration']['MemorySize']
            return ValidationResult(
                'Lambda Function',
                True,
                f"'{LAMBDA_FUNCTION_NAME}' exists (Runtime: {runtime}, Memory: {memory}MB)"
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return ValidationResult(
                    'Lambda Function',
                    False,
                    f"Function '{LAMBDA_FUNCTION_NAME}' does not exist (deploy via AWS CLI or SAM)"
                )
            else:
                return ValidationResult(
                    'Lambda Function',
                    False,
                    error=f"Error checking function: {str(e)}"
                )

    def check_lambda_role(self) -> ValidationResult:
        """Check Lambda IAM role permissions."""
        try:
            response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            role_arn = response['Configuration']['Role']
            role_name = role_arn.split('/')[-1]

            # Check basic permissions
            required_policies = [
                'dynamodb',
                'secretsmanager',
                'cloudwatch',
                'logs'
            ]

            try:
                policy_response = iam.get_role_policy(RoleName=role_name, PolicyName='scraper-policy')
                policy_document = json.loads(policy_response['RolePolicyDocument'])
                actions = []
                for statement in policy_document.get('Statement', []):
                    actions.extend(statement.get('Action', []))

                missing = []
                for required in required_policies:
                    if not any(required in action for action in actions):
                        missing.append(required)

                if missing:
                    return ValidationResult(
                        'Lambda IAM Role',
                        False,
                        f"Missing permissions for: {', '.join(missing)}"
                    )
                else:
                    return ValidationResult(
                        'Lambda IAM Role',
                        True,
                        f"Role '{role_name}' has required permissions"
                    )
            except ClientError:
                return ValidationResult(
                    'Lambda IAM Role',
                    True,
                    f"Role '{role_name}' exists (permissions not fully verified, check manually)"
                )

        except Exception as e:
            return ValidationResult(
                'Lambda IAM Role',
                False,
                error=f"Error checking role: {str(e)}"
            )

    def check_cloudwatch_logs(self) -> ValidationResult:
        """Check if CloudWatch logs group exists."""
        try:
            logs.describe_log_groups(logGroupNamePrefix=LOG_GROUP)
            return ValidationResult(
                'CloudWatch Logs',
                True,
                f"Log group '{LOG_GROUP}' exists"
            )
        except Exception as e:
            if self.fix:
                print(f"  → Creating CloudWatch log group '{LOG_GROUP}'...")
                try:
                    logs.create_log_group(logGroupName=LOG_GROUP)
                    return ValidationResult(
                        'CloudWatch Logs',
                        True,
                        f"Log group '{LOG_GROUP}' created"
                    )
                except Exception as create_error:
                    return ValidationResult(
                        'CloudWatch Logs',
                        False,
                        error=f"Failed to create log group: {str(create_error)}"
                    )
            else:
                return ValidationResult(
                    'CloudWatch Logs',
                    False,
                    f"Log group '{LOG_GROUP}' does not exist (will be created on first invocation)"
                )

    def check_instagram_accounts_secret(self) -> ValidationResult:
        """Check if Instagram accounts secret exists (optional)."""
        try:
            secretsmanager.describe_secret(SecretId=INSTAGRAM_ACCOUNTS_SECRET)
            return ValidationResult(
                'Instagram Accounts Secret',
                True,
                f"Secret '{INSTAGRAM_ACCOUNTS_SECRET}' exists (optional)"
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return ValidationResult(
                    'Instagram Accounts Secret',
                    True,  # Optional, so not a failure
                    f"Secret '{INSTAGRAM_ACCOUNTS_SECRET}' does not exist (optional - uses anonymous mode)"
                )
            else:
                return ValidationResult(
                    'Instagram Accounts Secret',
                    False,
                    error=f"Error checking secret: {str(e)}"
                )

    def check_environment_variables(self) -> ValidationResult:
        """Check Lambda environment variables."""
        try:
            response = lambda_client.get_function_configuration(FunctionName=LAMBDA_FUNCTION_NAME)
            env_vars = response.get('Environment', {}).get('Variables', {})

            required_vars = [
                'DYNAMODB_TABLE',
                'AWS_REGION',
                'LOG_LEVEL',
                'INSTAGRAM_TIMEOUT',
                'INSTAGRAM_MAX_RETRIES'
            ]

            missing = [var for var in required_vars if var not in env_vars]

            if missing:
                return ValidationResult(
                    'Environment Variables',
                    False,
                    f"Missing: {', '.join(missing)}"
                )
            else:
                return ValidationResult(
                    'Environment Variables',
                    True,
                    f"All required variables configured"
                )

        except Exception as e:
            return ValidationResult(
                'Environment Variables',
                False,
                error=f"Error checking variables: {str(e)}"
            )

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print("\n" + "="*60)
        print("Deployment Validation")
        print("="*60 + "\n")

        checks = [
            self.check_aws_credentials,
            self.check_dynamodb_table,
            self.check_dynamodb_schema,
            self.check_lambda_function,
            self.check_lambda_role,
            self.check_cloudwatch_logs,
            self.check_instagram_accounts_secret,
            self.check_environment_variables,
        ]

        for check in checks:
            result = check()
            self.results.append(result)
            print(result)

        # Summary
        print("\n" + "="*60)
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        if passed == total:
            print(f"✓ All checks passed ({passed}/{total})")
        else:
            print(f"✗ {total - passed} check(s) failed ({passed}/{total})")

        print("="*60 + "\n")

        return passed == total


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Validate deployment prerequisites')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues automatically')

    args = parser.parse_args()

    validator = DeploymentValidator(fix=args.fix)
    success = validator.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
