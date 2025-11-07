#!/usr/bin/env python3
"""
Phase 1: Seed Celebrity Metadata into DynamoDB

This script populates the celebrity-database table with 100 celebrity
metadata records that Phase 2 scrapers will then enrich with data.
"""

import os
import boto3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

table_name = os.environ.get('DYNAMODB_TABLE', 'celebrity-database')
table = dynamodb.Table(table_name)

# List of 100 celebrities
CELEBRITIES = [
    ("Leonardo DiCaprio", "1974-11-11", "American"),
    ("Tom Hanks", "1956-07-09", "American"),
    ("Johnny Depp", "1963-06-09", "American"),
    ("Brad Pitt", "1963-12-18", "American"),
    ("Will Smith", "1968-09-25", "American"),
    ("Tom Cruise", "1962-12-03", "American"),
    ("Matthew McConaughey", "1969-11-04", "American"),
    ("Christian Bale", "1974-01-30", "British"),
    ("Robert Downey Jr.", "1965-04-04", "American"),
    ("Ryan Reynolds", "1976-10-23", "Canadian"),
    ("Hugh Jackman", "1968-10-12", "Australian"),
    ("Jake Gyllenhaal", "1980-12-19", "American"),
    ("Chris Evans", "1981-06-13", "American"),
    ("Chris Hemsworth", "1983-08-11", "Australian"),
    ("Chris Pratt", "1979-08-21", "American"),
    ("Dwayne Johnson", "1972-05-02", "American"),
    ("Mark Wahlberg", "1971-06-05", "American"),
    ("Liam Neeson", "1952-06-07", "Irish"),
    ("Morgan Freeman", "1937-06-01", "American"),
    ("Al Pacino", "1940-04-25", "American"),
    ("Jack Nicholson", "1937-04-22", "American"),
    ("Arnold Schwarzenegger", "1947-07-30", "Austrian"),
    ("Sylvester Stallone", "1946-07-06", "American"),
    ("Kevin Hart", "1979-07-17", "American"),
    ("Denzel Washington", "1954-12-28", "American"),
    ("Keanu Reeves", "1964-09-02", "Canadian"),
    ("Johnny Depp", "1963-06-09", "American"),
    ("Tom Hardy", "1977-09-15", "British"),
    ("Oscar Isaac", "1979-03-09", "Guatemalan"),
    ("Michael Fassbender", "1977-04-02", "Irish"),
    ("Tom Hiddleston", "1981-02-09", "British"),
    ("Benedict Cumberbatch", "1976-07-19", "British"),
    ("Adam Driver", "1983-11-01", "American"),
    ("Rami Malek", "1981-05-12", "American"),
    ("Timothée Chalamet", "1994-12-27", "French"),
    ("Riz Ahmed", "1982-12-01", "British"),
    ("Chadwick Boseman", "1977-11-29", "American"),
    ("Idris Elba", "1972-09-06", "British"),
    ("Michael B. Jordan", "1987-02-09", "American"),
    ("Sterling K. Brown", "1973-04-05", "American"),
    ("Jason Momoa", "1979-08-01", "American"),
    ("Henry Cavill", "1983-05-05", "British"),
    ("Pedro Pascal", "1975-04-02", "American"),
    ("Oscar Isaac", "1979-03-09", "Guatemalan"),
    ("Andrew Garfield", "1983-08-20", "British"),
    ("Tobey Maguire", "1975-06-27", "American"),
    ("Shia LaBeouf", "1986-06-11", "American"),
    ("Ryan Gosling", "1980-11-12", "Canadian"),
    ("Ryan Reynolds", "1976-10-23", "Canadian"),
    ("James McAvoy", "1979-04-21", "Scottish"),
    ("Michael Fassbender", "1977-04-02", "Irish"),
    ("Gary Oldman", "1958-03-21", "British"),
    ("Joaquin Phoenix", "1974-10-28", "American"),
    ("Jake Gyllenhaal", "1980-12-19", "American"),
    ("Andrew Lincoln", "1973-09-14", "British"),
    ("Norman Reedus", "1974-03-06", "American"),
    ("Jeffrey Dean Morgan", "1966-04-22", "American"),
    ("Jon Hamm", "1971-03-10", "American"),
    ("Charlie Hunnam", "1980-04-10", "British"),
    ("Henry Rollins", "1961-02-13", "American"),
    ("Dave Bautista", "1969-01-18", "American"),
    ("John Cena", "1977-04-23", "American"),
    ("Vin Diesel", "1978-07-18", "American"),
    ("Jason Statham", "1967-07-26", "British"),
    ("Terry Crews", "1968-07-30", "American"),
    ("Michael Jai White", "1972-11-10", "American"),
    ("Wesley Snipes", "1962-07-31", "American"),
    ("Jean-Claude Van Damme", "1960-10-18", "Belgian"),
    ("Chuck Norris", "1940-03-10", "American"),
    ("Steven Seagal", "1952-04-10", "American"),
    ("Bruce Willis", "1955-03-19", "American"),
    ("Pierce Brosnan", "1953-05-16", "Irish"),
    ("Sean Connery", "1930-08-25", "Scottish"),
    ("Daniel Craig", "1968-03-02", "British"),
    ("Harrison Ford", "1942-07-13", "American"),
    ("Mark Ruffalo", "1966-11-22", "American"),
    ("Jeremy Renner", "1971-01-07", "American"),
    ("Scarlett Johansson", "1984-11-22", "American"),
    ("Elizabeth Olsen", "1989-02-16", "American"),
    ("Zoe Saldana", "1978-06-19", "American"),
    ("Margot Robbie", "1990-07-02", "Australian"),
    ("Charlize Theron", "1975-08-07", "South African"),
    ("Gal Gadot", "1985-04-30", "Israeli"),
    ("Wonder Woman", "1985-04-30", "Israeli"),
    ("Angelina Jolie", "1975-06-04", "American"),
    ("Jennifer Aniston", "1969-02-11", "American"),
    ("Jennifer Lawrence", "1990-08-15", "American"),
    ("Emma Stone", "1988-11-06", "American"),
    ("Emma Watson", "1990-04-15", "British"),
    ("Kristen Stewart", "1990-04-09", "American"),
    ("Blake Lively", "1987-08-25", "American"),
    ("Natalie Portman", "1981-06-09", "Israeli"),
]

def seed_celebrities():
    """Seed 100 celebrities into DynamoDB."""
    print(f"Seeding {len(CELEBRITIES)} celebrities into {table_name}...")

    success = 0
    errors = 0

    for idx, (name, birth_date, nationality) in enumerate(CELEBRITIES, 1):
        celebrity_id = f"celeb_{idx:03d}"

        item = {
            'celebrity_id': celebrity_id,
            'source_type#timestamp': f"metadata#{datetime.utcnow().isoformat()}Z",
            'id': celebrity_id,  # Simple ID for metadata
            'name': name,
            'birth_date': birth_date,
            'nationality': nationality,
            'occupation': 'Actor/Actress',
            'raw_text': None,
            'source': 'phase-1-metadata',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'weight': None,
            'sentiment': None,
            'metadata': {
                'scraper_name': 'phase-1-seed',
                'source_type': 'metadata',
                'processed': False,
            }
        }

        try:
            table.put_item(Item=item)
            success += 1
            if idx % 20 == 0:
                print(f"  [{idx}/{len(CELEBRITIES)}] Seeded {success} celebrities...")
        except Exception as e:
            errors += 1
            print(f"  ✗ Error seeding {name}: {str(e)}")

    print(f"\n✓ Seeding complete: {success}/{len(CELEBRITIES)} successful")
    if errors > 0:
        print(f"✗ {errors} errors encountered")

    return success == len(CELEBRITIES)

if __name__ == '__main__':
    success = seed_celebrities()

    # Verify
    response = table.scan(Select='COUNT')
    print(f"\nDynamoDB table now contains {response['Count']} items")
    exit(0 if success else 1)
