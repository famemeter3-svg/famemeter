# Phase 2 - Quick Setup Reference

**Quick commands for completing Phase 2 production setup**

---

## 🎯 IMMEDIATE TASKS (Do These First)

### 1️⃣ Update Google API Credentials

```bash
aws secretsmanager update-secret \
  --secret-id google-api-keys \
  --secret-string '{
    "api_keys": [
      {
        "key_id": "key_001",
        "api_key": "YOUR_ACTUAL_GOOGLE_API_KEY",
        "status": "active"
      }
    ],
    "search_engine_id": "YOUR_SEARCH_ENGINE_ID"
  }' \
  --region us-east-1
```

**Get credentials from**: https://console.cloud.google.com/ (Custom Search API)

---

### 2️⃣ Update Instagram Credentials (Optional but needed for Threads)

```bash
aws secretsmanager update-secret \
  --secret-id instagram-accounts \
  --secret-string '{
    "accounts": [
      {
        "account_id": "account_001",
        "username": "your_instagram_username",
        "password": "your_instagram_password",
        "status": "active",
        "created": "2025-11-08"
      }
    ]
  }' \
  --region us-east-1
```

---

### 3️⃣ Update Proxy List (Required for Threads)

```bash
aws secretsmanager update-secret \
  --secret-id proxy-list \
  --secret-string '{
    "proxies": [
      {
        "proxy_id": "proxy_001",
        "url": "http://proxy.server.com:8080",
        "username": "proxy_user",
        "password": "proxy_password",
        "status": "active"
      }
    ]
  }' \
  --region us-east-1
```

---

### 4️⃣ Update YouTube API Credentials

```bash
aws secretsmanager update-secret \
  --secret-id youtube-api-key \
  --secret-string '{
    "api_key": "YOUR_ACTUAL_YOUTUBE_API_KEY"
  }' \
  --region us-east-1
```

**Get credentials from**: https://console.cloud.google.com/ (YouTube Data API v3)

---

### 5️⃣ Subscribe to Email Notifications

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:775287841920:scraper-alerts-prod \
  --protocol email \
  --notification-endpoint YOUR_EMAIL@example.com \
  --region us-east-1
```

⚠️ **Check your email** for the subscription confirmation and click the link!

---

## ✅ VERIFY SETUP

### Check All Secrets Are Created
```bash
aws secretsmanager list-secrets --region us-east-1 \
  --query 'SecretList[?contains(Name, `key` || Name || `account` || `proxy`)].{Name: Name, Updated: LastChangedDate}' \
  --output table
```

### Check All Lambda Functions
```bash
aws lambda list-functions --region us-east-1 \
  --query 'Functions[?contains(FunctionName, `scraper-`)].{Name: FunctionName, Runtime: Runtime, Updated: LastModified}' \
  --output table
```

### Check EventBridge Schedules
```bash
aws events list-rules --region us-east-1 \
  --query 'Rules[?contains(Name, `scraper-`)].{Name: Name, State: State, Schedule: ScheduleExpression}' \
  --output table
```

### Check SNS Subscriptions
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:775287841920:scraper-alerts-prod \
  --region us-east-1 \
  --query 'Subscriptions[].{Endpoint: Endpoint, Protocol: Protocol, Status: SubscriptionArn}' \
  --output table
```

---

## 🧪 TEST EXECUTION

### Manual Test (After Updating Credentials)

```bash
# Test Instagram
aws lambda invoke \
  --function-name scraper-instagram-prod \
  --region us-east-1 \
  --payload '{}' \
  /tmp/instagram_test.json

# View response
cat /tmp/instagram_test.json | python3 -m json.tool

# Check CloudWatch logs
aws logs tail /aws/lambda/scraper-instagram-prod --since 5m --region us-east-1
```

---

## 📅 SCHEDULED EXECUTION TIMES

| Function | Schedule | Time (UTC) | Cron |
|----------|----------|-----------|------|
| Google Search | Weekly | Wednesday 3 AM | `cron(0 3 ? * 3 *)` |
| Instagram | Weekly | Monday 2 AM | `cron(0 2 ? * 1 *)` |
| Threads | Weekly | Tuesday 2 AM | `cron(0 2 ? * 2 *)` |
| YouTube | Weekly | Thursday 4 AM | `cron(0 4 ? * 4 *)` |

---

## 🔄 EXPECTED DATA FLOW

```
1. EventBridge triggers at scheduled time
         ↓
2. Lambda function invoked
         ↓
3. Secrets Manager provides credentials
         ↓
4. Scraper collects data from API/site
         ↓
5. Data written to DynamoDB
         ↓
6. DynamoDB Stream triggers
         ↓
7. Phase 3 Lambda receives event (future)
         ↓
8. Phase 3 processes data (enrichment, sentiment)
         ↓
9. Updated item stored back in DynamoDB
```

---

## 📊 VERIFY DATA IN DYNAMODB

```bash
# Count items in table
aws dynamodb scan \
  --table-name celebrity-database \
  --region us-east-1 \
  --select COUNT

# Query by source (example)
aws dynamodb query \
  --table-name celebrity-database \
  --region us-east-1 \
  --key-condition-expression "celebrity_id = :id" \
  --expression-attribute-values '{":id": {"S": "celeb_001"}}' \
  --output table

# Scan recent items (first 5)
aws dynamodb scan \
  --table-name celebrity-database \
  --region us-east-1 \
  --limit 5 \
  --output table
```

---

## 🚨 TROUBLESHOOTING QUICK LINKS

| Problem | Solution |
|---------|----------|
| Lambda not executing | Check EventBridge rule is ENABLED: `aws events describe-rule --name scraper-instagram-schedule-prod` |
| Credentials error | Check secret exists: `aws secretsmanager get-secret-value --secret-id google-api-keys` |
| No data in DB | Check Lambda logs: `aws logs tail /aws/lambda/scraper-instagram-prod --follow` |
| No email alerts | Confirm SNS subscription: https://console.aws.amazon.com/sns/ |
| API rate limit | Check metrics: `aws cloudwatch get-metric-statistics --namespace GoogleSearchScraper` |

---

## 🎯 CHECKLIST

- [ ] Google API credentials updated
- [ ] Instagram credentials updated (optional)
- [ ] Proxy list updated (required for Threads)
- [ ] YouTube API credentials updated
- [ ] Email subscription confirmed (check inbox!)
- [ ] Manual test invocation succeeded
- [ ] Data visible in DynamoDB
- [ ] CloudWatch logs show successful execution
- [ ] No errors in logs
- [ ] Ready for scheduled execution!

---

## 📞 CONFIGURATION DETAILS

### Secrets Manager ARNs
```
Google:     arn:aws:secretsmanager:us-east-1:775287841920:secret:google-api-keys-Jt3TDk
Instagram:  arn:aws:secretsmanager:us-east-1:775287841920:secret:instagram-accounts-5kq0uo
Proxies:    arn:aws:secretsmanager:us-east-1:775287841920:secret:proxy-list-BLqSrc
YouTube:    arn:aws:secretsmanager:us-east-1:775287841920:secret:youtube-api-key-sGfvuO
```

### Lambda Functions
```
Google Search:  scraper-google-search-prod
Instagram:      scraper-instagram-prod
Threads:        scraper-threads-prod
YouTube:        scraper-youtube-prod
```

### EventBridge Rules
```
Google Search:  scraper-google-search-schedule-prod (existing)
Instagram:      scraper-instagram-schedule-prod
Threads:        scraper-threads-schedule-prod
YouTube:        scraper-youtube-schedule-prod
```

### DynamoDB
```
Table:          celebrity-database
Streams ARN:    arn:aws:dynamodb:us-east-1:775287841920:table/celebrity-database/stream/2025-11-07T11:01:34.356
Items:          408 (initial)
```

### SNS
```
Topic:          scraper-alerts-prod
ARN:            arn:aws:sns:us-east-1:775287841920:scraper-alerts-prod
Subscriptions:  (Add your email!)
```

---

**Status**: Production Ready - Awaiting Credential Updates ✅
**Last Updated**: November 8, 2025, 13:36 UTC
**Next Action**: Update Secrets Manager with real credentials!

