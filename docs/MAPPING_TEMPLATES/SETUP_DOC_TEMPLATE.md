# HubSpot [ENTITY] Sync System

This system synchronizes HubSpot [ENTITY] data to a Neon PostgreSQL database. Based on comprehensive analysis of [X] HubSpot [ENTITY] properties.

## System Overview

- **HubSpot API Analysis**: Discovered [X] [ENTITY] properties across [Y] data types
- **Database Table**: `hubspot.[entity]` with comprehensive field mapping
- **Sync Strategy**: Batch processing ([BATCH_SIZE] [ENTITY] per batch) with upsert operations
- **Error Handling**: Batch-level rollback with detailed logging

## Property Distribution Analysis

From the HubSpot API analysis:
- **STRING**: [X] properties
- **NUMBER**: [X] properties  
- **DATETIME**: [X] properties
- **BOOLEAN**: [X] properties
- **ENUMERATION**: [X] properties
- **[OTHER_TYPES]**: [X] properties each

## Field Mapping Strategy

All HubSpot properties are mapped to database fields with the `property_` prefix:

### Core [ENTITY] Fields
```sql
-- Primary identification
property_[key_field] [TYPE],           -- Main identifier/name
property_[description_field] [TYPE],   -- Description/content

-- System IDs
property_hubspot_owner_id INTEGER,     -- Owner ID
property_hubspot_team_id INTEGER,      -- Team ID

-- Relationship fields (customize based on entity)
property_[relationship_id] [TYPE],     -- Link to related entity
```

### Entity-Specific Categories

#### [CATEGORY 1] Fields ([X] fields)
- **[Field Group]**: Core business information
- **Examples**: `property_[field1]`, `property_[field2]`, `property_[field3]`

#### [CATEGORY 2] Fields ([X] fields)  
- **[Field Group]**: Operational data
- **Examples**: `property_[field4]`, `property_[field5]`, `property_[field6]`

#### [CATEGORY 3] Fields ([X] fields)
- **[Field Group]**: Analytics and tracking
- **Examples**: `property_[field7]`, `property_[field8]`, `property_[field9]`

### Important Timestamps (TIMESTAMP WITH TIME ZONE)
- `property_hs_createdate` → Creation timestamp
- `property_hs_lastmodifieddate` → Last modification timestamp
- `property_[other_dates]` → Entity-specific date fields

## Database Schema

### Core System Fields
```sql
id BIGINT PRIMARY KEY,                     -- HubSpot [ENTITY] ID
portal_id INTEGER DEFAULT 1849303,        -- HubSpot Portal ID
is_deleted BOOLEAN DEFAULT FALSE,          -- Deletion flag
_fivetran_deleted BOOLEAN DEFAULT FALSE,   -- Fivetran deletion flag
_fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- Last sync timestamp
```

### Database Table Creation

```sql
-- Create hubspot schema
CREATE SCHEMA IF NOT EXISTS hubspot;

-- Create the [entity] table
CREATE TABLE hubspot.[entity] (
    -- Core system fields
    id BIGINT PRIMARY KEY,
    portal_id INTEGER DEFAULT 1849303,
    is_deleted BOOLEAN DEFAULT FALSE,
    _fivetran_deleted BOOLEAN DEFAULT FALSE,
    _fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core [ENTITY] information
    property_[key_fields] [TYPE],
    
    -- System IDs
    property_hubspot_owner_id INTEGER,
    property_hubspot_team_id INTEGER,
    
    -- Relationship fields
    property_[relationship_fields] [TYPE],
    
    -- Business logic fields
    property_[business_fields] [TYPE],
    
    -- Important timestamps
    property_hs_createdate TIMESTAMP WITH TIME ZONE,
    property_hs_lastmodifieddate TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_hubspot_[entity]_[key_field] ON hubspot.[entity] (property_[key_field]);
CREATE INDEX idx_hubspot_[entity]_owner ON hubspot.[entity] (property_hubspot_owner_id);
CREATE INDEX idx_hubspot_[entity]_created ON hubspot.[entity] (property_hs_createdate);
CREATE INDEX idx_hubspot_[entity]_modified ON hubspot.[entity] (property_hs_lastmodifieddate);
CREATE INDEX idx_hubspot_[entity]_fivetran_synced ON hubspot.[entity] (_fivetran_synced);

-- Relationship indexes (if applicable)
CREATE INDEX idx_hubspot_[entity]_[relationship] ON hubspot.[entity] (property_[relationship_field]);
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
3. Verify the table was created: `SELECT COUNT(*) FROM hubspot.[entity];`

### 3. Running the Sync

#### Full Sync
```bash
python hubspot_[entity]_sync.py
```

#### Test Mode (limit [ENTITY])
```bash
python hubspot_[entity]_sync.py 10
```

#### Via Flask Dashboard
```bash
python app.py
# Navigate to http://localhost:5001
# Click "HubSpot [ENTITY]" sync button
```

## Sync Process Details

### Data Flow
1. **Connect to HubSpot API** using HUBSPOT_API_TOKEN
2. **Fetch [ENTITY] properties** (currently mapped: [X] key properties)
3. **Paginate through [ENTITY]** using HubSpot's cursor-based pagination
4. **Process in batches** of [BATCH_SIZE] [ENTITY] for optimal performance
5. **Transform data** using type-safe conversion functions
6. **Upsert to database** using `ON CONFLICT DO UPDATE`

### Error Handling
- **Batch-level transactions**: Each batch of [BATCH_SIZE] [ENTITY] is processed as a single transaction
- **Individual [ENTITY] errors**: Skip problematic [ENTITY] but continue batch processing
- **Batch failures**: Roll back entire batch and log detailed error information
- **Comprehensive logging**: All operations logged with timestamps and [ENTITY] details

### Data Type Conversions
- **String fields**: Escape single quotes for SQL safety
- **Numbers**: Safe conversion with None handling for missing values
- **Booleans**: Handle various truthy/falsy string representations
- **Timestamps**: Convert HubSpot timestamps (milliseconds) to PostgreSQL TIMESTAMP WITH TIME ZONE

## Relationship Mapping

### Established Relationships
```sql
-- [ENTITY] → [Related Entity]
hubspot.[entity].property_[relationship_field] → hubspot.[related_entity].id

-- Example relationships:
-- Line Items → Deals
-- hubspot.line_item.property_deal_id → hubspot.deal.id

-- Tickets → Companies
-- hubspot.ticket.property_companyid_hs_sync → hubspot.company.id
```

### Join Queries
```sql
-- Example: [ENTITY] with related entity data
SELECT 
    e.property_[key_field],
    r.property_name as related_name,
    e.property_[business_field]
FROM hubspot.[entity] e
LEFT JOIN hubspot.[related_entity] r ON e.property_[relationship_field] = r.id
WHERE e.property_[filter_field] IS NOT NULL
ORDER BY e.property_hs_createdate DESC;
```

## Flask App Integration

### Dashboard Configuration
```python
# Added to SYNC_SCRIPTS in app.py
'hubspot_[entity]': {
    'script': 'hubspot_[entity]_sync.py',
    'name': 'HubSpot [ENTITY]',
    'color': '[color]',                    # Color theme
    'estimated_duration': [duration],      # Estimated seconds
    'object_type': '[entity_plural]'       # Plural form
}
```

### Real-time Monitoring
- **Live Progress**: Real-time sync progress via Server-Sent Events
- **Metrics Tracking**: [ENTITY] processed, success rates, duration
- **Error Reporting**: Immediate error notifications and detailed logging
- **Status Management**: Prevents duplicate syncs, shows current status

## Performance Metrics

### Sync Performance
- **Speed**: ~[X] [ENTITY]/second processing rate
- **Batch Size**: [BATCH_SIZE] [ENTITY] per API request (optimized)
- **Memory Usage**: Efficient streaming processing
- **API Efficiency**: Single request fetches [X]+ properties per [ENTITY]

### Database Performance
- **Indexes**: Strategic indexes on frequently queried fields
- **Storage**: Efficient column types for different data formats
- **Query Speed**: Fast lookups on [ENTITY] names, owners, dates

## Extending the Field Mapping

To add more HubSpot properties to the sync:

1. **Add to property_mappings** in `hubspot_[entity]_sync.py`:
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
ALTER TABLE hubspot.[entity] ADD COLUMN property_new_field_name TEXT;
ALTER TABLE hubspot.[entity] ADD COLUMN property_new_integer_field INTEGER;
```

3. **Update indexes if needed** for new searchable fields

## Monitoring and Maintenance

### Key Metrics to Monitor
- **Sync frequency**: How often [ENTITY] are updated
- **Error rates**: Failed batches or individual [ENTITY] processing failures
- **Data freshness**: Time since last successful sync
- **Row counts**: Growth in [ENTITY] database
- **Relationship integrity**: Validity of foreign key relationships

### Useful Queries
```sql
-- Recent [ENTITY]
SELECT property_[key_field], property_hs_createdate 
FROM hubspot.[entity] 
WHERE property_hs_createdate > NOW() - INTERVAL '7 days'
ORDER BY property_hs_createdate DESC;

-- Sync status
SELECT COUNT(*) as total_[entity], 
       MAX(_fivetran_synced) as last_sync,
       COUNT(CASE WHEN _fivetran_synced > NOW() - INTERVAL '1 day' THEN 1 END) as recent_syncs
FROM hubspot.[entity];

-- [ENTITY] activity by owner
SELECT property_hubspot_owner_id, COUNT(*) as [entity]_count
FROM hubspot.[entity] 
GROUP BY property_hubspot_owner_id 
ORDER BY [entity]_count DESC;

-- Relationship validation
SELECT 
    COUNT(*) as total_[entity],
    COUNT(property_[relationship_field]) as with_[relationship],
    COUNT(CASE WHEN r.id IS NOT NULL THEN 1 END) as valid_[relationship]
FROM hubspot.[entity] e
LEFT JOIN hubspot.[related_entity] r ON e.property_[relationship_field] = r.id;
```

## Data Quality Checks

### Validation Queries
```sql
-- Completeness check
SELECT 
    COUNT(*) as total,
    COUNT(property_[key_field]) as with_[key_field],
    COUNT(property_hubspot_owner_id) as with_owner,
    ROUND(100.0 * COUNT(property_[key_field]) / COUNT(*), 2) as completeness_pct
FROM hubspot.[entity];

-- Duplicate check
SELECT property_[key_field], COUNT(*) 
FROM hubspot.[entity] 
GROUP BY property_[key_field] 
HAVING COUNT(*) > 1;

-- Data integrity check
SELECT 
    '[field_name]' as field,
    COUNT(*) as total,
    COUNT(property_[field_name]) as populated,
    COUNT(DISTINCT property_[field_name]) as unique_values
FROM hubspot.[entity];
```

## File Structure

- `hubspot_[entity]_sync.py` - Main sync script
- `explore_hubspot_[entity].py` - HubSpot API exploration tool
- `HUBSPOT_[ENTITY]_SETUP.md` - This documentation
- Generated files:
  - `hubspot_[entity]_analysis_*.json` - Detailed property analysis
  - `hubspot_[entity]_summary_*.txt` - Property summary report
  - `hubspot_[entity]_sync_log_*.txt` - Sync operation logs

## Testing Results

### Initial Testing
- ✅ **[X] [ENTITY] processed** - Perfect data integrity
- ✅ **0 errors** - Robust error handling
- ✅ **[X] database columns** - Complete field mapping
- ✅ **[X] seconds** - Excellent performance
- ✅ **Real-time monitoring** - Full Flask integration

### Data Quality Verification
- ✅ **[X]% [ENTITY] have [key_field]** - Core data completeness
- ✅ **[X]% [ENTITY] have [business_field]** - Business data coverage
- ✅ **Full relationship mapping** - Related entity associations preserved
- ✅ **Rich metadata** - Owner IDs, timestamps, all core fields captured

## Troubleshooting

### Common Issues

**"No [ENTITY] found"**
- Check HubSpot API token permissions
- Verify your portal has [ENTITY] data
- Confirm API endpoint is correct

**"Database connection error"**
- Verify Neon database credentials
- Check IP whitelisting in Neon
- Ensure database schema exists

**"Sync performance issues"**
- Monitor batch size (default [BATCH_SIZE])
- Check database indexes
- Review network connectivity

### Debug Queries
```sql
-- Check recent sync activity
SELECT 
    DATE_TRUNC('hour', _fivetran_synced) as sync_hour,
    COUNT(*) as [entity]_synced
FROM hubspot.[entity] 
WHERE _fivetran_synced > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', _fivetran_synced)
ORDER BY sync_hour DESC;
```

## Next Steps

1. **Run the database schema creation SQL** in your Neon database
2. **Set up environment variables** in `.env` file
3. **Test with limited [ENTITY]**: `python hubspot_[entity]_sync.py 5`
4. **Run full sync**: `python hubspot_[entity]_sync.py`
5. **Schedule regular syncs** (e.g., via cron job or cloud scheduler)
6. **Extend field mappings** based on your specific HubSpot property needs
7. **Set up monitoring** for data quality and sync frequency

## Production Readiness

### Data Integrity
- ✅ **Comprehensive field mapping** - [X] HubSpot properties covered
- ✅ **Type safety** - Robust data conversion and validation
- ✅ **Relationship preservation** - Foreign key associations maintained
- ✅ **Audit trail** - Full creation and modification tracking

### Monitoring & Operations
- ✅ **Real-time monitoring** - Live progress via Flask dashboard
- ✅ **Error tracking** - Detailed logging and metrics
- ✅ **Performance monitoring** - Duration and throughput metrics
- ✅ **Easy management** - Web-based sync control

### Scalability
- ✅ **Batch processing** - Handles large [ENTITY] volumes efficiently
- ✅ **Pagination** - Automatic handling of API limits
- ✅ **Resource efficient** - Streaming processing minimizes memory usage
- ✅ **Database optimized** - Proper indexes and data types

## Support

For issues with this sync system:
1. Check the generated log files for detailed error information
2. Verify all environment variables are correctly set
3. Ensure HubSpot API token has proper permissions for [ENTITY]
4. Check Neon database connectivity and permissions
5. Review the Flask app dashboard for real-time status updates

---

**Status**: ✅ **PRODUCTION READY**  
**Last Updated**: [DATE]  
**Implementation**: Complete [ENTITY] sync with [X] properties mapped 