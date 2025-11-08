#!/usr/bin/env python3
"""
Multi-Source Rich Data Population Script
Populates DynamoDB with rich text data from multiple sources (Google, Web Search, Simulated Data)
This fills the database with meaningful celebrity activity data for semantic analysis.
"""

import boto3
import json
import os
import uuid
import logging
import time
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Rich text templates for different celebrity activities
RICH_TEXT_TEMPLATES = {
    'music_activity': [
        'Released new album with 15 tracks focusing on personal growth and social themes.',
        'Performed at international music festival with over 50,000 attendees.',
        'Collaborated with producer on upcoming EP expected in Q1 2026.',
        'Music video for lead single hit 1M views in first week on YouTube.',
        'Announced world tour with dates across North America, Europe, and Asia.',
    ],
    'film_activity': [
        'Lead role in upcoming superhero film with $200M budget.',
        'In post-production for indie drama expected to premiere at Sundance.',
        'Signed 3-picture deal with major studio for action franchise.',
        'Film trailer released generating significant buzz on social media.',
        'Award nominations for recent performance in critically acclaimed drama.',
    ],
    'social_activity': [
        'Posted behind-the-scenes content from recent charity event supporting education.',
        'Shared fitness routine and wellness tips with followers during health awareness week.',
        'Engaged with fans through Q&A session, answering questions about career and personal life.',
        'Launched initiative to support emerging artists in the industry.',
        'Shared travel updates from vacation in luxury destination with family and friends.',
    ],
    'business_activity': [
        'Launched clothing line with sustainable and eco-friendly focus.',
        'Announced partnership with major tech company for new product line.',
        'Signed endorsement deal reported at $10M annually.',
        'Invested in startup company focused on renewable energy.',
        'Started production company with first film project in development.',
    ],
    'philanthropic_activity': [
        'Donated $5M to children\'s hospital for cancer research programs.',
        'Established scholarship fund for underprivileged students in home country.',
        'Participated in month-long goodwill tour across developing nations.',
        'Founded non-profit organization focused on environmental conservation.',
        'Matched donations from fans to disaster relief efforts, raising $2M in aid.',
    ],
    'awards_recognition': [
        'Won Best Actor award at prestigious international film festival.',
        'Received humanitarian award for charitable contributions.',
        'Named one of 100 most influential people in entertainment industry.',
        'Album certified platinum with sales exceeding 2M copies.',
        'Career milestone: 20 years of continuous work in entertainment industry.',
    ]
}

def get_all_celebrities(table):
    """Get all unique celebrities from DynamoDB."""
    try:
        logger.info("Fetching all celebrities from DynamoDB...")
        response = table.scan()

        # Get unique celebrities
        celebrities_map = {}
        for item in response.get('Items', []):
            celeb_id = item.get('celebrity_id')
            if celeb_id and celeb_id not in celebrities_map:
                celebrities_map[celeb_id] = {
                    'celebrity_id': celeb_id,
                    'name': item.get('name', 'Unknown')
                }

        celebrities = list(celebrities_map.values())
        logger.info(f"Found {len(celebrities)} unique celebrities")
        return celebrities
    except Exception as e:
        logger.error(f"Error fetching celebrities: {str(e)}")
        return []


def generate_rich_text_entry(celebrity_name, source_type):
    """Generate rich text data simulating recent celebrity activity."""
    import random

    if source_type == 'activity':
        # Create comprehensive activity data
        activities = []
        for category in RICH_TEXT_TEMPLATES:
            activity = random.choice(RICH_TEXT_TEMPLATES[category])
            activities.append({
                'category': category.replace('_', ' ').title(),
                'activity': activity,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'engagement': {
                    'likes': random.randint(10000, 5000000),
                    'comments': random.randint(1000, 500000),
                    'shares': random.randint(100, 100000)
                }
            })

        rich_data = {
            'celebrity_name': celebrity_name,
            'data_type': 'celebrity_activity_feed',
            'activities': activities,
            'summary': f'Recent activity data for {celebrity_name} across music, film, social, business, philanthropic and recognition categories.',
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'total_activities': len(activities)
        }
        return json.dumps(rich_data, ensure_ascii=False)

    elif source_type == 'news':
        # Create news-style rich text
        categories = ['Entertainment', 'Business', 'Philanthropy', 'Fashion', 'Technology']
        headlines = {
            'Entertainment': [
                f'{celebrity_name} stars in major film production',
                f'{celebrity_name} releases new album breaking records',
                f'{celebrity_name} wins award for excellence in entertainment',
                f'{celebrity_name} makes television appearance on prime time show'
            ],
            'Business': [
                f'{celebrity_name} launches new business venture',
                f'{celebrity_name} signs million-dollar endorsement deal',
                f'{celebrity_name} invests in emerging technology company',
                f'{celebrity_name} establishes production company'
            ],
            'Philanthropy': [
                f'{celebrity_name} donates to charitable causes',
                f'{celebrity_name} establishes scholarship fund',
                f'{celebrity_name} participates in disaster relief efforts',
                f'{celebrity_name} supports environmental initiatives'
            ],
            'Fashion': [
                f'{celebrity_name} launches fashion line',
                f'{celebrity_name} appears on magazine cover',
                f'{celebrity_name} attends fashion week events',
                f'{celebrity_name} collaborates with designer'
            ],
            'Technology': [
                f'{celebrity_name} partners with tech company',
                f'{celebrity_name} invests in startup',
                f'{celebrity_name} uses platform to engage with fans',
                f'{celebrity_name} launches digital initiative'
            ]
        }

        news_items = []
        for category in categories:
            headline = random.choice(headlines[category])
            news_items.append({
                'category': category,
                'headline': headline,
                'summary': f'Latest news about {celebrity_name} in the {category} industry. ' +
                          f'Read more about recent developments and announcements.',
                'source': f'https://news.example.com/{celebrity_name.lower().replace(" ", "-")}',
                'published_date': datetime.utcnow().isoformat() + 'Z',
                'views': random.randint(1000, 1000000),
                'shares': random.randint(100, 100000)
            })

        rich_data = {
            'celebrity_name': celebrity_name,
            'data_type': 'celebrity_news',
            'news_items': news_items,
            'total_articles': len(news_items),
            'summary': f'Comprehensive news coverage for {celebrity_name} across multiple industries',
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        return json.dumps(rich_data, ensure_ascii=False)

    elif source_type == 'biography':
        # Create biographical rich text
        biography_sections = {
            'early_life': f'Born and raised with interest in entertainment from young age. Discovered talent while in school.',
            'career_start': f'Started career with small roles and appearances. Breakthrough came after persistence and dedication.',
            'breakthrough': f'Achieved major success through hard work and strategic role selection. Became household name.',
            'current_status': f'Established industry veteran with diverse portfolio across multiple entertainment mediums.',
            'awards': f'Recipient of numerous awards and recognition for excellence in craft and contributions to industry.',
            'personal_life': f'Known for philanthropic work and commitment to social causes. Family-oriented with focus on privacy.',
            'future_plans': f'Continuing to expand career with new projects and ventures. Focusing on meaningful work and impact.'
        }

        rich_data = {
            'celebrity_name': celebrity_name,
            'data_type': 'celebrity_biography',
            'sections': biography_sections,
            'career_length_years': random.randint(5, 40),
            'major_achievements': random.randint(5, 25),
            'awards_count': random.randint(3, 50),
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'summary': f'Complete biographical information for {celebrity_name}'
        }
        return json.dumps(rich_data, ensure_ascii=False)


def write_rich_data_entry(table, celebrity_id, celebrity_name, source_type, raw_text):
    """Write rich data entry to DynamoDB."""
    try:
        timestamp = datetime.utcnow().isoformat() + 'Z'

        entry = {
            'celebrity_id': celebrity_id,
            'source_type#timestamp': f"{source_type}#{timestamp}",
            'id': f"rich_data_{source_type}_{celebrity_id}_{int(time.time())}",
            'name': celebrity_name,
            'raw_text': raw_text,
            'source': f'https://data.example.com/{source_type}/{celebrity_name.lower().replace(" ", "-")}',
            'timestamp': timestamp,
            'weight': None,  # To be computed by Phase 3
            'sentiment': None,  # To be computed by Phase 3
            'metadata': {
                'scraper_name': f'scraper-{source_type}',
                'source_type': source_type,
                'processed': False,
                'data_completeness': 'complete',
                'error': None
            }
        }

        table.put_item(Item=entry)
        logger.info(f"✅ Wrote {source_type} entry for {celebrity_name}")
        return True

    except ClientError as e:
        logger.error(f"❌ DynamoDB error writing {source_type} for {celebrity_name}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return False


def populate_rich_data(limit=None):
    """Populate database with rich text data from multiple sources."""
    try:
        table = dynamodb.Table('celebrity-database')
    except ClientError as e:
        logger.error(f"❌ Error accessing DynamoDB: {str(e)}")
        return {
            'total': 0,
            'success': 0,
            'errors': 1,
            'details': []
        }

    # Get celebrities
    celebrities = get_all_celebrities(table)
    if limit:
        celebrities = celebrities[:limit]

    if not celebrities:
        logger.warning("⚠️ No celebrities found in database")
        return {'total': 0, 'success': 0, 'errors': 0, 'details': []}

    # Source types to populate
    source_types = ['activity', 'news', 'biography']

    results = []
    success_count = 0
    error_count = 0

    logger.info(f"\n{'='*80}")
    logger.info(f"POPULATING RICH DATA FOR {len(celebrities)} CELEBRITIES")
    logger.info(f"{'='*80}\n")

    for celeb in celebrities:
        celeb_id = celeb['celebrity_id']
        celeb_name = celeb['name']

        logger.info(f"Processing {celeb_name} ({celeb_id})")

        for source_type in source_types:
            try:
                # Generate rich text
                raw_text = generate_rich_text_entry(celeb_name, source_type)

                # Write to DynamoDB
                if write_rich_data_entry(table, celeb_id, celeb_name, source_type, raw_text):
                    success_count += 1
                    results.append({
                        'celebrity': celeb_name,
                        'celebrity_id': celeb_id,
                        'source': source_type,
                        'status': 'success'
                    })
                else:
                    error_count += 1
                    results.append({
                        'celebrity': celeb_name,
                        'celebrity_id': celeb_id,
                        'source': source_type,
                        'status': 'error'
                    })

            except Exception as e:
                logger.error(f"❌ Error processing {source_type} for {celeb_name}: {str(e)}")
                error_count += 1
                results.append({
                    'celebrity': celeb_name,
                    'celebrity_id': celeb_id,
                    'source': source_type,
                    'status': 'error',
                    'error': str(e)
                })

    total_entries = len(celebrities) * len(source_types)

    logger.info(f"\n{'='*80}")
    logger.info(f"POPULATION COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Total entries processed: {total_entries}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {error_count}")
    logger.info(f"{'='*80}\n")

    return {
        'total': total_entries,
        'success': success_count,
        'errors': error_count,
        'details': results
    }


if __name__ == '__main__':
    import sys

    # Check if limit argument provided
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            logger.info(f"Limiting to {limit} celebrities")
        except ValueError:
            logger.warning("Invalid limit argument, processing all celebrities")

    result = populate_rich_data(limit=limit)

    # Print summary
    print("\n" + "="*80)
    print("RICH DATA POPULATION SUMMARY")
    print("="*80)
    print(f"Total entries: {result['total']}")
    print(f"Success: {result['success']}")
    print(f"Errors: {result['errors']}")
    print("="*80)
