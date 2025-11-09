# Phase 8: Monitoring & Maintenance - Observability & Operations

## Executive Summary

Phase 8 establishes comprehensive monitoring, logging, and maintenance procedures to ensure the system remains healthy, performant, and cost-efficient in production. This ongoing phase includes CloudWatch dashboards, automated alerts, backup/recovery procedures, security monitoring, and regular maintenance tasks. System observability is critical for early detection of issues and proactive problem resolution.

**Key Design**: Multi-layer monitoring (infrastructure, application, business metrics), automated alerting with smart thresholds, point-in-time recovery, regular testing, and documented runbooks.

## Overview

Phase 8 accomplishes:
1. **CloudWatch Dashboards**: Real-time visibility into system health
2. **Automated Alarms**: Notify team of anomalies and failures
3. **Centralized Logging**: Aggregate logs from all services
4. **Performance Tracking**: Monitor latency and throughput
5. **Cost Monitoring**: Track and optimize spending
6. **Backup & Recovery**: Ensure data protection and RPO/RTO targets
7. **Security Monitoring**: Detect unauthorized access attempts
8. **Operational Runbooks**: Documented procedures for common tasks

## Architecture

```
AWS Services (producing metrics and logs)
  ├─ Lambda (CloudWatch Logs)
  ├─ DynamoDB (CloudWatch Metrics)
  ├─ API Gateway (CloudWatch Logs & Metrics)
  ├─ S3 (CloudWatch Metrics)
  └─ CloudFront (CloudWatch Logs)
  ↓
CloudWatch (metrics aggregation & storage)
  ├─ CloudWatch Logs (centralized logging)
  ├─ CloudWatch Metrics (time-series data)
  └─ CloudWatch Alarms (threshold detection)
  ↓
SNS Topics (notifications)
  ├─ Critical alerts → PagerDuty
  ├─ Warnings → Email
  └─ Info → Slack
  ↓
Dashboard & Analytics
  ├─ CloudWatch Dashboard (visual)
  ├─ Custom analytics
  └─ Business intelligence
```

## CloudWatch Dashboards

### 1. Main Operations Dashboard

```json
{
  "DashboardName": "celebrity-database-monitoring",
  "Widgets": [
    {
      "Type": "Metric",
      "Title": "Lambda Invocations (Last 24h)",
      "Metrics": [
        ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
        [".", "Errors", {"stat": "Sum", "color": "#ff0000"}],
        [".", "Duration", {"stat": "Average", "color": "#ffa500"}]
      ],
      "Period": 300,
      "Stat": "Sum"
    },
    {
      "Type": "Metric",
      "Title": "Lambda Error Rate (%)",
      "Metrics": [
        ["AWS/Lambda", "Errors", {"stat": "Sum"}],
        [".", "Invocations", {"stat": "Sum"}]
      ],
      "YAxis": {
        "Left": {"Min": 0, "Max": 100}
      },
      "Annotations": {
        "Horizontal": [
          {"Value": 5, "Label": "5% threshold", "Color": "#ff0000"}
        ]
      }
    },
    {
      "Type": "Metric",
      "Title": "DynamoDB Consumed Capacity",
      "Metrics": [
        ["AWS/DynamoDB", "ConsumedReadCapacityUnits", {"stat": "Sum"}],
        [".", "ConsumedWriteCapacityUnits", {"stat": "Sum"}]
      ]
    },
    {
      "Type": "Metric",
      "Title": "API Gateway Requests",
      "Metrics": [
        ["AWS/ApiGateway", "Count", {"stat": "Sum"}],
        [".", "4XXError", {"stat": "Sum"}],
        [".", "5XXError", {"stat": "Sum"}]
      ]
    },
    {
      "Type": "Metric",
      "Title": "API Latency (ms)",
      "Metrics": [
        ["AWS/ApiGateway", "Latency", {"stat": "Average"}],
        [".", "Latency", {"stat": "p95"}],
        [".", "Latency", {"stat": "p99"}]
      ],
      "YAxis": {
        "Left": {"Min": 0, "Max": 5000}
      }
    },
    {
      "Type": "Log",
      "Title": "Recent Errors (Last Hour)",
      "LogGroupName": "/aws/lambda/scraper-*",
      "QueryString": "fields @timestamp, @message | filter @message like /ERROR/ | stats count() by @logStream"
    }
  ]
}
```

### 2. Data Quality Dashboard

```json
{
  "DashboardName": "celebrity-database-data-quality",
  "Widgets": [
    {
      "Type": "Metric",
      "Title": "Total Celebrities in Database",
      "Metrics": [
        ["AWS/DynamoDB", "ItemCount", {"dimensions": {"TableName": "celebrity-database"}}]
      ]
    },
    {
      "Type": "Log",
      "Title": "Average Weight Score",
      "LogGroupName": "/aws/lambda/post-processor",
      "QueryString": "fields weight | stats avg(weight) as average_weight"
    },
    {
      "Type": "Log",
      "Title": "Sentiment Distribution",
      "LogGroupName": "/aws/lambda/post-processor",
      "QueryString": "fields sentiment | stats count() by sentiment"
    },
    {
      "Type": "Log",
      "Title": "Data Freshness (Hours Since Update)",
      "LogGroupName": "/aws/lambda/scraper-*",
      "QueryString": "fields @timestamp | stats (now() - max(@timestamp)) / 3600000 as hours_since_update"
    },
    {
      "Type": "Log",
      "Title": "Scraper Success Rate (%)",
      "LogGroupName": "/aws/lambda/scraper-*",
      "QueryString": "fields status | stats sum(case when status='success' then 1 else 0 end)*100/count(*) as success_rate"
    }
  ]
}
```

### 3. Cost Dashboard

```json
{
  "DashboardName": "celebrity-database-costs",
  "Widgets": [
    {
      "Type": "Metric",
      "Title": "Estimated Daily Cost",
      "Metrics": [
        ["AWS/Billing", "EstimatedCharges", {"dimensions": {"Currency": "USD"}}]
      ]
    },
    {
      "Type": "Log",
      "Title": "Cost Breakdown by Service",
      "QueryString": "fields service, cost | stats sum(cost) by service"
    },
    {
      "Type": "Metric",
      "Title": "Lambda Duration (sec)",
      "Metrics": [
        ["AWS/Lambda", "Duration", {"stat": "Average"}],
        [".", "Duration", {"stat": "Maximum"}]
      ]
    },
    {
      "Type": "Metric",
      "Title": "DynamoDB Read/Write Units",
      "Metrics": [
        ["AWS/DynamoDB", "ConsumedReadCapacityUnits", {"stat": "Average"}],
        [".", "ConsumedWriteCapacityUnits", {"stat": "Average"}]
      ]
    }
  ]
}
```

## CloudWatch Alarms

### Critical Alarms (Immediate Notification)

**1. Lambda Error Rate > 5%**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-high-error-rate \
  --alarm-description "Alert when Lambda error rate exceeds 5%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:critical-alerts
```

**Causes**: Invalid API keys, permission issues, malformed requests, DynamoDB throttling

**Recovery Procedure**:
```bash
# 1. Check specific Lambda logs
aws logs tail /aws/lambda/scraper-tmdb --follow --filter-pattern ERROR

# 2. Look for specific error patterns
# If "Unauthorized": Check API keys in environment variables
# If "ThrottlingException": Scale Lambda memory or increase DynamoDB capacity
# If "TimeoutException": Increase Lambda timeout

# 3. Fix and redeploy
aws lambda update-function-code \
  --function-name scraper-tmdb \
  --zip-file fileb://lambda.zip

# 4. Monitor recovery
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**2. API Gateway 5xx Errors > 10 in 5 minutes**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name api-gateway-5xx-errors \
  --alarm-description "Alert on API Gateway 5xx errors" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --dimensions Name=ApiName,Value=celebrity-database-api \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:critical-alerts
```

**Recovery**: Check Lambda function logs and DynamoDB status

**3. DynamoDB Throttling**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name dynamodb-throttling \
  --alarm-description "Alert on DynamoDB throttling" \
  --metric-name UserErrors \
  --namespace AWS/DynamoDB \
  --dimensions Name=TableName,Value=celebrity-database \
  --statistic Sum \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:critical-alerts
```

**Recovery**: Increase DynamoDB on-demand pricing or add provisioned capacity

### Warning Alarms (Email Notification)

**4. Scraper No Update in 8+ Days**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name scraper-data-stale \
  --alarm-description "Alert if data not updated in 8+ days" \
  --metric-name DataFreshness \
  --namespace custom/celebrity-database \
  --statistic Maximum \
  --period 86400 \
  --threshold 8 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:warnings
```

**Recovery Procedure**:
```bash
# 1. Check if EventBridge rule is enabled
aws events describe-rule --name celebrity-weekly-scrape

# 2. Check most recent Lambda execution
aws logs filter-log-events \
  --log-group-name /aws/lambda/scraper-tmdb \
  --query 'events[0].timestamp'

# 3. Manually trigger scraper
aws lambda invoke \
  --function-name scraper-tmdb \
  --invocation-type Event \
  response.json

# 4. Monitor execution
aws logs tail /aws/lambda/scraper-tmdb --follow
```

**5. High API Latency (p95 > 2 seconds)**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name api-high-latency \
  --alarm-description "Alert if API p95 latency > 2s" \
  --metric-name Latency \
  --namespace AWS/ApiGateway \
  --dimensions Name=ApiName,Value=celebrity-database-api \
  --statistic ExtendedStatistic p95 \
  --period 300 \
  --threshold 2000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:warnings
```

**Recovery**: Optimize Lambda (increase memory), add CloudFront caching, optimize DynamoDB queries

**6. Cost Exceeding Budget**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name monthly-cost-exceeded \
  --alarm-description "Alert if estimated monthly cost > $15" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --dimensions Name=Currency,Value=USD \
  --statistic Maximum \
  --period 86400 \
  --threshold 15 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:cost-alerts
```

### Informational Alarms (Slack Notification)

**7. Weekly Scraper Execution Completed**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name scraper-execution-completed \
  --alarm-description "Notify when weekly scraper completes" \
  --metric-name ScraperSuccess \
  --namespace custom/celebrity-database \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:slack-notifications
```

## Centralized Logging

### CloudWatch Logs Configuration

**Log Group Structure**:
```
/aws/lambda/scraper-tmdb
/aws/lambda/scraper-wikipedia
/aws/lambda/scraper-news
/aws/lambda/scraper-social
/aws/lambda/post-processor
/aws/lambda/list-celebrities
/aws/lambda/get-celebrity
/aws/api-gateway/celebrity-database-api
/aws/s3/celebrity-database-frontend
```

### Log Retention Policies

```bash
# Set 30-day retention for all Lambda logs
for log_group in /aws/lambda/*; do
  aws logs put-retention-policy \
    --log-group-name "$log_group" \
    --retention-in-days 30
done

# API Gateway: 14 days
aws logs put-retention-policy \
  --log-group-name /aws/api-gateway/celebrity-database-api \
  --retention-in-days 14
```

### Log Insights Queries

**Find all errors in last hour**:
```
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| stats count() by @logStream
```

**Calculate average API response time**:
```
fields latency
| stats avg(latency) as average_latency, max(latency) as max_latency, pct(latency, 95) as p95_latency
```

**Track data freshness**:
```
fields @timestamp, celebrity_id
| filter source_type = 'tmdb'
| stats max(@timestamp) as last_update by celebrity_id
| fields last_update, (now() - last_update) / 3600000 as hours_old
```

**Monitor scraper failures**:
```
fields @timestamp, source_type, error_message
| filter status = 'failed'
| stats count() by source_type
```

## Backup & Recovery

### Point-in-Time Recovery (PITR)

**Enable PITR for DynamoDB**:
```bash
aws dynamodb update-continuous-backups \
  --table-name celebrity-database \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Verify enabled
aws dynamodb describe-continuous-backups \
  --table-name celebrity-database \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus'
# Expected: ENABLED
```

**RPO/RTO Targets**:
- RPO (Recovery Point Objective): 5 minutes
- RTO (Recovery Time Objective): < 5 minutes
- Cost: ~$0.20/month

### Manual Backup & Restore

**Create On-Demand Backup**:
```bash
# Create backup
BACKUP_ARN=$(aws dynamodb create-backup \
  --table-name celebrity-database \
  --backup-name celebrity-db-backup-$(date +%Y%m%d-%H%M%S) \
  --query 'BackupDetails.BackupArn' \
  --output text)

echo "Backup created: $BACKUP_ARN"

# List all backups
aws dynamodb list-backups \
  --table-name celebrity-database \
  --query 'BackupSummaries[*].[BackupName,BackupStatus]'
```

**Restore from Backup**:
```bash
# Restore to new table
aws dynamodb restore-table-from-backup \
  --target-table-name celebrity-database-restored \
  --backup-arn $BACKUP_ARN

# Wait for restore to complete
aws dynamodb wait table-exists \
  --table-name celebrity-database-restored

# Verify
aws dynamodb describe-table \
  --table-name celebrity-database-restored \
  --query 'Table.ItemCount'

# Swap tables if needed
# 1. Update API to point to new table
# 2. Verify data
# 3. Delete old table
```

**Quarterly Restore Test** (Runbook):
```bash
#!/bin/bash
# test-restore.sh

DATE=$(date +%Y-%m-%d)
BACKUP_NAME="celebrity-db-test-restore-$DATE"

echo "=== Quarterly DynamoDB Restore Test ==="
echo "Date: $DATE"

# Get latest backup
LATEST_BACKUP=$(aws dynamodb list-backups \
  --table-name celebrity-database \
  --query 'BackupSummaries[0].BackupArn' \
  --output text)

echo "Latest backup: $LATEST_BACKUP"

# Restore to test table
TEST_TABLE="celebrity-database-restore-test-$DATE"

aws dynamodb restore-table-from-backup \
  --target-table-name $TEST_TABLE \
  --backup-arn $LATEST_BACKUP

# Wait for completion
echo "Waiting for restore..."
aws dynamodb wait table-exists --table-name $TEST_TABLE

# Verify item count matches
ORIGINAL=$(aws dynamodb describe-table \
  --table-name celebrity-database \
  --query 'Table.ItemCount' \
  --output text)

RESTORED=$(aws dynamodb describe-table \
  --table-name $TEST_TABLE \
  --query 'Table.ItemCount' \
  --output text)

echo "Original items: $ORIGINAL"
echo "Restored items: $RESTORED"

if [ "$ORIGINAL" -eq "$RESTORED" ]; then
  echo "✓ Restore test PASSED"

  # Cleanup
  aws dynamodb delete-table --table-name $TEST_TABLE
  echo "Test table deleted"
else
  echo "✗ Restore test FAILED - Item count mismatch!"
  exit 1
fi
```

## Security Monitoring

### Access Logging

**API Gateway Access Logs**:
```bash
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=*accessLogSetting/destinationArn,value=arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/aws/api-gateway/celebrity-database-api \
    op=replace,path=*accessLogSetting/format,value='$context.requestId $context.identity.sourceIp $context.requestTime "$context.httpMethod $context.resourcePath" $context.status'
```

**S3 Access Logs**:
```bash
# Create logging bucket
aws s3api create-bucket \
  --bucket celebrity-database-frontend-logs

# Enable logging on main bucket
aws s3api put-bucket-logging \
  --bucket celebrity-database-frontend \
  --bucket-logging-status file:///dev/stdin << EOF
{
  "LoggingEnabled": {
    "TargetBucket": "celebrity-database-frontend-logs",
    "TargetPrefix": "access-logs/"
  }
}
EOF
```

### Unauthorized Access Detection

```bash
# Find 401 errors in last 24 hours
aws logs filter-log-events \
  --log-group-name /aws/api-gateway/celebrity-database-api \
  --filter-pattern '401' \
  --start-time $(($(date +%s%N)/1000000 - 86400000)) \
  --query 'events[*].[timestamp,message]'

# Find repeated access from same IP
aws logs filter-log-events \
  --log-group-name /aws/api-gateway/celebrity-database-api \
  --filter-pattern '401' \
  --query 'events[*].message' \
  | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+' | sort | uniq -c | sort -rn
```

## Operational Runbooks

### Runbook 1: Responding to Lambda Error Alert

**When**: Lambda Error Rate > 5%

**Steps**:
1. **Check Dashboard**: Open CloudWatch dashboard → Lambda metrics
2. **Identify Failed Function**: Look at error graph, see which function has high error rate
3. **Review Logs**:
   ```bash
   aws logs tail /aws/lambda/FUNCTION_NAME --follow --filter-pattern ERROR
   ```
4. **Diagnose**:
   - If "Unauthorized": Check API keys in Lambda environment
   - If "Timeout": Increase Lambda memory or timeout
   - If "Throttled": Check DynamoDB capacity
   - If "Connection": Check network/permissions
5. **Fix**: Update function code, configuration, or environment
6. **Redeploy**:
   ```bash
   aws lambda update-function-code --function-name FUNCTION_NAME --zip-file fileb://lambda.zip
   ```
7. **Monitor**: Watch error rate for 5 minutes to confirm recovery

### Runbook 2: High API Latency Response

**When**: API latency p95 > 2 seconds

**Steps**:
1. **Confirm**: Check API Gateway metrics → Latency graph
2. **Check Dependencies**:
   ```bash
   # Lambda duration
   aws logs filter-log-events \
     --log-group-name /aws/lambda/list-celebrities \
     --filter-pattern Duration
   ```
3. **Optimize**:
   - Increase Lambda memory (more CPU)
   - Check for DynamoDB throttling
   - Add query pagination
   - Increase CloudFront cache TTL
4. **Deploy**: Apply changes and monitor
5. **Verify**: Confirm latency returns to < 1.5s

### Runbook 3: Cost Spike Response

**When**: Daily cost exceeds $0.25/day (run rate > $7.50/month)

**Steps**:
1. **Review**: Check cost dashboard for which service is expensive
2. **Analyze**:
   ```bash
   # Lambda: Check invocations and duration
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --statistics Sum,Maximum

   # DynamoDB: Check read/write units
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name ConsumedReadCapacityUnits
   ```
3. **Optimize**:
   - Reduce Lambda memory if execution time < 1s
   - Enable CloudFront caching
   - Add query optimization
   - Review for runaway queries
4. **Monitor**: Track daily costs for next week

## Regular Maintenance Tasks

### Weekly Checklist

- [ ] Review CloudWatch dashboard for anomalies
- [ ] Check Lambda error logs for patterns
- [ ] Verify scraper ran successfully (Sunday 2 AM UTC)
- [ ] Check data freshness (not older than 7 days)
- [ ] Review cost trend (should be stable)
- [ ] Check disk usage on logs (should stay below 500GB)

### Monthly Checklist

- [ ] Review all CloudWatch alarms for false positives
- [ ] Analyze Lambda performance (duration, memory)
- [ ] Check DynamoDB hot partitions (uneven load)
- [ ] Review security logs for unauthorized access attempts
- [ ] Update dependencies (Lambda layers, libraries)
- [ ] Test backup/restore procedure
- [ ] Review cost optimization opportunities
- [ ] Check for deprecated APIs or services

### Quarterly Checklist

- [ ] Full DynamoDB backup and restore test
- [ ] Security audit of IAM permissions
- [ ] Load test system with 10x normal traffic
- [ ] Review and update disaster recovery procedures
- [ ] Update monitoring runbooks based on incidents
- [ ] Review data retention policies
- [ ] Analyze trending data (growth rate, usage patterns)

### Annual Checklist

- [ ] Architecture review with team
- [ ] Security assessment
- [ ] Disaster recovery drill (simulated major failure)
- [ ] Cost optimization opportunity review
- [ ] Technology upgrade evaluation
- [ ] Capacity planning for next year

## Metrics Glossary

| Metric | Description | Target | Action if Exceeded |
|--------|-------------|--------|-------------------|
| Lambda Error Rate | % of invocations that fail | < 1% | Check logs, increase memory |
| Lambda Duration | Time to execute function | < 1 second | Optimize code, increase memory |
| DynamoDB Throttling | Request rate exceeded capacity | 0 | Increase provisioned or on-demand capacity |
| API Response Time (p95) | 95th percentile latency | < 1.5s | Optimize query, add caching |
| Data Freshness | Hours since last update | < 24h | Check EventBridge rule, verify scrapers |
| Daily Cost | Estimated daily AWS spend | < $0.25 | Review expensive resources |
| Scraper Success Rate | % of scraper runs that succeed | > 95% | Investigate failures, improve error handling |

## Timeline & Milestones

- [ ] Create main CloudWatch dashboard (day 1)
- [ ] Create secondary dashboards (day 2)
- [ ] Set up critical alarms (day 2-3)
- [ ] Configure SNS notifications (day 3)
- [ ] Set up log retention policies (day 3)
- [ ] Enable DynamoDB PITR (day 4)
- [ ] Document operational runbooks (day 4-5)
- [ ] Perform first backup test (day 5)
- [ ] Train team on monitoring (day 5)
- [ ] Enable ongoing monitoring (day 6)

## Current Implementation Status

### ✅ Completed
- [x] Phase 8 directory structure
- [x] Dashboard specifications documented
- [x] Alarm configurations documented
- [x] Runbooks documented
- [x] Backup/recovery procedures documented

### 🟡 In Progress
- [ ] Deploy CloudWatch dashboards
- [ ] Create alarms
- [ ] Configure SNS topics

### ⏳ Not Started
- [ ] Ongoing monitoring and maintenance

## Operational Handover Checklist

Before handing system to operations team:

- [ ] All dashboards created and tested
- [ ] All alarms configured and tested
- [ ] SNS topics created and subscriptions active
- [ ] Log retention policies configured
- [ ] Backup/recovery tested
- [ ] On-call rotation established
- [ ] Runbooks documented and accessible
- [ ] Escalation procedures defined
- [ ] Team training completed
- [ ] 24/7 monitoring enabled

## References

- Project Plan: `../../project-updated.md`
- AWS CloudWatch: https://docs.aws.amazon.com/cloudwatch/
- CloudWatch Alarms: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/
- DynamoDB Backup: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BackupRestore.html
- Best Practices: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/Best_Practice_Recommended_Alarms_AWS_Services.html

---

**Phase 8 Status**: Ready for Deployment
**Created**: November 7, 2025
**Last Updated**: November 7, 2025
