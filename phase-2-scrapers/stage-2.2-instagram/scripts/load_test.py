#!/usr/bin/env python3
"""
Load testing script for Instagram scraper.

Tests the Lambda function with increasing load to measure performance.

Usage:
    python scripts/load_test.py [--celebrities N] [--parallel P] [--region REGION]

Options:
    --celebrities N: Number of celebrities to scrape (default: 50)
    --parallel P: Number of parallel Lambda invocations (default: 5)
    --region REGION: AWS region (default: us-east-1)
    --dry-run: Print configuration without running tests
"""

import sys
import argparse
import json
import time
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.exceptions import ClientError

# AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.client('dynamodb')

LAMBDA_FUNCTION_NAME = 'scraper-instagram'
DYNAMODB_TABLE_NAME = 'celebrity-database'

# Sample celebrities for testing
SAMPLE_CELEBRITIES = [
    {'celebrity_id': f'celeb_{i:03d}', 'name': f'Celebrity {i}', 'instagram_handle': f'celebrity_handle_{i}'}
    for i in range(1, 201)
]


class LoadTestConfig:
    """Configuration for load testing."""

    def __init__(self, num_celebrities: int = 50, parallel_invocations: int = 5):
        self.num_celebrities = num_celebrities
        self.parallel_invocations = parallel_invocations
        self.batch_size = max(1, num_celebrities // parallel_invocations)
        self.celebrities = SAMPLE_CELEBRITIES[:num_celebrities]

    def __str__(self):
        return f"""
Load Test Configuration
─────────────────────────────
Total Celebrities: {self.num_celebrities}
Parallel Invocations: {self.parallel_invocations}
Batch Size: {self.batch_size}
Lambda Function: {LAMBDA_FUNCTION_NAME}
DynamoDB Table: {DYNAMODB_TABLE_NAME}
"""


class LoadTestResult:
    """Result of a load test run."""

    def __init__(self, invocation_id: str):
        self.invocation_id = invocation_id
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.status_code = None
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.error = None

    def get_duration(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def __str__(self):
        status = "✓" if self.status_code == 200 else "✗"
        return f"{status} {self.invocation_id}: {self.successful} success, {self.failed} failed, {self.skipped} skipped ({self.get_duration():.2f}s)"


class LoadTester:
    """Load testing for Lambda function."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results: List[LoadTestResult] = []

    def invoke_lambda(self, batch_id: int, celebrities: List[Dict]) -> LoadTestResult:
        """Invoke Lambda function with batch of celebrities."""
        result = LoadTestResult(f"Batch {batch_id}")
        result.start_time = datetime.utcnow()

        try:
            payload = json.dumps({'celebrities': celebrities})

            response = lambda_client.invoke(
                FunctionName=LAMBDA_FUNCTION_NAME,
                InvocationType='RequestResponse',
                LogType='Tail',
                Payload=payload
            )

            result.status_code = response['StatusCode']

            if response['StatusCode'] == 200:
                response_payload = json.loads(response['Payload'].read())
                if isinstance(response_payload, dict):
                    body = response_payload.get('body')
                    if isinstance(body, str):
                        body = json.loads(body)
                    result.successful = body.get('successful', 0)
                    result.failed = body.get('failed', 0)
                    result.skipped = body.get('skipped', 0)
            else:
                result.error = f"HTTP {response['StatusCode']}"

        except Exception as e:
            result.error = str(e)
            result.status_code = 500

        result.end_time = datetime.utcnow()
        return result

    def run_parallel_test(self) -> List[LoadTestResult]:
        """Run parallel Lambda invocations."""
        print(f"\nRunning {self.config.parallel_invocations} parallel invocations...")
        print(f"Batch size: {self.config.batch_size} celebrities each\n")

        batches = []
        for i in range(self.config.parallel_invocations):
            start_idx = i * self.config.batch_size
            end_idx = min(start_idx + self.config.batch_size, len(self.config.celebrities))
            batch = self.config.celebrities[start_idx:end_idx]
            batches.append((i + 1, batch))

        with ThreadPoolExecutor(max_workers=self.config.parallel_invocations) as executor:
            futures = {executor.submit(self.invoke_lambda, batch_id, batch): batch_id for batch_id, batch in batches}

            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
                print(result)

        return self.results

    def run_progressive_test(self):
        """Run test with progressively increasing load."""
        print("\nRunning progressive load test...")
        print("(Gradually increasing number of parallel invocations)\n")

        load_levels = [1, 2, 5, 10]

        for load_level in load_levels:
            if load_level > self.config.parallel_invocations:
                break

            print(f"\n--- Load Level {load_level} (1-{load_level} parallel invocations) ---")

            test_config = LoadTestConfig(self.config.num_celebrities, load_level)
            tester = LoadTester(test_config)
            tester.run_parallel_test()
            self.results.extend(tester.results)

    def print_summary(self):
        """Print test summary."""
        if not self.results:
            print("No results to summarize")
            return

        print("\n" + "="*60)
        print("Load Test Summary")
        print("="*60 + "\n")

        total_duration = sum(r.get_duration() for r in self.results)
        total_successful = sum(r.successful for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        successful_invocations = sum(1 for r in self.results if r.status_code == 200)

        print(f"Total Invocations: {len(self.results)}")
        print(f"Successful Invocations: {successful_invocations}/{len(self.results)}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Average Duration per Invocation: {total_duration / len(self.results):.2f}s")
        print()

        print("Scraping Results:")
        print(f"  Successful: {total_successful}")
        print(f"  Failed: {total_failed}")
        print(f"  Skipped: {total_skipped}")
        print(f"  Success Rate: {total_successful / max(1, total_successful + total_failed) * 100:.1f}%")
        print()

        # Performance metrics
        print("Performance Metrics:")
        print(f"  Throughput: {total_successful / total_duration:.2f} celebrities/second")
        print(f"  Average per Invocation: {total_successful / len(self.results):.1f} celebrities")
        print()

        # DynamoDB verification
        try:
            response = dynamodb.scan(
                TableName=DYNAMODB_TABLE_NAME,
                Select='COUNT'
            )
            total_items = response['Count']
            print(f"DynamoDB Items: {total_items} total entries")
        except Exception as e:
            print(f"DynamoDB verification failed: {str(e)}")

        print("\n" + "="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Load test Instagram scraper Lambda function')
    parser.add_argument('--celebrities', type=int, default=50, help='Number of celebrities to test (default: 50)')
    parser.add_argument('--parallel', type=int, default=5, help='Number of parallel invocations (default: 5)')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--progressive', action='store_true', help='Run progressive load test')
    parser.add_argument('--dry-run', action='store_true', help='Print config without running')

    args = parser.parse_args()

    # Update boto3 region
    global lambda_client, dynamodb
    lambda_client = boto3.client('lambda', region_name=args.region)
    dynamodb = boto3.client('dynamodb', region_name=args.region)

    # Create config
    config = LoadTestConfig(args.celebrities, args.parallel)
    print(config)

    if args.dry_run:
        print("(Dry run - no tests executed)")
        return 0

    try:
        # Run tests
        if args.progressive:
            tester = LoadTester(config)
            tester.run_progressive_test()
        else:
            tester = LoadTester(config)
            tester.run_parallel_test()

        # Print summary
        tester.print_summary()

        return 0

    except ClientError as e:
        print(f"\n✗ AWS Error: {str(e)}")
        print(f"\nMake sure:")
        print(f"  1. Lambda function '{LAMBDA_FUNCTION_NAME}' exists and is deployed")
        print(f"  2. DynamoDB table '{DYNAMODB_TABLE_NAME}' exists")
        print(f"  3. You have AWS credentials configured")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
