#!/usr/bin/env python3
"""
HubSpot [ENTITY] API Exploration Template

This template script discovers all available properties for a HubSpot entity.
Replace [ENTITY] with the actual entity name (e.g., line_items, tickets, products).

Usage:
    python explore_hubspot_[entity].py

Requirements:
    - HUBSPOT_API_TOKEN environment variable
    - requests library
    - dotenv library

Output:
    - Comprehensive property analysis
    - Data type categorization  
    - Field mapping recommendations
    - Analysis saved to analysis/ directory
"""

import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HubSpotEntityExplorer:
    # TODO: Replace 'Entity' with actual entity name (e.g., LineItems, Tickets, Products)
    def __init__(self):
        self.api_token = os.getenv('HUBSPOT_API_TOKEN')
        if not self.api_token:
            raise ValueError("HUBSPOT_API_TOKEN environment variable is required")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # Replace with actual HubSpot API endpoint for the entity
        self.properties_url = "https://api.hubapi.com/crm/v3/properties/[entity]"
        self.objects_url = "https://api.hubapi.com/crm/v3/objects/[entity]"
        
        # Ensure analysis directory exists
        os.makedirs('analysis', exist_ok=True)
    
    def get_all_properties(self):
        """Fetch all available properties for the entity from HubSpot API."""
        print(f"🔍 Fetching all [ENTITY] properties from HubSpot API...")
        
        try:
            response = requests.get(self.properties_url, headers=self.headers)
            response.raise_for_status()
            
            properties_data = response.json()
            properties = properties_data.get('results', [])
            
            print(f"✅ Found {len(properties)} [ENTITY] properties")
            return properties
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching properties: {e}")
            return []
    
    def analyze_properties(self, properties):
        """Analyze properties by data type and generate mapping recommendations."""
        print(f"📊 Analyzing {len(properties)} properties...")
        
        # Initialize analysis structure
        analysis = {
            'total_properties': len(properties),
            'by_type': {},
            'property_details': [],
            'mapping_recommendations': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Categorize properties by type
        for prop in properties:
            prop_name = prop.get('name', '')
            prop_type = prop.get('type', 'UNKNOWN')
            prop_label = prop.get('label', '')
            prop_description = prop.get('description', '')
            
            # Count by type
            if prop_type not in analysis['by_type']:
                analysis['by_type'][prop_type] = 0
            analysis['by_type'][prop_type] += 1
            
            # Store detailed information
            analysis['property_details'].append({
                'name': prop_name,
                'type': prop_type,
                'label': prop_label,
                'description': prop_description,
                'field_type': prop.get('fieldType', 'unknown'),
                'has_unique_value': prop.get('hasUniqueValue', False),
                'calculated': prop.get('calculated', False),
                'external_options': prop.get('externalOptions', False)
            })
        
        # Generate mapping recommendations
        analysis['mapping_recommendations'] = self.generate_mapping_recommendations(properties)
        
        # Display summary
        print(f"\n📈 Property Type Distribution:")
        for prop_type, count in sorted(analysis['by_type'].items()):
            print(f"  {prop_type}: {count} properties")
        
        return analysis
    
    def generate_mapping_recommendations(self, properties):
        """Generate field mapping recommendations for database schema."""
        mappings = {
            'string_fields': [],
            'numeric_fields': [], 
            'boolean_fields': [],
            'datetime_fields': [],
            'text_fields': [],  # For longer text content
            'json_fields': []   # For complex nested data
        }
        
        for prop in properties:
            prop_name = prop.get('name', '')
            prop_type = prop.get('type', 'UNKNOWN')
            
            # Map to appropriate database field type
            if prop_type in ['string', 'enumeration', 'phone_number']:
                if 'description' in prop_name.lower() or 'note' in prop_name.lower():
                    mappings['text_fields'].append(prop_name)
                else:
                    mappings['string_fields'].append(prop_name)
            elif prop_type in ['number']:
                mappings['numeric_fields'].append(prop_name)
            elif prop_type in ['bool', 'boolean']:
                mappings['boolean_fields'].append(prop_name)
            elif prop_type in ['datetime', 'date']:
                mappings['datetime_fields'].append(prop_name)
            elif prop_type in ['json', 'object']:
                mappings['json_fields'].append(prop_name)
            else:
                # Default to string for unknown types
                mappings['string_fields'].append(prop_name)
        
        return mappings
    
    def get_sample_records(self, limit=5):
        """Fetch sample records to understand data structure."""
        print(f"📝 Fetching {limit} sample [ENTITY] records...")
        
        params = {
            'limit': limit,
            'properties': 'hs_object_id'  # Always include object ID
        }
        
        try:
            response = requests.get(self.objects_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            records_data = response.json()
            records = records_data.get('results', [])
            
            print(f"✅ Retrieved {len(records)} sample records")
            return records
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching sample records: {e}")
            return []
    
    def save_analysis(self, analysis, sample_records):
        """Save complete analysis to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Complete analysis with sample data
        complete_analysis = {
            'properties_analysis': analysis,
            'sample_records': sample_records,
            'metadata': {
                'entity': '[entity]',
                'api_version': 'v3',
                'portal_id': 1849303,  # Your portal ID
                'generated_by': 'explore_hubspot_[entity].py',
                'timestamp': timestamp
            }
        }
        
        # Save detailed analysis
        analysis_file = f'analysis/hubspot_[entity]_properties_analysis_{timestamp}.json'
        with open(analysis_file, 'w') as f:
            json.dump(complete_analysis, f, indent=2, default=str)
        
        print(f"💾 Analysis saved to: {analysis_file}")
        
        # Save summary report
        self.save_summary_report(analysis, timestamp)
        
        return analysis_file
    
    def save_summary_report(self, analysis, timestamp):
        """Save human-readable summary report."""
        summary_file = f'analysis/hubspot_[entity]_summary_{timestamp}.txt'
        
        with open(summary_file, 'w') as f:
            f.write("HubSpot [ENTITY] Properties Analysis Summary\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Properties: {analysis['total_properties']}\n")
            f.write(f"Analysis Date: {analysis['timestamp']}\n\n")
            
            f.write("Property Distribution by Type:\n")
            f.write("-" * 30 + "\n")
            for prop_type, count in sorted(analysis['by_type'].items()):
                f.write(f"{prop_type:20} {count:>3} properties\n")
            
            f.write("\nDatabase Field Mapping Recommendations:\n")
            f.write("-" * 40 + "\n")
            
            mappings = analysis['mapping_recommendations']
            for field_type, fields in mappings.items():
                if fields:
                    f.write(f"\n{field_type.upper()} ({len(fields)} fields):\n")
                    for field in sorted(fields):
                        f.write(f"  property_{field}\n")
            
            f.write(f"\nKey Properties to Include (Top 20):\n")
            f.write("-" * 35 + "\n")
            
            # List most important properties (customize based on entity)
            important_props = [prop for prop in analysis['property_details'] 
                             if not prop['calculated'] and prop['name'] not in ['hs_created_by', 'hs_updated_by']][:20]
            
            for prop in important_props:
                f.write(f"  {prop['name']:30} ({prop['type']})\n")
        
        print(f"📄 Summary report saved to: {summary_file}")
    
    def run_complete_analysis(self):
        """Run complete property analysis workflow."""
        print(f"🚀 Starting HubSpot [ENTITY] Properties Analysis")
        print("=" * 60)
        
        # Step 1: Get all properties
        properties = self.get_all_properties()
        if not properties:
            print("❌ No properties found. Check API token and permissions.")
            return
        
        # Step 2: Analyze properties
        analysis = self.analyze_properties(properties)
        
        # Step 3: Get sample records
        sample_records = self.get_sample_records(limit=5)
        
        # Step 4: Save complete analysis
        analysis_file = self.save_analysis(analysis, sample_records)
        
        print(f"\n✅ Analysis Complete!")
        print(f"📁 Files created:")
        print(f"   - {analysis_file}")
        print(f"   - analysis/hubspot_[entity]_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        print(f"\n🔄 Next Steps:")
        print(f"   1. Review the analysis files")
        print(f"   2. Create database schema using mapping recommendations")
        print(f"   3. Implement hubspot_[entity]_sync.py")
        print(f"   4. Add to Flask app dashboard")
        
        return analysis

def main():
    """Main execution function."""
    try:
        # TODO: Replace with actual entity class name
        explorer = HubSpotEntityExplorer()
        analysis = explorer.run_complete_analysis()
        
        if analysis:
            print(f"\n🎉 HubSpot ENTITY exploration completed successfully!")
        else:
            print(f"\n❌ Exploration failed. Check logs for details.")
            
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 