#!/usr/bin/env python3
"""
HubSpot Line Items Sync Script

Synchronizes HubSpot line items to Neon PostgreSQL database with deal associations.
Uses HubSpot MCP server for API calls and follows established batch processing patterns.

Usage:
    python hubspot_line_items_sync.py [limit]
    
Example:
    python hubspot_line_items_sync.py 10    # Test with 10 records
    python hubspot_line_items_sync.py       # Full sync

Requirements:
    - Environment variables in .env file
    - Database table hubspot.line_item already created
    - HubSpot API permissions for line items and deals
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

class HubSpotLineItemsSync:
    """Sync HubSpot line items to Neon PostgreSQL database."""
    
    def __init__(self):
        # HubSpot configuration
        self.portal_id = 1849303  # Your HubSpot Portal ID
        
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
        
        # Property mappings for comprehensive field coverage
        self.property_mappings = {
            'string': [
                'name', 'description', 'hs_sku', 'category', 'hs_line_item_currency_code',
                'hs_product_type', 'hs_tax_label', 'hs_tax_category', 'hs_tax_rate_group_id',
                'hs_recurring_billing_period', 'hs_recurring_billing_terms', 'recurringbillingfrequency',
                'hs_billing_start_delay_type', 'hs_pricing_model', 'hs_tier_prices', 'hs_tier_ranges',
                'hs_tiers', 'hs_origin_key', 'hs_group_key', 'hs_images', 'hs_url',
                'hs_all_owner_ids', 'hs_all_team_ids', 'hs_all_accessible_team_ids',
                'hs_owning_teams', 'hs_shared_team_ids', 'hs_shared_user_ids',
                'hs_all_assigned_business_unit_ids', 'hs_object_source', 'hs_object_source_id',
                'hs_object_source_label', 'hs_object_source_detail_1', 'hs_object_source_detail_2',
                'hs_object_source_detail_3', 'hs_merged_object_ids', 'hs_unique_creation_key',
                'hs_user_ids_of_all_notification_followers', 'hs_user_ids_of_all_notification_unfollowers',
                'hs_user_ids_of_all_owners', 'ip__sync_extension__external_source_account_id',
                'ip__sync_extension__external_source_app_id'
            ],
            'integer': [
                'hubspot_owner_id', 'hubspot_team_id', 'hs_created_by_user_id', 'hs_updated_by_user_id',
                'hs_object_source_user_id'
            ],
            'bigint': [
                'hs_product_id', 'hs_variant_id', 'hs_bundle_id', 'hs_external_id', 'hs_object_id'
            ],
            'numeric': [
                'price', 'quantity', 'amount', 'discount', 'hs_discount_percentage',
                'hs_pre_discount_amount', 'hs_total_discount', 'hs_effective_unit_price',
                'tax', 'hs_tax_amount', 'hs_auto_tax_amount', 'hs_tax_rate', 'hs_post_tax_amount',
                'hs_cost_of_goods_sold', 'hs_margin', 'hs_margin_acv', 'hs_margin_arr',
                'hs_margin_mrr', 'hs_margin_tcv', 'hs_acv', 'hs_arr', 'hs_mrr', 'hs_tcv',
                'hs_term_in_months', 'hs_recurring_billing_number_of_payments',
                'hs_billing_start_delay_days', 'hs_billing_start_delay_months',
                'hs_tier_amount', 'hs_position_on_quote', 'points', 'hs_sync_amount',
                'hs_buyer_selected_quantity_min', 'hs_buyer_selected_quantity_max'
            ],
            'boolean': [
                'hs_is_editable_price', 'hs_is_optional', 'hs_read_only', 'hs_was_imported',
                'hs_allow_buyer_selected_quantity'
            ],
            'date': [
                'hs_recurring_billing_start_date', 'hs_recurring_billing_end_date',
                'hs_billing_period_start_date', 'hs_billing_period_end_date'
            ],
            'datetime': [
                'createdate', 'hs_createdate', 'hs_lastmodifieddate', 'hubspot_owner_assigneddate'
            ]
        }
    
    def setup_logging(self):
        """Configure logging for the sync process."""
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f'logs/hubspot_line_items_sync_log_{timestamp}.txt'
        
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
        self.logger.info("HubSpot Line Items Sync Started")
        self.logger.info(f"Portal ID: {self.portal_id}")
        self.logger.info(f"Database: {self.db_config['host']}/{self.db_config['database']}")
        self.logger.info(f"Log file: {log_filename}")
    
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
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def safe_integer(self, value):
        """Safely convert value to integer, handling None and invalid values."""
        if value is None or value == '':
            return None
        
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def safe_boolean(self, value):
        """Safely convert value to boolean, handling various representations."""
        if value is None or value == '':
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        
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
            if isinstance(value, str) and 'T' in value:
                # Already formatted datetime string
                return value
            
            timestamp_seconds = int(value) / 1000
            dt = datetime.fromtimestamp(timestamp_seconds)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError, OSError):
            return None
    
    def safe_date(self, value):
        """Safely convert value to date format."""
        if value is None or value == '':
            return None
        
        try:
            if isinstance(value, str) and '-' in value:
                # Already formatted date string
                return value
            
            # Convert timestamp to date
            timestamp_seconds = int(value) / 1000
            dt = datetime.fromtimestamp(timestamp_seconds)
            return dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError, OSError):
            return None
    
    def get_all_line_items(self, limit=None):
        """Fetch all line items from HubSpot API."""
        self.logger.info("Fetching line items from HubSpot API...")
        
        # Check for API token
        api_token = os.getenv('HUBSPOT_API_TOKEN')
        if not api_token:
            self.logger.error("HUBSPOT_API_TOKEN not found in environment variables")
            return []
        
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        all_line_items = []
        after = None
        page_count = 0
        
        # Comprehensive list of properties to fetch
        properties = [
            'hs_object_id', 'name', 'description', 'hs_sku', 'category', 'hs_line_item_currency_code',
            'hs_product_id', 'hs_product_type', 'hs_variant_id', 'hs_bundle_id',
            'price', 'quantity', 'amount', 'discount', 'hs_discount_percentage',
            'hs_pre_discount_amount', 'hs_total_discount', 'hs_effective_unit_price',
            'tax', 'hs_tax_amount', 'hs_auto_tax_amount', 'hs_tax_rate', 'hs_post_tax_amount',
            'hs_tax_label', 'hs_tax_category', 'hs_tax_rate_group_id',
            'hs_cost_of_goods_sold', 'hs_margin', 'hs_margin_acv', 'hs_margin_arr',
            'hs_margin_mrr', 'hs_margin_tcv', 'hs_acv', 'hs_arr', 'hs_mrr', 'hs_tcv',
            'hs_term_in_months', 'hs_recurring_billing_period', 'hs_recurring_billing_terms',
            'hs_recurring_billing_number_of_payments', 'recurringbillingfrequency',
            'hs_recurring_billing_start_date', 'hs_recurring_billing_end_date',
            'hs_billing_period_start_date', 'hs_billing_period_end_date',
            'hs_billing_start_delay_days', 'hs_billing_start_delay_months', 'hs_billing_start_delay_type',
            'hs_pricing_model', 'hs_tier_amount', 'hs_tier_prices', 'hs_tier_ranges', 'hs_tiers',
            'hs_position_on_quote', 'points', 'hs_external_id', 'hs_sync_amount',
            'hs_origin_key', 'hs_group_key', 'hs_images', 'hs_url',
            'hs_is_editable_price', 'hs_is_optional', 'hs_read_only', 'hs_was_imported',
            'hs_allow_buyer_selected_quantity', 'hs_buyer_selected_quantity_min', 'hs_buyer_selected_quantity_max',
            'hubspot_owner_id', 'hubspot_team_id', 'hs_created_by_user_id', 'hs_updated_by_user_id',
            'hs_object_source', 'hs_object_source_id', 'hs_object_source_label',
            'hs_object_source_detail_1', 'hs_object_source_detail_2', 'hs_object_source_detail_3',
            'hs_object_source_user_id', 'hs_merged_object_ids', 'hs_unique_creation_key',
            'createdate', 'hs_createdate', 'hs_lastmodifieddate', 'hubspot_owner_assigneddate'
        ]
        
        try:
            while True:
                page_count += 1
                self.logger.info(f"Fetching page {page_count} of line items...")
                
                # Build request parameters
                params = {
                    'limit': 100,
                    'properties': ','.join(properties)
                }
                if after:
                    params['after'] = after
                
                # Make API request
                response = requests.get(
                    'https://api.hubapi.com/crm/v3/objects/line_items',
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    self.logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                line_items = data.get('results', [])
                
                if not line_items:
                    self.logger.info("No more line items found")
                    break
                
                all_line_items.extend(line_items)
                self.logger.info(f"Retrieved {len(line_items)} line items (total: {len(all_line_items)})")
                
                # Apply limit if specified
                if limit and len(all_line_items) >= limit:
                    all_line_items = all_line_items[:limit]
                    self.logger.info(f"Reached limit of {limit} line items")
                    break
                
                # Check for more pages
                paging = data.get('paging', {})
                after = paging.get('next', {}).get('after')
                
                if not after:
                    self.logger.info("No more pages available")
                    break
            
            self.logger.info(f"✅ Total line items retrieved: {len(all_line_items)}")
            return all_line_items
            
        except Exception as e:
            self.logger.error(f"Error fetching line items from HubSpot: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def get_line_item_associations(self, line_item_id):
        """Get deal associations for a line item using HubSpot API."""
        try:
            api_token = os.getenv('HUBSPOT_API_TOKEN')
            if not api_token:
                return []
            
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'https://api.hubapi.com/crm/v4/objects/line_items/{line_item_id}/associations/deals',
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                # Log warning but don't fail the entire sync
                self.logger.warning(f"Could not fetch associations for line item {line_item_id}: {response.status_code}")
                return []
            
            data = response.json()
            associations = data.get('results', [])
            
            # Extract deal IDs
            deal_ids = []
            for assoc in associations:
                if assoc.get('toObjectId'):
                    deal_ids.append(assoc['toObjectId'])
            
            if deal_ids:
                self.logger.debug(f"Line item {line_item_id} associated with deals: {deal_ids}")
            
            return deal_ids
            
        except Exception as e:
            self.logger.warning(f"Error fetching associations for line item {line_item_id}: {e}")
            return []
    
    def process_line_item_batch(self, line_items):
        """Process a batch of line items and insert/update in database."""
        if not line_items:
            return 0
        
        success_count = 0
        
        try:
            # Connect to database
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            for line_item in line_items:
                try:
                    # Extract line item data
                    line_item_id = line_item.get('id')
                    properties = line_item.get('properties', {})
                    
                    # Get deal associations
                    deal_associations = self.get_line_item_associations(line_item_id)
                    deal_id = deal_associations[0] if deal_associations else None
                    
                    # Build field values using property mappings
                    field_values = {
                        'id': line_item_id,
                        'portal_id': self.portal_id,
                        'deal_id': deal_id,
                        '_fivetran_synced': 'NOW()'
                    }
                    
                    # Process string fields
                    for field in self.property_mappings['string']:
                        value = self.safe_string(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process integer fields
                    for field in self.property_mappings['integer']:
                        value = self.safe_integer(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process bigint fields
                    for field in self.property_mappings['bigint']:
                        value = self.safe_integer(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process numeric fields
                    for field in self.property_mappings['numeric']:
                        value = self.safe_number(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process boolean fields
                    for field in self.property_mappings['boolean']:
                        value = self.safe_boolean(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process date fields
                    for field in self.property_mappings['date']:
                        value = self.safe_date(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Process datetime fields
                    for field in self.property_mappings['datetime']:
                        value = self.safe_datetime(properties.get(field))
                        field_values[f'property_{field}'] = value
                    
                    # Build SQL statement
                    sql = self.build_upsert_sql('hubspot.line_item', field_values)
                    
                    # Execute SQL
                    cursor.execute(sql)
                    success_count += 1
                    
                    if success_count % 5 == 0:
                        self.logger.info(f"Processed {success_count} line items in current batch")
                    
                except Exception as e:
                    self.logger.error(f"Error processing line item {line_item_id}: {e}")
                    continue
            
            # Commit all changes for this batch
            conn.commit()
            self.logger.info(f"✅ Batch completed successfully: {success_count} line items processed")
            
        except psycopg2.Error as e:
            self.logger.error(f"❌ Database error processing batch: {e}")
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
        self.logger.info(f"Starting line items sync at {start_time}")
        
        if limit:
            self.logger.info(f"Sync limited to {limit} line items")
        
        try:
            # Step 1: Fetch all line items from HubSpot
            line_items = self.get_all_line_items(limit=limit)
            
            if not line_items:
                self.logger.warning("No line items found to sync")
                self.logger.info("Note: MCP server integration needed for actual data fetching")
                return
            
            # Step 2: Process line items in batches
            batch_size = 25
            total_processed = 0
            total_batches = (len(line_items) + batch_size - 1) // batch_size
            
            self.logger.info(f"Processing {len(line_items)} line items in {total_batches} batches")
            
            for i in range(0, len(line_items), batch_size):
                batch = line_items[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} line items)")
                
                processed = self.process_line_item_batch(batch)
                total_processed += processed
                
                # Brief pause between batches
                if i + batch_size < len(line_items):
                    import time
                    time.sleep(0.1)
            
            # Step 3: Log completion
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.logger.info("=" * 80)
            self.logger.info("✅ SYNC COMPLETED SUCCESSFULLY")
            self.logger.info(f"✅ Total line items processed: {total_processed}")
            self.logger.info(f"⏱️ Duration: {duration}")
            if total_processed > 0:
                self.logger.info(f"📈 Average rate: {total_processed / duration.total_seconds():.2f} line items/second")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"❌ Sync failed with error: {e}")
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
            print(f"🧪 Running in test mode with limit: {limit}")
        except ValueError:
            print("❌ Error: Limit must be a number")
            sys.exit(1)
    
    try:
        # Initialize and run sync
        sync = HubSpotLineItemsSync()
        sync.run_sync(limit=limit)
        
        print(f"\n🎉 HubSpot Line Items sync completed!")
        if limit:
            print(f"📝 This was a test run with {limit} line items")
            print(f"🚀 Run without limit for full sync: python hubspot_line_items_sync.py")
        
    except Exception as e:
        print(f"💥 Sync failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 