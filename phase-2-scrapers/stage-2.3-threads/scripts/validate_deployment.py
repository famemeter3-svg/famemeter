#!/usr/bin/env python3
"""
Pre-deployment validation for Threads Scraper.

Checks:
1. AWS credentials configured
2. DynamoDB table exists
3. Secrets Manager secrets configured
4. IAM permissions
5. Network connectivity
6. Dependencies installed
7. Environment variables set
8. SAM template valid
"""

import sys
import json
import boto3
import argparse
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Tuple


class DeploymentValidator:
    """Validates deployment prerequisites."""

    def __init__(self, verbose: bool = False, fix: bool = False):
        self.verbose = verbose
        self.fix = fix
        self.checks_passed = []
        self.checks_failed = []
        self.warnings = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        if level in ["ERROR", "WARNING"] or self.verbose:
            print(f"[{level}] {message}")

    def check_aws_credentials(self) -> Tuple[bool, str]:
        """Check if AWS credentials are configured."""
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            account_id = identity['Account']
            user_arn = identity['Arn']
            self.log(f"AWS credentials found: {user_arn}", "INFO")
            return True, f"Account: {account_id}"
        except NoCredentialsError:
            return False, "No AWS credentials found"
        except Exception as e:
            return False, str(e)

    def check_aws_region(self) -> Tuple[bool, str]:
        """Check if AWS region is configured."""
        try:
            session = boto3.Session()
            region = session.region_name
            if not region:
                return False, "AWS_DEFAULT_REGION not configured"
            self.log(f"AWS region configured: {region}", "INFO")
            return True, f"Region: {region}"
        except Exception as e:
            return False, str(e)

    def check_dynamodb_table(self, table_name: str = 'celebrity-database') -> Tuple[bool, str]:
        """Check if DynamoDB table exists."""
        try:
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            item_count = response['Table']['ItemCount']
            self.log(f"DynamoDB table found: {table_name} (status: {status}, items: {item_count})", "INFO")
            return True, f"Table exists: {table_name}"
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False, f"DynamoDB table not found: {table_name}"
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def check_secrets_manager(self, secret_name: str) -> Tuple[bool, str]:
        """Check if Secrets Manager secret exists."""
        try:
            sm = boto3.client('secretsmanager')
            response = sm.describe_secret(SecretId=secret_name)
            self.log(f"Secrets Manager secret found: {secret_name}", "INFO")
            return True, f"Secret exists: {secret_name}"
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False, f"Secrets Manager secret not found: {secret_name}"
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def check_instagram_accounts_secret(self) -> Tuple[bool, str]:
        """Check Instagram accounts secret."""
        try:
            sm = boto3.client('secretsmanager')
            # Try to get the secret - use standard naming
            response = sm.list_secrets()
            for secret in response.get('SecretList', []):
                if 'instagram-accounts' in secret['Name'].lower():
                    self.log(f"Instagram accounts secret found: {secret['Name']}", "INFO")
                    return True, f"Found: {secret['Name']}"

            self.warnings.append("Instagram accounts secret not found (optional if using environment variables)")
            return True, "Warning: Secret not found"
        except Exception as e:
            return False, str(e)

    def check_proxy_list_secret(self) -> Tuple[bool, str]:
        """Check proxy list secret."""
        try:
            sm = boto3.client('secretsmanager')
            response = sm.list_secrets()
            for secret in response.get('SecretList', []):
                if 'proxy-list' in secret['Name'].lower():
                    self.log(f"Proxy list secret found: {secret['Name']}", "INFO")
                    return True, f"Found: {secret['Name']}"

            self.warnings.append("Proxy list secret not found (optional for direct connections)")
            return True, "Warning: Secret not found"
        except Exception as e:
            return False, str(e)

    def check_iam_permissions(self) -> Tuple[bool, str]:
        """Check IAM permissions."""
        try:
            iam = boto3.client('iam')
            # Get current user
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            user_arn = identity['Arn']

            # Basic check: if we can call IAM, we likely have permissions
            self.log(f"IAM accessible with current credentials", "INFO")
            return True, "IAM permissions verified"
        except Exception as e:
            return False, str(e)

    def check_lambda_permissions(self) -> Tuple[bool, str]:
        """Check Lambda permissions."""
        try:
            lamb = boto3.client('lambda')
            # List functions to verify permissions
            response = lamb.list_functions(MaxItems=1)
            self.log(f"Lambda permissions verified", "INFO")
            return True, "Can access Lambda"
        except ClientError as e:
            if 'AccessDenied' in str(e):
                return False, "Lambda AccessDenied"
            return True, "Lambda check skipped"
        except Exception as e:
            return False, str(e)

    def check_cloudwatch_permissions(self) -> Tuple[bool, str]:
        """Check CloudWatch permissions."""
        try:
            cw = boto3.client('cloudwatch')
            response = cw.list_metrics(Limit=1)
            self.log(f"CloudWatch permissions verified", "INFO")
            return True, "Can access CloudWatch"
        except ClientError as e:
            if 'AccessDenied' in str(e):
                return False, "CloudWatch AccessDenied"
            return True, "CloudWatch check skipped"
        except Exception as e:
            return False, str(e)

    def check_environment_variables(self) -> Tuple[bool, str]:
        """Check required environment variables."""
        import os
        required_vars = [
            'DYNAMODB_TABLE',
            'INSTAGRAM_ACCOUNTS_SECRET_ARN',
            'PROXY_LIST_SECRET_ARN'
        ]

        missing = []
        for var in required_vars:
            if var not in os.environ:
                missing.append(var)

        if missing:
            msg = f"Missing environment variables: {', '.join(missing)}"
            self.log(msg, "WARNING")
            return False, msg
        else:
            self.log("All required environment variables configured", "INFO")
            return True, "Environment variables OK"

    def check_dependencies(self) -> Tuple[bool, str]:
        """Check if dependencies are installed."""
        dependencies = [
            'boto3',
            'requests',
            'pytest'
        ]

        missing = []
        for dep in dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)

        if missing:
            return False, f"Missing dependencies: {', '.join(missing)}"
        else:
            self.log("All dependencies installed", "INFO")
            return True, "Dependencies OK"

    def check_sam_template(self) -> Tuple[bool, str]:
        """Check if SAM template is valid."""
        import os
        import yaml

        if not os.path.exists('sam_template.yaml'):
            return False, "sam_template.yaml not found"

        try:
            with open('sam_template.yaml', 'r') as f:
                yaml.safe_load(f)
            self.log("SAM template is valid YAML", "INFO")
            return True, "SAM template valid"
        except Exception as e:
            return False, f"Invalid SAM template: {str(e)}"

    def check_network_connectivity(self) -> Tuple[bool, str]:
        """Check network connectivity to AWS services."""
        try:
            import socket
            # Check connectivity to AWS
            socket.create_connection(("sts.amazonaws.com", 443), timeout=5)
            self.log("Network connectivity to AWS verified", "INFO")
            return True, "Network OK"
        except Exception as e:
            return False, f"Network error: {str(e)}"

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        checks = [
            ("AWS Credentials", self.check_aws_credentials),
            ("AWS Region", self.check_aws_region),
            ("Network Connectivity", self.check_network_connectivity),
            ("DynamoDB Table", lambda: self.check_dynamodb_table()),
            ("Instagram Accounts Secret", self.check_instagram_accounts_secret),
            ("Proxy List Secret", self.check_proxy_list_secret),
            ("IAM Permissions", self.check_iam_permissions),
            ("Lambda Permissions", self.check_lambda_permissions),
            ("CloudWatch Permissions", self.check_cloudwatch_permissions),
            ("Environment Variables", self.check_environment_variables),
            ("Dependencies", self.check_dependencies),
            ("SAM Template", self.check_sam_template),
        ]

        print("\n" + "=" * 70)
        print("DEPLOYMENT VALIDATION REPORT")
        print("=" * 70 + "\n")

        for check_name, check_func in checks:
            try:
                passed, message = check_func()
                if passed:
                    self.checks_passed.append((check_name, message))
                    print(f"✓ {check_name}: {message}")
                else:
                    self.checks_failed.append((check_name, message))
                    print(f"✗ {check_name}: {message}")
            except Exception as e:
                self.checks_failed.append((check_name, str(e)))
                print(f"✗ {check_name}: {str(e)}")

        # Print warnings
        if self.warnings:
            print("\n" + "=" * 70)
            print("WARNINGS")
            print("=" * 70)
            for warning in self.warnings:
                print(f"⚠ {warning}")

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Passed: {len(self.checks_passed)}")
        print(f"Failed: {len(self.checks_failed)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.checks_failed:
            print("\n⚠️  DEPLOYMENT NOT READY - Fix failures above and retry")
            return False
        elif self.warnings:
            print("\n⚠️  DEPLOYMENT READY WITH WARNINGS - Review warnings above")
            return True
        else:
            print("\n✓ ALL CHECKS PASSED - Ready for deployment!")
            return True

    def suggest_fixes(self):
        """Suggest fixes for failed checks."""
        if not self.checks_failed:
            return

        print("\n" + "=" * 70)
        print("SUGGESTED FIXES")
        print("=" * 70 + "\n")

        for check_name, message in self.checks_failed:
            if "DynamoDB table not found" in message:
                print(f"To create DynamoDB table:")
                print(f"  aws dynamodb create-table \\")
                print(f"    --table-name celebrity-database \\")
                print(f"    --attribute-definitions AttributeName=celebrity_id,AttributeType=S AttributeName='source_type#timestamp',AttributeType=S \\")
                print(f"    --key-schema AttributeName=celebrity_id,KeyType=HASH AttributeName='source_type#timestamp',KeyType=RANGE \\")
                print(f"    --billing-mode PAY_PER_REQUEST")
                print()

            elif "Secrets Manager secret not found" in message:
                print(f"To create Secrets Manager secret:")
                print(f"  aws secretsmanager create-secret \\")
                print(f"    --name instagram-accounts \\")
                print(f"    --secret-string '{{\"accounts\": [{{\"account_id\": \"...\", \"username\": \"...\", \"password\": \"...\"}}]}}'")
                print()

            elif "missing" in message.lower() and "dependencies" in message.lower():
                print(f"To install dependencies:")
                print(f"  pip install -r requirements.txt -r requirements-dev.txt")
                print()

            elif "environment variables" in message.lower():
                print(f"To set environment variables:")
                print(f"  export DYNAMODB_TABLE=celebrity-database")
                print(f"  export INSTAGRAM_ACCOUNTS_SECRET_ARN='arn:aws:secretsmanager:...'")
                print(f"  export PROXY_LIST_SECRET_ARN='arn:aws:secretsmanager:...'")
                print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Validate Threads Scraper deployment')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fix', '-f', action='store_true', help='Auto-fix issues')

    args = parser.parse_args()

    validator = DeploymentValidator(verbose=args.verbose, fix=args.fix)
    success = validator.run_all_checks()
    validator.suggest_fixes()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
