# Celebrity Seed Data

## Overview
Initialize DynamoDB with 100 celebrities for baseline data.

## Files
- `celebrities.json`: Master list of 100 celebrities
- `seed-database.py`: Script to bulk insert celebrities
- `validate-seed.py`: Verify seed data was inserted correctly

## Celebrity Data Structure
```json
{
  "celebrity_id": "celeb_001",
  "name": "Leonardo DiCaprio",
  "birth_date": "1974-11-11",
  "nationality": "American",
  "occupation": ["Actor", "Producer"]
}
```

## Tasks
- [ ] Create celebrities.json with 100 celebrities
- [ ] Run seed-database.py to insert data
- [ ] Verify all 100 records inserted
- [ ] Validate data integrity
- [ ] Check for duplicates

## Next Steps
After seeding completes, move to phase-2-scrapers to collect data for each celebrity.
