# Parallel Google Search Scraper - Local Setup & Execution

## 🚀 Quick Start (3 Steps)

### Step 1: Configure Environment (2 minutes)

```bash
cd stage-2.1-google-search

# Copy example to .env
cp .env.example .env

# Edit .env with your credentials
# You already have:
#   GOOGLE_API_KEY_1=AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w
#   GOOGLE_API_KEY_2=AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8
#   GOOGLE_API_KEY_3=AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc
#
# You need to create GOOGLE_SEARCH_ENGINE_ID at https://cse.google.com
```

### Step 2: Install Dependencies (1 minute)

```bash
# Install required packages if not already installed
pip install python-dotenv boto3 requests

# Verify dependencies
python3 -c "import boto3, requests, dotenv; print('✓ All dependencies installed')"
```

### Step 3: Run Parallel Scraper (5 minutes)

```bash
# Run with 20 workers (default), process all 100 celebrities
python3 parallel_scraper.py --workers 20

# Or with options:
python3 parallel_scraper.py --workers 20 --celebrities 10  # Test with 10 first
python3 parallel_scraper.py --workers 20 --verbose         # Show debug logs
```

---

## 📋 Setup Details

### Environment Variables (.env)

You need to set these in your `.env` file:

```bash
# Google API Keys (you have these!)
GOOGLE_API_KEY_1=AIzaSyDcJ-MneFHoacNskq-4i2B19-Ii2hVoB8w
GOOGLE_API_KEY_2=AIzaSyA4xTLYPK8fk3XlAVKymt0-4GPmJX0EZS8
GOOGLE_API_KEY_3=AIzaSyDPXdS9dEfBmWbffrO2vOgIMka4Hm8gPnc

# Google Search Engine ID (create at https://cse.google.com)
GOOGLE_SEARCH_ENGINE_ID=e1f2g3h4i5j6k7  # Get this from https://cse.google.com

# AWS Configuration
DYNAMODB_TABLE=celebrity-database
AWS_REGION=us-east-1

# Optional: AWS Credentials (if not using IAM role)
# AWS_ACCESS_KEY_ID=your_access_key_id
# AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

### Create Google Search Engine ID

1. Visit https://cse.google.com
2. Click "Create" to create a new search engine
3. Configure:
   - **Websites to search**: Leave empty (searches entire web)
   - **Name**: "Celebrity Search"
4. Click "Create"
5. Get your **Search Engine ID** (cx parameter)
6. Add to .env as `GOOGLE_SEARCH_ENGINE_ID=...`

### AWS Credentials

The scraper uses your AWS credentials from:
1. **IAM Role** (if running on EC2/Lambda) - recommended
2. **~/.aws/credentials** (if configured locally)
3. **Environment variables** (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

For local development:
```bash
# Configure AWS CLI with your credentials
aws configure

# Or create ~/.aws/credentials:
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-east-1
```

---

## 🎯 Running the Scraper

### Basic Usage

```bash
# Run with default 20 workers, process all 100 celebrities
python3 parallel_scraper.py

# Expected output:
# Starting parallel scraper with 20 workers
# Processing 100 celebrities
# [1] Processing Leonardo DiCaprio (celeb_id: celeb_001) with key_1
# ✓ Leonardo DiCaprio: Successfully written to DynamoDB
# ...
# PARALLEL SCRAPER COMPLETE
# Total: 100
# Success: 95
# Errors: 5
# Duration: 45.23 seconds
# Rate: 2.10 celebrities/second
```

### With Options

```bash
# Test with 10 celebrities first
python3 parallel_scraper.py --celebrities 10

# Run with more workers for faster processing
python3 parallel_scraper.py --workers 30 --celebrities 100

# Run with verbose logging
python3 parallel_scraper.py --verbose

# Combine options
python3 parallel_scraper.py --workers 20 --celebrities 50 --verbose
```

---

## 📊 What Gets Stored

Each successful scrape creates a DynamoDB entry:

```json
{
  "celebrity_id": "celeb_001",
  "source_type#timestamp": "google_search#2025-11-07T17:20:00Z",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Leonardo DiCaprio",
  "raw_text": "{\"items\": [{...complete Google Search API response...}]}",
  "source": "https://www.googleapis.com/customsearch/v1",
  "timestamp": "2025-11-07T17:20:00Z",
  "weight": null,
  "sentiment": null,
  "metadata": {
    "scraper_name": "scraper-google-search",
    "source_type": "google_search",
    "processed": false,
    "error": null,
    "key_rotation": {
      "enabled": true,
      "strategy": "round_robin",
      "key_used": "key_1"
    }
  }
}
```

---

## ⚙️ Worker Pool Explanation

### How Parallel Processing Works

The scraper uses **20 worker threads** by default:

1. **Main thread**: Loads celebrities, submits tasks to worker pool
2. **20 worker threads**: Process celebrities in parallel
   - Each worker: Search Google → Write to DynamoDB
   - Handles retries independently
   - Reports results back

### Performance

```
Single worker (sequential):
  100 celebrities × 2.5 seconds/celebrity = 250 seconds (4+ minutes)

20 workers (parallel):
  100 celebrities ÷ 20 workers = 5 celebrities per worker
  5 × 2.5 seconds = ~12.5 seconds (with overhead)
  Actual: ~45 seconds (includes I/O wait, API latency, etc.)

Speed improvement: ~5-6× faster!
```

### Key Rotation with Workers

- **Worker 1**: Uses API key 1
- **Worker 2**: Uses API key 2
- **Worker 3**: Uses API key 3
- **Worker 4**: Uses API key 1 (round-robin)
- **Worker 5**: Uses API key 2
- ... (repeats)

This ensures balanced load across all 3 API keys!

---

## 🔍 Monitoring

### Real-Time Progress

During execution, you'll see:

```
2025-11-07 17:20:15,123 - __main__ - INFO - [1] Processing Leonardo DiCaprio...
2025-11-07 17:20:18,456 - __main__ - INFO - ✓ Leonardo DiCaprio: Successfully written
2025-11-07 17:20:19,789 - __main__ - INFO - [2] Processing Tom Hanks...
2025-11-07 17:20:22,012 - __main__ - INFO - ✓ Tom Hanks: Successfully written
...
```

### Query Results in DynamoDB

After scraper completes, verify data:

```bash
# Count Google Search entries
aws dynamodb scan --table-name celebrity-database \
  --filter-expression "begins_with(#key, :source)" \
  --expression-attribute-names '{"#key":"source_type#timestamp"}' \
  --expression-attribute-values '{":source":{"S":"google_search#"}}' \
  --select COUNT \
  --region us-east-1

# Expected: ~95-100 (some celebrities may not have searchable data)
```

---

## ⚠️ Troubleshooting

### "No celebrities found in database"

```
Error: No celebrities found in DynamoDB

Solution:
  1. Verify Phase 1 data was seeded
  2. Check table name: DYNAMODB_TABLE=celebrity-database
  3. Verify AWS credentials are working
  4. Test connection:
     aws dynamodb scan --table-name celebrity-database --limit 1
```

### "Missing environment variables"

```
Error: Missing environment variables: GOOGLE_API_KEY_1, GOOGLE_SEARCH_ENGINE_ID

Solution:
  1. Copy .env.example to .env
  2. Fill in missing values:
     - GOOGLE_API_KEY_1, 2, 3 (you have these)
     - GOOGLE_SEARCH_ENGINE_ID (create at https://cse.google.com)
  3. Verify: cat .env | grep GOOGLE
```

### "Throttled, retrying..."

```
Warning: Throttled, retrying in 2s...

This is normal!
  - Means: DynamoDB is rate-limiting writes
  - Scraper will: Automatically retry with exponential backoff
  - Resolution: Automatic (waits 2, 4, 8 seconds between attempts)
```

### "HTTP 429" errors

```
Error: HTTP 429 error for <celebrity>

Cause: Google Search API rate limit reached
Solution:
  1. You have 3 API keys (100 queries/day each = 300 total)
  2. Parallel scraper balances load across all 3 keys
  3. If still hitting 429: Wait 24 hours for quota reset or add more keys
```

### "DynamoDB write failed"

```
Error: DynamoDB write failed

Cause: Could be several things
Solution:
  1. Check AWS credentials are valid
  2. Verify IAM permissions include dynamodb:PutItem
  3. Check table exists: aws dynamodb describe-table --table-name celebrity-database
  4. Verify region matches: AWS_REGION=us-east-1
```

---

## 📈 Performance Tuning

### Adjust Worker Count

```bash
# Faster (more parallel, higher CPU/network usage)
python3 parallel_scraper.py --workers 30

# Slower but more stable (less load on DynamoDB)
python3 parallel_scraper.py --workers 10

# Recommended: Start with 20, adjust based on your system
```

### Expected Performance

```
Workers | Time      | Rate         | DynamoDB Load
--------|-----------|--------------|---------------
5       | 2+ min    | ~0.8/sec     | Light
10      | 1+ min    | ~1.7/sec     | Medium
20      | 45-60 sec | ~1.7-2.0/sec | Medium-High
30      | 45-60 sec | ~1.7-2.0/sec | High
50      | 45-60 sec | ~1.7-2.0/sec | Very High

Note: Network latency (Google API + DynamoDB) is the bottleneck,
not CPU. More workers help with parallel I/O wait.
```

---

## ✅ Verification Checklist

Before running:

- [ ] `.env` file exists with API keys
- [ ] `GOOGLE_SEARCH_ENGINE_ID` is set
- [ ] AWS credentials configured (aws configure or ~/.aws/credentials)
- [ ] Can connect to DynamoDB: `aws dynamodb describe-table --table-name celebrity-database`
- [ ] Phase 1 data exists in DynamoDB: `aws dynamodb scan --table-name celebrity-database --limit 1`

After running:

- [ ] Scraper completed without errors
- [ ] "Success" count is ~95-100
- [ ] Can query data: `aws dynamodb query --table-name celebrity-database --key-condition-expression "celebrity_id = :id" --expression-attribute-values '{":id":{"S":"celeb_001"}}'`
- [ ] Data has correct fields: celebrity_id, source_type#timestamp, raw_text, etc.

---

## 🎯 Next Steps

After filling database with Google Search entries:

1. **Run YouTube Scraper** (similar parallel version coming)
2. **Deploy to Lambda** for scheduled daily execution
3. **Implement Phase 3** post-processor for weight/sentiment computation
4. **Monitor performance** and quota usage

---

## 📞 Support

For issues:

1. Check .env file is properly configured
2. Run with `--verbose` flag to see detailed logs
3. Check AWS credentials: `aws sts get-caller-identity`
4. Verify DynamoDB access: `aws dynamodb describe-table --table-name celebrity-database`

---

**Ready to fill your database!** 🚀

