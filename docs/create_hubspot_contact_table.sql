-- HubSpot Contacts Table Schema
-- Based on analysis of 498 HubSpot contact properties
-- Run this SQL to create the hubspot.contact table in your Neon database

-- Create hubspot schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS hubspot;

-- Drop the table if it exists (be careful with this in production)
-- DROP TABLE IF EXISTS hubspot.contact;

-- Create the main hubspot.contact table
CREATE TABLE hubspot.contact (
    -- Core system fields
    id BIGINT PRIMARY KEY,
    portal_id INTEGER,
    is_deleted BOOLEAN DEFAULT FALSE,
    _fivetran_deleted BOOLEAN DEFAULT FALSE,
    _fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core contact information (string fields)
    property_firstname TEXT,
    property_lastname TEXT,
    property_email TEXT,
    property_company TEXT,
    property_phone TEXT,
    property_mobilephone TEXT,
    property_address TEXT,
    property_address_2 TEXT,
    property_city TEXT,
    property_state TEXT,
    property_zip TEXT,
    property_country TEXT,
    property_hs_country_region_code TEXT,
    property_website TEXT,
    property_jobtitle TEXT,
    property_salutation TEXT,
    
    -- Communication & social fields
    property_hs_email_domain TEXT,
    property_hs_whatsapp_phone_number TEXT,
    property_fax TEXT,
    property_hs_calculated_phone_number TEXT,
    property_hs_calculated_mobile_number TEXT,
    property_hs_calculated_phone_number_area_code TEXT,
    property_hs_calculated_phone_number_country_code TEXT,
    property_hs_calculated_phone_number_region_code TEXT,
    property_hs_facebookid TEXT,
    property_hs_googleplusid TEXT,
    property_twitterhandle TEXT,
    property_linkedinbio TEXT,
    property_twitter TEXT,
    property_linkedinconnections TEXT,
    
    -- Professional information
    property_industry TEXT,
    property_seniority TEXT,
    property_hs_job_function TEXT,
    property_school TEXT,
    property_degree TEXT,
    property_field_of_study TEXT,
    property_graduation_date TEXT,
    property_company_size TEXT,
    property_annualrevenue TEXT,
    property_military_status TEXT,
    property_relationship_status TEXT,
    property_gender TEXT,
    property_date_of_birth TEXT,
    
    -- Marketing & analytics fields
    property_hs_analytics_first_url TEXT,
    property_hs_analytics_last_url TEXT,
    property_hs_analytics_first_referrer TEXT,
    property_hs_analytics_last_referrer TEXT,
    property_hs_analytics_source TEXT,
    property_hs_analytics_source_data_1 TEXT,
    property_hs_analytics_source_data_2 TEXT,
    property_hs_latest_source TEXT,
    property_hs_latest_source_data_1 TEXT,
    property_hs_latest_source_data_2 TEXT,
    property_hs_analytics_first_touch_converting_campaign TEXT,
    property_hs_analytics_last_touch_converting_campaign TEXT,
    property_gclid TEXT,
    property_hs_google_click_id TEXT,
    property_hs_facebook_click_id TEXT,
    property_utm_campaign TEXT,
    property_utm_content TEXT,
    property_utm_medium TEXT,
    property_utm_source TEXT,
    property_utm_term TEXT,
    
    -- Content & engagement fields
    property_hs_email_last_email_name TEXT,
    property_hs_last_sales_activity_type TEXT,
    property_hs_last_sms_send_name TEXT,
    property_recent_conversion_event_name TEXT,
    property_first_conversion_event_name TEXT,
    
    -- Lifecycle and status fields
    property_lifecyclestage TEXT,
    property_lead_status TEXT,
    property_hs_lead_status TEXT,
    property_hs_pipeline TEXT,
    property_hs_object_source TEXT,
    property_hs_object_source_id TEXT,
    property_hs_object_source_label TEXT,
    property_hs_object_source_detail_1 TEXT,
    property_hs_avatar_filemanager_key TEXT,
    
    -- Content membership fields
    property_hs_content_membership_email TEXT,
    property_hs_content_membership_notes TEXT,
    property_hs_content_membership_registration_domain_sent_to TEXT,
    property_hs_conversations_visitor_email TEXT,
    property_hs_ip_timezone TEXT,
    
    -- Email marketing fields
    property_hs_email_hard_bounce_reason TEXT,
    property_hs_email_optimal_send_day_of_week TEXT,
    property_hs_email_optimal_send_time_of_day TEXT,
    property_hs_feedback_last_nps_follow_up TEXT,
    property_hs_feedback_last_csat_survey_follow_up TEXT,
    property_hs_full_name_or_email TEXT,
    property_hs_gps_coordinates TEXT,
    property_hs_gps_error TEXT,
    
    -- Campaign & tracking fields
    property_campaign_name TEXT,
    property_caller_id TEXT,
    property_call_recording_link TEXT,
    property_duration TEXT,
    property_formatted_duration TEXT,
    property_first_source_contacted TEXT,
    property_first_tracking_number_contacted TEXT,
    property_form_capture_data TEXT,
    property_grader_website TEXT,
    
    -- Custom integration fields
    property_comments TEXT,
    property_notes TEXT,
    property_message TEXT,
    property_clickup_user_id TEXT,
    property_gdrivecompanyid TEXT,
    property_databox_password TEXT,
    property_work_email TEXT,
    property_personal_email TEXT,
    property_home_phone TEXT,
    property_company_type TEXT,
    property_contact_type TEXT,
    property_customer_type TEXT,
    property_it_channel_role TEXT,
    property_pain_point TEXT,
    property_marketing_software TEXT,
    property_crm TEXT,
    property_tags TEXT,
    property_company_tags TEXT,
    
    -- Enumeration fields (stored as text)
    property_hs_persona TEXT,
    property_blog_default_hubspot_blog_subscription TEXT,
    property_currentlyinworkflow TEXT,
    property_hs_marketable_status TEXT,
    property_hs_marketable_reason_id TEXT,
    property_hs_marketable_reason_type TEXT,
    property_hs_content_membership_status TEXT,
    property_hs_all_contact_vids TEXT,
    
    -- Integer fields
    property_associatedcompanyid INTEGER,
    property_hubspot_owner_id INTEGER,
    property_hubspot_team_id INTEGER,
    property_hs_object_id INTEGER,
    property_hs_created_by_user_id INTEGER,
    property_hs_updated_by_user_id INTEGER,
    property_hs_object_source_user_id INTEGER,
    property_hs_parent_company_id INTEGER,
    property_hs_email_sends INTEGER,
    property_hs_email_opens INTEGER,
    property_hs_email_clicks INTEGER,
    property_hs_email_replies INTEGER,
    property_hs_email_bounces INTEGER,
    property_hs_sequences_enrolled_count INTEGER,
    property_followercount INTEGER,
    property_kloutscoregeneral INTEGER,
    property_twitterprofilephoto INTEGER,
    property_num_associated_deals INTEGER,
    property_num_contacted_notes INTEGER,
    property_num_notes INTEGER,
    property_num_unique_forms_submitted INTEGER,
    
    -- Float/Numeric fields
    property_hs_predictivecontactscore_v2 NUMERIC,
    property_hs_predictivecontactscorebucket NUMERIC,
    property_total_revenue NUMERIC,
    property_days_to_close NUMERIC,
    property_recent_deal_amount NUMERIC,
    property_hs_analytics_num_page_views NUMERIC,
    property_hs_analytics_num_visits NUMERIC,
    property_hs_analytics_num_event_completions NUMERIC,
    property_hs_analytics_average_page_views NUMERIC,
    property_hs_analytics_revenue NUMERIC,
    property_hs_time_in_lead NUMERIC,
    property_hs_time_in_subscriber NUMERIC,
    property_hs_time_in_opportunity NUMERIC,
    property_hs_time_in_customer NUMERIC,
    property_hs_time_in_evangelist NUMERIC,
    property_hs_time_in_other NUMERIC,
    property_hs_time_in_marketingqualifiedlead NUMERIC,
    property_hs_time_in_salesqualifiedlead NUMERIC,
    property_grader_result_overall_score NUMERIC,
    property_grader_result_mobile_score NUMERIC,
    property_grader_result_performance_score NUMERIC,
    property_grader_result_security_score NUMERIC,
    property_grader_result_seo_score NUMERIC,
    
    -- Boolean fields
    property_hs_email_optout BOOLEAN,
    property_hs_email_is_ineligible BOOLEAN,
    property_hs_email_bad_address BOOLEAN,
    property_hs_data_privacy_ads_consent BOOLEAN,
    property_hs_content_membership_email_confirmed BOOLEAN,
    property_hs_created_by_conversations BOOLEAN,
    property_hs_was_imported BOOLEAN,
    property_hs_is_contact BOOLEAN,
    property_hs_is_unworked BOOLEAN,
    property_hs_cross_sell_opportunity BOOLEAN,
    property_fb_ad_clicked BOOLEAN,
    property_hs_contact_enrichment_opt_out BOOLEAN,
    property_hs_currently_enrolled_in_prospecting_agent BOOLEAN,
    property_hs_email_suppression_opted_out BOOLEAN,
    property_ip_latlon_accuracy BOOLEAN,
    
    -- DateTime fields
    property_createdate TIMESTAMP WITH TIME ZONE,
    property_lastmodifieddate TIMESTAMP WITH TIME ZONE,
    property_hs_lastmodifieddate TIMESTAMP WITH TIME ZONE,
    property_closedate TIMESTAMP WITH TIME ZONE,
    property_first_conversion_date TIMESTAMP WITH TIME ZONE,
    property_recent_conversion_date TIMESTAMP WITH TIME ZONE,
    property_recent_deal_close_date TIMESTAMP WITH TIME ZONE,
    property_first_deal_created_date TIMESTAMP WITH TIME ZONE,
    property_hubspot_owner_assigneddate TIMESTAMP WITH TIME ZONE,
    property_associatedcompanylastupdated TIMESTAMP WITH TIME ZONE,
    
    -- Analytics timestamps
    property_hs_analytics_first_timestamp TIMESTAMP WITH TIME ZONE,
    property_hs_analytics_last_timestamp TIMESTAMP WITH TIME ZONE,
    property_hs_analytics_first_visit_timestamp TIMESTAMP WITH TIME ZONE,
    property_hs_analytics_last_visit_timestamp TIMESTAMP WITH TIME ZONE,
    property_hs_latest_source_timestamp TIMESTAMP WITH TIME ZONE,
    property_hs_analytics_latest_source_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Email engagement timestamps
    property_hs_email_first_send_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_last_send_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_first_open_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_last_open_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_first_click_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_last_click_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_first_reply_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_last_reply_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_first_forward_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_last_forward_date TIMESTAMP WITH TIME ZONE,
    property_hs_email_delivered TIMESTAMP WITH TIME ZONE,
    property_hs_email_first_bounce_date TIMESTAMP WITH TIME ZONE,
    
    -- Sales activity timestamps
    property_hs_sales_email_last_replied TIMESTAMP WITH TIME ZONE,
    property_hs_last_sales_activity_date TIMESTAMP WITH TIME ZONE,
    property_hs_last_sales_activity_timestamp TIMESTAMP WITH TIME ZONE,
    property_notes_last_contacted TIMESTAMP WITH TIME ZONE,
    property_notes_last_updated TIMESTAMP WITH TIME ZONE,
    property_notes_next_activity_date TIMESTAMP WITH TIME ZONE,
    property_hs_latest_meeting_activity TIMESTAMP WITH TIME ZONE,
    property_hs_last_booked_meeting_date TIMESTAMP WITH TIME ZONE,
    property_hs_last_logged_call_date TIMESTAMP WITH TIME ZONE,
    property_hs_last_open_task_date TIMESTAMP WITH TIME ZONE,
    property_hs_last_logged_outgoing_email_date TIMESTAMP WITH TIME ZONE,
    property_hs_last_logged_sms_date TIMESTAMP WITH TIME ZONE,
    property_engagements_last_meeting_booked TIMESTAMP WITH TIME ZONE,
    
    -- Lifecycle stage timestamps
    property_hs_date_entered_subscriber TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_subscriber TIMESTAMP WITH TIME ZONE,
    property_hs_date_entered_lead TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_lead TIMESTAMP WITH TIME ZONE,
    property_hs_date_entered_marketingqualifiedlead TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_marketingqualifiedlead TIMESTAMP WITH TIME ZONE,
    property_hs_date_entered_salesqualifiedlead TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_salesqualifiedlead TIMESTAMP WITH TIME ZONE,
    property_hs_date_entered_opportunity TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_opportunity TIMESTAMP WITH TIME ZONE,
    property_hs_date_entered_customer TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_customer TIMESTAMP WITH TIME ZONE,
    property_hs_date_entered_evangelist TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_evangelist TIMESTAMP WITH TIME ZONE,
    property_hs_date_entered_other TIMESTAMP WITH TIME ZONE,
    property_hs_date_exited_other TIMESTAMP WITH TIME ZONE,
    property_hs_latest_createdate_of_active_subscriptions TIMESTAMP WITH TIME ZONE,
    
    -- Content & enrichment timestamps
    property_hs_content_membership_registration_email_sent_date TIMESTAMP WITH TIME ZONE,
    property_hs_contact_enrichment_opt_out_timestamp TIMESTAMP WITH TIME ZONE,
    property_hs_employment_change_detected_date TIMESTAMP WITH TIME ZONE,
    property_hs_job_change_detected_date TIMESTAMP WITH TIME ZONE,
    property_hs_returning_to_office_detected_date TIMESTAMP WITH TIME ZONE
);

-- Create useful indexes
CREATE INDEX idx_hubspot_contact_email ON hubspot.contact (property_email);
CREATE INDEX idx_hubspot_contact_company ON hubspot.contact (property_company);
CREATE INDEX idx_hubspot_contact_owner ON hubspot.contact (property_hubspot_owner_id);
CREATE INDEX idx_hubspot_contact_created ON hubspot.contact (property_createdate);
CREATE INDEX idx_hubspot_contact_modified ON hubspot.contact (property_lastmodifieddate);
CREATE INDEX idx_hubspot_contact_lifecycle ON hubspot.contact (property_lifecyclestage);
CREATE INDEX idx_hubspot_contact_lead_status ON hubspot.contact (property_lead_status);
CREATE INDEX idx_hubspot_contact_fivetran_synced ON hubspot.contact (_fivetran_synced);

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON hubspot.contact TO your_sync_user;

-- Example queries to verify the table structure
-- SELECT COUNT(*) FROM hubspot.contact;
-- SELECT property_email, property_firstname, property_lastname FROM hubspot.contact LIMIT 10;

COMMENT ON TABLE hubspot.contact IS 'HubSpot contacts data synchronized from HubSpot API';
COMMENT ON COLUMN hubspot.contact.id IS 'HubSpot contact ID (primary key)';
COMMENT ON COLUMN hubspot.contact.portal_id IS 'HubSpot portal/account ID';
COMMENT ON COLUMN hubspot.contact._fivetran_synced IS 'Timestamp of last sync operation'; 