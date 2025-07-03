# Project Structure - Make Wrike Neon SQL DB

## 📁 Directory Organization

This project has been organized into a clean, logical structure for better maintainability and development workflow.

### 🗂️ Root Directory
```
make_wrike_neonsqldb/
├── 📁 analysis/           # Data analysis files and property mappings
├── 📁 data/              # Raw data files and exports
├── 📁 docs/              # Documentation, SQL schemas, and setup guides
├── 📁 logs/              # All application and sync log files
├── 📁 scripts/           # Utility and helper scripts
├── 📁 static/            # Web app static files (CSS, JS)
├── 📁 templates/         # Flask HTML templates
├── 📁 __pycache__/       # Python cache files
├── 🚀 app.py             # Main Flask web application
├── 🔄 *_sync.py          # Core sync scripts
├── 📄 README.md          # Project documentation
├── 📋 requirements.txt   # Python dependencies
├── ⚙️ config.example     # Configuration template
└── 🔧 wrike_sync.py      # Main Wrike sync script
```

## 📂 Folder Details

### 📊 `/analysis/` - Data Analysis & Property Mappings
Contains analysis files from HubSpot API exploration and property mapping:
- `hubspot_contacts_analysis_*.json` - Contact properties analysis
- `hubspot_deal_properties_analysis.json` - Deal properties analysis  
- `hubspot_companies_detailed_*.json` - Company properties analysis

**Purpose**: Reference files for understanding API schemas and field mappings.

### 💾 `/data/` - Raw Data & Exports
Stores raw data files and configuration exports:
- `hubspot_deal_properties_raw.json` - Raw deal properties from HubSpot API
- `Wrike - OpsAI NEON DB.blueprint.json` - Wrike configuration blueprint

**Purpose**: Backup of raw API responses and system configurations.

### 📚 `/docs/` - Documentation & SQL Schemas
Comprehensive documentation with AI-agent-ready templates:

#### Implementation Guides
- `HUBSPOT_CONTACTS_SETUP.md` - HubSpot Contacts sync documentation
- `HUBSPOT_DEALS_SETUP.md` - HubSpot Deals sync documentation  
- `BATCH_PROCESSING_SUMMARY.md` - Batch processing guidelines

#### Schema Files
- `create_hubspot_*.sql` - Database table creation scripts
- `hubspot_contact_schema.sql` - Contact table schema

#### Templates for AI Agents (`MAPPING_TEMPLATES/`)
- `EXPLORATION_TEMPLATE.py` - Template for HubSpot API property discovery
- `SYNC_SCRIPT_TEMPLATE.py` - Complete sync script template
- `DATABASE_SCHEMA_TEMPLATE.sql` - Database table creation template
- `APP_INTEGRATION_TEMPLATE.py` - Flask app integration guide
- `SETUP_DOC_TEMPLATE.md` - Documentation template

**Purpose**: Setup guides, templates for consistent implementations, and database schemas.

### 📋 `/logs/` - Application & Sync Logs
All log files are centralized here:
- `hubspot_deals_sync.log` - Current deals sync log (auto-created)
- `hubspot_sync_log_*.txt` - Historical sync logs
- `hubspot_contacts_summary_*.txt` - Contact sync summaries
- `hubspot_companies_summary_*.txt` - Company sync summaries

**Purpose**: Centralized logging for debugging and monitoring.

### 🛠️ `/scripts/` - Utility & Helper Scripts
Development and utility scripts:
- `list_hubspot_companies.py` - HubSpot companies exploration tool
- `test_connection.py` - Database connection testing
- `test_sync.py` - Sync testing utilities
- `setup.py` - Project setup script

**Purpose**: Development tools and testing utilities.

### 🌐 `/static/` & `/templates/` - Web Application
Flask web application assets:
- `static/` - CSS, JavaScript, images for web interface
- `templates/` - HTML templates for Flask routes

**Purpose**: Web dashboard UI components.

## 🚀 Core Sync Scripts (Root Level)

### Primary Application
- **`app.py`** - Main Flask web application with real-time monitoring dashboard

### HubSpot Sync Scripts
- **`hubspot_deals_sync.py`** - Comprehensive deals sync (198 fields)
- **`hubspot_contacts_sync.py`** - Contacts sync with relationship mapping
- **`hubspot_companies_sync.py`** - Companies sync and data management

### Wrike Sync Scripts
- **`clients_sync.py`** - Wrike client folders sync
- **`parentprojects_sync.py`** - Parent project folders sync
- **`childprojects_sync.py`** - Child project folders sync
- **`tasks_sync.py`** - Wrike tasks sync
- **`deliverables_sync.py`** - Wrike deliverables sync
- **`wrike_sync.py`** - Main Wrike sync orchestrator

## 📝 Configuration Files

### Required Files
- **`requirements.txt`** - Python package dependencies
- **`config.example`** - Environment variable template
- **`README.md`** - Project overview and setup instructions

### Environment Variables (.env file - not in repo)
```bash
# HubSpot Configuration
HUBSPOT_API_TOKEN=your_hubspot_token

# Neon Database Configuration
NEON_HOST=your_neon_host
NEON_DATABASE=your_database_name
NEON_USER=your_username
NEON_PASSWORD=your_password
NEON_PORT=5432

# Wrike Configuration
WRIKE_TOKEN=your_wrike_token
```

## 🔄 Logging Strategy

### Centralized Logging
All application logs are now written to the `/logs/` folder:

- **Automatic Directory Creation**: Scripts ensure the logs directory exists
- **Organized by Service**: Separate log files for different sync services
- **Historical Preservation**: Past logs are retained for analysis
- **Real-time Monitoring**: Live log streaming in web dashboard

### Log File Naming Convention
- `hubspot_deals_sync.log` - Current deals sync (auto-rotating)
- `hubspot_sync_log_YYYYMMDD_HHMMSS.txt` - Timestamped historical logs
- `hubspot_*_summary_YYYYMMDD_HHMMSS.txt` - Sync summary reports

## 🧹 Maintenance & Best Practices

### Regular Cleanup
```bash
# Clean old logs (keep last 30 days)
find logs/ -name "*.log" -mtime +30 -delete
find logs/ -name "*.txt" -mtime +30 -delete

# Clean Python cache
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### Development Workflow
1. **Main sync scripts** remain in root for easy access
2. **Utilities and helpers** organized in `/scripts/`
3. **Documentation** centralized in `/docs/`
4. **Logs** automatically organized in `/logs/`
5. **Analysis data** preserved in `/analysis/` and `/data/`

### File Organization Rules
- **Scripts in root**: Only core sync scripts and main application
- **No log files in root**: All logs go to `/logs/` folder
- **Documentation together**: Setup guides and schemas in `/docs/`
- **Data preservation**: Raw API responses and analysis in `/data/` and `/analysis/`

## 🎯 Benefits of This Structure

### For Development
- ✅ **Clean root directory** - Easy to find main scripts
- ✅ **Organized logs** - All logging in one place
- ✅ **Separated concerns** - Docs, data, scripts in logical folders
- ✅ **Easy maintenance** - Clear file organization

### For Operations
- ✅ **Centralized monitoring** - All logs in `/logs/`
- ✅ **Documentation hub** - All setup guides in `/docs/`
- ✅ **Data preservation** - Historical analysis data preserved
- ✅ **Utility access** - Helper scripts organized in `/scripts/`

### For Scaling
- ✅ **Modular structure** - Easy to add new sync services
- ✅ **Clear separation** - Development vs production concerns
- ✅ **Maintainable** - Logical file organization
- ✅ **Professional** - Industry-standard project structure

---

**Status**: ✅ **Fully Organized**  
**Last Updated**: June 2025  
**Maintained By**: Project sync system with automated log organization 