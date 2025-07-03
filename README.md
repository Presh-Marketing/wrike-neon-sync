# Wrike & HubSpot to Neon Database Sync Scripts

This repository contains Python scripts for syncing data from multiple sources to a Neon PostgreSQL database:

- **Wrike Sync** - Replicates the Make.com workflow for syncing Wrike project data 
- **HubSpot Sync** - Syncs HubSpot companies data to your database

These scripts eliminate the need for Make.com subscriptions by providing direct API integrations.

## Available Scripts

### Main Scripts
- **`wrike_sync.py`** - Complete sync of all Wrike entities (clients, parent projects, child projects, tasks, deliverables)
- **`hubspot_companies_sync.py`** - Sync HubSpot companies to `hubspot.company` table
- **`test_connection.py`** - Test Wrike API and database connections

### Standalone Entity Scripts (Wrike)
- **`clients_sync.py`** - Sync only Wrike clients
- **`parentprojects_sync.py`** - Sync only Wrike parent projects  
- **`childprojects_sync.py`** - Sync only Wrike child projects
- **`deliverables_sync.py`** - Sync only Wrike deliverables
- **`tasks_sync.py`** - Sync only Wrike tasks

## Features

### Wrike Sync Features
- Syncs Wrike spaces, projects, tasks, and deliverables
- Handles custom field mappings
- Implements upsert logic (insert or update)
- Parent relationship validation
- Raw effort storage (minutes from API)

### HubSpot Sync Features
- Syncs all company properties from HubSpot
- Dynamic field mapping based on your instance
- Handles 100+ custom properties
- Pagination support for large datasets
- Type-safe data conversion (strings, numbers, booleans, dates)

### Common Features
- Comprehensive logging
- Error handling and recovery
- Test mode with record limits
- Environment variable configuration

## Prerequisites

1. **Python 3.7+**
2. **API Tokens**:
   - **Wrike API Token** - Get this from your Wrike account settings
   - **HubSpot API Token** - Get this from your HubSpot developer account
3. **Neon Database** - Your PostgreSQL database connection details
4. **Database Schema** - The following tables should exist in your database:
   
   **Wrike Tables:**
   - `projects.clients`
   - `projects.parentprojects`
   - `projects.childprojects`
   - `projects.tasks`
   - `projects.deliverables`
   
   **HubSpot Tables:**
   - `hubspot.company` (with 200+ property fields)

## Installation

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables (see Configuration section)

## Configuration

Create a `.env` file in the project directory with your credentials:

```bash
cp config.example .env
```

Then edit `.env` with your actual values:

```env
# Wrike API Configuration
WRIKE_API_TOKEN=your_wrike_api_token_here

# HubSpot API Configuration
HUBSPOT_API_TOKEN=your_hubspot_api_token_here

# Neon Database Configuration
NEON_HOST=your_neon_host_here
NEON_DATABASE=your_database_name_here
NEON_USER=your_username_here
NEON_PASSWORD=your_password_here
NEON_PORT=5432
```

### Getting Your API Tokens

#### Wrike API Token
1. Log in to your Wrike account
2. Go to **Apps & Integrations** → **API**
3. Click **Create Token**
4. Give it a name and appropriate permissions
5. Copy the generated token

#### HubSpot API Token
1. Log in to your HubSpot account
2. Go to **Settings** → **Integrations** → **API key**
3. Click **Create key** (or use an existing private app)
4. For production use, create a **Private App** with these scopes:
   - `crm.objects.companies.read`
   - `crm.schemas.companies.read`
5. Copy the generated token

### Neon Database Setup

Make sure your Neon database has the required schema. The script expects these tables:

- `projects.clients` - Client/customer information
- `projects.parentprojects` - Parent project data
- `projects.childprojects` - Child project data  
- `projects.tasks` - Task information
- `projects.deliverables` - Deliverable information

## Usage

### Testing with Limited Records (Recommended)

Before running a full sync, test with a small number of records:

```bash
# Test with 5 records per entity type
python wrike_sync.py 5

# Test with 250 records per entity type  
python wrike_sync.py 250

# Alternative test script
python test_sync.py 10
```

### Full Sync

Run the complete sync (all records):

```bash
# Wrike full sync
python wrike_sync.py

# HubSpot companies full sync
python hubspot_companies_sync.py
```

### Standalone Entity Syncs

```bash
# Sync specific Wrike entities
python clients_sync.py 5
python parentprojects_sync.py 10
python childprojects_sync.py 15
python deliverables_sync.py 20
python tasks_sync.py 25

# HubSpot companies with test limit
python hubspot_companies_sync.py 50
```

### Using with Environment Variables

You can also set environment variables directly:

```bash
export WRIKE_API_TOKEN="your_token"
export NEON_HOST="your_host"
export NEON_DATABASE="your_db"
export NEON_USER="your_user"
export NEON_PASSWORD="your_password"

python wrike_sync.py
```

### Scheduled Execution

To run the script on a schedule, you can use:

**Using cron (Linux/Mac):**
```bash
# Run every hour
0 * * * * /usr/bin/python3 /path/to/wrike_sync.py

# Run every day at 2 AM
0 2 * * * /usr/bin/python3 /path/to/wrike_sync.py
```

**Using Windows Task Scheduler:**
- Create a new task
- Set the action to start `python.exe`
- Add arguments: `C:\path\to\wrike_sync.py`

## Web Dashboard

For easy management and monitoring, use the web dashboard interface:

```bash
python app.py
```

Then open your browser to: **http://localhost:5001**

### Dashboard Features

- **🔄 One-click sync buttons** for each data type
- **📊 Real-time logging** with auto-refresh every 3 seconds
- **⚙️ Test mode** - limit records for safe testing
- **🎯 Status indicators** - see which syncs are running/completed/failed
- **🧹 Log management** - clear logs and refresh manually
- **📱 Responsive design** - works on desktop and mobile

### Available Sync Operations

The dashboard includes color-coded sync buttons for:

- 🟠 **HubSpot Companies** - Sync companies from HubSpot to database
- 🔵 **Wrike Clients** - Sync client folders from Wrike  
- 🟢 **Parent Projects** - Sync parent project folders from Wrike
- 🟣 **Child Projects** - Sync child project folders from Wrike
- 🟡 **Tasks** - Sync tasks from Wrike
- 🔴 **Deliverables** - Sync deliverables from Wrike

### How to Use the Dashboard

1. **Start the dashboard**: `python app.py`
2. **Open browser**: Navigate to `http://localhost:5001`
3. **Set test limit** (optional): Enter a number like `5` to limit records for testing
4. **Click sync button**: Choose the data type you want to sync
5. **Monitor progress**: Watch the real-time logs and status indicators
6. **Wait for completion**: Status will change from "Running..." to "Completed" or "Failed"

The dashboard prevents multiple syncs of the same type from running simultaneously and provides detailed logging for troubleshooting.

## How It Works

The script follows this workflow:

1. **Authentication** - Connects to Wrike API using your token
2. **Space Discovery** - Finds the "Production" space in Wrike
3. **Data Extraction** - Retrieves folders and tasks by custom item type:
   - Clients (`IEAGEMDVPIABX4FV`)
   - Parent Projects (`IEAGEMDVPIABXIU5`) 
   - Child Projects (`IEAGEMDVPIABXIVA`)
   - Deliverables (`IEAGEMDVPIABWGFL`)
4. **Custom Field Mapping** - Extracts custom field values using field IDs
5. **Database Sync** - Inserts or updates records in Neon database
6. **Error Handling** - Logs issues and continues processing

## Custom Field Mappings

The script maps these Wrike custom fields to database columns:

| Field Name | Field ID | Description |
|------------|----------|-------------|
| google_drive_folder_id | IEAGEMDVJUAGD64G | Google Drive folder ID |
| approver_email | IEAGEMDVJUAFZXR5 | Approver email address |
| ziflow_id | IEAGEMDVJUAFZXVS | Ziflow proof ID |
| hubspot_id | IEAGEMDVJUAFZN76 | HubSpot contact/deal ID |
| brand_guide_url | IEAGEMDVJUAF2QEK | Brand guide URL |
| deliverable_type | IEAGEMDVJUAFX3LA | Type of deliverable |
| proof_version | IEAGEMDVJUAFZN7V | Proof version number |

## Logging

The script creates detailed logs in `wrike_sync.log` and outputs to console:

- INFO: Normal operations and progress
- WARNING: Non-critical issues  
- ERROR: Serious problems that may require attention

## Troubleshooting

### Common Issues

**"Missing required environment variables"**
- Make sure your `.env` file exists and contains all required variables
- Check that variable names match exactly

**"Production space not found"**
- Verify you have a Wrike space named exactly "Production"
- Check your API token has access to this space

**"Error connecting to database"**
- Verify your Neon database credentials
- Check that your IP is whitelisted in Neon
- Ensure the database and schema exist

**"Permission denied" errors**
- Check your Wrike API token permissions
- Verify database user has INSERT/UPDATE permissions

### Debug Mode

For more detailed logging, modify the logging level in the script:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Extending the Script

To add support for additional custom fields:

1. Add the field ID to `self.custom_fields` in `__init__()`
2. Update the processing methods to extract and use the new field
3. Modify the SQL statements to include the new column

### Testing

Create a test environment with:
- A separate Wrike space for testing
- A test database/schema
- Test environment variables

## Security

- Never commit your `.env` file to version control
- Rotate your API tokens regularly
- Use read-only database users when possible
- Monitor your logs for suspicious activity

## Support

If you encounter issues:

1. Check the logs for detailed error messages
2. Verify your configuration and credentials
3. Test connectivity to both Wrike API and Neon database
4. Review the Wrike API documentation for any changes

## License

This script is provided as-is for internal use. Modify as needed for your specific requirements.

# Professional API Sync Monitor Dashboard

A sophisticated real-time monitoring dashboard for Wrike and HubSpot API synchronization jobs with comprehensive logging, metrics tracking, and object-level reporting.

## 🚀 Features

### Professional Dashboard Interface
- **Dark Theme**: Modern, professional dark UI optimized for monitoring environments
- **Real-Time Updates**: Server-Sent Events (SSE) for live status updates and logging
- **Responsive Design**: Fully responsive layout that works on desktop, tablet, and mobile
- **Advanced Animations**: Smooth transitions and visual feedback for all interactions

### Monitoring & Metrics
- **Live Metrics Cards**: Real-time tracking of active jobs, completion rates, and performance
- **System Monitoring**: CPU, memory, and disk usage tracking with performance alerts
- **Job History**: Complete audit trail of all sync operations with detailed timing
- **Object-Level Reporting**: Track individual record counts and processing rates

### Enhanced Logging
- **Real-Time Log Stream**: Live log updates with automatic scrolling and filtering
- **Advanced Filtering**: Filter by log level, sync source, and time range
- **Export Functionality**: Export logs in JSON format for analysis
- **Search & Navigation**: Quick search and keyboard shortcuts for efficient navigation

### Sync Management
- **Intelligent Job Control**: Prevent duplicate jobs with status tracking
- **Progress Indicators**: Visual progress bars and estimated completion times
- **Error Handling**: Comprehensive error reporting with retry mechanisms
- **Test Mode**: Limit records for testing without affecting production data

## 📋 Requirements

- Python 3.8+
- Flask 2.3.0+
- PostgreSQL (via psycopg2-binary)
- psutil for system monitoring
- Modern web browser with SSE support

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd make_wrike_neonsqldb
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp config.example .env
   # Edit .env with your actual credentials
   ```

4. **Required environment variables**
   ```
   WRIKE_TOKEN=your_wrike_api_token
   NEON_HOST=your_neon_host
   NEON_DATABASE=your_database_name
   NEON_USER=your_database_user
   NEON_PASSWORD=your_database_password
   HUBSPOT_API_KEY=your_hubspot_api_key (if using HubSpot sync)
   ```

## 🚀 Running the Dashboard

### Development Mode
```bash
python app.py
```

### Production Mode
```bash
gunicorn -w 4 -b 0.0.0.0:5001 --timeout 120 app:app
```

The dashboard will be available at `http://localhost:5001`

## 📊 Available Sync Operations

| Sync Type | Description | Estimated Duration | Object Type |
|-----------|-------------|-------------------|-------------|
| **HubSpot Companies** | Sync companies from HubSpot to database | ~2 minutes | Companies |
| **Wrike Clients** | Sync client folders from Wrike | ~1 minute | Folders |
| **Parent Projects** | Sync parent project folders from Wrike | ~1.5 minutes | Projects |
| **Child Projects** | Sync child project folders from Wrike | ~2.5 minutes | Projects |
| **Wrike Tasks** | Sync tasks from Wrike | ~5 minutes | Tasks |
| **Wrike Deliverables** | Sync deliverables from Wrike | ~3 minutes | Deliverables |

## 🎯 Dashboard Usage

### Starting Sync Jobs
1. Select the desired sync operation from the sidebar
2. Optionally set a record limit for testing
3. Click the sync button to start the job
4. Monitor progress in real-time via the live logs

### Monitoring Features
- **Metrics Overview**: Track active jobs, completion rates, and system performance
- **Live Logs**: Real-time log streaming with automatic scrolling
- **Filter Options**: Filter logs by level (INFO, SUCCESS, WARNING, ERROR) and source
- **Export Logs**: Download logs for external analysis

### Keyboard Shortcuts
- `Ctrl/Cmd + R`: Refresh all data
- `Ctrl/Cmd + C`: Clear logs (with confirmation)
- `Escape`: Close notifications and clear selections

## 🔧 API Endpoints

### Core Endpoints
- `GET /` - Main dashboard interface
- `GET /events` - Server-Sent Events stream for real-time updates
- `POST /api/sync/<sync_type>` - Start a sync job
- `GET /api/status` - Get current status of all sync jobs

### Data Endpoints
- `GET /api/logs` - Get recent logs with filtering options
- `GET /api/metrics` - Get current system and application metrics
- `GET /api/history` - Get sync job history
- `GET /api/system-info` - Get detailed system information

### Utility Endpoints
- `DELETE /api/clear-logs` - Clear all logs

## 🏗 Architecture

### Frontend Architecture
- **Modern CSS Grid/Flexbox**: Responsive layout system
- **CSS Custom Properties**: Consistent theming and easy customization
- **Progressive Enhancement**: Graceful degradation for older browsers
- **Performance Optimized**: Efficient rendering and memory management

### Backend Architecture
- **Flask Web Framework**: Lightweight and flexible Python web framework
- **Server-Sent Events**: Real-time communication without WebSocket overhead
- **Thread-Safe Operations**: Concurrent job execution with proper synchronization
- **Comprehensive Error Handling**: Robust error recovery and logging

### Data Flow
1. **Job Initiation**: User triggers sync via dashboard interface
2. **Background Processing**: Python subprocess executes sync scripts
3. **Real-Time Updates**: SSE streams progress updates to all connected clients
4. **Metrics Collection**: System automatically tracks performance and completion data
5. **History Logging**: Complete audit trail stored for reporting and analysis

## 🔍 Troubleshooting

### Common Issues

**SSE Connection Problems**
- Check browser developer console for connection errors
- Verify no proxy/firewall blocking SSE connections
- Dashboard will automatically fall back to polling if SSE fails

**High Memory Usage**
- Monitor browser memory usage in developer tools
- Clear logs regularly to prevent memory buildup
- Dashboard includes automatic memory monitoring and warnings

**Sync Job Failures**
- Check environment variables are correctly set
- Verify database connectivity and permissions
- Review detailed error logs in the dashboard

### Performance Optimization
- Use record limits during testing to reduce processing time
- Monitor system resources via the built-in metrics
- Clear logs periodically to maintain performance

## 🔐 Security Considerations

- **Environment Variables**: Store sensitive credentials in environment variables, never in code
- **Network Security**: Use HTTPS in production environments
- **Access Control**: Implement authentication/authorization as needed for your environment
- **Log Sanitization**: Ensure no sensitive data is logged

## 📈 Monitoring Best Practices

1. **Regular Health Checks**: Monitor system metrics for resource usage trends
2. **Log Retention**: Implement log rotation to prevent storage issues
3. **Error Alerting**: Set up monitoring for error rates and failed jobs
4. **Performance Baselines**: Track average job completion times for performance regression detection

## 🛠 Development

### Adding New Sync Types
1. Add sync script configuration to `SYNC_SCRIPTS` dictionary in `app.py`
2. Include estimated duration and object type metadata
3. Update HTML template to include new sync button
4. Test thoroughly with record limits before production use

### Customizing the Interface
- Modify CSS custom properties in `templates/index.html` for theming
- Add custom animations in `static/css/dashboard-animations.css`
- Extend functionality in `static/js/dashboard-utils.js`

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For issues, questions, or contributions, please create an issue in this repository or contact the development team. 