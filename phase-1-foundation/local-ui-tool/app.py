"""
Local UI Tool - Simple Flask server to verify DynamoDB data schema and entries
Displays celebrities, their metadata, and scraped data in a web interface
"""

import os
import json
import boto3
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from botocore.exceptions import ClientError
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = 'celebrity-database'

try:
    table = dynamodb.Table(table_name)
except Exception as e:
    logger.error(f"Failed to connect to DynamoDB: {e}")
    table = None


@app.route('/')
def index():
    """Serve the main UI page"""
    return render_template('index.html')


@app.route('/api/health')
def health():
    """Check if DynamoDB connection is working"""
    if table is None:
        return jsonify({
            'status': 'error',
            'message': 'DynamoDB table not found',
            'table': table_name
        }), 503

    try:
        # Try to describe the table
        response = table.table_status
        return jsonify({
            'status': 'healthy',
            'table': table_name,
            'table_status': response,
            'message': 'Connected to DynamoDB'
        })
    except ClientError as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'table': table_name
        }), 503


@app.route('/api/celebrities')
def get_celebrities():
    """Get all celebrities (metadata entries only)"""
    try:
        if table is None:
            return jsonify({'error': 'DynamoDB not connected'}), 503

        # Scan for all metadata records
        response = table.scan()

        # Filter for metadata entries and organize by celebrity
        celebrities = {}
        for item in response.get('Items', []):
            celeb_id = item.get('celebrity_id')
            sort_key = item.get('source_type#timestamp', '')

            # Include both metadata and recent scraper entries
            if sort_key.startswith('metadata#'):
                if celeb_id not in celebrities:
                    celebrities[celeb_id] = {
                        'celebrity_id': celeb_id,
                        'name': item.get('name', 'Unknown'),
                        'birth_date': item.get('birth_date'),
                        'nationality': item.get('nationality'),
                        'occupation': item.get('occupation', []),
                        'is_active': item.get('is_active', True),
                        'created_at': item.get('created_at'),
                        'updated_at': item.get('updated_at'),
                        'data_sources': []
                    }
            else:
                # Track data sources
                if celeb_id not in celebrities:
                    celebrities[celeb_id] = {
                        'celebrity_id': celeb_id,
                        'name': item.get('name', 'Unknown'),
                        'data_sources': []
                    }

                source_type = sort_key.split('#')[0]
                celebrities[celeb_id]['data_sources'].append({
                    'source': source_type,
                    'timestamp': item.get('timestamp'),
                    'has_data': True
                })

        # Convert to list and sort
        celeb_list = list(celebrities.values())
        celeb_list.sort(key=lambda x: x.get('celebrity_id', ''))

        return jsonify({
            'total': len(celeb_list),
            'celebrities': celeb_list
        })
    except ClientError as e:
        logger.error(f"Error fetching celebrities: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/celebrity/<celebrity_id>')
def get_celebrity_detail(celebrity_id):
    """Get detailed info for a single celebrity including all data sources"""
    try:
        if table is None:
            return jsonify({'error': 'DynamoDB not connected'}), 503

        # Query for all entries with this celebrity_id
        response = table.query(
            KeyConditionExpression='celebrity_id = :id',
            ExpressionAttributeValues={':id': celebrity_id}
        )

        if not response.get('Items'):
            return jsonify({
                'error': f'Celebrity {celebrity_id} not found',
                'celebrity_id': celebrity_id
            }), 404

        # Organize data
        metadata = {}
        data_sources = []

        for item in response['Items']:
            sort_key = item.get('source_type#timestamp', '')

            if sort_key.startswith('metadata#'):
                metadata = {
                    'celebrity_id': item.get('celebrity_id'),
                    'name': item.get('name'),
                    'birth_date': item.get('birth_date'),
                    'nationality': item.get('nationality'),
                    'occupation': item.get('occupation'),
                    'is_active': item.get('is_active'),
                    'created_at': item.get('created_at'),
                    'updated_at': item.get('updated_at')
                }
            else:
                # Scraper entry
                source_type = sort_key.split('#')[0]
                data_sources.append({
                    'source_type': source_type,
                    'timestamp': item.get('timestamp'),
                    'id': item.get('id'),
                    'raw_text_preview': (item.get('raw_text', '')[:200] + '...'
                                        if item.get('raw_text') and len(item.get('raw_text', '')) > 200
                                        else item.get('raw_text', 'N/A')),
                    'raw_text_length': len(item.get('raw_text', '')),
                    'source': item.get('source'),
                    'weight': item.get('weight'),
                    'sentiment': item.get('sentiment'),
                    'metadata': item.get('metadata', {}),
                    'full_item': item  # Include full item for inspection
                })

        # Sort data sources by timestamp (newest first)
        data_sources.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return jsonify({
            'metadata': metadata,
            'data_sources_count': len(data_sources),
            'data_sources': data_sources
        })
    except ClientError as e:
        logger.error(f"Error fetching celebrity detail: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        if table is None:
            return jsonify({'error': 'DynamoDB not connected'}), 503

        # Scan entire table
        response = table.scan()
        items = response.get('Items', [])

        # Count by source type
        sources = {}
        metadata_count = 0
        scraper_count = 0

        for item in items:
            sort_key = item.get('source_type#timestamp', '')

            if sort_key.startswith('metadata#'):
                metadata_count += 1
            else:
                scraper_count += 1
                source_type = sort_key.split('#')[0]
                sources[source_type] = sources.get(source_type, 0) + 1

        return jsonify({
            'total_items': len(items),
            'metadata_records': metadata_count,
            'scraper_records': scraper_count,
            'sources': sources,
            'celebrities_with_data': metadata_count,
            'average_entries_per_celebrity': round(scraper_count / max(metadata_count, 1), 2)
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/schema')
def get_schema():
    """Get table schema information"""
    try:
        if table is None:
            return jsonify({'error': 'DynamoDB not connected'}), 503

        # Get table description
        table_desc = table.table_status

        return jsonify({
            'table_name': table_name,
            'status': table_desc,
            'partition_key': 'celebrity_id',
            'sort_key': 'source_type#timestamp',
            'gsi': [
                {
                    'index_name': 'name-index',
                    'partition_key': 'name',
                    'projection': 'ALL'
                },
                {
                    'index_name': 'source-index',
                    'partition_key': 'source',
                    'sort_key': 'timestamp',
                    'projection': 'ALL'
                }
            ],
            'billing_mode': 'PAY_PER_REQUEST',
            'stream_enabled': True,
            'stream_view_type': 'NEW_AND_OLD_IMAGES'
        })
    except Exception as e:
        logger.error(f"Error fetching schema: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate/celebrity/<celebrity_id>')
def validate_celebrity(celebrity_id):
    """Validate a celebrity's data schema and completeness"""
    try:
        if table is None:
            return jsonify({'error': 'DynamoDB not connected'}), 503

        # Get all entries for this celebrity
        response = table.query(
            KeyConditionExpression='celebrity_id = :id',
            ExpressionAttributeValues={':id': celebrity_id}
        )

        if not response.get('Items'):
            return jsonify({
                'valid': False,
                'errors': [f'Celebrity {celebrity_id} not found']
            }), 404

        items = response['Items']
        errors = []
        warnings = []

        # Check for metadata entry
        metadata_found = False
        for item in items:
            if item.get('source_type#timestamp', '').startswith('metadata#'):
                metadata_found = True

                # Validate required fields
                if not item.get('name'):
                    errors.append('Metadata missing: name')
                if not item.get('celebrity_id'):
                    errors.append('Metadata missing: celebrity_id')
                if not item.get('birth_date'):
                    warnings.append('Metadata missing: birth_date')
                if not item.get('nationality'):
                    warnings.append('Metadata missing: nationality')
                if not item.get('occupation'):
                    warnings.append('Metadata missing: occupation')
                break

        if not metadata_found:
            warnings.append('No metadata record found')

        # Check scraper entries
        scraper_count = 0
        for item in items:
            sort_key = item.get('source_type#timestamp', '')
            if not sort_key.startswith('metadata#'):
                scraper_count += 1

                # Validate first-hand data pattern
                if not item.get('raw_text'):
                    errors.append(f'Scraper entry missing: raw_text (source: {sort_key})')
                if not item.get('source'):
                    errors.append(f'Scraper entry missing: source (source: {sort_key})')
                if not item.get('timestamp'):
                    errors.append(f'Scraper entry missing: timestamp (source: {sort_key})')
                if not item.get('id'):
                    errors.append(f'Scraper entry missing: id (source: {sort_key})')

        return jsonify({
            'celebrity_id': celebrity_id,
            'valid': len(errors) == 0,
            'has_metadata': metadata_found,
            'scraper_entries': scraper_count,
            'total_entries': len(items),
            'errors': errors,
            'warnings': warnings,
            'validation_status': 'PASS' if not errors else 'FAIL'
        })
    except Exception as e:
        logger.error(f"Error validating celebrity: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate/all')
def validate_all():
    """Validate all celebrities in the database"""
    try:
        if table is None:
            return jsonify({'error': 'DynamoDB not connected'}), 503

        # Get all celebrities
        response = table.scan()
        items = response.get('Items', [])

        # Group by celebrity_id
        celebrities = {}
        for item in items:
            celeb_id = item.get('celebrity_id')
            if celeb_id not in celebrities:
                celebrities[celeb_id] = []
            celebrities[celeb_id].append(item)

        # Validate each
        validation_results = {
            'total_celebrities': len(celebrities),
            'passed': 0,
            'failed': 0,
            'with_warnings': 0,
            'results': []
        }

        for celeb_id, items in celebrities.items():
            errors = []
            warnings = []

            # Check metadata
            metadata_found = False
            for item in items:
                if item.get('source_type#timestamp', '').startswith('metadata#'):
                    metadata_found = True
                    if not item.get('name'):
                        errors.append('Missing name')
                    break

            if not metadata_found:
                errors.append('No metadata record')

            # Check scraper entries
            scraper_count = sum(1 for item in items
                               if not item.get('source_type#timestamp', '').startswith('metadata#'))

            if scraper_count == 0:
                warnings.append('No scraper entries')

            status = 'PASS' if not errors else 'FAIL'
            if status == 'PASS':
                validation_results['passed'] += 1
            else:
                validation_results['failed'] += 1

            if warnings:
                validation_results['with_warnings'] += 1

            validation_results['results'].append({
                'celebrity_id': celeb_id,
                'status': status,
                'entries': len(items),
                'has_metadata': metadata_found,
                'scraper_entries': scraper_count,
                'errors': errors,
                'warnings': warnings
            })

        return jsonify(validation_results)
    except Exception as e:
        logger.error(f"Error validating all: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/raw/<celebrity_id>/<source_type>')
def get_raw_data(celebrity_id, source_type):
    """Get the complete raw_text for a specific source"""
    try:
        if table is None:
            return jsonify({'error': 'DynamoDB not connected'}), 503

        # Query for entries matching this celebrity and source
        response = table.query(
            KeyConditionExpression='celebrity_id = :id',
            ExpressionAttributeValues={':id': celebrity_id}
        )

        for item in response.get('Items', []):
            sort_key = item.get('source_type#timestamp', '')
            if sort_key.startswith(f'{source_type}#'):
                try:
                    # Try to parse as JSON if possible
                    raw_data = json.loads(item.get('raw_text', '{}'))
                    return jsonify({
                        'celebrity_id': celebrity_id,
                        'source_type': source_type,
                        'timestamp': item.get('timestamp'),
                        'is_json': True,
                        'data': raw_data
                    })
                except json.JSONDecodeError:
                    # Return as plain text
                    return jsonify({
                        'celebrity_id': celebrity_id,
                        'source_type': source_type,
                        'timestamp': item.get('timestamp'),
                        'is_json': False,
                        'data': item.get('raw_text', '')
                    })

        return jsonify({'error': f'No data found for {source_type}'}), 404
    except Exception as e:
        logger.error(f"Error fetching raw data: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("LOCAL UI TOOL - DynamoDB Viewer")
    print("="*60)
    print(f"Table: {table_name}")
    print("Status: " + ("Connected ✓" if table else "Not Connected ✗"))
    print("\nServer running at: http://localhost:5000")
    print("="*60 + "\n")

    app.run(debug=True, host='localhost', port=5000)
