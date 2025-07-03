# AI Agent Development Guide
## 🤖 Master Reference for Future AI Agents

This guide provides everything a future AI agent needs to understand and extend this HubSpot/Wrike sync system. Follow these patterns exactly for consistent, professional implementations.

## 🎯 Quick Start Command Template

For any new HubSpot entity mapping, use this exact prompt:

```
Create HubSpot [ENTITY] sync following the established pattern:

1. **API Exploration**: Create `explore_hubspot_[entity].py` to discover ALL available properties
2. **Database Schema**: Create `hubspot.[entity]` table using mcp-server-neon with ALL fields  
3. **Sync Script**: Create `hubspot_[entity]_sync.py` with comprehensive field mapping
4. **App Integration**: Add to `app.py` SYNC_SCRIPTS with monitoring integration
5. **Documentation**: Create setup guide following existing patterns

Environment: Portal ID 1849303, use existing .env variables
Database: Use mcp-server-neon, follow property_ prefix naming convention
Testing: Start with limit=2, then limit=10, then full sync
Pattern: Follow hubspot_contacts_sync.py and hubspot_deals_sync.py exactly
```

## 🏗️ System Architecture

### Current Implementation Status
✅ **HubSpot Companies** - 254+ fields, base relationship table  
✅ **HubSpot Contacts** - 177 fields, links to companies via `property_associatedcompanyid`  
✅ **HubSpot Deals** - 198 fields, links to companies via `property_companyid_hs_sync`  
🔄 **Wrike Entities** - Clients, projects, tasks, deliverables (complete)  
⏳ **Future**: Line Items, Tickets, Products, etc.

### Database Schema Pattern
```sql
-- Every HubSpot table follows this pattern:
CREATE TABLE hubspot.[entity] (
    -- Core system fields (ALWAYS include these)
    id BIGINT PRIMARY KEY,                     -- HubSpot Entity ID
    portal_id INTEGER DEFAULT 1849303,        -- Our Portal ID
    is_deleted BOOLEAN DEFAULT FALSE,          -- Deletion flag
    _fivetran_deleted BOOLEAN DEFAULT FALSE,   -- Fivetran compatibility
    _fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- All HubSpot properties with property_ prefix
    property_[field_name] [appropriate_type],
    -- Example: property_dealname TEXT, property_amount NUMERIC
);

-- Always add performance indexes
CREATE INDEX idx_hubspot_[entity]_[key_field] ON hubspot.[entity] (property_[key_field]);
```

### File Naming Convention
- **Exploration**: `explore_hubspot_[entity].py`
- **Sync Script**: `hubspot_[entity]_sync.py`  
- **Documentation**: `docs/HUBSPOT_[ENTITY]_SETUP.md`
- **Schema**: `docs/create_hubspot_[entity]_table.sql`

## 🔌 Required Environment Variables

```bash
# HubSpot API (CRITICAL: Check web for latest API version)
HUBSPOT_API_TOKEN=your_hubspot_api_token

# Neon Database
NEON_HOST=your_neon_host.aws.neon.tech
NEON_DATABASE=your_database_name
NEON_USER=your_database_user
NEON_PASSWORD=your_database_password
NEON_PORT=5432

# Wrike API (if extending Wrike functionality)
WRIKE_TOKEN=your_wrike_token

# System Constants
PORTAL_ID=1849303  # Our HubSpot Portal ID (hardcoded in scripts)
```

## 🚀 Implementation Process - Step by Step

### Step 1: API Exploration Script
**Template**: `docs/MAPPING_TEMPLATES/EXPLORATION_TEMPLATE.py`

```python
# explore_hubspot_[entity].py
import requests
import json
import os
from dotenv import load_dotenv

# Follow this exact pattern for property discovery
# - Get ALL properties from HubSpot API
# - Analyze data types (STRING, NUMBER, DATETIME, BOOLEAN, ENUMERATION)
# - Generate comprehensive field mapping
# - Save analysis to analysis/ directory
```

### Step 2: Database Schema Creation
**Template**: `docs/MAPPING_TEMPLATES/DATABASE_SCHEMA_TEMPLATE.sql`

Use **mcp-server-neon** for table creation:
```sql
-- ALWAYS follow this pattern:
-- 1. Create schema if not exists: CREATE SCHEMA IF NOT EXISTS hubspot;
-- 2. Core system fields (id, portal_id, is_deleted, _fivetran_deleted, _fivetran_synced)
-- 3. All HubSpot properties with property_ prefix
-- 4. Appropriate data types: TEXT, NUMERIC, BOOLEAN, TIMESTAMP WITH TIME ZONE, INTEGER
-- 5. Performance indexes on key fields
```

### Step 3: Sync Script Development
**Template**: `docs/MAPPING_TEMPLATES/SYNC_SCRIPT_TEMPLATE.py`

Critical patterns to follow:
```python
# hubspot_[entity]_sync.py
class HubSpot[Entity]Sync:
    def __init__(self):
        self.api_token = os.getenv('HUBSPOT_API_TOKEN')
        self.portal_id = 1849303
        self.db_config = {
            'host': os.getenv('NEON_HOST'),
            'database': os.getenv('NEON_DATABASE'),
            'user': os.getenv('NEON_USER'), 
            'password': os.getenv('NEON_PASSWORD'),
            'port': int(os.getenv('NEON_PORT', 5432))
        }
        
    # ALWAYS include these helper functions:
    def safe_string(self, value): # Handle None/empty strings
    def safe_number(self, value): # Convert to float/int safely  
    def safe_boolean(self, value): # Handle various boolean formats
    def safe_datetime(self, value): # Convert HubSpot timestamps
```

### Step 4: Flask App Integration  
**Template**: `docs/MAPPING_TEMPLATES/APP_INTEGRATION_TEMPLATE.py`

Add to `app.py` SYNC_SCRIPTS dictionary:
```python
SYNC_SCRIPTS = {
    'hubspot_[entity]': {
        'script': 'hubspot_[entity]_sync.py',
        'name': 'HubSpot [Entity]',
        'color': '[appropriate_color]',  # Use color scheme: blue, green, purple, amber, emerald, etc.
        'estimated_duration': [duration_seconds],  # Based on entity complexity
        'object_type': '[entity_plural]'  # e.g., 'line_items', 'deals', 'contacts'
    }
}
```

### Step 5: Documentation
**Template**: `docs/MAPPING_TEMPLATES/SETUP_DOC_TEMPLATE.md`

Follow the exact structure of existing setup docs:
- Overview with property counts and field categories
- Database schema details
- Setup instructions  
- Usage examples
- Monitoring and maintenance
- Extension guidelines

## 📊 Data Type Mapping Reference

### HubSpot → PostgreSQL Type Mapping
```python
HUBSPOT_TYPE_MAPPING = {
    'string': 'TEXT',
    'number': 'NUMERIC', 
    'datetime': 'TIMESTAMP WITH TIME ZONE',
    'date': 'DATE',
    'bool': 'BOOLEAN',
    'enumeration': 'TEXT',  # Store enum values as text
    'phone_number': 'TEXT',
    'json': 'JSONB'  # For complex nested data
}
```

### Field Naming Convention
- **HubSpot API**: `dealname`, `hs_acv`, `hubspot_owner_id`
- **Database Column**: `property_dealname`, `property_hs_acv`, `property_hubspot_owner_id`
- **Always** prefix with `property_` for consistency

## 🔗 Relationship Patterns

### Established Relationships
```sql
-- Contacts → Companies
hubspot.contact.property_associatedcompanyid → hubspot.company.id

-- Deals → Companies  
hubspot.deal.property_companyid_hs_sync → hubspot.company.id

-- Future: Line Items → Deals
hubspot.line_item.property_deal_id → hubspot.deal.id
```

### Relationship Implementation
1. **Foreign Key Fields**: Include relationship ID fields in schema
2. **Index Creation**: Always index relationship fields for performance
3. **Join Queries**: Provide example queries in documentation
4. **Data Integrity**: Handle missing relationships gracefully

## 🧪 Testing Protocol

### Standard Testing Sequence
```bash
# 1. Test with minimal records
python hubspot_[entity]_sync.py --limit 2

# 2. Verify data structure  
# Check database table creation and field mapping

# 3. Small batch test
python hubspot_[entity]_sync.py --limit 10

# 4. Medium batch test  
python hubspot_[entity]_sync.py --limit 100

# 5. Full sync (only after all tests pass)
python hubspot_[entity]_sync.py
```

### Validation Checklist
- ✅ All HubSpot properties discovered and mapped
- ✅ Database table created with correct schema
- ✅ Sync script handles all data types safely
- ✅ Error handling prevents data corruption
- ✅ Flask app integration displays correctly
- ✅ Real-time monitoring shows progress
- ✅ Relationships with existing tables work
- ✅ Performance indexes created

## 📁 File Organization

### Required Files for Each Entity
```
Root Directory:
├── explore_hubspot_[entity].py          # API exploration
├── hubspot_[entity]_sync.py             # Main sync script

docs/ Directory:  
├── HUBSPOT_[ENTITY]_SETUP.md            # Setup documentation
├── create_hubspot_[entity]_table.sql    # Database schema

analysis/ Directory:
├── hubspot_[entity]_properties_analysis.json  # Property analysis
├── hubspot_[entity]_summary_[timestamp].txt   # Summary report

logs/ Directory:
├── hubspot_[entity]_sync.log            # Current sync logs
└── hubspot_sync_log_[timestamp].txt     # Historical logs
```

## 🎨 Flask App Styling

### Color Scheme for New Entities
- **HubSpot Companies**: Orange (`text-orange-600`, `bg-orange-50`)
- **HubSpot Contacts**: Amber (`text-amber-600`, `bg-amber-50`)  
- **HubSpot Deals**: Emerald (`text-emerald-600`, `bg-emerald-50`)
- **HubSpot Line Items**: Purple (`text-purple-600`, `bg-purple-50`)
- **HubSpot Tickets**: Blue (`text-blue-600`, `bg-blue-50`)
- **HubSpot Products**: Indigo (`text-indigo-600`, `bg-indigo-50`)

### Estimated Durations  
Base estimates on entity complexity:
- **Simple entities** (Products, Line Items): 60-120 seconds
- **Medium entities** (Contacts, Tickets): 120-180 seconds  
- **Complex entities** (Deals, Companies): 180-300 seconds

## 🚨 Critical Requirements

### API Version Requirements
**ALWAYS check web for most recent versions** (per user rules):
- HubSpot API: Use latest v3 API endpoints
- OpenAI API: Latest version for any AI features
- Wrike API: Latest version for Wrike integrations

### Data Safety Requirements
1. **ALWAYS use transactions** for batch operations
2. **ALWAYS implement rollback** on batch failures  
3. **ALWAYS validate data types** before insertion
4. **ALWAYS handle API rate limits** with proper delays
5. **ALWAYS log comprehensive details** for debugging

### Performance Requirements
1. **Batch processing**: Process in batches (25-100 records)
2. **Pagination**: Handle large datasets with cursor-based pagination
3. **Indexing**: Create indexes on frequently queried fields
4. **Memory efficiency**: Stream processing, don't load all data at once

## 🔧 MCP-Server-Neon Usage

### Table Creation Pattern
```python
# Use mcp_Neon_MCP_run_sql for table creation
mcp_Neon_MCP_run_sql({
    "params": {
        "projectId": "your_project_id",
        "sql": "CREATE TABLE hubspot.[entity] (...)"
    }
})
```

### Data Insertion Pattern  
```python
# Use mcp_Neon_MCP_run_sql_transaction for batch inserts
mcp_Neon_MCP_run_sql_transaction({
    "params": {
        "projectId": "your_project_id", 
        "sqlStatements": [list_of_sql_statements]
    }
})
```

## 📈 Success Metrics

### Implementation Completeness
- ✅ **100% Property Coverage**: All available HubSpot properties mapped
- ✅ **Type Safety**: All data types converted safely
- ✅ **Relationship Integrity**: Foreign keys and joins working
- ✅ **Error Handling**: Graceful failure recovery
- ✅ **Performance**: Reasonable sync times for data volume
- ✅ **Monitoring**: Real-time progress tracking
- ✅ **Documentation**: Complete setup and usage guides

### Quality Indicators
- **Zero data loss** during sync operations
- **Consistent naming** following established conventions  
- **Comprehensive logging** for troubleshooting
- **Test coverage** from small to full dataset
- **Production readiness** with monitoring integration

## 🚀 Ready-to-Use Commands

### For HubSpot Line Items (Example)
```bash
# Complete implementation command for AI agent:
"Create HubSpot line items sync: 1) explore_hubspot_line_items.py for API discovery, 2) hubspot.line_item table with mcp-server-neon including property_deal_id relationship, 3) hubspot_line_items_sync.py with ALL fields mapped, 4) integrate into app.py with purple theme and 90s duration, 5) test with limit=2 then full sync. Use Portal ID 1849303, follow property_ naming convention, include comprehensive error handling and logging."
```

### For Any New Entity
```bash
# Template command:
"Create HubSpot [ENTITY] sync following established pattern: API exploration → database schema → sync script → app integration → testing. Use mcp-server-neon, Portal ID 1849303, property_ prefix, comprehensive field mapping, and real-time monitoring."
```

---

## 📞 Support References

- **Existing Implementations**: Study `hubspot_contacts_sync.py` and `hubspot_deals_sync.py`
- **Database Patterns**: Follow `hubspot.company`, `hubspot.contact`, `hubspot.deal` schemas
- **Flask Integration**: Reference `app.py` SYNC_SCRIPTS configuration
- **Documentation Style**: Match `docs/HUBSPOT_CONTACTS_SETUP.md` format

**Status**: ✅ **READY FOR AI AGENT USE**  
**Last Updated**: January 2025  
**Next Entity Target**: HubSpot Line Items → Tickets → Products → Custom Objects 