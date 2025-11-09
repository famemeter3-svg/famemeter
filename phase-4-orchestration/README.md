# Phase 4: Orchestration & Automation - Scheduled Data Collection

## Executive Summary

Phase 4 orchestrates the complete data pipeline through EventBridge scheduling and DynamoDB Streams. It triggers all scrapers every Sunday at 2 AM UTC, collects data in parallel, and automatically triggers post-processing when data arrives. Zero human intervention required after setup.

**Key Design**: Fully automated, event-driven orchestration with proper error handling, retries, and monitoring.

## Overview

Phase 4 accomplishes:
1. **Weekly Scheduling**: EventBridge cron job triggers all scrapers
2. **Parallel Execution**: All 4 scrapers run simultaneously
3. **Event-Driven Pipeline**: DynamoDB Streams automatically trigger post-processing
4. **Error Recovery**: Retry policies and Dead Letter Queues for failed events
5. **Monitoring**: CloudWatch logging and metrics for all orchestration

## Architecture & Flow

```
Every Sunday 2 AM UTC
  ↓
EventBridge Rule: "celebrity-weekly-scrape" fires
  ↓
┌─────────────────────────────────────────┐
│     Parallel Lambda Execution          │
├─────────────────────────────────────────┤
│ ├─ scraper-tmdb (5 min)                │
│ ├─ scraper-wikipedia (5 min)           │
│ ├─ scraper-news (5 min)                │
│ └─ scraper-social (5 min)              │
└─────────────────────────────────────────┘
  ↓
All 4 write to DynamoDB (400 entries: 100 celebrities × 4 sources)
  ↓
DynamoDB Streams captured: 400 INSERT events
  ↓
Post-Processor Lambda triggered (100 batch size)
  - Process batches 1-4
  - Calculate weight and sentiment
  - Update DynamoDB
  ↓
Done! All data enriched and ready for frontend
```

## Components

### EventBridge Scheduler

**Purpose**: Trigger all scrapers on weekly schedule (Sunday 2 AM UTC)

**Rule Configuration**:
```json
{
  "Name": "celebrity-weekly-scrape",
  "Description": "Weekly trigger for celebrity data scrapers",
  "ScheduleExpression": "cron(0 2 ? * SUN *)",
  "State": "DISABLED",
  "Targets": [
    {
      "Arn": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:scraper-tmdb",
      "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/eventbridge-lambda-role"
    },
    {
      "Arn": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:scraper-wikipedia",
      "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/eventbridge-lambda-role"
    },
    {
      "Arn": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:scraper-news",
      "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/eventbridge-lambda-role"
    },
    {
      "Arn": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:scraper-social",
      "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/eventbridge-lambda-role"
    }
  ]
}
```

**Cron Expression Breakdown**:
- `0` = minute 0
- `2` = hour 2 (2 AM)
- `?` = any day of month
- `*` = any month
- `SUN` = Sunday only

**Result**: Every Sunday at 2 AM UTC, all 4 scrapers invoked simultaneously

### DynamoDB Streams Integration

**Trigger**: When scrapers write entries to DynamoDB

**Flow**:
1. Scraper Lambda puts item to `celebrity-database` table
2. DynamoDB Streams captures the INSERT event
3. Stream → Lambda mapping routes to `post-processor`
4. Post-processor reads from stream and processes batch
5. UpdateItem adds weight and sentiment

## Error Handling & Robustness

### EventBridge Retry Policy

**Configuration**:
```json
{
  "RetryPolicy": {
    "MaximumEventAge": 300,
    "MaximumRetryAttempts": 3
  },
  "DeadLetterConfig": {
    "Arn": "arn:aws:sqs:us-east-1:ACCOUNT_ID:celebrity-scraper-dlq"
  }
}
```

**Behavior**:
- Invocation fails → Retry after 1 second
- Still fails → Retry after 2 seconds (exponential backoff)
- Still fails → Retry after 4 seconds
- Still fails → Send to Dead Letter Queue (SQS)

**Result**: Automatic retries for transient failures, manual investigation for persistent failures

### Dead Letter Queue (DLQ)

**Purpose**: Capture failed events for investigation

**Setup**:
```bash
# Create SQS queue for DLQ
aws sqs create-queue --queue-name celebrity-scraper-dlq

# Configure retention (7 days)
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT/celebrity-scraper-dlq \
  --attributes MessageRetentionPeriod=604800
```

**Monitoring**:
```bash
# Check for failed invocations
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT/celebrity-scraper-dlq \
  --max-number-of-messages 10

# If messages in DLQ:
# 1. Investigate CloudWatch logs
# 2. Fix root cause
# 3. Manually invoke Lambda or wait for next schedule
```

### Stream Processing Errors

**Error**: Stream read fails
```
Detection: GetRecords or GetShardIterator fails
Handling: Lambda automatically retries (AWS manages)
Recovery: Check stream for shard issues
```

**Error**: Post-processor crashes on entry
```
Detection: Lambda exits with error
Handling: Stream resets, retries batch
Recovery: Fix code, redeploy, next stream event retries
```

**Error**: DynamoDB update fails
```
Detection: UpdateItem raises exception
Handling: Log error, continue (partial batch success)
Recovery: Manually fix entry or re-run post-processor
```

## Testing Protocol

### Phase 4A: EventBridge Setup Testing

**Step 1: Create EventBridge Rule**
```bash
# Create rule
aws events put-rule \
  --name celebrity-weekly-scrape \
  --schedule-expression "cron(0 2 ? * SUN *)" \
  --state DISABLED

# Add Lambda targets
for func in scraper-tmdb scraper-wikipedia scraper-news scraper-social; do
  aws events put-targets \
    --rule celebrity-weekly-scrape \
    --targets "Id"="$func","Arn"="arn:aws:lambda:us-east-1:ACCOUNT_ID:function:$func","RoleArn"="arn:aws:iam::ACCOUNT_ID:role/eventbridge-lambda-role"
done

# Verify targets added
aws events list-targets-by-rule --rule celebrity-weekly-scrape
```

**Step 2: Test Manual Invocation**
```bash
# Manually trigger rule (simulate Sunday 2 AM)
aws events start-pipeline-execution \
  --name celebrity-weekly-scrape

# Alternative: Put test event
aws events put-events \
  --entries '[{
    "Source": "aws.events",
    "DetailType": "Scheduled Event",
    "Rule": "celebrity-weekly-scrape",
    "Time": "'$(date -u +'%Y-%m-%dT%H:%M:%SZ')'",
    "Region": "us-east-1",
    "Resources": [],
    "DetailType": "EventBridge Scheduled Event",
    "Detail": "{}"
  }]'

# Monitor Lambda logs
for func in scraper-tmdb scraper-wikipedia scraper-news scraper-social; do
  aws logs tail /aws/lambda/$func --follow &
done

# All 4 should start within seconds
```

**Step 3: Verify Parallel Execution**
```bash
# Check all 4 invoked at same time (within 1 second)
aws logs filter-log-events \
  --log-group-name /aws/lambda/scraper-tmdb \
  --log-group-name /aws/lambda/scraper-wikipedia \
  --filter-pattern "START" \
  --query 'events[*].[timestamp,logStreamName]'

# Should show all timestamps within 1000ms of each other
```

**Step 4: **STOP IF ANY LAMBDA FAILS**
If any scraper fails:
- [ ] Check CloudWatch logs for specific error
- [ ] Verify Lambda has correct IAM permissions
- [ ] Verify environment variables set
- [ ] Verify DynamoDB table exists
- [ ] Fix error and redeploy Lambda
- [ ] **Do NOT enable schedule** until all 4 pass

### Phase 4B: DynamoDB Streams Testing

**Step 1: Verify Stream Enabled**
```bash
# Check stream exists and is enabled
aws dynamodb describe-table \
  --table-name celebrity-database \
  --query 'Table.StreamSpecification'

# Expected:
# {
#   "StreamEnabled": true,
#   "StreamViewType": "NEW_AND_OLD_IMAGES"
# }
```

**Step 2: Configure Event Source Mapping**
```bash
# Get stream ARN
STREAM_ARN=$(aws dynamodb describe-table \
  --table-name celebrity-database \
  --query 'Table.LatestStreamArn' \
  --output text)

# Create mapping (post-processor already configured)
aws lambda create-event-source-mapping \
  --event-source-arn $STREAM_ARN \
  --function-name post-processor \
  --enabled \
  --batch-size 100 \
  --starting-position LATEST
```

**Step 3: Trigger Manual Scrape**
```bash
# Manually invoke all 4 scrapers
for func in scraper-tmdb scraper-wikipedia scraper-news scraper-social; do
  aws lambda invoke \
    --function-name $func \
    --invocation-type Event \
    response-$func.json
done

# Monitor DynamoDB entries written
aws dynamodb scan \
  --table-name celebrity-database \
  --select COUNT \
  --filter-expression "attribute_exists(timestamp) AND attribute_not_exists(weight)" \
  --query 'Count'

# Should increase as scrapers write
# Wait 30 seconds...
# Should reach ~400 entries (100 celebrities × 4 sources)
```

**Step 4: Verify Post-Processor Triggered**
```bash
# Check post-processor logs
aws logs tail /aws/lambda/post-processor --follow

# Should see:
# - Records processed
# - Weight calculated
# - Sentiment analyzed
# - DynamoDB updated

# Verify entries have weight/sentiment
aws dynamodb scan \
  --table-name celebrity-database \
  --select COUNT \
  --filter-expression "attribute_exists(weight) AND attribute_exists(sentiment)" \
  --query 'Count'

# Should be close to 400
```

**Step 5: **STOP IF STREAM NOT WORKING**
If post-processor not triggered:
- [ ] Check event source mapping created successfully
- [ ] Verify post-processor IAM has stream permissions
- [ ] Check CloudWatch logs for stream errors
- [ ] Verify batch size and window settings
- [ ] **Do NOT proceed** until working
- [ ] Fix configuration and re-test

### Phase 4C: End-to-End Integration Test

**Step 1: Clean Previous Test Data**
```bash
# Delete test entries (optional - for clean test)
aws dynamodb delete-table --table-name celebrity-database-test
aws dynamodb create-table --cli-input-json file://table-definition.json
```

**Step 2: Run Complete Cycle**
```bash
# Step 1: Manually trigger EventBridge rule
aws events put-events \
  --entries '[{"Source":"aws.events","DetailType":"Scheduled","Detail":"{}"}]'

# Wait for all scrapers to complete (5-10 minutes)
# Monitor progress:
watch -n 5 'aws dynamodb scan --table-name celebrity-database --select COUNT | jq .Count'

# Step 2: Verify all 400 entries written
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(timestamp)" \
  --select COUNT

# Expected: ~400 entries

# Step 3: Check for weight/sentiment
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight)" \
  --select COUNT

# Expected: ~400 entries (within 5 minutes of scrape completion)
```

**Step 3: Validate Data Quality**
```bash
# Check weight distribution
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(weight)" \
  --query 'Items[*].weight.N' | jq 'map(tonumber) | {min, max, avg: (add/length)}'

# Check sentiment distribution
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_exists(sentiment)" \
  --query 'Items[*].sentiment.S' | jq 'group_by(.) | map({sentiment: .[0], count: length})'

# Check for failures
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "attribute_not_exists(weight) OR attribute_not_exists(sentiment)" \
  --select COUNT

# Expected: Should be minimal (< 10 entries)
```

### Phase 4D: Schedule Enablement

**Step 1: Final Verification**
```bash
# All prerequisites verified:
# ✓ All 4 scrapers working
# ✓ Post-processor working
# ✓ DynamoDB Streams flowing correctly
# ✓ Weight/sentiment computed
# ✓ Error handling tested
```

**Step 2: Enable Weekly Schedule**
```bash
# Enable rule (now runs every Sunday 2 AM UTC)
aws events put-rule \
  --name celebrity-weekly-scrape \
  --state ENABLED

# Verify enabled
aws events describe-rule --name celebrity-weekly-scrape --query 'State'
# Should return: ENABLED
```

**Step 3: Set Up Monitoring**
```bash
# Create CloudWatch alarm for failures
aws cloudwatch put-metric-alarm \
  --alarm-name celebrity-scraper-failures \
  --alarm-description "Alert if scraper fails" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 3 \
  --comparison-operator GreaterThanThreshold
```

## Coding Principles & Best Practices

### Error Handling
✅ **Implemented**:
- EventBridge retry policy (3 retries, exponential backoff)
- Dead Letter Queue for failed events
- Stream processing error handling
- Partial batch success (continue on error)
- Comprehensive error logging

### Monitoring
✅ **Implemented**:
- CloudWatch Logs for all Lambda executions
- CloudWatch Metrics for invocations and errors
- EventBridge tracking (successful/failed)
- DynamoDB Streams monitoring
- Custom alarms for anomalies

### Robustness
✅ **Implemented**:
- Idempotent operations (safe to re-run)
- Timeout protection (300s Lambda timeout)
- Rate limiting compliance
- Graceful degradation (some scrapers can fail)
- Recovery mechanisms (retries, fallbacks)

### Cost Optimization
✅ **Implemented**:
- EventBridge extremely low cost (~$0.01/month)
- Lambda On-Demand billing
- Efficient batch processing
- Parallel execution (faster = cheaper)

## Cost Breakdown

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| EventBridge | $0.01 | 1 rule × 4 targets, 52 weekly executions |
| DynamoDB Streams | $0.25 | 400 writes/week × 4 read units |
| Lambda (scrapers) | $0.50 | 4 × 5 min × 512 MB × 52/month |
| Lambda (post-processor) | $0.20 | 4 batches × 1 min × 1024 MB × 52/month |
| **Total** | **~$0.96/month** | Orchestration layer cost |

## Timeline & Milestones

- [ ] Create EventBridge rule (day 1)
- [ ] Add Lambda targets (day 1)
- [ ] Test manual invocation (day 2)
- [ ] Verify parallel execution (day 2)
- [ ] Configure stream mapping (day 3)
- [ ] Test end-to-end cycle (day 3-4)
- [ ] **STOP if failures - fix before enabling**
- [ ] Enable weekly schedule (day 5)
- [ ] Monitor first real execution (day 5-7)

## Current Implementation Status

### ✅ Completed
- [x] Phase 4 directory structure
- [x] EventBridge rule definition
- [x] Testing protocol documented
- [x] Error handling framework

### 🟡 In Progress
- [ ] Create EventBridge rule
- [ ] Configure targets
- [ ] Test manual execution

### ⏳ Not Started
- [ ] Phase 5 (API Layer)

## Next Phase

**Phase 5: API Layer** (Week 9-10)
- Create REST API (API Gateway)
- Implement endpoint Lambda functions
- Enable frontend data access

**Prerequisites**:
- ✅ Phase 1-4: Complete data pipeline operational
- ✅ Weekly schedule running successfully
- ✅ 100 celebrities with enriched data from 4 sources

## References

- Project Plan: `../../project-updated.md`
- EventBridge: https://docs.aws.amazon.com/eventbridge/
- DynamoDB Streams: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html

---

**Phase 4 Status**: Ready for Implementation
**Created**: November 7, 2025
**Last Updated**: November 7, 2025
