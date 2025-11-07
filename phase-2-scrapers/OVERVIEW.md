# Phase 2: Data Source Scrapers - Overview & Navigation

## Quick Start

Phase 2 implements a **four-stage data collection pipeline**, where each stage collects data from different sources using optimized methodologies.

### The Four Stages

| Stage | Name | Method | Data | Status | Cost |
|-------|------|--------|------|--------|------|
| **2.1** | Google Search | API | Search results | ✅ Ready | $0-2/mo |
| **2.2** | Instagram | Account + Proxy | Followers, Posts | ⚠️ Anti-Bot | $10-20/mo |
| **2.3** | Threads | Account + Proxy | Followers, Posts | ⚠️ Anti-Bot | $5-10/mo |
| **2.4** | YouTube | Official API | Subscribers, Videos | ✅ Ready | Free |

## Directory Structure

```
phase-2-scrapers/
├── OVERVIEW.md                          ← You are here
├── stage-2.1-google-search/
│   ├── README.md                        # Stage 2.1 documentation
│   ├── lambda_function.py               # Implementation
│   ├── requirements.txt
│   ├── test_scraper.py
│   └── .env.template
├── stage-2.2-instagram/
│   ├── README.md                        # Stage 2.2 documentation
│   ├── lambda_function.py
│   ├── proxy_manager.py
│   ├── requirements.txt
│   ├── test_scraper.py
│   └── .env.template
├── stage-2.3-threads/
│   ├── README.md                        # Stage 2.3 documentation
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── test_scraper.py
│   └── .env.template
├── stage-2.4-youtube/
│   ├── README.md                        # Stage 2.4 documentation
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── test_scraper.py
│   └── .env.template
├── shared-resources/
│   ├── lambda-layers/
│   │   ├── requirements.txt
│   │   └── publish-layer.sh
│   ├── shared-utilities/
│   │   ├── dynamodb_helper.py
│   │   ├── logger_config.py
│   │   └── retry_handler.py
│   └── iam-policy.json
└── deployment/
    ├── deploy.sh
    └── test-all-stages.sh
```

## How to Use

### For Individual Stage Documentation

Click on the stage you're interested in:

- **[Stage 2.1: Google Search](./stage-2.1-google-search/README.md)** - Simple API calls with text cleaning
- **[Stage 2.2: Instagram](./stage-2.2-instagram/README.md)** - Account-based with proxy rotation
- **[Stage 2.3: Threads](./stage-2.3-threads/README.md)** - Account-based (same as Instagram)
- **[Stage 2.4: YouTube](./stage-2.4-youtube/README.md)** - Official API integration

### For Deployment

```bash
# Deploy all stages at once
bash deployment/deploy.sh

# Test all stages
bash deployment/test-all-stages.sh
```

## Data Collection Architecture

### First-Hand Data Requirement

All stages collect **first-hand data** - the raw, unprocessed response from each source:

```json
{
  "id": "uuid-string",
  "name": "Celebrity Name",
  "raw_text": "{complete unprocessed API response or HTML}",
  "source": "https://source.url/endpoint",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null
}
```

### DynamoDB Write Pattern

Each stage writes to DynamoDB with this key pattern:

```
celebrity_id + source_type#timestamp

Examples:
- celeb_001 + google_search#2025-11-07T17:20:00Z
- celeb_001 + instagram#2025-11-07T17:20:00Z
- celeb_001 + threads#2025-11-07T17:20:00Z
- celeb_001 + youtube#2025-11-07T17:20:00Z
```

## Implementation Timeline

| Week | Stage | Tasks |
|------|-------|-------|
| **3** | 2.1 | API setup → Code → Test (1, 5, 100) → Deploy |
| **4** | 2.2 | Account setup → Proxies → Code → Test → Deploy |
| **5** | 2.3 | Code → Test → Validation → Deploy |
| **6** | 2.4 | Code → Test → Deploy → Integration testing |

## Key Principles

### Error Handling
- ✅ Try-catch blocks for all API calls
- ✅ Specific handling per error type (timeout, rate limit, detection)
- ✅ Exponential backoff with jitter
- ✅ Circuit breaker for detection blocks
- ✅ Graceful degradation (continue if 1 celebrity fails)

### Security
- ✅ API keys in AWS Secrets Manager (never hardcoded)
- ✅ Account credentials encrypted
- ✅ HTTPS for all requests
- ✅ User-Agent rotation (respect APIs)
- ✅ No sensitive data in logs

### Robustness
- ✅ Idempotent operations
- ✅ Comprehensive logging
- ✅ Timeout protection
- ✅ Partial success handling
- ✅ Health checks before operations

### Performance
- ✅ Connection reuse
- ✅ Rate limit compliance
- ✅ Batch operations where possible
- ✅ Proxy rotation for stages 2.2 & 2.3
- ✅ Request timing for human-like behavior

## Testing at Each Step

**Critical**: All stages follow a test-at-each-step protocol:

1. **Phase XA**: Setup (API keys, accounts, proxies)
2. **Phase XB**: Single celebrity test (online)
3. **Phase XC**: Data verification (DynamoDB check)
4. **Phase XD**: Batch test (5 celebrities)
5. **Phase XE**: Full deployment (100 celebrities)

**STOP if errors found - fix before proceeding**

## Cost Summary

| Stage | Service | Cost |
|-------|---------|------|
| 2.1 | Google Search API | $0-2/month |
| 2.2 | Instagram + Proxy | $10-20/month |
| 2.3 | Threads + Proxy | $5-10/month |
| 2.4 | YouTube API | Free |
| **Total Phase 2** | | **~$15-32/month** |

## Dependencies

### Common (All Stages)

```
requests==2.31.0
boto3==1.28.0
python-dateutil==2.8.2
beautifulsoup4==4.12.2
```

### Lambda Layers

**Layer Name**: `celebrity-scrapers-dependencies`

```bash
mkdir -p python
pip install -r requirements.txt -t python/
zip -r layer.zip python/
aws lambda publish-layer-version \
  --layer-name celebrity-scrapers-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11
```

## AWS Permissions Required

All scrapers need these IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/celebrity-database"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:instagram-accounts*",
        "arn:aws:secretsmanager:*:*:secret:proxy-list*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Integration Testing

After all 4 stages are deployed:

### Test All Stages Together

```bash
# Trigger all scrapers simultaneously
for scraper in scraper-google-search scraper-instagram scraper-threads scraper-youtube; do
  aws lambda invoke \
    --function-name $scraper \
    --payload '{"limit": 5}' \
    response-$scraper.json &
done

wait

# Check results
for scraper in scraper-google-search scraper-instagram scraper-threads scraper-youtube; do
  echo "=== $scraper ==="
  cat response-$scraper.json | jq '.success, .errors'
done
```

### Verify Data Completeness

```bash
# For each celebrity, verify all stages have data
for celeb_id in celeb_001 celeb_002 celeb_003; do
  echo "=== $celeb_id ==="

  aws dynamodb query --table-name celebrity-database \
    --key-condition-expression "celebrity_id = :id" \
    --expression-attribute-values "{\":id\":{\"S\":\"$celeb_id\"}}" \
    --query 'Items[] | [?!begins_with(source_type#timestamp, `master`) | source_type#timestamp | split(`#`)[0]]' | sort | uniq
done

# Expected output for each celebrity:
# [
#   "google_search",
#   "instagram" (or skip if no profile),
#   "threads" (or skip if no profile),
#   "youtube" (or skip if no channel)
# ]
```

## Fallback & Recovery

### Stage Temporary Failure
```
Detection: Timeout errors, 503 responses
Response: Exponential backoff up to 5 minutes
Recovery: Skip affected celebrities, continue
Result: Some data missing for this stage
Next Week: Re-attempt on next scheduled run
```

### Partial Batch Failure
```
Detection: 80% success, 20% error
Response: Log details of failures
Recovery: Proceed if success rate > 70%
Action: Failed celebrities retried next week
```

### Rate Limit Across Stages
```
Detection: 429 responses from multiple sources
Response: Stagger stage execution (don't run all at once)
Recovery: Space out by 5-10 minutes
Action: Use EventBridge for staggered triggers
```

## Monitoring & Logging

### CloudWatch Metrics to Track

- Lambda invocation count and errors (per stage)
- DynamoDB write operations
- Rate limit errors (429, 403)
- Detection blocks (Instagram/Threads)
- Average response time per stage

### Sample CloudWatch Logs

```bash
# View logs for specific stage
aws logs tail /aws/lambda/scraper-google-search --follow

# View errors only
aws logs tail /aws/lambda/scraper-instagram --follow --filter-pattern "ERROR"

# Count errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scraper-google-search \
  --filter-pattern "ERROR" \
  --query 'events | length'
```

## References

- **Main Project Plan**: `../project-updated.md`
- **Google Custom Search API**: https://developers.google.com/custom-search/v1/overview
- **Instagram**: https://www.instagram.com/
- **Threads**: https://www.threads.net/
- **YouTube Data API**: https://developers.google.com/youtube/v3
- **AWS Secrets Manager**: https://docs.aws.amazon.com/secretsmanager/

## Status

### ✅ Completed
- [x] Phase 2 restructured into 4 stages
- [x] Individual stage documentation
- [x] Error handling framework
- [x] Testing protocols
- [x] Code examples for each stage

### 🟡 In Progress
- [ ] Deploy Stage 2.1 (Google Search)
- [ ] Test with 1, 5, then 100 celebrities
- [ ] Deploy Stage 2.2 (Instagram)
- [ ] Deploy Stage 2.3 (Threads)
- [ ] Deploy Stage 2.4 (YouTube)

### ⏳ Pending
- [ ] Phase 3 (Post-Processing)

## Next Steps

1. **Choose Starting Stage**: Typically start with Stage 2.1 (Google) for simplicity
2. **Set Up Prerequisites**: API keys, accounts, proxies (as needed per stage)
3. **Review Stage Documentation**: Read the specific README for your chosen stage
4. **Follow Testing Protocol**: Phase XA → XB → XC → XD → XE
5. **Monitor Execution**: Check CloudWatch logs during testing
6. **Proceed to Next Stage**: Only after previous stage passes all tests
7. **Integration Testing**: After all stages deployed

---

**Phase 2 Status**: Ready for Implementation
**Created**: November 7, 2025
**Version**: 1.0
**Architecture**: Four-Stage Pipeline
