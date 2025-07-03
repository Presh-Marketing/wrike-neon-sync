#!/usr/bin/env python3
"""
HubSpot Companies to Neon DB Sync Script
Standalone script for syncing HubSpot companies to database
"""

import os
import logging
import requests
import psycopg2
import psycopg2.errors
from typing import Dict, List, Optional, Any
from datetime import datetime

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HubSpotCompaniesSync:
    def __init__(self, test_limit=None):
        """Initialize with environment variables."""
        self.hubspot_token = os.getenv('HUBSPOT_API_TOKEN')
        self.hubspot_base_url = 'https://api.hubapi.com/crm/v3'
        self.test_limit = test_limit  # Limit for testing
        
        self.db_config = {
            'host': os.getenv('NEON_HOST'),
            'database': os.getenv('NEON_DATABASE'),
            'user': os.getenv('NEON_USER'),
            'password': os.getenv('NEON_PASSWORD'),
            'port': os.getenv('NEON_PORT', 5432),
            'sslmode': 'require'
        }
        
        # HubSpot property mappings by data type (from actual database schema analysis)
        self.property_mappings = {
            'string': [
                'description', 'airtablecompanyid', 'name', 'country', 'hs_pipeline',
                'timezone', 'hs_object_source', 'city', 'website', 'hs_analytics_source',
                'linkedin_company_page', 'hs_object_source_label', 'hs_analytics_latest_source_data_2',
                'hs_user_ids_of_all_owners', 'hs_analytics_latest_source_data_1', 'hs_all_accessible_team_ids',
                'state', 'hs_analytics_latest_source', 'hs_analytics_source_data_2', 'hs_analytics_source_data_1',
                'domain', 'lifecyclestage', 'hs_object_source_id', 'hs_all_team_ids',
                'hs_annual_revenue_currency_code', 'hs_all_owner_ids', 'linkedinbio', 'address',
                'phone', 'zip', 'type', 'facebook_company_page', 'it_channel_role',
                'industry', 'twitterhandle', 'address_2', 'disti_sales_contact', 'cisco_tier',
                'cisco_distributor', 'disti_marketing_contact', 'manufacturer_partners', 'crm',
                'google_drive_id', 'lqb_qb_sync_2', 'first_conversion_event_name', 'company_abbreviation',
                'program_participation', 'recent_conversion_event_name', 'company_billing_comtact',
                'wrikeid', 'hs_additional_domains', 'hs_merged_object_ids', 'marketing_software',
                'pain_point', 'google_drive_url', 'deal_category_status', 'total_money_raised',
                'hs_last_sales_activity_type', 'cisco_region', 'hs_analytics_last_touch_converting_campaign',
                'hs_analytics_first_touch_converting_campaign', 'website_cms', 'cisco_programs',
                'cisco_specializations', 'maverick_agency', 'cisco_territory', 'hs_avatar_filemanager_key',
                'distributor_sales_divison', 'target_audience_geo', 'target_audience_size',
                'target_audience_vertical', 'business_objective', 'ziflowcompanyid', 'billing_email',
                'ziflow_internal_review_id', 'landing_page_cms', 'service_software', 'blog_cms',
                'hs_object_source_detail_1', 'primary_approver', 'sales_-deprecated-ae6eb54b-5165-422b-b05e-b7e7f9080f79',
                'marketing_process', 'hs_notes_next_activity_type', 'brand_-deprecated-70c5de48-fc37-417b-adec-3a660f2e4225',
                'compan-deprecated-06c95f49-676e-44b2-89ee-b7c240042224', 'compan-deprecated-20769619-75ab-4159-ab5d-3d1afb1fd258',
                'opsai_create_uvp', 'opsai_create_about_us', 'cisco_partner_name', 'create_assessment',
                'cm_notes', 'abm_campaign_enrollment', 'hs_logo_url', 'preferred_meeting_platform',
                'usa_state', 'cm_recommendations', 'ai_files', 'presh_opsai_prompt', 'company_tags',
                'company_legal_name', 'company_twitter_site', 'company_twitter_handle', 'twitterbio',
                'sub_industry', 'reporting_marketing', 'holiday', 'publishing_methods',
                'publishing_preference', 'widely_observed_days', 'technology', 'tracking_and_analytics_tools',
                'services_offered', 'target_geo_states', 'unique_value_proposition', 'instagram_profile',
                'ziflow_client_folder_url', 'web_technologies', 'content_guidelines', 'brand_positioning',
                'marketing_successes', 'marketing_failures', 'ongoing_marketing_efforts',
                'company_strengths', 'about_us', 'company_threats', 'company_opportunities',
                'company_weaknesses', 'competitors', 'tags', 'opsai_crawl', 'company_fit_score_threshold',
                'hs_task_label', 'company_style_guide', 'brand_guide', 'compan-deprecated-a370bd8a-602a-4f67-94bf-114eed337edc',
                'sample_proposals', 'company_logo', 'additional_brand_files', 'brand_design_files',
                'sales_process', 'ziflow_client_folder_url_complete_'
            ],
            'integer': [
                'hubspot_team_id', 'founded_year', 'hubspot_owner_id', 'owneremail',
                'cisco_account_geo_id', 'quickbooksclientid', 'hs_user_ids_of_all_notification_unfollowers',
                'hubdb_id', 'owner_coordinator', 'hubdb_proofs_id', 'clickupcompanyid',
                'snitcher_id', 'hs_all_assigned_business_unit_ids', 'secondary_owner', 'cisco_disti_geo_id'
            ],
            'float': [
                'number_of_tickets', 'num_associated_contacts', 'hs_num_contacts_with_buying_roles',
                'annualrevenue', 'hs_num_decision_makers', 'hs_num_open_deals', 'hs_num_child_companies',
                'hs_num_blockers', 'hs_analytics_num_visits', 'hs_target_account_probability',
                'num_notes', 'hs_time_in_subscriber', 'hs_predictivecontactscore_v_2',
                'hs_analytics_num_page_views', 'hs_updated_by_user_id', 'num_contacted_notes',
                'hs_object_id', 'numberofemployees', 'hs_time_in_other', 'distributor_revenue_12_months_',
                'days_to_close', 'total_revenue', 'num_conversion_events', 'hs_total_deal_value',
                'recent_deal_amount', 'hs_time_in_salesqualifiedlead', 'hs_time_in_opportunity',
                'num_associated_deals', 'hs_time_in_customer', 'hs_created_by_user_id',
                'hs_time_in_lead', 'hs_object_source_user_id', 'hs_time_in_evangelist',
                'hs_time_in_marketingqualifiedlead', 'marketing_employees', 'hs_parent_company_id',
                'company_fit_score'
            ],
            'boolean': [
                'hs_is_target_account', 'is_public', 'hs_was_imported', 'program_partner',
                'company_assets', 'deal_category_retainer', 'dnc_no_marketing_company_wide_',
                'deal_category_project', 'ziflow_create_folder', 'google_drive', 'qb_customer',
                'customer_portal', 'wrike_create_client', 'update_ticket_owner',
                'deal_category_program', 'deal_category_program_partner', 'managed_social',
                'opsai_relationship'
            ],
            'datetime': [
                'hs_analytics_first_timestamp', 'notes_last_updated', 'hs_lastmodifieddate',
                'first_contact_createdate', 'hs_analytics_latest_source_timestamp', 'notes_last_contacted',
                'hubspot_owner_assigneddate', 'createdate', 'hs_sales_email_last_replied',
                'hs_date_entered_subscriber', 'hs_last_sales_activity_timestamp', 'hs_last_sales_activity_date',
                'hs_date_entered_other', 'notes_next_activity_date', 'hs_latest_meeting_activity',
                'hs_last_booked_meeting_date', 'hs_date_exited_opportunity', 'closedate',
                'last_project_end_date', 'hs_date_exited_salesqualifiedlead', 'first_deal_created_date',
                'hs_last_open_task_date', 'hs_date_entered_customer', 'hs_analytics_first_visit_timestamp',
                'hs_analytics_last_timestamp', 'hs_date_entered_opportunity', 'engagements_last_meeting_booked',
                'hs_analytics_last_visit_timestamp', 'hs_date_entered_salesqualifiedlead',
                'recent_conversion_date', 'recent_deal_project_end_date', 'recent_deal_close_date',
                'first_conversion_date', 'hs_date_exited_lead', 'hs_date_entered_lead',
                'hs_date_exited_subscriber', 'hs_last_logged_call_date', 'hs_date_entered_marketingqualifiedlead',
                'hs_date_entered_evangelist', 'hs_date_exited_marketingqualifiedlead',
                'hs_latest_createdate_of_active_subscriptions', 'recent_assessment_date',
                'hs_last_logged_outgoing_email_date'
            ]
        }
        
        # All 254 properties for HubSpot API request (from actual database schema)
        self.all_properties = []
        for prop_type, props in self.property_mappings.items():
            self.all_properties.extend(props)
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.hubspot_token}',
            'Content-Type': 'application/json'
        })

    def safe_string(self, value: Any) -> str:
        """Safely convert value to string and escape single quotes for SQL."""
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
            # HubSpot can return timestamps in different formats
            if isinstance(value, (int, float)):
                # Milliseconds timestamp
                dt = datetime.fromtimestamp(value / 1000)
                return dt.isoformat()
            elif isinstance(value, str):
                # Already in ISO format or similar - PostgreSQL can handle this
                # Just validate it's a reasonable datetime string
                if len(value) > 10 and ('T' in value or '-' in value):
                    return value
        except (ValueError, TypeError):
            pass
        return None

    def get_companies_batch(self, after_token: Optional[str] = None, limit: int = 100) -> Dict:
        """Get a batch of companies from HubSpot API."""
        try:
            params = {
                'properties': ','.join(self.all_properties),
                'limit': limit
            }
            
            if after_token:
                params['after'] = after_token
            
            response = self.session.get(
                f'{self.hubspot_base_url}/objects/companies',
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Retrieved {len(data.get('results', []))} companies from HubSpot API")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching companies from HubSpot: {e}")
            return {}

    def get_all_companies(self) -> List[Dict]:
        """Get all companies from HubSpot with pagination."""
        all_companies = []
        after_token = None
        batch_size = 100
        
        if self.test_limit:
            batch_size = min(batch_size, self.test_limit)
        
        while True:
            batch_data = self.get_companies_batch(after_token, batch_size)
            
            if not batch_data or 'results' not in batch_data:
                break
                
            companies = batch_data['results']
            all_companies.extend(companies)
            
            # Check if we've reached test limit
            if self.test_limit and len(all_companies) >= self.test_limit:
                all_companies = all_companies[:self.test_limit]
                break
            
            # Check for pagination
            paging = batch_data.get('paging', {})
            if 'next' not in paging:
                break
                
            after_token = paging['next'].get('after')
            if not after_token:
                break
        
        logger.info(f"Retrieved total of {len(all_companies)} companies from HubSpot")
        return all_companies

    def connect_db(self):
        """Connect to Neon PostgreSQL database."""
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to Neon database")
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def process_companies(self, companies: List[Dict], conn):
        """Process and sync company data in batches of 25."""
        if self.test_limit:
            companies = companies[:self.test_limit]
            logger.info(f"Limited to {len(companies)} companies for testing")
        
        logger.info(f"Found {len(companies)} companies to process")
        
        # Batch processing configuration
        BATCH_SIZE = 25
        total_batches = (len(companies) + BATCH_SIZE - 1) // BATCH_SIZE
        
        processed_count = 0
        skipped_count = 0
        failed_batches = []
        successful_batches = 0
        
        # Create sync log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sync_log_file = f"hubspot_sync_log_{timestamp}.txt"
        
        with open(sync_log_file, 'w') as log_file:
            log_file.write(f"HubSpot Companies Sync Log\n")
            log_file.write(f"Generated: {datetime.now().isoformat()}\n")
            log_file.write(f"Total Companies to Process: {len(companies)}\n")
            log_file.write(f"Processing in batches of {BATCH_SIZE} companies\n")
            log_file.write(f"Total Batches: {total_batches}\n")
            log_file.write("="*80 + "\n\n")
        
        # Process companies in batches
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(companies))
            batch = companies[start_idx:end_idx]
            batch_company_ids = []
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} companies)")
            
            with open(sync_log_file, 'a') as log_file:
                log_file.write(f"\n--- BATCH {batch_num + 1}/{total_batches} ---\n")
            
            try:
                with conn.cursor() as cursor:
                    batch_processed = 0
                    batch_skipped = 0
                    
                    for i, company in enumerate(batch):
                        try:
                            company_id = company.get('id')
                            batch_company_ids.append(company_id)
                            properties = company.get('properties', {})
                            
                            # Log company being processed
                            company_name = properties.get('name', 'Unknown')
                            company_domain = properties.get('domain', 'N/A')
                            
                            global_idx = start_idx + i + 1
                            logger.info(f"Processing company {global_idx}/{len(companies)}: {company_name} (ID: {company_id})")
                            
                            with open(sync_log_file, 'a') as log_file:
                                log_file.write(f"{global_idx:3d}. ID: {company_id:<12} Name: {company_name:<30} Domain: {company_domain}\n")
                            
                            # Map properties to database fields
                            db_values = {
                                'id': int(company_id) if company_id else None,
                                'portal_id': 1849303,  # From schema analysis - appears to be constant
                                'is_deleted': False,
                                '_fivetran_deleted': False,
                                '_fivetran_synced': datetime.now().isoformat()
                            }
                            
                            # Process all properties with property_ prefix using actual database schema mappings
                            for data_type, properties_list in self.property_mappings.items():
                                for prop_name in properties_list:
                                    value = properties.get(prop_name)
                                    db_field = f'property_{prop_name}'
                                    
                                    # Handle different data types based on actual database schema
                                    if data_type == 'datetime':
                                        db_values[db_field] = self.safe_datetime(value)
                                    elif data_type == 'float':
                                        db_values[db_field] = self.safe_number(value)
                                    elif data_type == 'integer':
                                        # Convert to integer, but allow None for missing values
                                        if value is not None and value != '':
                                            try:
                                                db_values[db_field] = int(float(value))  # Handle string numbers
                                            except (ValueError, TypeError):
                                                db_values[db_field] = None
                                        else:
                                            db_values[db_field] = None
                                    elif data_type == 'boolean':
                                        db_values[db_field] = self.safe_boolean(value)
                                    else:  # string type
                                        db_values[db_field] = self.safe_string(value) if value else None
                            
                            # Build dynamic INSERT statement based on available data
                            non_null_fields = {k: v for k, v in db_values.items() if v is not None}
                            
                            field_names = list(non_null_fields.keys())
                            placeholders = ['%s'] * len(field_names)
                            values = list(non_null_fields.values())
                            
                            # Build ON CONFLICT update clause
                            update_fields = [f"{field} = EXCLUDED.{field}" for field in field_names if field not in ['id']]
                            
                            sql = f"""
                                INSERT INTO hubspot.company ({', '.join(field_names)})
                                VALUES ({', '.join(placeholders)})
                                ON CONFLICT (id) DO UPDATE SET
                                    {', '.join(update_fields)};
                            """
                            
                            cursor.execute(sql, values)
                            batch_processed += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing company {company.get('id')} in batch {batch_num + 1}: {e}")
                            batch_skipped += 1
                            continue
                    
                    # Commit this batch
                    conn.commit()
                    processed_count += batch_processed
                    skipped_count += batch_skipped
                    successful_batches += 1
                    
                    logger.info(f"✅ Batch {batch_num + 1} completed successfully: {batch_processed} processed, {batch_skipped} skipped")
                    
                    with open(sync_log_file, 'a') as log_file:
                        log_file.write(f"✅ Batch {batch_num + 1} SUCCESS: {batch_processed} processed, {batch_skipped} skipped\n")
                        
            except Exception as e:
                # Batch failed - rollback and log the failure
                conn.rollback()
                failed_batch_info = {
                    'batch_number': batch_num + 1,
                    'company_ids': batch_company_ids,
                    'error': str(e),
                    'companies_count': len(batch)
                }
                failed_batches.append(failed_batch_info)
                
                logger.error(f"❌ Batch {batch_num + 1} FAILED: {e}")
                logger.error(f"Failed company IDs: {batch_company_ids}")
                
                with open(sync_log_file, 'a') as log_file:
                    log_file.write(f"❌ Batch {batch_num + 1} FAILED: {e}\n")
                    log_file.write(f"Failed company IDs: {', '.join(map(str, batch_company_ids))}\n")
                
                # Skip all companies in this batch
                skipped_count += len(batch)

        # Create detailed failure report
        failure_report_file = None
        if failed_batches:
            failure_report_file = f"hubspot_sync_failures_{timestamp}.txt"
            with open(failure_report_file, 'w') as report_file:
                report_file.write(f"HubSpot Companies Sync - Failed Batches Report\n")
                report_file.write(f"Generated: {datetime.now().isoformat()}\n")
                report_file.write(f"Total Failed Batches: {len(failed_batches)}\n")
                report_file.write("="*80 + "\n\n")
                
                for failed_batch in failed_batches:
                    report_file.write(f"FAILED BATCH {failed_batch['batch_number']}\n")
                    report_file.write(f"Error: {failed_batch['error']}\n")
                    report_file.write(f"Companies Count: {failed_batch['companies_count']}\n")
                    report_file.write(f"Company IDs that failed to update:\n")
                    for company_id in failed_batch['company_ids']:
                        report_file.write(f"  - {company_id}\n")
                    report_file.write("\n" + "-"*40 + "\n\n")

        return processed_count, skipped_count, sync_log_file, failed_batches, successful_batches, failure_report_file

    def run_sync(self):
        """Main HubSpot companies sync process."""
        logger.info("Starting HubSpot Companies sync...")
        
        try:
            # Connect to database
            conn = self.connect_db()

            try:
                # Get companies from HubSpot
                companies = self.get_all_companies()
                
                if not companies:
                    logger.warning("No companies retrieved from HubSpot")
                    return
                
                processed, skipped, sync_log_file, failed_batches, successful_batches, failure_report_file = self.process_companies(companies, conn)
                
                # Calculate total batches
                BATCH_SIZE = 25
                total_batches = (len(companies) + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info("HubSpot Companies sync completed!")
                logger.info(f"Summary: {processed} companies processed, {skipped} skipped")
                logger.info(f"Batch Summary: {successful_batches}/{total_batches} batches successful")
                
                if failed_batches:
                    logger.warning(f"❌ {len(failed_batches)} batches FAILED!")
                    logger.warning(f"Failed batch report saved to: {failure_report_file}")
                    
                    # Log summary of failed batches
                    for failed_batch in failed_batches:
                        logger.error(f"Batch {failed_batch['batch_number']}: {failed_batch['companies_count']} companies failed - {failed_batch['error']}")
                    
                    print("\n" + "="*60)
                    print("⚠️  SYNC COMPLETED WITH FAILURES")
                    print("="*60)
                    print(f"✅ Successful: {processed} companies in {successful_batches} batches")
                    print(f"❌ Failed: {len(failed_batches)} batches with {sum(batch['companies_count'] for batch in failed_batches)} companies")
                    print(f"📄 Detailed failure report: {failure_report_file}")
                    print("="*60)
                else:
                    logger.info("✅ All batches completed successfully!")
                    print("\n" + "="*60)
                    print("✅ SYNC COMPLETED SUCCESSFULLY")
                    print("="*60)
                    print(f"✅ Processed: {processed} companies in {successful_batches} batches")
                    print(f"⏭️  Skipped: {skipped} companies (individual record errors)")
                    print("="*60)

                logger.info(f"Sync log saved to: {sync_log_file}")

            finally:
                conn.close()
                logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"HubSpot Companies sync failed: {e}")
            raise


def main():
    """Main function."""
    import sys
    
    # Check for test limit argument
    test_limit = None
    if len(sys.argv) > 1:
        try:
            test_limit = int(sys.argv[1])
            logger.info(f"Running in test mode with limit: {test_limit} companies")
        except ValueError:
            logger.error("Test limit must be a number. Usage: python hubspot_companies_sync.py [limit]")
            return
    
    required_vars = ['HUBSPOT_API_TOKEN', 'NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Create a .env file or set these environment variables:")
        for var in missing_vars:
            logger.info(f"  {var}=your_value_here")
        return

    sync = HubSpotCompaniesSync(test_limit=test_limit)
    sync.run_sync()


if __name__ == '__main__':
    main() 