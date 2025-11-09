# Installation & Setup

Complete step-by-step guide to get the tool running.

## Prerequisites Check

Before starting, verify you have:

```bash
# 1. Check Python 3 is installed
python3 --version
# Should show: Python 3.7 or higher

# 2. Check AWS CLI is configured
aws sts get-caller-identity
# Should show your AWS account info

# 3. Check table exists
aws dynamodb list-tables | grep celebrity-database
# Should show: celebrity-database

# 4. Check table has data
aws dynamodb scan --table-name celebrity-database --select COUNT
# Should show: Count > 0
```

If any check fails, see "Troubleshooting Prerequisites" below.

## Installation Method 1: Automatic (Recommended)

### Step 1: Navigate to Tool Directory

```bash
cd phase-1-foundation/local-ui-tool
```

### Step 2: Run the Setup Script

```bash
./run.sh
```

The script will:
1. ✓ Check Python 3 is installed
2. ✓ Create virtual environment
3. ✓ Install dependencies (Flask, boto3)
4. ✓ Verify AWS credentials
5. ✓ Start the server

### Step 3: Open in Browser

When you see:
```
============================================================
LOCAL UI TOOL - DynamoDB Viewer
============================================================
Server running at: http://localhost:5000
============================================================
```

Open your browser to: **http://localhost:5000**

**Done!** You're now running the tool.

---

## Installation Method 2: Manual

If the script doesn't work, do it manually:

### Step 1: Create Virtual Environment

```bash
cd phase-1-foundation/local-ui-tool
python3 -m venv venv
```

### Step 2: Activate Virtual Environment

**On Mac/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Expected output:
```
Successfully installed Flask-2.3.3
Successfully installed boto3-1.28.85
Successfully installed flask-cors-4.0.0
...
```

### Step 4: Verify AWS Configuration

```bash
aws sts get-caller-identity
```

Should show your AWS account.

### Step 5: Run the Server

```bash
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

### Step 6: Open Browser

Go to: **http://localhost:5000**

---

## Troubleshooting Prerequisites

### Problem: Python 3 Not Found

```bash
python3 --version
# Shows: command not found
```

**Solution**:
- Install Python 3.7+ from python.org
- Or use homebrew: `brew install python3`
- Or use package manager: `apt-get install python3`

### Problem: AWS Credentials Not Found

```bash
aws sts get-caller-identity
# Shows: Unable to locate credentials
```

**Solution 1 - Use AWS Configure** (recommended):
```bash
aws configure
# Enter:
# AWS Access Key ID: [your-key]
# AWS Secret Access Key: [your-secret]
# Default region: us-east-1
# Default output format: json
```

**Solution 2 - Set Environment Variables**:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

**Solution 3 - Use AWS Profile**:
```bash
export AWS_PROFILE=your_profile_name
aws sts get-caller-identity
```

### Problem: DynamoDB Table Not Found

```bash
aws dynamodb list-tables
# Shows: celebrity-database is missing
```

**Solution**: Create the table first:
```bash
cd ../dynamodb-setup
python3 create-table.py --region us-east-1
```

### Problem: Table Has No Data

```bash
aws dynamodb scan --table-name celebrity-database --select COUNT
# Shows: Count = 0
```

**Solution**: Seed the database:
```bash
cd ../celebrity-seed
python3 seed-database.py --region us-east-1
```

---

## Troubleshooting Installation

### Problem: "pip: command not found"

```bash
pip install -r requirements.txt
# Shows: pip: command not found
```

**Solution**: Use python3 -m pip:
```bash
python3 -m pip install -r requirements.txt
```

### Problem: "Permission denied" on run.sh

```bash
./run.sh
# Shows: Permission denied
```

**Solution**: Make it executable:
```bash
chmod +x run.sh
./run.sh
```

### Problem: "ModuleNotFoundError" when running

```bash
python3 app.py
# Shows: ModuleNotFoundError: No module named 'flask'
```

**Solution**: Activate virtual environment:
```bash
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate     # On Windows

# Then run:
python3 app.py
```

### Problem: "Port 5000 already in use"

```bash
python3 app.py
# Shows: OSError: [Errno 48] Address already in use
```

**Solution 1**: Kill the process using port 5000:
```bash
# On Mac/Linux:
lsof -i :5000
kill -9 <PID>

# On Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Solution 2**: Use a different port:
Edit `app.py` line 202:
```python
app.run(debug=True, host='localhost', port=5001)  # Changed to 5001
```

Then run:
```bash
python3 app.py
# Now open http://localhost:5001
```

---

## Verifying Installation

Once the server is running, verify it works:

### Check 1: Open Browser
```
http://localhost:5000
```

You should see the DynamoDB Data Viewer page with:
- Header showing "Connected ✓"
- Overview tab with statistics
- Celebrities table
- Search box

### Check 2: Verify Connection
In the header, check for:
```
● Connected to DynamoDB ✓
Table: celebrity-database
```

Green dot + "Connected" = Success!

### Check 3: Check Data Loads
Go to Celebrities tab:
- Should see list of celebrities
- Should show 100+ rows
- Search should work

### Check 4: Run Validation
Go to Validation tab:
1. Click "Validate All"
2. Should see summary:
   ```
   Total: 100
   Passed: 98
   Warnings: 2
   ```

3. If all are PASS, installation is complete!

---

## Quick Start Commands

After installation, use these commands:

### Start the Server
```bash
cd phase-1-foundation/local-ui-tool
./run.sh
# or
source venv/bin/activate
python3 app.py
```

### Stop the Server
```
Press Ctrl+C in the terminal
```

### Reset Virtual Environment
```bash
rm -rf venv
./run.sh
```

### Check Dependencies
```bash
pip list
# Should show Flask, boto3, flask-cors
```

### Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.7 | 3.9+ |
| RAM | 256 MB | 1 GB |
| Disk | 500 MB | 1 GB |
| Network | AWS connection required | Good connection |
| OS | Mac, Linux, Windows | Any with Python 3 |

## File Locations

After installation, you'll have:

```
local-ui-tool/
├── venv/                  ← Virtual environment (created)
│   ├── bin/               ← Python executables
│   └── lib/               ← Installed packages
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── app.js
├── app.py
├── requirements.txt
├── run.sh
└── Documentation...
```

## Next Steps

1. **Start the server**: `./run.sh`
2. **Open browser**: http://localhost:5000
3. **Check Overview**: Verify you see statistics
4. **Browse celebrities**: See your data
5. **Run validation**: Check everything is correct
6. **Deploy Phase 2**: Return here to verify scraped data

---

**Installation Complete!**

You now have a working DynamoDB data viewer.

See **QUICKSTART.md** for next steps.
