# Quick Start - Local UI Tool

Get the data viewer running in 2 minutes.

## Option 1: Using the Run Script (Recommended)

```bash
cd phase-1-foundation/local-ui-tool
./run.sh
```

The script will:
1. Check for Python 3
2. Create a virtual environment
3. Install dependencies
4. Verify AWS configuration
5. Start the server

Then open: **http://localhost:5000**

## Option 2: Manual Setup

```bash
# Navigate to tool directory
cd phase-1-foundation/local-ui-tool

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python3 app.py
```

Open: **http://localhost:5000**

## Prerequisites

- **Python 3.7+** - Check with `python3 --version`
- **AWS credentials configured** - Check with `aws sts get-caller-identity`
- **DynamoDB table created** - Run Phase 1 setup first if not done
- **Celebrities seeded** - Run `cd ../celebrity-seed && python3 seed-database.py`

## Verify Setup

Before running the UI tool, make sure:

```bash
# 1. AWS credentials work
aws sts get-caller-identity

# 2. Table exists
aws dynamodb list-tables | grep celebrity-database

# 3. Has data
aws dynamodb scan --table-name celebrity-database --select COUNT
# Should show Count > 0
```

If any of these fail:
1. Configure AWS: `aws configure`
2. Create table: `cd ../dynamodb-setup && python3 create-table.py`
3. Seed data: `cd ../celebrity-seed && python3 seed-database.py`

## First Steps

1. **Check Overview** - Verify you see statistics and "Connected ✓"
2. **View Celebrities** - Click through a few celebrities to see metadata
3. **Run Validation** - Click "Validate All" to check data integrity
4. **Inspect Raw Data** - Open a celebrity and check scraped data format

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Port 5000 in use. Try port 5001 in app.py |
| "Table not found" | Run DynamoDB setup first |
| "No celebrities found" | Run celebrity seed script |
| "AWS credentials error" | Run `aws configure` |

## Next Steps

After verifying the database:
- Deploy Phase 2 scrapers
- Return to this UI to check scraped data
- Run validation after each scraper deployment
- Verify weight/sentiment after Phase 3

---

**Ready?** Run `./run.sh` now!
