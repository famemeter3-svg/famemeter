"""
Post-Processing Lambda Function

Computes weight and sentiment for all scraped data entries.
Triggered by DynamoDB Streams.

Environment Variables Required:
- DYNAMODB_TABLE: DynamoDB table name
- AWS_REGION: AWS region
- USE_AWS_COMPREHEND: 'true' to use AWS Comprehend (optional)
"""

import boto3
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Resources
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'celebrity-database'))
comprehend = boto3.client('comprehend', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

USE_AWS_COMPREHEND = os.environ.get('USE_AWS_COMPREHEND', 'false').lower() == 'true'


def calculate_weight(raw_text, source):
    """
    Calculate confidence score (0-1) based on data completeness and source reliability.

    Args:
        raw_text: Raw response data (JSON string)
        source: Source URL

    Returns:
        Float (0-1)
    """
    weight = 0.0

    # Check data completeness
    try:
        data = json.loads(raw_text)
        field_count = len([v for v in data.values() if v is not None and v != ''])
        completeness_score = min(field_count / 10, 1.0)  # Normalize to 0-1
    except:
        completeness_score = 0.3

    # Source reliability mapping
    source_reliability = {
        "api.themoviedb.org": 0.95,
        "en.wikipedia.org": 0.90,
        "newsapi.org": 0.85,
        "twitter.com": 0.80,
        "instagram.com": 0.75,
        "youtube.com": 0.85
    }

    reliability_score = 0.5  # Default
    for domain, score in source_reliability.items():
        if domain in source.lower():
            reliability_score = score
            break

    # Combine scores with weighted average
    weight = (completeness_score * 0.5) + (reliability_score * 0.5)

    return round(weight, 2)


def calculate_sentiment_textblob(raw_text):
    """
    Calculate sentiment using TextBlob (simple/offline).

    Args:
        raw_text: Raw text to analyze

    Returns:
        String: 'positive', 'negative', or 'neutral'
    """
    try:
        from textblob import TextBlob

        # Extract text content
        if raw_text.startswith('{'):
            try:
                data = json.loads(raw_text)
                # Extract text fields
                text_content = ' '.join([
                    str(v) for k, v in data.items()
                    if isinstance(v, str) and k not in ['id', 'raw_text', 'source']
                ])
            except:
                text_content = raw_text
        else:
            text_content = raw_text

        # Limit text length for performance
        text_content = text_content[:500]

        # Analyze sentiment
        blob = TextBlob(text_content)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"

    except ImportError:
        logger.warning("TextBlob not available, using default sentiment")
        return "neutral"
    except Exception as e:
        logger.error(f"Error calculating sentiment with TextBlob: {str(e)}")
        return "neutral"


def calculate_sentiment_aws(raw_text):
    """
    Calculate sentiment using AWS Comprehend.

    Args:
        raw_text: Raw text to analyze

    Returns:
        String: 'positive', 'negative', 'neutral', or 'mixed'
    """
    try:
        # Extract text content
        if raw_text.startswith('{'):
            try:
                data = json.loads(raw_text)
                text_content = ' '.join([
                    str(v) for k, v in data.items()
                    if isinstance(v, str) and k not in ['id', 'raw_text', 'source']
                ])
            except:
                text_content = raw_text
        else:
            text_content = raw_text

        # Limit text length (AWS Comprehend has limits)
        text_content = text_content[:500]

        # Call AWS Comprehend
        response = comprehend.detect_sentiment(
            Text=text_content,
            LanguageCode='en'
        )

        sentiment = response.get('Sentiment', 'NEUTRAL').lower()

        # Map AWS values to our values
        sentiment_map = {
            'positive': 'positive',
            'negative': 'negative',
            'neutral': 'neutral',
            'mixed': 'neutral'  # Treat mixed as neutral
        }

        return sentiment_map.get(sentiment, 'neutral')

    except Exception as e:
        logger.error(f"Error calculating sentiment with AWS Comprehend: {str(e)}")
        return "neutral"


def calculate_sentiment(raw_text):
    """
    Calculate sentiment using configured method.

    Args:
        raw_text: Raw text to analyze

    Returns:
        String: 'positive', 'negative', or 'neutral'
    """
    if USE_AWS_COMPREHEND:
        return calculate_sentiment_aws(raw_text)
    else:
        return calculate_sentiment_textblob(raw_text)


def process_stream_record(record):
    """
    Process a single DynamoDB Stream record.

    Args:
        record: DynamoDB Stream record

    Returns:
        Boolean indicating success
    """
    try:
        event_name = record['eventName']

        # Only process INSERT and MODIFY events
        if event_name not in ['INSERT', 'MODIFY']:
            logger.info(f"Skipping {event_name} event")
            return True

        # Get the item from the stream
        dynamodb_record = record['dynamodb']

        if 'NewImage' not in dynamodb_record:
            logger.warning("No NewImage in record")
            return True

        new_image = dynamodb_record['NewImage']

        # Extract key fields
        celebrity_id = new_image.get('celebrity_id', {}).get('S')
        source_type_timestamp = new_image.get('source_type#timestamp', {}).get('S')
        raw_text = new_image.get('raw_text', {}).get('S')
        source = new_image.get('source', {}).get('S')

        if not all([celebrity_id, source_type_timestamp, raw_text, source]):
            logger.warning(f"Missing required fields in record: {new_image}")
            return True

        # Calculate weight and sentiment
        weight = calculate_weight(raw_text, source)
        sentiment = calculate_sentiment(raw_text)

        logger.info(f"Computed: weight={weight}, sentiment={sentiment}")

        # Update DynamoDB with computed fields
        update_expression = "SET #weight = :weight, #sentiment = :sentiment, updated_at = :updated_at"
        expression_attribute_names = {
            '#weight': 'weight',
            '#sentiment': 'sentiment'
        }
        expression_attribute_values = {
            ':weight': weight,
            ':sentiment': sentiment,
            ':updated_at': datetime.utcnow().isoformat() + 'Z'
        }

        table.update_item(
            Key={
                'celebrity_id': celebrity_id,
                'source_type#timestamp': source_type_timestamp
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        logger.info(f"✓ Updated {celebrity_id} with weight and sentiment")
        return True

    except Exception as e:
        logger.error(f"Error processing record: {str(e)}")
        return False


def lambda_handler(event, context):
    """
    Lambda handler for post-processing.

    Args:
        event: DynamoDB Stream event
        context: Lambda context

    Returns:
        Response with results
    """
    logger.info("Starting post-processor")

    if 'Records' not in event:
        logger.error("No Records in event")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No Records in event'})
        }

    records = event['Records']
    logger.info(f"Processing {len(records)} records")

    success_count = 0
    error_count = 0

    for idx, record in enumerate(records, 1):
        try:
            if process_stream_record(record):
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            logger.error(f"Exception processing record {idx}: {str(e)}")
            error_count += 1

    logger.info(f"Post-processor complete: {success_count} success, {error_count} errors")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'total': len(records),
            'success': success_count,
            'errors': error_count
        })
    }


if __name__ == '__main__':
    # For local testing
    print("This is a Lambda function. Use test scripts for local testing.")
