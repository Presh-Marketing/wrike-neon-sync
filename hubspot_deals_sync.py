#!/usr/bin/env python3
"""
HubSpot Deals Sync Script
Comprehensive sync of deal data from HubSpot to PostgreSQL database
with full property mapping and error handling.
"""

import os
import sys
import logging
import requests
import psycopg2
from datetime import datetime
import argparse
from typing import Dict, Any, Optional, List

# Setup logging
os.makedirs('logs', exist_ok=True)  # Ensure logs directory exists
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/hubspot_deals_sync.log')
    ]
)
logger = logging.getLogger(__name__)

class HubSpotDealsSync:
    def __init__(self):
        """Initialize the sync client with configuration."""
        self.hubspot_token = os.getenv('HUBSPOT_API_TOKEN')
        if not self.hubspot_token:
            raise ValueError("HUBSPOT_API_TOKEN environment variable not set")
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('NEON_HOST'),
            'database': os.getenv('NEON_DATABASE'),
            'user': os.getenv('NEON_USER'),
            'password': os.getenv('NEON_PASSWORD'),
            'port': os.getenv('NEON_PORT', '5432'),
            'sslmode': 'require'
        }
        
        # Validate database config
        missing_db_vars = [k for k, v in self.db_config.items() if not v and k != 'sslmode']
        if missing_db_vars:
            raise ValueError(f"Missing database environment variables: {missing_db_vars}")
        
        self.base_url = "https://api.hubapi.com/crm/v3/objects/deals"
        self.headers = {
            'Authorization': f'Bearer {self.hubspot_token}',
            'Content-Type': 'application/json'
        }
        
        # Portal ID for consistency
        self.portal_id = 1849303
        
        # Track statistics
        self.stats = {
            'total_deals': 0,
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }

    def safe_string(self, value: Any, max_length: int = None) -> Optional[str]:
        """Safely convert value to string with optional length limit."""
        if value is None:
            return None
        
        str_value = str(value).strip()
        if not str_value:
            return None
            
        if max_length and len(str_value) > max_length:
            str_value = str_value[:max_length]
            
        return str_value

    def safe_number(self, value: Any) -> Optional[float]:
        """Safely convert value to number."""
        if value is None or value == '':
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def safe_integer(self, value: Any) -> Optional[int]:
        """Safely convert value to integer."""
        if value is None or value == '':
            return None
        
        try:
            return int(float(value))
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
        
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            return None

    def safe_datetime(self, value: Any) -> Optional[str]:
        """Safely convert value to datetime string."""
        if value is None or value == '':
            return None
        
        try:
            # Handle timestamp in milliseconds
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                timestamp = int(value) / 1000 if int(value) > 1e10 else int(value)
                dt = datetime.fromtimestamp(timestamp)
                return dt.isoformat()
            
            # Handle ISO strings
            if isinstance(value, str):
                # Clean up the string
                value = value.strip()
                if 'T' in value:
                    return value
                    
        except (ValueError, TypeError, OSError):
            pass
        
        return None

    def get_deals_batch(self, after: str = None, limit: int = 100) -> Dict[str, Any]:
        """Fetch a batch of deals from HubSpot API."""
        # Comprehensive property list for deals
        properties = [
            # Core deal properties
            'dealname', 'description', 'amount', 'amount_in_home_currency', 'closedate', 'createdate',
            'dealstage', 'dealtype', 'pipeline', 'deal_currency_code', 'closed_lost_reason', 'closed_won_reason',
            'hubspot_owner_id', 'hubspot_team_id', 'hs_priority',
            
            # Financial metrics
            'hs_acv', 'hs_arr', 'hs_mrr', 'hs_tcv', 'hs_exchange_rate', 'hs_forecast_amount',
            'hs_forecast_probability', 'hs_projected_amount', 'hs_projected_amount_in_home_currency',
            'hs_deal_stage_probability', 'hs_likelihood_to_close', 'hs_predicted_amount',
            'hs_predicted_amount_in_home_currency',
            
            # Deal scoring & analytics
            'hs_deal_score', 'hs_closed_amount', 'hs_closed_amount_in_home_currency',
            'hs_open_amount_in_home_currency', 'days_to_close', 'hs_days_to_close_raw', 'hs_duration',
            
            # Ownership & teams
            'hs_all_owner_ids', 'hs_all_team_ids', 'hs_owning_teams', 'hs_shared_team_ids',
            'hs_shared_user_ids', 'hs_all_collaborator_owner_ids', 'hubspot_owner_assigneddate',
            
            # Deal status & flags
            'hs_is_closed', 'hs_is_closed_won', 'hs_is_closed_lost', 'hs_is_deal_split',
            'hs_is_active_shared_deal', 'hs_read_only', 'hs_was_imported',
            
            # Contact & activity tracking
            'num_associated_contacts', 'num_contacted_notes', 'num_notes', 'notes_last_contacted',
            'notes_last_updated', 'notes_next_activity_date', 'hs_latest_meeting_activity',
            'hs_next_step', 'hs_next_step_updated_at',
            
            # Meeting information
            'engagements_last_meeting_booked', 'engagements_last_meeting_booked_campaign',
            'engagements_last_meeting_booked_medium', 'engagements_last_meeting_booked_source',
            'hs_next_meeting_id', 'hs_next_meeting_name', 'hs_next_meeting_start_time',
            
            # System fields
            'hs_object_id', 'hs_created_by_user_id', 'hs_updated_by_user_id', 'hs_createdate',
            'hs_lastmodifieddate', 'hs_object_source', 'hs_object_source_detail_1', 'hs_object_source_detail_2',
            'hs_object_source_detail_3', 'hs_object_source_id', 'hs_object_source_user_id',
            'hs_source_object_id', 'hs_unique_creation_key', 'hs_merged_object_ids',
            
            # Marketing & campaign attribution
            'hs_campaign', 'hs_manual_campaign_ids', 'hs_tag_ids',
            
            # Predictive analytics features
            'hs_number_of_call_engagements', 'hs_number_of_inbound_calls', 'hs_number_of_outbound_calls',
            'hs_number_of_scheduled_meetings', 'hs_number_of_overdue_tasks', 'hs_average_call_duration',
            
            # Traffic source analytics
            'hs_analytics_source', 'hs_analytics_source_data_1', 'hs_analytics_source_data_2',
            'hs_analytics_latest_source', 'hs_analytics_latest_source_data_1', 'hs_analytics_latest_source_data_2',
            'hs_analytics_latest_source_timestamp', 'hs_analytics_latest_source_company',
            'hs_analytics_latest_source_contact', 'hs_analytics_latest_source_data_1_company',
            'hs_analytics_latest_source_data_2_company', 'hs_analytics_latest_source_data_1_contact',
            'hs_analytics_latest_source_data_2_contact', 'hs_analytics_latest_source_timestamp_company',
            'hs_analytics_latest_source_timestamp_contact',
            
            # Financial/accounting data
            'budget_gross_profit', 'cost_hard_cost', 'cost_labor', 'gross_profit', 'margin_',
            'invoice_amount', 'invoice_status', 'invoice_number', 'invoice_recipient', 'invoice_due_date',
            'invoices_created', 'payment_type', 'invoiced__all', 'sum_of_all_invoices', 'of_invoices',
            'total_amount_per_invoice', 'recent_invoice_id',
            
            # Commission fields
            'commission_net_new', 'commission_net_new_exec', 'commission_up_sell_team',
            'commission_up_sell_exec', 'commission_team_up_sell', 'commission_exec_up_sell',
            
            # Project hard costs
            'project_hard_cost_total', 'project_hard_cost_paid_media', 'project_hard_cost_print',
            'project_hard_cost_software', 'project_hard_cost_travel', 'hard_cost_contractors', 'media_budget',
            
            # Integration fields
            'wrike_project_id', 'wrike_client_id', 'quickbooks_customer_id', 'quickbooksprojectid',
            'qb_customer_id', 'google_drive_id', 'gdrive_company_id', 'ziflow_company_id',
            'ziflow_id___company', 'ziflow_internal_review_id', 'companyid_hs_sync',
            'create_gdrive_folder', 'line_items_added',
            
            # Revenue tracking
            'mrr', 'software_budget', 'forecast_percentage', 'forecast_revenue', 'project_start_date',
            'project_complete_date', 'invoicing_terms', 'retainer_timeframe',
            
            # Line items
            'line_items__cost', 'line_items__margin', 'line_items__revenue', 'hs_num_of_associated_line_items',
            
            # Recurring revenue
            'recurring_revenue_amount', 'recurring_revenue_deal_type', 'recurring_revenue_inactive_date',
            'recurring_revenue_inactive_reason',
            
            # Business-specific fields
            'company_name', 'bidtype', 'billing_email', 'executive_summary', 'primary_approver',
            'marketing_coordinator', 'team', 'project_owner', 'project_type', 'lost_reason',
            'renewal_created', 'approval', 'co_marketing_partner',
            
            # Stage tracking (key ones)
            'hs_v2_date_entered_current_stage', 'hs_v2_time_in_current_stage',
            'hs_date_entered_closedwon', 'hs_date_entered_closedlost', 'hs_date_exited_closedwon',
            'hs_date_exited_closedlost', 'hs_time_in_closedwon', 'hs_time_in_closedlost',
            
            # Forecast & sales process
            'hs_manual_forecast_category', 'hs_deal_amount_calculation_preference',
            'hs_notes_next_activity_type', 'hs_primary_associated_company', 'hs_net_pipeline_impact',
            'hs_latest_approval_status', 'hs_latest_approval_status_approval_id',
            
            # Program/partnership
            'program', 'cisco_geo_id', 'program_partner__status', 'deal_registration_hubspot_shared_selling',
            'deal_registration_most_likely_hubspot_product_s_', 'hs_synced_deal_owner_name_and_email'
        ]
        
        params = {
            'limit': limit,
            'properties': ','.join(properties)
        }
        
        if after:
            params['after'] = after
        
        try:
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching deals: {e}")
            raise

    def map_deal_properties(self, deal: Dict[str, Any]) -> Dict[str, Any]:
        """Map HubSpot deal properties to database columns."""
        props = deal.get('properties', {})
        
        mapped = {
            'id': int(deal['id']),
            'portal_id': self.portal_id,
            
            # Core deal information
            'property_dealname': self.safe_string(props.get('dealname')),
            'property_description': self.safe_string(props.get('description')),
            'property_amount': self.safe_number(props.get('amount')),
            'property_amount_in_home_currency': self.safe_number(props.get('amount_in_home_currency')),
            'property_closedate': self.safe_datetime(props.get('closedate')),
            'property_createdate': self.safe_datetime(props.get('createdate')),
            'property_dealstage': self.safe_string(props.get('dealstage')),
            'property_dealtype': self.safe_string(props.get('dealtype')),
            'property_pipeline': self.safe_string(props.get('pipeline')),
            'property_deal_currency_code': self.safe_string(props.get('deal_currency_code')),
            'property_closed_lost_reason': self.safe_string(props.get('closed_lost_reason')),
            'property_closed_won_reason': self.safe_string(props.get('closed_won_reason')),
            'property_hubspot_owner_id': self.safe_integer(props.get('hubspot_owner_id')),
            'property_hubspot_team_id': self.safe_integer(props.get('hubspot_team_id')),
            'property_hs_priority': self.safe_string(props.get('hs_priority')),
            
            # Financial metrics
            'property_hs_acv': self.safe_number(props.get('hs_acv')),
            'property_hs_arr': self.safe_number(props.get('hs_arr')),
            'property_hs_mrr': self.safe_number(props.get('hs_mrr')),
            'property_hs_tcv': self.safe_number(props.get('hs_tcv')),
            'property_hs_exchange_rate': self.safe_number(props.get('hs_exchange_rate')),
            'property_hs_forecast_amount': self.safe_number(props.get('hs_forecast_amount')),
            'property_hs_forecast_probability': self.safe_number(props.get('hs_forecast_probability')),
            'property_hs_projected_amount': self.safe_number(props.get('hs_projected_amount')),
            'property_hs_projected_amount_in_home_currency': self.safe_number(props.get('hs_projected_amount_in_home_currency')),
            'property_hs_deal_stage_probability': self.safe_number(props.get('hs_deal_stage_probability')),
            'property_hs_likelihood_to_close': self.safe_number(props.get('hs_likelihood_to_close')),
            'property_hs_predicted_amount': self.safe_number(props.get('hs_predicted_amount')),
            'property_hs_predicted_amount_in_home_currency': self.safe_number(props.get('hs_predicted_amount_in_home_currency')),
            
            # Deal scoring & analytics
            'property_hs_deal_score': self.safe_number(props.get('hs_deal_score')),
            'property_hs_closed_amount': self.safe_number(props.get('hs_closed_amount')),
            'property_hs_closed_amount_in_home_currency': self.safe_number(props.get('hs_closed_amount_in_home_currency')),
            'property_hs_open_amount_in_home_currency': self.safe_number(props.get('hs_open_amount_in_home_currency')),
            'property_days_to_close': self.safe_number(props.get('days_to_close')),
            'property_hs_days_to_close_raw': self.safe_number(props.get('hs_days_to_close_raw')),
            'property_hs_duration': self.safe_number(props.get('hs_duration')),
            
            # Ownership & teams 
            'property_hs_all_owner_ids': self.safe_string(props.get('hs_all_owner_ids')),
            'property_hs_all_team_ids': self.safe_string(props.get('hs_all_team_ids')),
            'property_hs_owning_teams': self.safe_string(props.get('hs_owning_teams')),
            'property_hs_shared_team_ids': self.safe_string(props.get('hs_shared_team_ids')),
            'property_hs_shared_user_ids': self.safe_string(props.get('hs_shared_user_ids')),
            'property_hs_all_collaborator_owner_ids': self.safe_string(props.get('hs_all_collaborator_owner_ids')),
            'property_hubspot_owner_assigneddate': self.safe_datetime(props.get('hubspot_owner_assigneddate')),
            
            # Deal status & flags
            'property_hs_is_closed': self.safe_boolean(props.get('hs_is_closed')),
            'property_hs_is_closed_won': self.safe_boolean(props.get('hs_is_closed_won')),
            'property_hs_is_closed_lost': self.safe_boolean(props.get('hs_is_closed_lost')),
            'property_hs_is_deal_split': self.safe_boolean(props.get('hs_is_deal_split')),
            'property_hs_is_active_shared_deal': self.safe_boolean(props.get('hs_is_active_shared_deal')),
            'property_hs_read_only': self.safe_boolean(props.get('hs_read_only')),
            'property_hs_was_imported': self.safe_boolean(props.get('hs_was_imported')),
            
            # Contact & activity tracking
            'property_num_associated_contacts': self.safe_integer(props.get('num_associated_contacts')),
            'property_num_contacted_notes': self.safe_integer(props.get('num_contacted_notes')),
            'property_num_notes': self.safe_integer(props.get('num_notes')),
            'property_notes_last_contacted': self.safe_datetime(props.get('notes_last_contacted')),
            'property_notes_last_updated': self.safe_datetime(props.get('notes_last_updated')),
            'property_notes_next_activity_date': self.safe_datetime(props.get('notes_next_activity_date')),
            'property_hs_latest_meeting_activity': self.safe_datetime(props.get('hs_latest_meeting_activity')),
            'property_hs_next_step': self.safe_string(props.get('hs_next_step')),
            'property_hs_next_step_updated_at': self.safe_datetime(props.get('hs_next_step_updated_at')),
            
            # Meeting information
            'property_engagements_last_meeting_booked': self.safe_datetime(props.get('engagements_last_meeting_booked')),
            'property_engagements_last_meeting_booked_campaign': self.safe_string(props.get('engagements_last_meeting_booked_campaign')),
            'property_engagements_last_meeting_booked_medium': self.safe_string(props.get('engagements_last_meeting_booked_medium')),
            'property_engagements_last_meeting_booked_source': self.safe_string(props.get('engagements_last_meeting_booked_source')),
            'property_hs_next_meeting_id': self.safe_integer(props.get('hs_next_meeting_id')),
            'property_hs_next_meeting_name': self.safe_string(props.get('hs_next_meeting_name')),
            'property_hs_next_meeting_start_time': self.safe_datetime(props.get('hs_next_meeting_start_time')),
            
            # System fields
            'property_hs_object_id': self.safe_integer(props.get('hs_object_id')),
            'property_hs_created_by_user_id': self.safe_integer(props.get('hs_created_by_user_id')),
            'property_hs_updated_by_user_id': self.safe_integer(props.get('hs_updated_by_user_id')),
            'property_hs_createdate': self.safe_datetime(props.get('hs_createdate')),
            'property_hs_lastmodifieddate': self.safe_datetime(props.get('hs_lastmodifieddate')),
            'property_hs_object_source': self.safe_string(props.get('hs_object_source')),
            'property_hs_object_source_detail_1': self.safe_string(props.get('hs_object_source_detail_1')),
            'property_hs_object_source_detail_2': self.safe_string(props.get('hs_object_source_detail_2')),
            'property_hs_object_source_detail_3': self.safe_string(props.get('hs_object_source_detail_3')),
            'property_hs_object_source_id': self.safe_string(props.get('hs_object_source_id')),
            'property_hs_object_source_user_id': self.safe_integer(props.get('hs_object_source_user_id')),
            'property_hs_source_object_id': self.safe_integer(props.get('hs_source_object_id')),
            'property_hs_unique_creation_key': self.safe_string(props.get('hs_unique_creation_key')),
            'property_hs_merged_object_ids': self.safe_string(props.get('hs_merged_object_ids')),
            
            # Marketing & campaign attribution
            'property_hs_campaign': self.safe_string(props.get('hs_campaign')),
            'property_hs_manual_campaign_ids': self.safe_integer(props.get('hs_manual_campaign_ids')),
            'property_hs_tag_ids': self.safe_string(props.get('hs_tag_ids')),
            
            # Predictive analytics features
            'property_hs_number_of_call_engagements': self.safe_integer(props.get('hs_number_of_call_engagements')),
            'property_hs_number_of_inbound_calls': self.safe_integer(props.get('hs_number_of_inbound_calls')),
            'property_hs_number_of_outbound_calls': self.safe_integer(props.get('hs_number_of_outbound_calls')),
            'property_hs_number_of_scheduled_meetings': self.safe_integer(props.get('hs_number_of_scheduled_meetings')),
            'property_hs_number_of_overdue_tasks': self.safe_integer(props.get('hs_number_of_overdue_tasks')),
            'property_hs_average_call_duration': self.safe_number(props.get('hs_average_call_duration')),
            
            # Analytics
            'property_hs_analytics_source': self.safe_string(props.get('hs_analytics_source')),
            'property_hs_analytics_source_data_1': self.safe_string(props.get('hs_analytics_source_data_1')),
            'property_hs_analytics_source_data_2': self.safe_string(props.get('hs_analytics_source_data_2')),
            'property_hs_analytics_latest_source': self.safe_string(props.get('hs_analytics_latest_source')),
            'property_hs_analytics_latest_source_data_1': self.safe_string(props.get('hs_analytics_latest_source_data_1')),
            'property_hs_analytics_latest_source_data_2': self.safe_string(props.get('hs_analytics_latest_source_data_2')),
            'property_hs_analytics_latest_source_timestamp': self.safe_datetime(props.get('hs_analytics_latest_source_timestamp')),
            'property_hs_analytics_latest_source_company': self.safe_string(props.get('hs_analytics_latest_source_company')),
            'property_hs_analytics_latest_source_contact': self.safe_string(props.get('hs_analytics_latest_source_contact')),
            'property_hs_analytics_latest_source_data_1_company': self.safe_string(props.get('hs_analytics_latest_source_data_1_company')),
            'property_hs_analytics_latest_source_data_2_company': self.safe_string(props.get('hs_analytics_latest_source_data_2_company')),
            'property_hs_analytics_latest_source_data_1_contact': self.safe_string(props.get('hs_analytics_latest_source_data_1_contact')),
            'property_hs_analytics_latest_source_data_2_contact': self.safe_string(props.get('hs_analytics_latest_source_data_2_contact')),
            'property_hs_analytics_latest_source_timestamp_company': self.safe_datetime(props.get('hs_analytics_latest_source_timestamp_company')),
            'property_hs_analytics_latest_source_timestamp_contact': self.safe_datetime(props.get('hs_analytics_latest_source_timestamp_contact')),
        }
        
        # Add financial/accounting fields
        financial_fields = [
            'budget_gross_profit', 'cost_hard_cost', 'cost_labor', 'gross_profit', 'margin_',
            'invoice_amount', 'invoiced__all', 'sum_of_all_invoices', 'total_amount_per_invoice',
            'commission_net_new', 'commission_net_new_exec', 'commission_up_sell_team',
            'commission_up_sell_exec', 'commission_team_up_sell', 'commission_exec_up_sell',
            'project_hard_cost_total', 'project_hard_cost_paid_media', 'project_hard_cost_print',
            'project_hard_cost_software', 'project_hard_cost_travel', 'hard_cost_contractors',
            'media_budget', 'mrr', 'software_budget', 'forecast_percentage', 'forecast_revenue',
            'line_items__cost', 'line_items__margin', 'line_items__revenue', 'recurring_revenue_amount'
        ]
        
        for field in financial_fields:
            mapped[f'property_{field}'] = self.safe_number(props.get(field))
        
        # Add string fields
        string_fields = [
            'invoice_status', 'invoice_number', 'invoice_recipient', 'invoices_created', 'payment_type',
            'recent_invoice_id', 'wrike_project_id', 'wrike_client_id', 'quickbooks_customer_id',
            'quickbooksprojectid', 'qb_customer_id', 'google_drive_id', 'gdrive_company_id',
            'ziflow_company_id', 'ziflow_id___company', 'ziflow_internal_review_id', 'create_gdrive_folder',
            'line_items_added', 'invoicing_terms', 'retainer_timeframe', 'recurring_revenue_deal_type',
            'recurring_revenue_inactive_reason', 'company_name', 'bidtype', 'billing_email',
            'executive_summary', 'primary_approver', 'marketing_coordinator', 'team', 'project_owner',
            'project_type', 'lost_reason', 'renewal_created', 'approval', 'co_marketing_partner',
            'hs_manual_forecast_category', 'hs_deal_amount_calculation_preference', 'hs_notes_next_activity_type',
            'hs_latest_approval_status', 'program', 'cisco_geo_id', 'program_partner__status',
            'deal_registration_hubspot_shared_selling', 'deal_registration_most_likely_hubspot_product_s_',
            'hs_synced_deal_owner_name_and_email'
        ]
        
        for field in string_fields:
            mapped[f'property_{field}'] = self.safe_string(props.get(field))
        
        # Add integer fields
        integer_fields = [
            'of_invoices', 'companyid_hs_sync', 'hs_num_of_associated_line_items',
            'hs_primary_associated_company', 'hs_latest_approval_status_approval_id'
        ]
        
        for field in integer_fields:
            mapped[f'property_{field}'] = self.safe_integer(props.get(field))
        
        # Add datetime fields
        datetime_fields = [
            'invoice_due_date', 'project_start_date', 'project_complete_date', 'recurring_revenue_inactive_date',
            'hs_v2_date_entered_current_stage', 'hs_v2_time_in_current_stage', 'hs_date_entered_closedwon',
            'hs_date_entered_closedlost', 'hs_date_exited_closedwon', 'hs_date_exited_closedlost'
        ]
        
        for field in datetime_fields:
            mapped[f'property_{field}'] = self.safe_datetime(props.get(field))
        
        # Add remaining numeric fields
        numeric_fields = [
            'hs_net_pipeline_impact', 'hs_time_in_closedwon', 'hs_time_in_closedlost'
        ]
        
        for field in numeric_fields:
            mapped[f'property_{field}'] = self.safe_number(props.get(field))
        
        return mapped

    def upsert_deal(self, cursor, deal_data: Dict[str, Any]) -> str:
        """Insert or update a deal in the database."""
        try:
            # Build the upsert query
            columns = list(deal_data.keys())
            placeholders = [f'%({col})s' for col in columns]
            
            # Columns to update on conflict (exclude id and portal_id)
            update_columns = [col for col in columns if col not in ('id', 'portal_id')]
            update_clause = ', '.join([f'{col} = EXCLUDED.{col}' for col in update_columns])
            
            query = f"""
                INSERT INTO hubspot.deal ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT (id) DO UPDATE SET
                {update_clause}
            """
            
            cursor.execute(query, deal_data)
            
            # Check if it was an insert or update
            if cursor.rowcount == 1:
                return 'created'
            else:
                return 'updated'
                
        except Exception as e:
            logger.error(f"Error upserting deal {deal_data.get('id')}: {e}")
            raise

    def sync_deals(self, limit: Optional[int] = None, test_mode: bool = False) -> Dict[str, int]:
        """Sync deals from HubSpot to the database."""
        logger.info("🚀 Starting HubSpot Deals sync...")
        
        try:
            # Connect to database
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False
            cursor = conn.cursor()
            
            after = None
            batch_size = 100
            batch_num = 0
            
            while True:
                batch_num += 1
                
                # Fetch batch of deals
                logger.info(f"Fetching batch {batch_num} (limit: {batch_size})")
                response = self.get_deals_batch(after=after, limit=batch_size)
                
                deals = response.get('results', [])
                if not deals:
                    logger.info("No more deals to process")
                    break
                
                logger.info(f"Processing batch {batch_num} with {len(deals)} deals")
                
                # Process each deal in the batch
                batch_processed = 0
                batch_created = 0
                batch_updated = 0
                batch_errors = 0
                
                try:
                    for deal in deals:
                        try:
                            deal_id = deal['id']
                            deal_name = deal.get('properties', {}).get('dealname', 'Unnamed Deal')
                            
                            logger.info(f"Processing deal: {deal_name} (ID: {deal_id})")
                            
                            # Map the deal properties
                            deal_data = self.map_deal_properties(deal)
                            
                            # Upsert the deal
                            result = self.upsert_deal(cursor, deal_data)
                            
                            if result == 'created':
                                batch_created += 1
                                self.stats['created'] += 1
                            elif result == 'updated':
                                batch_updated += 1
                                self.stats['updated'] += 1
                            
                            batch_processed += 1
                            self.stats['processed'] += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing deal {deal.get('id')}: {e}")
                            batch_errors += 1
                            self.stats['errors'] += 1
                            
                            if not test_mode:
                                # Continue processing other deals
                                continue
                            else:
                                raise
                    
                    # Commit the batch
                    conn.commit()
                    logger.info(f"✅ Batch {batch_num} completed successfully")
                    logger.info(f"   📊 Created: {batch_created}, Updated: {batch_updated}, Errors: {batch_errors}")
                    
                except Exception as e:
                    logger.error(f"Error in batch {batch_num}: {e}")
                    conn.rollback()
                    raise
                
                # Check pagination
                paging = response.get('paging', {})
                next_page = paging.get('next', {})
                after = next_page.get('after')
                
                if not after:
                    logger.info("No more pages to process")
                    break
                
                # Check limit
                if limit and self.stats['processed'] >= limit:
                    logger.info(f"Reached limit of {limit} deals")
                    break
            
            # Final summary
            logger.info("📈 Sync Summary:")
            logger.info(f"   Total Processed: {self.stats['processed']} deals")
            logger.info(f"   Created: {self.stats['created']}")
            logger.info(f"   Updated: {self.stats['updated']}")
            logger.info(f"   Errors: {self.stats['errors']}")
            logger.info(f"   Skipped: {self.stats['skipped']}")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            if 'conn' in locals():
                conn.rollback()
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

def main():
    """Main function to run the sync."""
    parser = argparse.ArgumentParser(description='Sync HubSpot Deals to PostgreSQL')
    parser.add_argument('limit', nargs='?', type=int, help='Limit number of deals to sync (for testing)', default=None)
    parser.add_argument('--limit', dest='limit_flag', type=int, help='Limit number of deals to sync (for testing)')
    parser.add_argument('--test', action='store_true', help='Run in test mode (stops on first error)')
    
    args = parser.parse_args()
    
    # Handle both positional and named limit arguments
    limit = args.limit or args.limit_flag
    
    try:
        # Initialize sync client
        sync_client = HubSpotDealsSync()
        
        # Run the sync
        stats = sync_client.sync_deals(limit=limit, test_mode=args.test)
        
        # Print summary
        print(f"\n🎯 Summary: {stats['processed']} deals processed, {stats['errors']} skipped")
        
        if stats['errors'] > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 