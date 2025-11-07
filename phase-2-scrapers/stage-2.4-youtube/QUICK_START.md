# Stage 2.4: Quick Start Guide

## 🚀 Get Started in 5 Minutes

### What You Have
✅ Complete YouTube API scraper
✅ 13 unit tests (all passing)
✅ Comprehensive documentation
✅ Free YouTube API quota (10,000 units/day)

---

## Step 1: Local Setup (2 minutes)

```bash
# 1. Copy environment template
cp .env.template .env

# 2. Edit .env and add your YouTube API key
vi .env

# Should contain:
YOUTUBE_API_KEY=your_valid_api_key_here
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
LOG_LEVEL=INFO
```

### Get Your YouTube API Key
1. Visit https://console.cloud.google.com
2. Create or select a project
3. Enable "YouTube Data API v3"
4. Go to Credentials → Create Credentials → API Key
5. Copy the key (starts with "AIza")
6. Paste into .env file

### Secure Your Keys
```bash
# Add .env to .gitignore (never commit keys!)
echo ".env" >> .gitignore
```

---

## Step 2: Test Locally (1 minute)

```bash
# Run offline test
python3 lambda_function.py --test-mode

# Expected output:
# ✓ Lambda handler function exists
# ✓ YouTube search function defined
# ✓ Channel data fetch function defined
# ✓ Error handling functions defined
# ✓ DynamoDB integration prepared
# ✓ Test mode completed
```

```bash
# Run all unit tests
python3 -m pytest test_scraper.py -v

# Expected: ✅ 13 passed
```

---

## Step 3: Deploy to AWS Lambda (2 minutes)

### Create the Lambda Function

```bash
# 1. Create deployment package
zip -r function.zip lambda_function.py

# 2. Create Lambda function
aws lambda create-function \
  --function-name scraper-youtube \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --memory-size 512 \
  --timeout 300 \
  --environment Variables={\
YOUTUBE_API_KEY=your_key_here,\
DYNAMODB_TABLE=celebrity-database,\
AWS_REGION=us-east-1,\
LOG_LEVEL=INFO\
}
```

### Test in AWS

```bash
# Invoke the function
aws lambda invoke \
  --function-name scraper-youtube \
  --payload '{}' \
  response.json

# View results
cat response.json | jq '.'\

# Check key statistics
cat response.json | jq '.success, .not_found, .errors'
```

---

## 📊 What to Expect

### Success Response
```json
{
  "total": 100,
  "success": 85,
  "errors": 3,
  "not_found": 12,
  "details": [
    {
      "celebrity_id": "celeb_001",
      "name": "Leonardo DiCaprio",
      "status": "success",
      "subscribers": "1000000",
      "channel_id": "UC1234567890"
    },
    {
      "celebrity_id": "celeb_002",
      "name": "Unknown Celebrity",
      "status": "not_found",
      "error": "Channel not found"
    },
    {
      "celebrity_id": "celeb_003",
      "name": "Celebrity Name",
      "status": "error",
      "error": "Timeout error"
    }
  ]
}
```

### Key Metrics
- **success**: Celebrities with YouTube channels found and data collected
- **not_found**: Celebrities with no YouTube channel
- **errors**: Processing errors (timeouts, quota, etc.)
- **subscribers**: Subscriber count from YouTube (may be "hidden" for private channels)

---

## 🔍 Monitor Execution

```bash
# View Lambda logs in real-time
aws logs tail /aws/lambda/scraper-youtube --follow

# Look for:
# - "Searching YouTube for channel: [name]"
# - "Found channel: [ID]"
# - "Successfully fetched channel data"
# - "Successfully wrote entry for [name]"
# - "YouTube scraper completed. Success: X/Y"
```

---

## 🎯 Testing Phases

### Phase 2.4A: API Key Setup
Manual steps (already done if you followed Step 1)
- ✓ YouTube API enabled in Google Cloud Console
- ✓ API key created and copied to .env
- ✓ .env file configured

### Phase 2.4B: Offline Test (Single Celebrity)
```bash
python3 lambda_function.py --test-mode
```
Expected: All validation checks pass

### Phase 2.4C: Online Test (Local)
Requires:
- AWS credentials configured locally
- DynamoDB table with at least one celebrity
- Valid YouTube API key in .env

```bash
# Run tests
python3 -m pytest test_scraper.py -v

# Expected: All 13 tests pass
```

### Phase 2.4D: DynamoDB Verification
After first Lambda invocation, verify data:
```bash
aws dynamodb query --table-name celebrity-database \
  --key-condition-expression "celebrity_id = :id AND begins_with(source_type#timestamp, :prefix)" \
  --expression-attribute-values \
    '{":id":{"S":"celeb_001"},":prefix":{"S":"youtube#"}}' \
  --region us-east-1
```

Expected fields in result:
- ✓ id: UUID string
- ✓ name: Celebrity name
- ✓ raw_text: Valid JSON from YouTube API
- ✓ source: "https://www.googleapis.com/youtube/v3/channels"
- ✓ timestamp: ISO 8601 format with Z suffix
- ✓ metadata.channel_id: YouTube channel ID

### Phase 2.4E: Full Deployment
```bash
# Process all celebrities
aws lambda invoke \
  --function-name scraper-youtube \
  --payload '{}' \
  response.json

# Check count of YouTube entries in DynamoDB
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names '{"#key":"source_type#timestamp"}' \
  --expression-attribute-values '{":source":{"S":"youtube#"}}' \
  --select COUNT \
  --region us-east-1
```

Expected: 80-100 YouTube entries (most celebrities have channels)

---

## ⚙️ Configuration Options

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| YOUTUBE_API_KEY | (required) | API key for YouTube Data API v3 |
| DYNAMODB_TABLE | celebrity-database | DynamoDB table name |
| AWS_REGION | us-east-1 | AWS region |
| YOUTUBE_TIMEOUT | 10 | Request timeout in seconds |
| YOUTUBE_MAX_RETRIES | 3 | Max retry attempts |
| YOUTUBE_BACKOFF_BASE | 1 | Initial backoff delay in seconds |
| LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Tuning Parameters

**For High Quota Usage:**
```bash
# Increase timeout for slow networks
YOUTUBE_TIMEOUT=15

# More retry attempts for flaky connections
YOUTUBE_MAX_RETRIES=5
```

**For Cost Optimization:**
```bash
# Reduce timeout to fail faster
YOUTUBE_TIMEOUT=5

# Fewer retry attempts
YOUTUBE_MAX_RETRIES=1
```

---

## 🆘 Troubleshooting

### "Invalid API Key" error
**Fix:** Check .env file has correct key format
```bash
grep "YOUTUBE_API_KEY" .env
```
Key should start with "AIza" and be 39+ characters.

### "Quota exceeded (403)" error
**Expected:** Free tier has 10,000 units/day
**Fix:** Wait 24 hours for quota reset
**Alternative:** Use multiple API keys with key rotation (similar to Stage 2.1)

### "Cannot connect to DynamoDB"
**Fix:** Verify Lambda execution role has permissions
```bash
# Role needs these permissions:
# dynamodb:Scan
# dynamodb:PutItem
# On: arn:aws:dynamodb:*:*:table/celebrity-database
```

### "Table does not exist"
**Fix:** Create the table first
```bash
aws dynamodb create-table \
  --table-name celebrity-database \
  --attribute-definitions AttributeName=celebrity_id,AttributeType=S \
                           AttributeName=source_type#timestamp,AttributeType=S \
  --key-schema AttributeName=celebrity_id,KeyType=HASH \
                AttributeName=source_type#timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

### Tests failing locally
**Fix:** Install dependencies
```bash
pip install -r requirements.txt
pip install pytest  # For running tests with pytest
```

### "No celebrities found in DynamoDB"
**Fix:** First, seed DynamoDB with celebrity records
```bash
# Your existing pipeline should have created these
# Check if celebrities table has data:
aws dynamodb scan --table-name celebrity-database --select COUNT
```

---

## 🔐 Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] Never commit `.env` file
- [ ] API key is not logged in CloudWatch
- [ ] Use IAM roles (not hardcoded credentials)
- [ ] Enable CloudTrail for audit logging
- [ ] Restrict Lambda execution role to minimum permissions
- [ ] Rotate API keys if exposed

---

## 📚 Documentation Reference

| Document | Content | Purpose |
|----------|---------|---------|
| **README.md** | YouTube API reference | API documentation |
| **IMPLEMENTATION_SUMMARY.md** | Architecture & code details | Deep technical reference |
| **QUICK_START.md** | This file - setup & testing | Fast ramp-up |

---

## 📊 Performance Summary

### Capacity
- **YouTube Quota**: 10,000 units/day (free tier)
- **Per Celebrity**: ~101 units (100 for search, 1 for fetch)
- **Capacity**: ~99 celebrities/day with free tier
- **Your Dataset**: 100 celebrities = 1-2 days of quota

### Execution Time
- 100 celebrities: 3-5 minutes
- Average per celebrity: 2-3 seconds
- Network latency: 300-500ms per request

### Cost
- **Before**: $0 (using free YouTube API tier)
- **After**: $0 (same tier)
- **Savings**: Zero cost to scrape YouTube data!

---

## ✅ Verification Checklist

Before considering Stage 2.4 complete:

- [ ] `.env` file created with valid API key
- [ ] `python3 lambda_function.py --test-mode` passes
- [ ] `python3 -m pytest test_scraper.py -v` shows 13 tests passing
- [ ] Lambda function created in AWS
- [ ] Environment variables configured in Lambda
- [ ] Single Lambda invocation succeeds
- [ ] CloudWatch logs show "YouTube scraper completed"
- [ ] DynamoDB contains entries with `youtube#` prefix
- [ ] Success count is reasonable (60-90 out of 100)
- [ ] No API keys exposed in logs

---

## 🚀 Next Steps

1. **Phase 2.4 Testing**: Complete all 5 testing phases above
2. **Schedule Execution**: Set up EventBridge to run daily
3. **Monitor Performance**: Track quota usage and success rates
4. **Consider Enhancements**:
   - Add key rotation for YouTube (like Stage 2.1)
   - Implement playlist scraping
   - Track subscriber count changes over time
5. **Move to Stage 2.2**: Instagram scraper (more complex)

---

## 🎓 Key Concepts

### First-Hand Data
All raw API responses stored as-is in DynamoDB under `raw_text` field. This allows future processing without re-scraping.

### Graceful Degradation
If one celebrity fails, the scraper continues with others. Failures are tracked separately from not-found results.

### Exponential Backoff
Failed requests are retried with increasing delays (1s, 2s, 4s) to handle transient failures without overwhelming the API.

### DynamoDB Optimization
Using composite sort key (`source_type#timestamp`) allows querying by source and timestamp efficiently.

---

## 📞 Support

For issues or questions:
1. Check the IMPLEMENTATION_SUMMARY.md for detailed information
2. Review CloudWatch logs for error details
3. Verify environment variables are set correctly
4. Test with `python3 -m pytest test_scraper.py -v`

---

**Version**: 1.0
**Last Updated**: November 7, 2025
**Status**: ✅ Production Ready

**Ready to deploy! Follow the steps above and you'll be collecting YouTube data in minutes.** 🎉
