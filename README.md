# Celebrity Multi-Source Database System

A serverless, event-driven architecture for aggregating and analyzing celebrity data from multiple sources using AWS.

## 📋 Project Overview

This system collects, stores, and manages data for **100+ celebrities** with **100+ data points per person**, updated weekly through automated scrapers. Data is aggregated from 4+ sources (TMDb, Wikipedia, News API, Social Media) and enriched with sentiment analysis and confidence scoring.

**Key Features:**
- ✅ Fully automated weekly data collection
- ✅ Multi-source data aggregation (4+ sources)
- ✅ Sentiment analysis & confidence scoring
- ✅ REST API for data access
- ✅ React dashboard for visualization
- ✅ Cost-optimized serverless architecture (~$4-6/month)
- ✅ Full monitoring and backup strategy

## 🏗️ Architecture

```
EventBridge Scheduler (Weekly)
    ↓
Multiple Lambda Scrapers (Parallel)
    ├── TMDb API      (Movies, TV shows)
    ├── Wikipedia     (Biography, awards)
    ├── News API      (Recent articles)
    └── Social Media  (Follower counts)
    ↓
DynamoDB (Central Database)
    ↓
DynamoDB Streams
    ↓
Post-Processor Lambda
    ├── Calculate weight (confidence)
    └── Compute sentiment
    ↓
REST API (API Gateway + Lambda)
    ↓
React Dashboard (S3 + CloudFront)
```

## 📁 Project Structure

The project is organized into **8 independent phases**, each designed to be:
- **Self-contained** with full documentation
- **Independently testable** without other phases
- **Complete context** for AI agent work

```
V_central/
├── phase-1-foundation/        (Week 1-2)   DynamoDB setup + seed data
├── phase-2-scrapers/          (Week 3-6)   4 data source scrapers
├── phase-3-post-processing/   (Week 7)     Weight & sentiment computation
├── phase-4-orchestration/     (Week 8)     EventBridge + scheduling
├── phase-5-api/               (Week 9-10)  REST API layer
├── phase-6-frontend/          (Week 11-13) React dashboard
├── phase-7-testing/           (Week 14-15) E2E testing & optimization
├── phase-8-monitoring/        (Ongoing)    CloudWatch dashboards & alarms
└── shared/                    (All phases) Utilities, constants, templates
```

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Required
AWS Account with CLI configured
Python 3.11+
Node.js 18+ (for frontend)
```

### 2. Environment Setup
```bash
cp shared/config-templates/.env.template .env
# Edit .env with your API keys and AWS settings
```

### 3. Phase 1: DynamoDB Setup (30 minutes)
```bash
cd phase-1-foundation/dynamodb-setup/
python3 create-table.py --region us-east-1

cd ../celebrity-seed/
python3 seed-database.py
```

### 4. Phase 2: Deploy First Scraper (1-2 hours)
```bash
cd phase-2-scrapers/scraper-tmdb/
# Get TMDB API key from https://www.themoviedb.org/
# Deploy lambda_function.py to AWS Lambda
```

## 📊 Data Model

Each scraper entry in DynamoDB contains:

**First-Hand Fields** (Collected during scrape):
- `id`: Unique entry identifier (UUID)
- `name`: Celebrity name from source
- `raw_text`: Complete API response (JSON/HTML)
- `source`: Source URL
- `timestamp`: ISO 8601 timestamp

**Computed Fields** (Added by post-processor):
- `weight`: Confidence score (0-1)
- `sentiment`: Positive/Negative/Neutral

## 💰 Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| DynamoDB (On-Demand) | $1-2 |
| Lambda (All functions) | $0.70 |
| API Gateway | $0.50 |
| S3 + CloudFront | $1-2 |
| EventBridge | $0.01 |
| CloudWatch Logs | $0.50 |
| DynamoDB PITR | $0.20 |
| **Total** | **~$4-6/month** |

## 📖 Documentation

| File | Purpose |
|------|---------|
| `PROJECT_STRUCTURE.md` | Detailed directory organization |
| `QUICK_START.md` | Step-by-step setup guide |
| `project-updated.md` | Complete project specification |
| `shared/documentation/ARCHITECTURE.md` | System design details |
| Each phase `README.md` | Phase-specific instructions |

## 🎯 Timeline

```
Week 1-2:   Phase 1 - Foundation (DynamoDB setup)
Week 3-6:   Phase 2 - Scrapers (Data collection)
Week 7:     Phase 3 - Post-Processing (Weight & sentiment)
Week 8:     Phase 4 - Orchestration (EventBridge)
Week 9-10:  Phase 5 - API Layer (REST API)
Week 11-13: Phase 6 - Frontend (React dashboard)
Week 14-15: Phase 7 - Testing (QA & optimization)
Ongoing:    Phase 8 - Monitoring (CloudWatch)

Total: ~16 weeks for complete system
```

## ✅ Success Criteria

The system is successful when:
1. ✅ 100 celebrities have data from 4+ sources
2. ✅ Each entry contains all first-hand fields
3. ✅ Weight & sentiment computed automatically
4. ✅ Data updates every Sunday automatically
5. ✅ Dashboard loads in < 3 seconds
6. ✅ Manual edits save successfully
7. ✅ Total monthly cost < $10
8. ✅ Zero data loss incidents
9. ✅ Scrapers run with > 95% success rate
10. ✅ API response time < 500ms

## 🔄 Data Flow

1. **EventBridge** triggers all scrapers every Sunday at 2 AM UTC
2. **Scrapers** collect data from 4+ sources in parallel
3. **First-hand data** written to DynamoDB with all fields
4. **DynamoDB Streams** triggers post-processor
5. **Post-processor** computes weight & sentiment
6. **Updated data** available via REST API
7. **Frontend** displays latest data with visualizations
8. **CloudWatch** monitors system health

## 🛠️ Technology Stack

**AWS Services:**
- DynamoDB (NoSQL database)
- Lambda (Serverless compute)
- EventBridge (Scheduling)
- API Gateway (REST API)
- S3 + CloudFront (Frontend hosting)
- CloudWatch (Monitoring)

**Backend:**
- Python 3.11
- boto3 (AWS SDK)
- requests library
- TextBlob (sentiment analysis)

**Frontend:**
- React 18
- React Router
- Axios
- Tailwind CSS
- React Query

**External APIs:**
- TMDb API
- Wikipedia API
- NewsAPI
- Twitter/YouTube APIs

## 📝 Key Files to Know

| File | Purpose |
|------|---------|
| `phase-1-foundation/dynamodb-setup/create-table.py` | Creates DynamoDB table |
| `phase-1-foundation/celebrity-seed/seed-database.py` | Seeds 100 celebrities |
| `phase-2-scrapers/scraper-*/lambda_function.py` | Scraper implementations |
| `phase-3-post-processing/post-processor/lambda_function.py` | Weight & sentiment |
| `phase-5-api/api-functions/` | API endpoint handlers |
| `phase-6-frontend/react-app/` | React dashboard |

## 🧪 Testing Protocol

Each phase follows a strict testing protocol:
1. Test with minimal data (1-5 items)
2. Review logs and verify data quality
3. Test with medium dataset (5-50 items)
4. **STOP if bugs found - report and fix**
5. Test with full dataset (100+ items)
6. Performance validation

## 🔐 Security

- All API keys stored in AWS Secrets Manager
- DynamoDB encryption at rest enabled
- API Gateway with API key authentication
- HTTPS via CloudFront
- IAM roles with least privilege
- Quarterly key rotation

## 📊 Monitoring

- CloudWatch Dashboards for key metrics
- Alarms for error rates, timeouts, failures
- DynamoDB Point-in-Time Recovery enabled
- Daily automated backups
- Quarterly restore testing

## 🤝 Contributing

Each component is designed for independent development:
1. Choose a phase to work on
2. Read the phase README.md
3. Follow the testing checklist
4. Ensure all tests pass before committing

## 📞 Support

**Resources:**
- `QUICK_START.md` - Step-by-step setup
- `PROJECT_STRUCTURE.md` - Directory organization
- `project-updated.md` - Complete specification
- Individual phase `README.md` files

**Common Issues:**
See `project-updated.md` → "Troubleshooting Guide"

## 📅 Project Status

- ✅ Project Structure Created
- ✅ Phase 1-8 Directories Set Up
- ✅ Documentation Complete
- ⏳ Phase 1 Implementation Ready

## 🎓 Learning Value

This project demonstrates:
- Serverless architecture design
- Event-driven systems
- Data aggregation from multiple sources
- Sentiment analysis implementation
- Cost optimization strategies
- AWS service integration
- Full-stack development (backend + frontend)

## 📄 License

This project is created for personal research and learning purposes.

---

## Next Steps

1. **Read QUICK_START.md** for step-by-step instructions
2. **Start with Phase 1** in `phase-1-foundation/`
3. **Follow testing checklist** in each phase
4. **Reference project-updated.md** for detailed specs

---

**Ready to begin?** Start here: `cd phase-1-foundation/ && cat README.md`

**Project Created**: November 7, 2025
**Last Updated**: November 7, 2025
