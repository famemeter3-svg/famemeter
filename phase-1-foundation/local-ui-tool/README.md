# Local UI Tool - DynamoDB Data Viewer

A simple localhost web interface to visualize and validate your DynamoDB celebrity database. Perfect for checking data schema and entry correctness before deploying scrapers.

## Features

✅ **View All Celebrities** - List all celebrities with metadata and source count
✅ **Detailed View** - See complete entry for each celebrity with all scraped data
✅ **Data Validation** - Validate individual celebrities or entire database
✅ **Schema Inspector** - View table schema, GSI, and stream configuration
✅ **Statistics** - Database stats including item count and sources
✅ **Search** - Filter celebrities by name or ID
✅ **Raw Data Inspector** - View complete JSON/text from scrapers

## Quick Start

### 1. Install Dependencies

```bash
cd phase-1-foundation/local-ui-tool
pip3 install -r requirements.txt
```

### 2. Configure AWS

Make sure your AWS credentials are configured:

```bash
# Check if configured
aws sts get-caller-identity

# If not, configure
aws configure
# or
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### 3. Run the Server

```bash
cd phase-1-foundation/local-ui-tool
python3 app.py
```

You should see:
```
============================================================
LOCAL UI TOOL - DynamoDB Viewer
============================================================
Table: celebrity-database
Status: Connected ✓

Server running at: http://localhost:5000
============================================================
```

### 4. Open Browser

Navigate to: **http://localhost:5000**

## Tabs Overview

### 📈 Overview
- Database statistics (total items, celebrities, sources)
- Connection status
- Data source breakdown

### 👥 Celebrities
- List of all celebrities with metadata
- Search/filter by name
- Quick view button for each celebrity
- Shows which data sources have been scraped

### ✅ Validation
- Validate all celebrities at once
- Check for required fields
- Identify missing data
- Reports on warnings and errors

### 📋 Schema
- Table name and status
- Partition key and sort key
- Global Secondary Indexes
- Billing mode and stream configuration

## Using the Tool

### Check Connection
The header will show connection status. If red, verify AWS credentials and table exists.

### View Celebrity Details
Click "View" on any row to see:
- Full metadata (name, birth date, nationality, occupation)
- All data sources with timestamps
- Raw data previews
- Weight and sentiment scores (if computed)

### Validate Data Schema
Click "Validate All" to check:
- ✅ All celebrities have metadata
- ✅ Required fields are present
- ✅ Raw text data is stored
- ✅ Source URLs are correct
- ⚠️ Missing optional fields

The validation shows:
- **Errors** (red) - Schema violations that need fixing
- **Warnings** (orange) - Missing optional data

### Check Raw Data
In celebrity detail view, each data source shows a preview of raw_text. Click "View Full Raw Text" to see the complete API response (useful for debugging scrapers).

## API Endpoints

If you want to use the API directly (e.g., for custom scripts):

```bash
# Get all celebrities
curl http://localhost:5000/api/celebrities

# Get specific celebrity
curl http://localhost:5000/api/celebrity/celeb_001

# Get database stats
curl http://localhost:5000/api/stats

# Get table schema
curl http://localhost:5000/api/schema

# Validate specific celebrity
curl http://localhost:5000/api/validate/celebrity/celeb_001

# Validate all
curl http://localhost:5000/api/validate/all

# Get raw data for a source
curl http://localhost:5000/api/raw/celeb_001/google_search
```

## Troubleshooting

### "DynamoDB not connected"
- Check AWS credentials: `aws sts get-caller-identity`
- Verify table exists: `aws dynamodb list-tables`
- Check region: `aws configure list`

### "Celebrity not found"
- Run seed script first: `cd ../celebrity-seed && python3 seed-database.py`
- Check table has data: `aws dynamodb scan --table-name celebrity-database --select COUNT`

### Port 5000 already in use
Change port in `app.py` line: `app.run(..., port=5001)` or kill the process:
```bash
lsof -i :5000
kill -9 <PID>
```

### Data is empty but table exists
Make sure celebrities were seeded:
```bash
cd ../celebrity-seed
python3 seed-database.py --region us-east-1
```

## Understanding the Data Schema

### Metadata Record (Seed Data)
```
celebrity_id: celeb_001
source_type#timestamp: metadata#2025-01-01T00:00:00Z
name: Leonardo DiCaprio
birth_date: 1974-11-11
nationality: American
occupation: ["Actor", "Producer"]
```

### Scraper Entry (Created by Phase 2)
```
celebrity_id: celeb_001
source_type#timestamp: google_search#2025-11-07T10:30:45Z
id: unique-entry-id
name: Leonardo DiCaprio (from source)
raw_text: {complete API response}
source: https://api.googleapis.com/customsearch/v1
timestamp: 2025-11-07T10:30:45Z
weight: 0.85 (computed by Phase 3)
sentiment: positive (computed by Phase 3)
```

## What to Check

When verifying your data setup, use this checklist:

- [ ] Connection shows "Connected ✓"
- [ ] Overview shows "Celebrities with data" > 0
- [ ] Can search and find celebrities by name
- [ ] Click View and see metadata fields
- [ ] (After scraping) See data sources in Detail view
- [ ] Validation shows all celebrities as PASS (or expected warnings)
- [ ] Raw data preview shows actual API responses

## Next Steps

After verifying the database:

1. **Run scrapers** - Deploy Phase 2 scrapers
2. **Check data** - Use this UI to verify scraped data looks correct
3. **Run validation** - Ensure all first-hand data fields are present
4. **Check sentiment** - After Phase 3, verify weight and sentiment are computed
5. **Deploy API** - Move to Phase 5 when satisfied with data quality

## Development

To modify the UI:

- **Backend logic**: Edit `app.py`
- **Styling**: Edit `static/style.css`
- **Frontend interactivity**: Edit `static/app.js`
- **HTML structure**: Edit `templates/index.html`

Changes will reflect immediately in the browser (with debug=True enabled).

---

**Created**: November 9, 2025
**Purpose**: Verify DynamoDB data schema and entries during development
