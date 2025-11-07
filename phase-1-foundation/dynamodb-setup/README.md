# DynamoDB Setup

## Overview
Create and configure the central DynamoDB table: `celebrity-database`

## Configuration
- **Table Name**: celebrity-database
- **Partition Key**: celebrity_id (String)
- **Sort Key**: source_type#timestamp (String)
- **Billing Mode**: ON_DEMAND (pay per request)
- **Streams**: Enabled (NEW_AND_OLD_IMAGES)

## Files
- `table-definition.json`: CloudFormation/Raw DynamoDB schema
- `gsi-indexes.json`: Global Secondary Indexes configuration
- `create-table.py`: Python script to create table
- `test-operations.py`: Validate table creation

## Tasks
- [ ] Define table schema
- [ ] Create CloudFormation template
- [ ] Create table via AWS CLI
- [ ] Verify table created successfully
- [ ] Enable DynamoDB Streams
- [ ] Create GSI indexes
- [ ] Test read/write operations

## Testing
See `test-operations.py` for validation procedures
