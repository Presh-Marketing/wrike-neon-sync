#!/usr/bin/env python3
"""
HubSpot Contacts to Neon DB Sync Script
"""

import os
import logging
import requests
import psycopg2
from typing import Dict, List, Optional, Any
from datetime import datetime

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HubSpotContactsSync:
    def __init__(self, test_limit=None):
        """Initialize with environment variables."""
        self.hubspot_token = os.getenv('HUBSPOT_API_TOKEN')
        self.hubspot_base_url = 'https://api.hubapi.com/crm/v3'
        self.test_limit = test_limit
        
        self.db_config = {
            'host': os.getenv('NEON_HOST'),
            'database': os.getenv('NEON_DATABASE'),
            'user': os.getenv('NEON_USER'),
            'password': os.getenv('NEON_PASSWORD'),
            'port': os.getenv('NEON_PORT', 5432),
            'sslmode': 'require'
        }
        
        # Field mappings based on comprehensive HubSpot contacts analysis (498 properties)
        self.property_mappings = {
            'string': [
                # Core contact information
                'firstname', 'lastname', 'email', 'company', 'phone', 'mobilephone',
                'address', 'address_2', 'city', 'state', 'zip', 'country', 'website', 'jobtitle',
                'salutation', 'hs_country_region_code', 'fax',
                
                # Social & digital presence
                'hs_email_domain', 'hs_facebookid', 'hs_googleplusid', 'twitterhandle',
                'linkedinbio', 'twitter', 'linkedinconnections',
                
                # Professional details
                'industry', 'seniority', 'hs_job_function', 'school', 'degree',
                'field_of_study', 'graduation_date', 'company_size', 'annualrevenue',
                
                # Demographics
                'military_status', 'relationship_status', 'gender', 'date_of_birth',
                
                # Marketing & analytics
                'hs_analytics_first_url', 'hs_analytics_last_url', 'hs_analytics_first_referrer',
                'hs_analytics_last_referrer', 'hs_analytics_source', 'hs_analytics_source_data_1',
                'hs_analytics_source_data_2', 'hs_latest_source', 'hs_latest_source_data_1',
                'hs_latest_source_data_2', 'gclid', 'hs_google_click_id', 'hs_facebook_click_id',
                
                # Campaign tracking
                'utm_campaign', 'utm_content', 'utm_medium', 'utm_source', 'utm_term',
                'hs_analytics_first_touch_converting_campaign', 'hs_analytics_last_touch_converting_campaign',
                
                # Email & engagement
                'hs_email_last_email_name', 'hs_last_sales_activity_type', 'hs_last_sms_send_name',
                'recent_conversion_event_name', 'first_conversion_event_name',
                
                # Lifecycle & status
                'lifecyclestage', 'lead_status', 'hs_lead_status', 'hs_pipeline',
                'hs_object_source', 'hs_object_source_id', 'hs_object_source_label',
                'hs_object_source_detail_1', 'hs_avatar_filemanager_key',
                
                # Content & membership
                'hs_content_membership_email', 'hs_content_membership_notes',
                'hs_content_membership_registration_domain_sent_to', 'hs_conversations_visitor_email',
                'hs_ip_timezone', 'hs_email_hard_bounce_reason',
                
                # Custom fields
                'comments', 'notes', 'message', 'clickup_user_id', 'gdrivecompanyid',
                'company_type', 'contact_type', 'customer_type', 'it_channel_role',
                'pain_point', 'marketing_software', 'crm', 'tags', 'company_tags'
            ],
            'integer': [
                # System IDs
                'associatedcompanyid', 'hubspot_owner_id', 'hubspot_team_id',
                'hs_object_id', 'hs_created_by_user_id', 'hs_updated_by_user_id',
                'hs_object_source_user_id',
                
                # Engagement metrics
                'hs_email_sends', 'hs_email_opens', 'hs_email_clicks', 'hs_email_replies',
                'hs_email_bounces', 'followercount', 'num_associated_deals',
                'num_contacted_notes', 'num_notes', 'num_unique_forms_submitted'
            ],
            'float': [
                # Scores & revenue
                'hs_predictivecontactscore_v2', 'total_revenue', 'days_to_close',
                'recent_deal_amount', 'hs_analytics_num_page_views', 'hs_analytics_num_visits',
                'hs_analytics_average_page_views', 'hs_analytics_revenue',
                
                # Lifecycle timing
                'hs_time_in_lead', 'hs_time_in_subscriber', 'hs_time_in_opportunity',
                'hs_time_in_customer', 'hs_time_in_marketingqualifiedlead',
                'hs_time_in_salesqualifiedlead'
            ],
            'boolean': [
                # Email preferences
                'hs_email_optout', 'hs_email_is_ineligible', 'hs_email_bad_address',
                'hs_data_privacy_ads_consent', 'hs_content_membership_email_confirmed',
                
                # System flags
                'hs_created_by_conversations', 'hs_was_imported', 'hs_is_contact',
                'hs_is_unworked', 'fb_ad_clicked', 'hs_contact_enrichment_opt_out'
            ],
            'datetime': [
                # Core timestamps
                'createdate', 'lastmodifieddate', 'hs_lastmodifieddate', 'closedate',
                'first_conversion_date', 'recent_conversion_date', 'hubspot_owner_assigneddate',
                
                # Analytics timestamps
                'hs_analytics_first_timestamp', 'hs_analytics_last_timestamp',
                'hs_analytics_first_visit_timestamp', 'hs_analytics_last_visit_timestamp',
                'hs_latest_source_timestamp',
                
                # Email engagement
                'hs_email_first_send_date', 'hs_email_last_send_date',
                'hs_email_first_open_date', 'hs_email_last_open_date',
                'hs_email_first_click_date', 'hs_email_last_click_date',
                
                # Sales activity
                'hs_last_sales_activity_date', 'hs_last_sales_activity_timestamp',
                'notes_last_contacted', 'notes_last_updated', 'notes_next_activity_date',
                'hs_latest_meeting_activity', 'hs_last_booked_meeting_date',
                'hs_last_logged_call_date', 'hs_last_open_task_date',
                
                # Lifecycle stages
                'hs_date_entered_subscriber', 'hs_date_exited_subscriber',
                'hs_date_entered_lead', 'hs_date_exited_lead',
                'hs_date_entered_marketingqualifiedlead', 'hs_date_exited_marketingqualifiedlead',
                'hs_date_entered_salesqualifiedlead', 'hs_date_exited_salesqualifiedlead',
                'hs_date_entered_opportunity', 'hs_date_exited_opportunity',
                'hs_date_entered_customer', 'hs_date_exited_customer'
            ]
        }
        
        # All properties for API request
        self.all_properties = []
        for prop_type, props in self.property_mappings.items():
            self.all_properties.extend(props)
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.hubspot_token}',
            'Content-Type': 'application/json'
        })

    def safe_string(self, value: Any) -> str:
        """Safely convert value to string."""
        if value is None:
            return ''
        return str(value).replace("'", "''")

    def safe_number(self, value: Any) -> Optional[float]:
        """Safely convert value to number."""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def safe_boolean(self, value: Any) -> Optional[bool]:
        """Safely convert value to boolean."""
        if value is None or value == '':
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def safe_datetime(self, value: Any) -> Optional[str]:
        """Safely convert HubSpot datetime to PostgreSQL format."""
        if value is None or value == '':
            return None
        try:
            if isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(value / 1000)
                return dt.isoformat()
            elif isinstance(value, str):
                if len(value) > 10 and ('T' in value or '-' in value):
                    return value
        except (ValueError, TypeError):
            pass
        return None

    def get_contacts_batch(self, after_token: Optional[str] = None, limit: int = 100) -> Dict:
        """Get a batch of contacts from HubSpot API."""
        try:
            params = {
                'properties': ','.join(self.all_properties),
                'limit': limit
            }
            
            if after_token:
                params['after'] = after_token
            
            response = self.session.get(
                f'{self.hubspot_base_url}/objects/contacts',
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Retrieved {len(data.get('results', []))} contacts from HubSpot API")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching contacts from HubSpot: {e}")
            return {}

    def get_all_contacts(self) -> List[Dict]:
        """Get all contacts from HubSpot with pagination."""
        all_contacts = []
        after_token = None
        batch_size = 100
        
        if self.test_limit:
            batch_size = min(batch_size, self.test_limit)
        
        while True:
            batch_data = self.get_contacts_batch(after_token, batch_size)
            
            if not batch_data or 'results' not in batch_data:
                break
                
            contacts = batch_data['results']
            all_contacts.extend(contacts)
            
            # Check if we've reached test limit
            if self.test_limit and len(all_contacts) >= self.test_limit:
                all_contacts = all_contacts[:self.test_limit]
                break
            
            # Check for pagination
            paging = batch_data.get('paging', {})
            if 'next' not in paging:
                break
                
            after_token = paging['next'].get('after')
            if not after_token:
                break
        
        logger.info(f"Retrieved total of {len(all_contacts)} contacts from HubSpot")
        return all_contacts

    def connect_db(self):
        """Connect to Neon PostgreSQL database."""
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to Neon database")
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def process_contacts(self, contacts: List[Dict], conn):
        """Process and sync contact data in batches of 25."""
        if self.test_limit:
            contacts = contacts[:self.test_limit]
            logger.info(f"Limited to {len(contacts)} contacts for testing")
        
        logger.info(f"Found {len(contacts)} contacts to process")
        
        # Batch processing configuration
        BATCH_SIZE = 25
        total_batches = (len(contacts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        processed_count = 0
        skipped_count = 0
        
        # Process contacts in batches
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(contacts))
            batch = contacts[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} contacts)")
            
            try:
                with conn.cursor() as cursor:
                    for i, contact in enumerate(batch):
                        try:
                            contact_id = contact.get('id')
                            properties = contact.get('properties', {})
                            
                            # Log contact being processed
                            first_name = properties.get('firstname', '')
                            last_name = properties.get('lastname', '')
                            email = properties.get('email', 'N/A')
                            
                            logger.info(f"Processing contact: {first_name} {last_name} (ID: {contact_id})")
                            
                            # Map properties to database fields
                            db_values = {
                                'id': int(contact_id) if contact_id else None,
                                'portal_id': 1849303,  # Your HubSpot portal ID
                                'is_deleted': False,
                                '_fivetran_deleted': False,
                                '_fivetran_synced': datetime.now().isoformat()
                            }
                            
                            # Process all properties with property_ prefix
                            for data_type, properties_list in self.property_mappings.items():
                                for prop_name in properties_list:
                                    value = properties.get(prop_name)
                                    db_field = f'property_{prop_name}'
                                    
                                    if data_type == 'datetime':
                                        db_values[db_field] = self.safe_datetime(value)
                                    elif data_type == 'float':
                                        db_values[db_field] = self.safe_number(value)
                                    elif data_type == 'integer':
                                        if value is not None and value != '':
                                            try:
                                                db_values[db_field] = int(float(value))
                                            except (ValueError, TypeError):
                                                db_values[db_field] = None
                                        else:
                                            db_values[db_field] = None
                                    elif data_type == 'boolean':
                                        db_values[db_field] = self.safe_boolean(value)
                                    else:  # string type
                                        db_values[db_field] = self.safe_string(value) if value else None
                            
                            # Build dynamic INSERT statement
                            non_null_fields = {k: v for k, v in db_values.items() if v is not None}
                            
                            field_names = list(non_null_fields.keys())
                            placeholders = ['%s'] * len(field_names)
                            values = list(non_null_fields.values())
                            
                            # Build ON CONFLICT update clause
                            update_fields = [f"{field} = EXCLUDED.{field}" for field in field_names if field not in ['id']]
                            
                            sql = f"""
                                INSERT INTO hubspot.contact ({', '.join(field_names)})
                                VALUES ({', '.join(placeholders)})
                                ON CONFLICT (id) DO UPDATE SET
                                    {', '.join(update_fields)};
                            """
                            
                            cursor.execute(sql, values)
                            processed_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing contact {contact.get('id')}: {e}")
                            skipped_count += 1
                            continue
                    
                    # Commit this batch
                    conn.commit()
                    logger.info(f"✅ Batch {batch_num + 1} completed successfully")
                        
            except Exception as e:
                conn.rollback()
                logger.error(f"❌ Batch {batch_num + 1} FAILED: {e}")
                skipped_count += len(batch)

        return processed_count, skipped_count

    def run_sync(self):
        """Main sync process."""
        logger.info("Starting HubSpot Contacts sync...")
        
        try:
            # Connect to database
            conn = self.connect_db()

            try:
                # Get contacts from HubSpot
                contacts = self.get_all_contacts()
                
                if not contacts:
                    logger.warning("No contacts retrieved from HubSpot")
                    return
                
                processed, skipped = self.process_contacts(contacts, conn)
                
                logger.info("HubSpot Contacts sync completed!")
                logger.info(f"Summary: {processed} contacts processed, {skipped} skipped")

            finally:
                conn.close()
                logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"HubSpot Contacts sync failed: {e}")
            raise

def main():
    """Main function."""
    import sys
    
    # Check for test limit argument
    test_limit = None
    if len(sys.argv) > 1:
        try:
            test_limit = int(sys.argv[1])
            logger.info(f"Running in test mode with limit: {test_limit} contacts")
        except ValueError:
            logger.error("Test limit must be a number. Usage: python hubspot_contacts_sync.py [limit]")
            return
    
    required_vars = ['HUBSPOT_API_TOKEN', 'NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Create a .env file or set these environment variables:")
        for var in missing_vars:
            logger.info(f"  {var}=your_value_here")
        return

    sync = HubSpotContactsSync(test_limit=test_limit)
    sync.run_sync()

if __name__ == '__main__':
    main() 