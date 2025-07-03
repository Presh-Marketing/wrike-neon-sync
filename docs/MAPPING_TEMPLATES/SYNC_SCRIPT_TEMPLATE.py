#!/usr/bin/env python3
"""
HubSpot Entity Sync Template

This template provides the complete structure for syncing HubSpot entities to Neon database.
Replace [ENTITY] placeholders with actual entity name (e.g., line_items, tickets, products).

Usage:
    python hubspot_entity_sync.py [limit]
    
Example:
    python hubspot_line_items_sync.py 10    # Test with 10 records
    python hubspot_line_items_sync.py       # Full sync

Requirements:
    - All environment variables from .env file
    - Database table hubspot.entity already created
    - HubSpot API permissions for the entity
"""

import os
import sys
import requests
import psycopg2
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HubSpotEntitySync:
    """Sync HubSpot entities to Neon PostgreSQL database."""
    
    def __init__(self):
        # HubSpot API configuration
        self.api_token = os.getenv('HUBSPOT_API_TOKEN')
        self.portal_id = 1849303  # Your HubSpot Portal ID
        
        if not self.api_token:
            raise ValueError("HUBSPOT_API_TOKEN environment variable is required")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # TODO: Replace with actual HubSpot API endpoint
        self.api_url = "https://api.hubapi.com/crm/v3/objects/ENTITY_NAME"
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('NEON_HOST'),
            'database': os.getenv('NEON_DATABASE'),
            'user': os.getenv('NEON_USER'),
            'password': os.getenv('NEON_PASSWORD'),
            'port': int(os.getenv('NEON_PORT', 5432))
        }
        
        # Validate database configuration
        required_db_vars = ['host', 'database', 'user', 'password']
        missing_vars = [var for var in required_db_vars if not self.db_config[var]]
        if missing_vars:
            raise ValueError(f"Missing database environment variables: {missing_vars}")
        
        # Setup logging
        self.setup_logging()
        
        # Property mappings - TODO: Customize based on entity analysis
        self.property_mappings = {
            'string': [
                # Add string properties from analysis
                # Example: 'name', 'description', 'status'
            ],
            'integer': [
                # Add integer properties from analysis  
                # Example: 'hubspot_owner_id', 'deal_id'
            ],
            'numeric': [
                # Add numeric properties from analysis
                # Example: 'amount', 'quantity', 'price'
            ],
            'boolean': [
                # Add boolean properties from analysis
                # Example: 'is_active', 'is_deleted'
            ],
            'datetime': [
                # Add datetime properties from analysis
                # Example: 'hs_createdate', 'hs_lastmodifieddate'
            ]
        }
    
    def setup_logging(self):
        """Configure logging for the sync process."""
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        log_filename = f'logs/hubspot_entity_sync.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Log startup
        self.logger.info("=" * 80)
        self.logger.info("HubSpot Entity Sync Started")
        self.logger.info(f"Portal ID: {self.portal_id}")
        self.logger.info(f"Database: {self.db_config['host']}/{self.db_config['database']}")
    
    def safe_string(self, value):
        """Safely convert value to string, handling None and escaping quotes."""
        if value is None or value == '':
            return None
        
        # Convert to string and escape single quotes
        str_value = str(value).replace("'", "''")
        return str_value
    
    def safe_number(self, value):
        """Safely convert value to number, handling None and invalid values."""
        if value is None or value == '':
            return None
        
        try:
            # Try float first (works for both int and float)
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def safe_boolean(self, value):
        """Safely convert value to boolean, handling various representations."""
        if value is None or value == '':
            return None
        
        if isinstance(value, bool):
            return value
        
        # Handle string representations
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        
        # Handle numeric representations
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            return None
    
    def safe_datetime(self, value):
        """Safely convert HubSpot timestamp to PostgreSQL timestamp."""
        if value is None or value == '':
            return None
        
        try:
            # HubSpot timestamps are in milliseconds
            timestamp_seconds = int(value) / 1000
            dt = datetime.fromtimestamp(timestamp_seconds)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError, OSError):
            return None
    
    def get_all_entities(self, limit=None):
        """Fetch all entities from HubSpot API with pagination."""
        all_entities = []
        after = None
        page_count = 0
        
        # TODO: Customize properties list based on analysis
        properties = [
            # Add all properties you want to sync
            # Example: 'hs_object_id', 'name', 'status', 'amount'
        ]
        
        while True:
            page_count += 1
            self.logger.info(f"Fetching page {page_count} of entities...")
            
            # Build request parameters
            params = {
                'limit': 100,  # Max per page
                'properties': ','.join(properties)
            }
            
            if after:
                params['after'] = after
            
            if limit and len(all_entities) >= limit:
                break
            
            try:
                response = requests.get(self.api_url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                entities = data.get('results', [])
                
                if not entities:
                    break
                
                all_entities.extend(entities)
                self.logger.info(f"Retrieved {len(entities)} entities (total: {len(all_entities)})")
                
                # Check for more pages
                paging = data.get('paging', {})
                after = paging.get('next', {}).get('after')
                
                if not after:
                    break
                
                # Apply limit if specified
                if limit and len(all_entities) >= limit:
                    all_entities = all_entities[:limit]
                    break
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching entities: {e}")
                break
        
        self.logger.info(f"Total entities retrieved: {len(all_entities)}")
        return all_entities
    
    def process_entity_batch(self, entities):
        """Process a batch of entities and insert/update in database."""
        if not entities:
            return 0
        
        success_count = 0
        
        try:
            # Connect to database
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            for entity in entities:
                try:
                    # Extract entity data
                    entity_id = entity.get('id')
                    properties = entity.get('properties', {})
                    
                    # Build field values using property mappings
                    field_values = {
                        'id': entity_id,
                        'portal_id': self.portal_id,
                        '_fivetran_synced': 'NOW()'
                    }
                    
                    # Process string fields
                    for field in self.property_mappings['string']:
                        value = self.safe_string(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process integer fields
                    for field in self.property_mappings['integer']:
                        value = self.safe_number(properties.get(field))
                        if value is not None:
                            value = int(value)
                        field_values[f'property_{field}'] = value
                    
                    # Process numeric fields
                    for field in self.property_mappings['numeric']:
                        value = self.safe_number(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process boolean fields
                    for field in self.property_mappings['boolean']:
                        value = self.safe_boolean(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process datetime fields
                    for field in self.property_mappings['datetime']:
                        value = self.safe_datetime(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Build SQL statement
                    # TODO: Customize table name and conflict resolution
                    sql = self.build_upsert_sql('hubspot.entity', field_values)
                    
                    # Execute SQL
                    cursor.execute(sql)
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing entity {entity_id}: {e}")
                    continue
            
            # Commit all changes for this batch
            conn.commit()
            self.logger.info(f"Successfully processed batch of {success_count} entities")
            
        except psycopg2.Error as e:
            self.logger.error(f"Database error processing batch: {e}")
            if conn:
                conn.rollback()
            return 0
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return success_count
    
    def build_upsert_sql(self, table_name, field_values):
        """Build PostgreSQL upsert SQL statement."""
        # Remove None values and build field lists
        valid_fields = {k: v for k, v in field_values.items() if v is not None}
        
        field_names = list(valid_fields.keys())
        field_placeholders = []
        
        # Build values with proper quoting
        for field, value in valid_fields.items():
            if field == '_fivetran_synced' and value == 'NOW()':
                field_placeholders.append('NOW()')
            elif isinstance(value, str):
                field_placeholders.append(f"'{value}'")
            elif isinstance(value, bool):
                field_placeholders.append('TRUE' if value else 'FALSE')
            elif value is None:
                field_placeholders.append('NULL')
            else:
                field_placeholders.append(str(value))
        
        # Build upsert SQL
        insert_sql = f"""
        INSERT INTO {table_name} ({', '.join(field_names)})
        VALUES ({', '.join(field_placeholders)})
        ON CONFLICT (id) DO UPDATE SET
        """
        
        # Build update clauses (exclude id from updates)
        update_clauses = []
        for field in field_names:
            if field != 'id':  # Don't update the primary key
                update_clauses.append(f"{field} = EXCLUDED.{field}")
        
        sql = insert_sql + ', '.join(update_clauses)
        return sql
    
    def run_sync(self, limit=None):
        """Run the complete sync process."""
        start_time = datetime.now()
        self.logger.info(f"Starting entity sync at {start_time}")
        
        if limit:
            self.logger.info(f"Sync limited to {limit} entities")
        
        try:
            # Step 1: Fetch all entities from HubSpot
            entities = self.get_all_entities(limit=limit)
            
            if not entities:
                self.logger.warning("No entities found to sync")
                return
            
            # Step 2: Process entities in batches
            batch_size = 25
            total_processed = 0
            
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(entities) + batch_size - 1) // batch_size
                
                self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} entities)")
                
                processed = self.process_entity_batch(batch)
                total_processed += processed
                
                # Brief pause between batches
                if i + batch_size < len(entities):
                    import time
                    time.sleep(0.1)
            
            # Step 3: Log completion
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.logger.info("=" * 80)
            self.logger.info("SYNC COMPLETED SUCCESSFULLY")
            self.logger.info(f"Total entities processed: {total_processed}")
            self.logger.info(f"Duration: {duration}")
            self.logger.info(f"Average rate: {total_processed / duration.total_seconds():.2f} entities/second")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"Sync failed with error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise

def main():
    """Main execution function."""
    # Parse command line arguments
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Error: Limit must be a number")
            sys.exit(1)
    
    try:
        # Initialize and run sync
        sync = HubSpotEntitySync()
        sync.run_sync(limit=limit)
        
    except Exception as e:
        print(f"Sync failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 