# Shared Resources

## Overview
Common utilities, constants, and configurations shared across all phases.

## Directories

### `utils/`
Reusable utility functions and helpers
- DynamoDB operations
- Error handling
- Logging utilities
- Data validation
- Rate limiting

### `constants/`
Shared constants and enums
- Field definitions
- Data source configurations
- AWS resource names
- API endpoints

### `config-templates/`
Template configuration files
- Environment variable templates
- AWS IAM policy templates
- Lambda Layer configurations
- Deployment scripts

### `documentation/`
Comprehensive documentation
- Architecture diagrams
- Data model documentation
- API documentation
- Setup guides

## Usage
Each phase imports utilities from `../shared/` as needed.

## Example Structure
```
shared/
├── utils/
│   ├── dynamodb_helper.py
│   ├── error_handler.py
│   ├── logger.py
│   ├── validation.py
│   └── rate_limiter.py
├── constants/
│   ├── field_definitions.py
│   ├── data_sources.py
│   ├── aws_resources.py
│   └── api_endpoints.py
├── config-templates/
│   ├── .env.template
│   ├── iam-policy-template.json
│   ├── lambda-layer-config.json
│   └── deploy.sh
└── documentation/
    ├── ARCHITECTURE.md
    ├── DATA_MODEL.md
    ├── API_REFERENCE.md
    └── SETUP_GUIDE.md
```

## Notes
- Keep utilities generic and reusable
- Document any shared functions thoroughly
- Use consistent naming conventions
- Update version info when making changes
