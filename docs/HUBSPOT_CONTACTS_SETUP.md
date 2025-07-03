# HubSpot Contacts Sync System

This system synchronizes HubSpot contacts to a Neon PostgreSQL database. Based on comprehensive analysis of 498 HubSpot contact properties.

## System Overview

- **HubSpot API Analysis**: Discovered 498 contact properties across 8 data types
- **Database Table**: `hubspot.contact` with comprehensive field mapping
- **Sync Strategy**: Batch processing (25 contacts per batch) with upsert operations
- **Error Handling**: Batch-level rollback with detailed logging

## Property Distribution Analysis

From the HubSpot API analysis:
- **STRING**: 158 properties
- **NUMBER**: 99 properties  
- **DATETIME**: 103 properties
- **BOOLEAN**: 21 properties
- **ENUMERATION**: 98 properties
- **PHONE_NUMBER**: 4 properties
- **UNKNOWN**: 15 properties

## Field Mapping Strategy

All HubSpot properties are mapped to database fields with the `property_` prefix:

### Core Contact Fields
- `firstname` → `property_firstname` (TEXT)
- `lastname` → `property_lastname` (TEXT)
- `email` → `property_email` (TEXT)
- `company` → `property_company` (TEXT)
- `phone` → `property_phone` (TEXT)
- `mobilephone` → `property_mobilephone` (TEXT)

### Address Fields
- `address` → `property_address` (TEXT)
- `city` → `property_city` (TEXT)
- `state` → `property_state` (TEXT)
- `zip` → `property_zip` (TEXT)
- `country` → `property_country` (TEXT)

### Professional Fields
- `jobtitle` → `property_jobtitle` (TEXT)
- `website` → `property_website` (TEXT)

### System IDs (INTEGER)
- `associatedcompanyid` → `property_associatedcompanyid` (INTEGER)
- `hubspot_owner_id` → `property_hubspot_owner_id` (INTEGER)
- `hubspot_team_id` → `property_hubspot_team_id` (INTEGER)

### Scores & Metrics (NUMERIC)
- `hs_predictivecontactscore_v2` → `property_hs_predictivecontactscore_v2` (NUMERIC)
- `total_revenue` → `property_total_revenue` (NUMERIC)
- `days_to_close` → `property_days_to_close` (NUMERIC)

### Flags (BOOLEAN)
- `hs_email_optout` → `property_hs_email_optout` (BOOLEAN)
- `hs_was_imported` → `property_hs_was_imported` (BOOLEAN)

### Important Timestamps (TIMESTAMP WITH TIME ZONE)
- `createdate` → `property_createdate`
- `lastmodifieddate` → `property_lastmodifieddate`
- `closedate` → `property_closedate`
- `first_conversion_date` → `property_first_conversion_date`

## Database Schema

### Core System Fields
```sql
id BIGINT PRIMARY KEY,                     -- HubSpot Contact ID
portal_id INTEGER,                         -- HubSpot Portal ID
is_deleted BOOLEAN DEFAULT FALSE,          -- Deletion flag
_fivetran_deleted BOOLEAN DEFAULT FALSE,   -- Fivetran deletion flag
_fivetran_synced TIMESTAMP WITH TIME ZONE  -- Last sync timestamp
```

### Database Table Creation

```sql
-- Create hubspot schema
CREATE SCHEMA IF NOT EXISTS hubspot;

-- Create the contact table
CREATE TABLE hubspot.contact (
    -- Core system fields
    id BIGINT PRIMARY KEY,
    portal_id INTEGER,
    is_deleted BOOLEAN DEFAULT FALSE,
    _fivetran_deleted BOOLEAN DEFAULT FALSE,
    _fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core contact information
    property_firstname TEXT,
    property_lastname TEXT,
    property_email TEXT,
    property_company TEXT,
    property_phone TEXT,
    property_mobilephone TEXT,
    property_address TEXT,
    property_city TEXT,
    property_state TEXT,
    property_zip TEXT,
    property_country TEXT,
    property_website TEXT,
    property_jobtitle TEXT,
    
    -- System IDs
    property_associatedcompanyid INTEGER,
    property_hubspot_owner_id INTEGER,
    property_hubspot_team_id INTEGER,
    
    -- Scores and metrics
    property_hs_predictivecontactscore_v2 NUMERIC,
    property_total_revenue NUMERIC,
    property_days_to_close NUMERIC,
    
    -- Boolean flags
    property_hs_email_optout BOOLEAN,
    property_hs_was_imported BOOLEAN,
    
    -- Important timestamps
    property_createdate TIMESTAMP WITH TIME ZONE,
    property_lastmodifieddate TIMESTAMP WITH TIME ZONE,
    property_closedate TIMESTAMP WITH TIME ZONE,
    property_first_conversion_date TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_hubspot_contact_email ON hubspot.contact (property_email);
CREATE INDEX idx_hubspot_contact_company ON hubspot.contact (property_company);
CREATE INDEX idx_hubspot_contact_owner ON hubspot.contact (property_hubspot_owner_id);
CREATE INDEX idx_hubspot_contact_created ON hubspot.contact (property_createdate);
CREATE INDEX idx_hubspot_contact_modified ON hubspot.contact (property_lastmodifieddate);
CREATE INDEX idx_hubspot_contact_fivetran_synced ON hubspot.contact (_fivetran_synced);
```

## Setup Instructions

### 1. Environment Variables

Create a `.env` file with the following variables:

```bash
# HubSpot API Configuration
HUBSPOT_API_TOKEN=your_hubspot_api_token_here

# Neon Database Configuration
NEON_HOST=your_neon_host_here.aws.neon.tech
NEON_DATABASE=your_database_name_here
NEON_USER=your_username_here
NEON_PASSWORD=your_password_here
NEON_PORT=5432
```

### 2. Database Setup

1. Connect to your Neon database
2. Run the database schema creation SQL above
3. Verify the table was created: `SELECT COUNT(*) FROM hubspot.contact;`

### 3. Running the Sync

#### Full Sync
```bash
python hubspot_contacts_sync.py
```

#### Test Mode (limit contacts)
```bash
python hubspot_contacts_sync.py 10
```

## Sync Process Details

### Data Flow
1. **Connect to HubSpot API** using HUBSPOT_API_TOKEN
2. **Fetch contact properties** (currently mapped: 19 key properties)
3. **Paginate through contacts** using HubSpot's cursor-based pagination
4. **Process in batches** of 25 contacts for optimal performance
5. **Transform data** using type-safe conversion functions
6. **Upsert to database** using `ON CONFLICT DO UPDATE`

### Error Handling
- **Batch-level transactions**: Each batch of 25 contacts is processed as a single transaction
- **Individual contact errors**: Skip problematic contacts but continue batch processing
- **Batch failures**: Roll back entire batch and log detailed error information
- **Comprehensive logging**: All operations logged with timestamps and contact details

### Data Type Conversions
- **String fields**: Escape single quotes for SQL safety
- **Numbers**: Safe conversion with None handling for missing values
- **Booleans**: Handle various truthy/falsy string representations
- **Timestamps**: Convert HubSpot timestamps (milliseconds) to PostgreSQL TIMESTAMP WITH TIME ZONE

## Extending the Field Mapping

To add more HubSpot properties to the sync:

1. **Add to property_mappings** in `hubspot_contacts_sync.py`:
```python
'string': [
    'existing_fields',
    'new_field_name'  # Add new string field
],
'integer': [
    'existing_fields',
    'new_integer_field'  # Add new integer field
]
```

2. **Add corresponding database column**:
```sql
ALTER TABLE hubspot.contact ADD COLUMN property_new_field_name TEXT;
ALTER TABLE hubspot.contact ADD COLUMN property_new_integer_field INTEGER;
```

3. **Update indexes if needed** for new searchable fields

## Monitoring and Maintenance

### Key Metrics to Monitor
- **Sync frequency**: How often contacts are updated
- **Error rates**: Failed batches or individual contact processing failures
- **Data freshness**: Time since last successful sync
- **Row counts**: Growth in contact database

### Useful Queries
```sql
-- Recent contacts
SELECT property_email, property_firstname, property_lastname, property_createdate 
FROM hubspot.contact 
WHERE property_createdate > NOW() - INTERVAL '7 days'
ORDER BY property_createdate DESC;

-- Sync status
SELECT COUNT(*) as total_contacts, 
       MAX(_fivetran_synced) as last_sync,
       COUNT(CASE WHEN _fivetran_synced > NOW() - INTERVAL '1 day' THEN 1 END) as recent_syncs
FROM hubspot.contact;

-- Contact activity by owner
SELECT property_hubspot_owner_id, COUNT(*) as contact_count
FROM hubspot.contact 
GROUP BY property_hubspot_owner_id 
ORDER BY contact_count DESC;
```

## File Structure

- `hubspot_contacts_sync.py` - Main sync script
- `explore_hubspot_contacts.py` - HubSpot API exploration tool
- `HUBSPOT_CONTACTS_SETUP.md` - This documentation
- Generated files:
  - `hubspot_contacts_analysis_*.json` - Detailed property analysis
  - `hubspot_contacts_summary_*.txt` - Property summary report
  - `hubspot_contacts_sync_log_*.txt` - Sync operation logs

## Next Steps

1. **Run the database schema creation SQL** in your Neon database
2. **Set up environment variables** in `.env` file
3. **Test with limited contacts**: `python hubspot_contacts_sync.py 5`
4. **Run full sync**: `python hubspot_contacts_sync.py`
5. **Schedule regular syncs** (e.g., via cron job or cloud scheduler)
6. **Extend field mappings** based on your specific HubSpot property needs

## Support

For issues with this sync system:
1. Check the generated log files for detailed error information
2. Verify all environment variables are correctly set
3. Ensure HubSpot API token has proper permissions for contacts
4. Check Neon database connectivity and permissions 