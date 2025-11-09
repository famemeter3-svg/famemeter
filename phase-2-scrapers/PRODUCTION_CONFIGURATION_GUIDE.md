# Phase 2 - Production Configuration Guide

**Date**: November 8, 2025
**Status**: Configuration Complete - Ready for Credentials Setup
**Region**: us-east-1
**Account**: 775287841920

---

## 📋 Configuration Summary

All Phase 2 infrastructure is now configured and ready for production use. This guide documents the setup and next steps for full deployment.

### ✅ Completed Configuration Tasks

- [x] AWS Secrets Manager created for all credential types
- [x] Lambda environment variables updated with Secrets Manager ARNs
- [x] EventBridge schedules created and enabled for stages 2.2-2.4
- [x] Lambda permissions configured for EventBridge invocation
- [x] DynamoDB Streams verified and enabled for Phase 3
- [x] SNS topic ready for alert subscriptions
- [x] CloudWatch monitoring and dashboards active

---

## 🔐 Secrets Manager Configuration

### 1. Google API Keys Secret
**Secret Name**: `google-api-keys`
**ARN**: `arn:aws:secretsmanager:us-east-1:775287841920:secret:google-api-keys-Jt3TDk`

**Required Structure**:
```json
{
  "api_keys": [
    {
      "key_id": "key_001",
      "api_key": "YOUR_GOOGLE_CUSTOM_SEARCH_API_KEY",
      "status": "active"
    }
  ],
  "search_engine_id": "YOUR_SEARCH_ENGINE_ID"
}
```

**How to Update**:
```bash
aws secretsmanager update-secret \
  --secret-id google-api-keys \
  --secret-string '{"api_keys":[{"key_id":"key_001","api_key":"YOUR_KEY","status":"active"}],"search_engine_id":"YOUR_ENGINE_ID"}' \
  --region us-east-1
```

**Where to Get Credentials**:
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Enable "Custom Search API"
3. Create API Key (Restricted)
4. Go to Custom Search Console: https://cse.google.com/cse/
5. Create or use existing search engine
6. Get your Search Engine ID (cx parameter)

---

### 2. Instagram Accounts Secret
**Secret Name**: `instagram-accounts`
**ARN**: `arn:aws:secretsmanager:us-east-1:775287841920:secret:instagram-accounts-5kq0uo`

**Required Structure**:
```json
{
  "accounts": [
    {
      "account_id": "account_001",
      "username": "instagram_username",
      "password": "instagram_password",
      "status": "active",
      "created": "2025-11-08"
    }
  ]
}
```

**How to Update**:
```bash
aws secretsmanager update-secret \
  --secret-id instagram-accounts \
  --secret-string '{"accounts":[{"account_id":"account_001","username":"YOUR_USERNAME","password":"YOUR_PASSWORD","status":"active","created":"2025-11-08"}]}' \
  --region us-east-1
```

**Notes**:
- Optional for Stage 2.2 (Instagram scraper can run anonymously)
- **REQUIRED** for Stage 2.3 (Threads scraper)
- Use account credentials with caution - consider using a dedicated account
- Enable 2FA on the account, then create an app-specific password

---

### 3. Proxy List Secret
**Secret Name**: `proxy-list`
**ARN**: `arn:aws:secretsmanager:us-east-1:775287841920:secret:proxy-list-BLqSrc`

**Required Structure**:
```json
{
  "proxies": [
    {
      "proxy_id": "proxy_001",
      "url": "http://proxy1.example.com:8080",
      "username": "proxy_username",
      "password": "proxy_password",
      "status": "active"
    },
    {
      "proxy_id": "proxy_002",
      "url": "http://proxy2.example.com:8080",
      "username": "proxy_username",
      "password": "proxy_password",
      "status": "active"
    }
  ]
}
```

**How to Update**:
```bash
aws secretsmanager update-secret \
  --secret-id proxy-list \
  --secret-string '{"proxies":[{"proxy_id":"proxy_001","url":"http://proxy1.com:8080","username":"user","password":"pass","status":"active"}]}' \
  --region us-east-1
```

**Notes**:
- **REQUIRED** for Stage 2.3 (Threads scraper)
- Optional for Stage 2.2 (Instagram scraper)
- Multiple proxies supported for rotation
- Supports HTTP/HTTPS with authentication

---

### 4. YouTube API Key Secret
**Secret Name**: `youtube-api-key`
**ARN**: `arn:aws:secretsmanager:us-east-1:775287841920:secret:youtube-api-key-sGfvuO`

**Required Structure**:
```json
{
  "api_key": "YOUR_YOUTUBE_DATA_API_V3_KEY"
}
```

**How to Update**:
```bash
aws secretsmanager update-secret \
  --secret-id youtube-api-key \
  --secret-string '{"api_key":"YOUR_YOUTUBE_API_KEY"}' \
  --region us-east-1
```

**Where to Get Credentials**:
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Enable "YouTube Data API v3"
3. Create API Key (Restricted)
4. Add allowed APIs: YouTube Data API v3

---

## 📅 EventBridge Schedules Configuration

All schedules are created and enabled. They will automatically invoke Lambda functions at specified times.

### Stage 2.2: Instagram Scraper
**Rule Name**: `scraper-instagram-schedule-prod`
**Schedule**: Monday 2 AM UTC (Weekly)
**Cron Expression**: `cron(0 2 ? * 1 *)`
**Target**: `scraper-instagram-prod` Lambda function

**View/Modify Schedule**:
```bash
# View rule
aws events describe-rule --name scraper-instagram-schedule-prod --region us-east-1

# Enable/Disable rule
aws events disable-rule --name scraper-instagram-schedule-prod --region us-east-1
aws events enable-rule --name scraper-instagram-schedule-prod --region us-east-1

# Modify schedule
aws events put-rule \
  --name scraper-instagram-schedule-prod \
  --schedule-expression "cron(0 2 ? * 1 *)" \
  --state ENABLED \
  --region us-east-1
```

### Stage 2.3: Threads Scraper
**Rule Name**: `scraper-threads-schedule-prod`
**Schedule**: Tuesday 2 AM UTC (Weekly)
**Cron Expression**: `cron(0 2 ? * 2 *)`
**Target**: `scraper-threads-prod` Lambda function

### Stage 2.4: YouTube Scraper
**Rule Name**: `scraper-youtube-schedule-prod`
**Schedule**: Thursday 4 AM UTC (Weekly)
**Cron Expression**: `cron(0 4 ? * 4 *)`
**Target**: `scraper-youtube-prod` Lambda function

### Schedule Rationale
Schedules are staggered across different days and times to:
- Avoid concurrent API rate limit issues
- Prevent simultaneous DynamoDB throttling
- Distribute load across the week
- Allow monitoring and debugging time between executions

---

## 📧 SNS Email Notifications Setup

The SNS topic `scraper-alerts-prod` is ready to receive alert subscriptions.

### Subscribe to Email Notifications

**Option 1: AWS Console**
1. Go to SNS console: https://console.aws.amazon.com/sns/
2. Select Topic: `scraper-alerts-prod`
3. Click "Create subscription"
4. Protocol: Email
5. Endpoint: Your email address
6. Confirm subscription in your email

**Option 2: AWS CLI**
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:775287841920:scraper-alerts-prod \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1
```

### Current Subscriptions
- Count: 0 (None configured yet)

### Alert Types
You will receive notifications for:
- **High Error Rate**: > 20 failed scrapes in 5 minutes
- **API Quota Issues**: > 15 key rotations in 5 minutes
- **Rate Limiting**: > 10 rate limit events in 5 minutes
- **Lambda Failures**: Execution errors or timeouts

---

## 🗄️ DynamoDB Configuration

### Celebrity Database Table
**Table Name**: `celebrity-database`
**Status**: ACTIVE ✅
**Item Count**: 408 items
**Streams**: ✅ ENABLED with `NEW_AND_OLD_IMAGES` view type
**Stream ARN**: `arn:aws:dynamodb:us-east-1:775287841920:table/celebrity-database/stream/2025-11-07T11:01:34.356`

### Schema

**Partition Key**: `celebrity_id` (String)
**Sort Key**: `source_type#timestamp` (String)

Example:
- Partition: `celeb_001`
- Sort: `google_search#2025-11-08T10:00:00Z`

### Data Written by Phase 2

All scrapers write data in this format:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "google_search#2025-11-08T10:00:00Z",
  "id": "uuid-v4-string",
  "name": "Celebrity Name",
  "raw_text": "complete unprocessed API response or HTML",
  "source": "https://source.url",
  "timestamp": "2025-11-08T10:00:00Z",
  "weight": null,
  "sentiment": null,
  "metadata": {
    "scraper_name": "scraper-google-search",
    "source_type": "google_search",
    "processed": false,
    "error": null,
    "request_id": "request-uuid"
  }
}
```

### Streams Configuration (For Phase 3)

DynamoDB Streams is enabled and ready for Phase 3 post-processing:
- **Stream Mode**: `NEW_AND_OLD_IMAGES` (captures both old and new item state)
- **Retention**: 24 hours
- **Use Case**: Triggers Phase 3 Lambda for sentiment analysis and data enrichment

**Phase 3 Will**:
1. Receive new items from DynamoDB Stream
2. Process `raw_text` field
3. Calculate `weight` (0-1 confidence score)
4. Determine `sentiment` (positive/negative/neutral)
5. Update item with `processed: true`

---

## ☁️ CloudWatch Monitoring

### Logs
All Lambda functions write structured JSON logs to CloudWatch:
- `/aws/lambda/scraper-google-search-prod` (30-day retention)
- `/aws/lambda/scraper-instagram-prod` (30-day retention)
- `/aws/lambda/scraper-threads-prod` (30-day retention)
- `/aws/lambda/scraper-youtube-prod` (30-day retention)

### View Logs
```bash
# Follow logs in real-time
aws logs tail /aws/lambda/scraper-instagram-prod --follow --region us-east-1

# View recent logs
aws logs tail /aws/lambda/scraper-instagram-prod --since 1h --region us-east-1
```

### Dashboards
- **Dashboard Name**: `scraper-google-search-prod`
- **URL**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=scraper-google-search-prod

### Metrics
Custom metrics published by all stages:
- `SuccessfulScrapes` - Number of successful data collection runs
- `FailedScrapes` - Number of failed attempts
- `RateLimitedCount` - Rate limiting events
- `RetryCount` - Retry attempts
- `ExecutionDuration` - Execution time in milliseconds

**Namespaces**:
- `GoogleSearchScraper`
- `InstagramScraper`
- `ThreadsScraper`
- `YouTubeScraper`

### Alarms
Two alarms configured for Stage 2.1 (Google Search):
1. **High Error Rate Alarm**
   - Name: `scraper-google-search-high-error-rate-prod`
   - Threshold: > 20 failures in 5 minutes
   - Action: SNS notification

2. **API Quota Alarm**
   - Name: `scraper-google-search-api-quota-prod`
   - Threshold: > 15 key rotations in 5 minutes
   - Action: SNS notification

Similar alarms can be configured for other stages if needed.

---

## 🚀 Next Steps

### 1. Update Secrets (CRITICAL)
```bash
# Update each secret with real credentials
aws secretsmanager update-secret --secret-id google-api-keys --secret-string '...' --region us-east-1
aws secretsmanager update-secret --secret-id instagram-accounts --secret-string '...' --region us-east-1
aws secretsmanager update-secret --secret-id proxy-list --secret-string '...' --region us-east-1
aws secretsmanager update-secret --secret-id youtube-api-key --secret-string '...' --region us-east-1
```

### 2. Subscribe to Email Notifications
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:775287841920:scraper-alerts-prod \
  --protocol email \
  --notification-endpoint YOUR_EMAIL@example.com \
  --region us-east-1
```

### 3. Test Manual Invocation
```bash
# Test with credentials now loaded
aws lambda invoke \
  --function-name scraper-instagram-prod \
  --region us-east-1 \
  --payload '{}' \
  response.json

cat response.json
```

### 4. Monitor First Scheduled Execution
- Wait for scheduled time (Monday 2 AM UTC for Instagram, etc.)
- Monitor CloudWatch logs: `/aws/lambda/scraper-instagram-prod`
- Verify data written to DynamoDB
- Check email notifications

### 5. Verify Phase 3 Readiness
- Confirm DynamoDB Streams events are flowing
- Set up Phase 3 Lambda trigger on DynamoDB Streams
- Test end-to-end flow from Phase 2 → DynamoDB → Phase 3

---

## 🔍 Troubleshooting

### Lambda Function Not Executing

**Check**:
1. EventBridge rule is ENABLED
2. Lambda has permission from EventBridge
3. Lambda execution role has Secrets Manager access
4. Credentials in Secrets Manager are valid

**View**:
```bash
# Check EventBridge rule
aws events describe-rule --name scraper-instagram-schedule-prod --region us-east-1

# Check Lambda permissions
aws lambda get-policy --function-name scraper-instagram-prod --region us-east-1

# Check function execution
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=scraper-instagram-prod \
  --start-time 2025-11-08T00:00:00Z \
  --end-time 2025-11-08T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

### Credentials Not Found

**Check**:
1. Secret name is correct
2. Secret ARN matches Lambda environment variable
3. Lambda execution role has `secretsmanager:GetSecretValue` permission
4. Secret is in same region (us-east-1)

**View Secret** (Admin only):
```bash
aws secretsmanager get-secret-value \
  --secret-id google-api-keys \
  --region us-east-1 \
  --query SecretString
```

### Data Not Written to DynamoDB

**Check**:
1. Lambda execution role has `dynamodb:PutItem` permission
2. DynamoDB table `celebrity-database` exists
3. Lambda logs for errors: `aws logs tail /aws/lambda/scraper-instagram-prod --follow`
4. Verify data schema matches requirements

---

## 📊 Health Check Commands

```bash
# Check all Lambda functions
aws lambda list-functions --region us-east-1 --query 'Functions[?contains(FunctionName, `scraper-`)]' --output table

# Check EventBridge rules
aws events list-rules --region us-east-1 --query 'Rules[?contains(Name, `scraper-`)]' --output table

# Check Secrets
aws secretsmanager list-secrets --region us-east-1 --query 'SecretList[?contains(Name, `scraper`)]' --output table

# Check DynamoDB table status
aws dynamodb describe-table --table-name celebrity-database --region us-east-1 --query 'Table.{Status: TableStatus, Items: ItemCount, Streams: StreamSpecification}'

# Check SNS subscriptions
aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:775287841920:scraper-alerts-prod --region us-east-1 --output table

# Check CloudWatch logs
aws logs describe-log-groups --region us-east-1 --query 'logGroups[?contains(logGroupName, `scraper`)]' --output table
```

---

## 📝 Configuration Checklist

- [ ] All 4 Secrets Manager secrets created
- [ ] All secrets updated with real credentials
- [ ] Lambda environment variables pointing to Secrets Manager ARNs
- [ ] EventBridge rules created and enabled (3 rules)
- [ ] Lambda permissions configured for EventBridge
- [ ] SNS email subscription confirmed
- [ ] DynamoDB Streams verified as enabled
- [ ] CloudWatch logs confirmed
- [ ] Manual test invocation successful
- [ ] Data written to DynamoDB verified
- [ ] First scheduled execution completed and verified

---

## 🎯 Phase 3 Integration Points

**DynamoDB Stream ARN** (for Phase 3 Lambda trigger):
```
arn:aws:dynamodb:us-east-1:775287841920:table/celebrity-database/stream/2025-11-07T11:01:34.356
```

**Data Schema**:
- Phase 2 writes items with `weight: null`, `sentiment: null`
- Phase 2 sets `metadata.processed: false`
- Phase 3 receives items via DynamoDB Stream
- Phase 3 populates `weight` and `sentiment`
- Phase 3 sets `metadata.processed: true`
- Phase 3 updates item in DynamoDB

**No schema transformation needed** - 100% compatible between phases.

---

**Last Updated**: November 8, 2025, 13:36 UTC
**Status**: Production Configuration Complete ✅
**Next Action**: Update Secrets Manager with real credentials and subscribe to SNS

