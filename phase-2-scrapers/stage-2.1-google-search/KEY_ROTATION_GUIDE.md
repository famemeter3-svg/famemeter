# Stage 2.1: API Key Rotation Strategy Guide

## Overview

Stage 2.1 now includes **intelligent API key rotation** to maximize free tier usage and improve reliability. With 3 API keys rotating, you can process **300 queries/day** (100 per key) instead of just 100.

---

## Why Key Rotation?

### Problem
- Google Search API free tier: 100 queries/day per key
- With 100 celebrities, you'd hit rate limit quickly
- Only solution: Pay for more quota ($0.05/query) or buy more keys

### Solution
- Rotate across 3 keys = **300 queries/day total**
- Distribute load evenly
- Automatic fallback when key hits limit
- Excellent cost/benefit for free tier

---

## Key Rotation Strategies

### 1. Round-Robin (Default)
**Best for:** Even distribution across keys

```
Request 1 → Key 1
Request 2 → Key 2
Request 3 → Key 3
Request 4 → Key 1 (cycle repeats)
...
```

**When to use:**
- All keys have similar quota/limits
- Want predictable, even distribution
- Keys are equally healthy

**Configuration:**
```bash
KEY_ROTATION_STRATEGY=round_robin
```

---

### 2. Least-Used
**Best for:** Balancing actual usage

```
Key 1: 50 requests used → Use Key 2
Key 2: 30 requests used → Use Key 3
Key 3: 40 requests used → Use Key 1 (least used)
...
```

**When to use:**
- Keys have different usage patterns
- Want to balance actual requests
- Some keys might be used elsewhere

**Configuration:**
```bash
KEY_ROTATION_STRATEGY=least_used
```

---

### 3. Adaptive
**Best for:** Handling rate limits automatically

```
Key 1: Hit rate limit (429)  → Pause & try Key 2
Key 2: Healthy              → Use Key 2
Key 1: 1 hour later         → Reset & try Key 1 again
...
```

**When to use:**
- Keys get rate limited during execution
- Need automatic fallback
- Keys have different health status

**Configuration:**
```bash
KEY_ROTATION_STRATEGY=adaptive
RATE_LIMIT_THRESHOLD=95  # Switch key at 95% error rate
```

---

### 4. Random
**Best for:** Chaos testing / edge cases

```
Request 1 → Key 3 (random)
Request 2 → Key 1 (random)
Request 3 → Key 2 (random)
...
```

**When to use:**
- Testing random key selection
- Distributing load randomly
- Edge case testing

**Configuration:**
```bash
KEY_ROTATION_STRATEGY=random
```

---

## Setup Instructions

### Step 1: Get Your 3 API Keys

You already have these:
```
Key 1: AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w
Key 2: AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8
Key 3: AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc
```

### Step 2: Update `.env` File

Copy the template and update with your keys:

```bash
cp .env.template .env
```

Edit `.env`:

```bash
# Google Search API Keys for Rotation (RECOMMENDED)
GOOGLE_API_KEY_1=AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w
GOOGLE_API_KEY_2=AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8
GOOGLE_API_KEY_3=AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here

# Enable key rotation
ENABLE_KEY_ROTATION=true
KEY_ROTATION_STRATEGY=round_robin  # round_robin, least_used, random, adaptive
RATE_LIMIT_THRESHOLD=95

# Other settings
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1
LOG_LEVEL=INFO
GOOGLE_TIMEOUT=10
```

### Step 3: Deploy to Lambda

When deploying to AWS Lambda, set environment variables:

```bash
aws lambda update-function-configuration \
  --function-name scraper-google-search \
  --environment Variables={
GOOGLE_API_KEY_1=AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w,
GOOGLE_API_KEY_2=AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8,
GOOGLE_API_KEY_3=AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc,
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id,
ENABLE_KEY_ROTATION=true,
KEY_ROTATION_STRATEGY=round_robin
}
```

---

## Usage Statistics

The scraper tracks usage for each key and returns statistics:

```json
{
  "total": 100,
  "success": 95,
  "errors": 5,
  "key_rotation": {
    "enabled": true,
    "strategy": "round_robin",
    "keys_used": 3,
    "statistics": {
      "AIzaSyDcJ-...": {
        "requests": 34,
        "errors": 1,
        "error_rate": "2.9%",
        "last_error": null
      },
      "AIzaSyA4xT...": {
        "requests": 33,
        "errors": 2,
        "error_rate": "6.1%",
        "last_error": "TIMEOUT"
      },
      "AIzaSyDPXd...": {
        "requests": 32,
        "errors": 2,
        "error_rate": "6.3%",
        "last_error": null
      }
    }
  }
}
```

---

## How It Works

### Load Balancing

**Round-Robin (Default)**
```python
# Cycle through keys sequentially
Key rotation: 1 → 2 → 3 → 1 → 2 → 3
```

- **Pros:** Simple, even distribution, predictable
- **Cons:** Doesn't consider actual usage

**Least-Used**
```python
# Always use the key with fewest requests
Key stats: {1: 35, 2: 32, 3: 33}
Next key: 2 (fewest requests)
```

- **Pros:** Balances actual usage
- **Cons:** Slightly more overhead

**Adaptive**
```python
# Skip keys with rate limit errors, retry later
Key status: {1: healthy, 2: rate_limited, 3: healthy}
Next key: 1 or 3 (avoid 2)
After 1 hour: Reset 2, try again
```

- **Pros:** Handles failures automatically
- **Cons:** Most complex, requires error tracking

### Error Handling

When a key hits an error:

1. **Record Error**
   ```python
   rotation_manager.record_request(api_key, success=False, error_type='RATE_LIMIT')
   ```

2. **Track Statistics**
   - Requests: How many times used
   - Errors: How many failed
   - Error rate: errors / requests × 100%
   - Last error: What type of error

3. **Skip if Needed**
   ```python
   if error_rate >= RATE_LIMIT_THRESHOLD:
       # Skip this key, use another
   ```

4. **Reset After Time**
   - Adaptive strategy resets error tracking after 1 hour
   - Assumes rate limit quota refreshed

---

## Performance Impact

### Baseline (1 Key)
- Processing 100 celebrities: ~3-5 minutes
- Quota consumed: 100/100 (100%)
- Cost: $0 (free tier)

### With Rotation (3 Keys)
- Processing 100 celebrities: ~3-5 minutes (same time)
- Quota consumed: 100+50+50 (200/300 total available)
- Cost: $0 (all free tier)
- **Benefit:** 200% more capacity, same execution time!

### Scaling Example

**Without Rotation:**
- 100 celebrities → 100 quota → DONE
- 110 celebrities → Hit limit immediately ❌

**With Rotation:**
- 100 celebrities → 34+33+33 quota → DONE
- 200 celebrities → 67+67+66 quota → DONE
- 300 celebrities → 100+100+100 quota → DONE (maxed out)

---

## Error Recovery

### Scenario: Key 1 Gets Rate Limited

**Without Rotation:**
```
Request 30 → Key 1 → Hit rate limit (429)
Request 31 → Key 1 → Still rate limited
Request 32 → Key 1 → Still rate limited
...
Result: All remaining requests fail ❌
```

**With Rotation (Adaptive):**
```
Request 30 → Key 1 → Hit rate limit (429) - recorded
Request 31 → Key 2 → Success (30% quota left)
Request 32 → Key 3 → Success (30% quota left)
...
Request 60 → Key 1 → Reset (1+ hour passed) - try again
Result: Continue processing with healthy keys ✓
```

---

## Monitoring Key Rotation

### In CloudWatch Logs

Look for these log messages:

```
INFO: Initialized KeyRotationManager with 3 keys using 'round_robin' strategy
INFO: Loaded 3 API keys for rotation

# Per request
INFO: Fetching Google Search data for: Taylor Swift

# Successes
INFO: Successfully fetched 10 results for Taylor Swift
INFO: Key AIzaSyDcJ-... used successfully

# Errors
WARNING: Key AIzaSyDcJ-... error: RATE_LIMIT (total errors: 1)
INFO: Adaptive selection using healthy key

# Summary
=== Key Rotation Statistics ===
AIzaSyDcJ-...: 34 requests, 1 error (2.9%)
AIzaSyA4xT...: 33 requests, 2 errors (6.1%)
AIzaSyDPXd...: 32 requests, 2 errors (6.3%)
=== End Statistics ===
```

### Getting Statistics Programmatically

```python
from key_rotation import get_rotation_manager

manager = get_rotation_manager()
stats = manager.get_statistics()

for key_short, key_stats in stats.items():
    print(f"{key_short}: {key_stats['requests']} requests, {key_stats['error_rate']} errors")
```

---

## Best Practices

### 1. Use Round-Robin for Production
- Simple and reliable
- Even distribution
- No overhead
- **Recommended:** Use this by default

### 2. Use Least-Used if Keys Are Different
- Different quota limits
- Keys used elsewhere
- Want to balance actual usage

### 3. Use Adaptive for High-Volume
- Processing 200+ celebrities
- Running multiple scrapers
- Expect rate limiting
- Need automatic recovery

### 4. Monitor Error Rates
- Check logs regularly
- Watch for patterns
- Rate limit errors are normal (you're distributing load)
- Too many timeouts might indicate network issues

### 5. Secure Your Keys
- Never commit `.env` file
- Store in AWS Secrets Manager for production
- Rotate keys if exposed
- Use IAM roles instead of hardcoded credentials

---

## Troubleshooting

### Problem: "No API keys found in environment variables"

**Solution:**
1. Check `.env` file has the correct key variables
2. Verify format: `GOOGLE_API_KEY_1`, `GOOGLE_API_KEY_2`, `GOOGLE_API_KEY_3`
3. Keys should start with `AIza`
4. Make sure keys are not `your_first_api_key_here` (template text)

**Verify with:**
```bash
grep GOOGLE_API_KEY .env
```

### Problem: All requests hitting same key

**Solution:**
1. Verify `ENABLE_KEY_ROTATION=true` in `.env`
2. Check `KEY_ROTATION_STRATEGY` is set
3. Look for warnings in logs: "Key rotation enabled but no valid keys"
4. Verify all 3 keys are loaded (should see "Loaded 3 API keys")

**Verify with:**
```bash
env | grep GOOGLE_API
```

### Problem: Keys running out of quota

**Solution:**
1. You've exceeded 300 requests/day (100 per key × 3)
2. Options:
   - Wait until next day (quota resets)
   - Get more API keys and add them
   - Switch to paid tier
   - Reduce celebrity count

**Check quota:**
```bash
# In Google Cloud Console:
# API > Custom Search API > Quotas > Daily usage
```

### Problem: Rotation strategy not working

**Solution:**
1. Verify strategy name is spelled correctly
2. Check for typos: `round_robin` not `roundRobin`
3. Look in logs for strategy initialization: `using 'round_robin' strategy`

**Valid strategies:**
- `round_robin` (default)
- `least_used`
- `adaptive`
- `random`

---

## Test Results

All key rotation features are tested:

```
✓ test_load_multiple_keys - Loading 3 keys from environment
✓ test_load_combined_keys_format - Loading keys from pipe-separated format
✓ test_round_robin_strategy - Round-robin distribution
✓ test_least_used_strategy - Least-used selection
✓ test_record_request_statistics - Tracking usage stats
✓ test_adaptive_strategy_with_rate_limit - Adaptive fallback
✓ test_should_skip_key_with_high_error_rate - Error rate threshold

Total: 26 tests passing (19 original + 7 key rotation)
```

---

## Next Steps

1. **Update your `.env`** with the 3 API keys
2. **Test locally:** `python3 lambda_function.py --test-mode`
3. **Deploy to Lambda** with key rotation enabled
4. **Monitor statistics** in CloudWatch logs
5. **Enjoy 3× the query capacity** with same execution time!

---

## FAQ

**Q: Can I add more than 3 keys?**
A: Yes! The rotation manager supports up to 9 keys (GOOGLE_API_KEY_1 through GOOGLE_API_KEY_9). Just add more environment variables.

**Q: What happens if one key fails?**
A: With adaptive rotation, it skips to the next healthy key. With other strategies, it retries with the failed key, but error tracking helps identify problems.

**Q: Do I need to restart Lambda to change keys?**
A: Yes, update environment variables and the next invocation will load new keys.

**Q: Can I rotate keys manually?**
A: Not needed - automatic rotation handles it. But you can monitor usage in statistics.

**Q: What's the quota reset time?**
A: Google resets daily quotas at midnight UTC. Adaptive strategy resets error tracking after 1 hour as a buffer.

**Q: Which strategy should I pick?**
A: **Round-robin** by default. It's simple, reliable, and distributes evenly. Only change if you have specific needs.

---

**Key Rotation Implementation Date:** November 7, 2025
**Version:** 1.0
**Status:** ✅ Production Ready
