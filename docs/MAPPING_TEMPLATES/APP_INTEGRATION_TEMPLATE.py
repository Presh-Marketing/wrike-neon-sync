# Flask App Integration Template for HubSpot Entity Sync
# This template shows the exact changes needed in app.py to add a new HubSpot entity sync

# Step 1: Add to SYNC_SCRIPTS dictionary in app.py
# Find the SYNC_SCRIPTS dictionary and add your new entity:

SYNC_SCRIPTS = {
    # ... existing entries ...
    
    # NEW ENTITY - Add this entry (customize the values)
    'hubspot_ENTITY': {
        'script': 'hubspot_ENTITY_sync.py',           # Your sync script filename
        'name': 'HubSpot ENTITY_NAME',                # Display name in dashboard
        'color': 'CHOOSE_COLOR',                      # Color theme (see options below)
        'estimated_duration': DURATION_SECONDS,       # Estimated sync time in seconds
        'object_type': 'ENTITY_PLURAL'                # Plural form for metrics display
    },
    
    # ... existing entries continue ...
}

# Step 2: Color Theme Options
# Choose an appropriate color that's not already used:

COLOR_OPTIONS = {
    'blue': {
        'button': 'text-blue-600 bg-blue-50 border-blue-200 hover:bg-blue-100',
        'status': 'text-blue-800 bg-blue-100'
    },
    'green': {
        'button': 'text-green-600 bg-green-50 border-green-200 hover:bg-green-100', 
        'status': 'text-green-800 bg-green-100'
    },
    'purple': {
        'button': 'text-purple-600 bg-purple-50 border-purple-200 hover:bg-purple-100',
        'status': 'text-purple-800 bg-purple-100'
    },
    'amber': {
        'button': 'text-amber-600 bg-amber-50 border-amber-200 hover:bg-amber-100',
        'status': 'text-amber-800 bg-amber-100'
    },
    'emerald': {
        'button': 'text-emerald-600 bg-emerald-50 border-emerald-200 hover:bg-emerald-100',
        'status': 'text-emerald-800 bg-emerald-100'
    },
    'indigo': {
        'button': 'text-indigo-600 bg-indigo-50 border-indigo-200 hover:bg-indigo-100',
        'status': 'text-indigo-800 bg-indigo-100'
    },
    'pink': {
        'button': 'text-pink-600 bg-pink-50 border-pink-200 hover:bg-pink-100',
        'status': 'text-pink-800 bg-pink-100'
    },
    'teal': {
        'button': 'text-teal-600 bg-teal-50 border-teal-200 hover:bg-teal-100',
        'status': 'text-teal-800 bg-teal-100'
    }
}

# Step 3: Estimated Duration Guidelines
# Base your duration estimate on entity complexity:

DURATION_GUIDELINES = {
    'simple_entities': {
        'examples': ['Products', 'Line Items', 'Simple Custom Objects'],
        'duration_range': '60-120 seconds',
        'typical_fields': '20-50 properties',
        'record_volume': 'Low-Medium (hundreds to few thousand)'
    },
    'medium_entities': {
        'examples': ['Contacts', 'Tickets', 'Quotes'],
        'duration_range': '120-180 seconds', 
        'typical_fields': '50-150 properties',
        'record_volume': 'Medium (thousands to tens of thousands)'
    },
    'complex_entities': {
        'examples': ['Deals', 'Companies', 'Complex Custom Objects'],
        'duration_range': '180-300 seconds',
        'typical_fields': '150+ properties',
        'record_volume': 'High (tens of thousands+)'
    }
}

# Step 4: Log Pattern Enhancement
# If your entity has specific log patterns, add them to parse_log_for_metrics()

def parse_log_for_metrics(line, sync_type):
    """Enhanced log parsing for new entity types."""
    
    # Existing patterns...
    
    # NEW ENTITY - Add parsing patterns for your entity
    if sync_type == 'hubspot_ENTITY':
        # Pattern 1: "Processing X ENTITY_PLURAL..."
        if 'ENTITY_PLURAL processed' in line.lower():
            match = re.search(r'(\d+)\s+ENTITY_PLURAL\s+processed', line, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Pattern 2: "Total ENTITY_PLURAL: X"
        if 'total ENTITY_PLURAL' in line.lower():
            match = re.search(r'total\s+ENTITY_PLURAL[:\s]+(\d+)', line, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Pattern 3: "Successfully synced X ENTITY_PLURAL"
        if 'successfully synced' in line.lower() and 'ENTITY_PLURAL' in line.lower():
            match = re.search(r'successfully\s+synced\s+(\d+)\s+ENTITY_PLURAL', line, re.IGNORECASE)
            if match:
                return int(match.group(1))
    
    return None

# Step 5: Entity-Specific Metrics (Optional)
# If your entity needs special metrics tracking, add to get_sync_metrics()

def get_entity_specific_metrics(sync_type):
    """Get entity-specific metrics for dashboard display."""
    
    if sync_type == 'hubspot_ENTITY':
        # Add custom metrics queries for your entity
        # Example: relationship counts, data quality metrics, etc.
        
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            # Custom metrics queries
            metrics = {}
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM hubspot.ENTITY")
            metrics['total_records'] = cursor.fetchone()[0]
            
            # Recent records (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM hubspot.ENTITY 
                WHERE _fivetran_synced > NOW() - INTERVAL '24 hours'
            """)
            metrics['recent_syncs'] = cursor.fetchone()[0]
            
            # Entity-specific metrics (customize based on your entity)
            # Example for line items:
            # cursor.execute("SELECT COUNT(*) FROM hubspot.line_item WHERE property_deal_id IS NOT NULL")
            # metrics['with_deal_relationship'] = cursor.fetchone()[0]
            
            # Example for tickets:
            # cursor.execute("SELECT COUNT(*) FROM hubspot.ticket WHERE property_hs_ticket_priority = 'HIGH'")
            # metrics['high_priority'] = cursor.fetchone()[0]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting {sync_type} metrics: {e}")
            return {}
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    return {}

# Step 6: Complete Integration Example
# Here's a complete example for HubSpot Line Items:

COMPLETE_EXAMPLE = {
    'hubspot_line_items': {
        'script': 'hubspot_line_items_sync.py',
        'name': 'HubSpot Line Items',
        'color': 'purple',                          # Purple theme
        'estimated_duration': 90,                   # 90 seconds (simple entity)
        'object_type': 'line_items'                 # Plural form
    }
}

# Step 7: Testing Integration
# After adding to SYNC_SCRIPTS, test the integration:

TESTING_CHECKLIST = [
    "✅ Entity appears in dashboard sidebar",
    "✅ Color theme displays correctly", 
    "✅ Sync button is clickable and shows proper status",
    "✅ Real-time logs stream correctly during sync",
    "✅ Progress metrics update properly",
    "✅ Completion status shows correctly",
    "✅ Error handling works if sync fails",
    "✅ Multiple syncs are prevented (button disabled during sync)"
]

# Step 8: Dashboard Button HTML Template
# The button will be automatically generated, but here's what it looks like:

BUTTON_HTML_TEMPLATE = """
<button 
    onclick="startSync('hubspot_ENTITY', 'HubSpot ENTITY_NAME')"
    class="w-full p-4 text-left rounded-lg border-2 transition-all duration-200 
           text-COLOR-600 bg-COLOR-50 border-COLOR-200 hover:bg-COLOR-100"
    id="sync-btn-hubspot_ENTITY">
    
    <div class="flex items-center justify-between">
        <div>
            <h3 class="font-semibold text-lg">HubSpot ENTITY_NAME</h3>
            <p class="text-sm opacity-75">Sync ENTITY_PLURAL from HubSpot</p>
            <p class="text-xs opacity-60 mt-1">~DURATION_SECONDS seconds</p>
        </div>
        <div class="text-2xl">🔄</div>
    </div>
    
    <!-- Status indicator (dynamically updated) -->
    <div id="status-hubspot_ENTITY" class="mt-2 hidden">
        <div class="text-xs px-2 py-1 rounded text-COLOR-800 bg-COLOR-100">
            <span id="status-text-hubspot_ENTITY">Ready</span>
        </div>
    </div>
    
</button>
"""

# Step 9: Monitoring and Alerts
# Optional: Add monitoring for your new entity

MONITORING_QUERIES = {
    'data_freshness': """
        SELECT 
            MAX(_fivetran_synced) as last_sync,
            COUNT(*) as total_records
        FROM hubspot.ENTITY
    """,
    
    'sync_frequency': """
        SELECT 
            DATE_TRUNC('day', _fivetran_synced) as sync_date,
            COUNT(*) as records_synced
        FROM hubspot.ENTITY 
        WHERE _fivetran_synced > NOW() - INTERVAL '7 days'
        GROUP BY DATE_TRUNC('day', _fivetran_synced)
        ORDER BY sync_date DESC
    """,
    
    'data_quality': """
        SELECT 
            COUNT(*) as total,
            COUNT(property_name) as with_name,
            COUNT(property_hubspot_owner_id) as with_owner
        FROM hubspot.ENTITY
    """
}

# Step 10: Deployment Checklist
DEPLOYMENT_CHECKLIST = [
    "✅ Sync script tested independently",
    "✅ Database table created and tested",
    "✅ Environment variables configured",
    "✅ Added to SYNC_SCRIPTS dictionary",
    "✅ Flask app restarted",
    "✅ Dashboard loads without errors",
    "✅ Test sync with small limit (e.g., 5 records)",
    "✅ Verify data appears in database",
    "✅ Check real-time monitoring works",
    "✅ Test full sync (if appropriate)",
    "✅ Document setup in docs/HUBSPOT_ENTITY_SETUP.md"
]

"""
SUMMARY: Complete Integration Steps

1. Create your sync script (hubspot_entity_sync.py)
2. Create database table (using DATABASE_SCHEMA_TEMPLATE.sql)
3. Add entry to SYNC_SCRIPTS dictionary in app.py
4. Choose appropriate color theme and duration
5. Test with small record limit
6. Verify dashboard integration works
7. Document in setup guide
8. Deploy to production

The Flask app will automatically:
- Generate the dashboard button
- Handle sync execution 
- Stream real-time logs
- Track progress metrics
- Manage sync status
- Prevent duplicate syncs
""" 