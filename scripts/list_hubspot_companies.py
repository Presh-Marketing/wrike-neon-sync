#!/usr/bin/env python3
"""
HubSpot Companies Lister
Shows which companies would be synced without actually syncing them
"""

import os
import logging
import requests
import json
from typing import Dict, List, Optional
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

class HubSpotCompaniesLister:
    def __init__(self, limit=None):
        """Initialize with environment variables."""
        self.hubspot_token = os.getenv('HUBSPOT_API_TOKEN')
        self.hubspot_base_url = 'https://api.hubapi.com/crm/v3'
        self.limit = limit
        
        # Basic properties for listing/validation
        self.basic_properties = [
            'name', 'domain', 'website', 'city', 'state', 'country', 'industry',
            'lifecyclestage', 'createdate', 'hs_lastmodifieddate', 'hubspot_owner_id',
            'annualrevenue', 'numberofemployees', 'phone', 'type', 'wrikeid',
            'ziflowcompanyid', 'quickbooksclientid'
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.hubspot_token}',
            'Content-Type': 'application/json'
        })

    def get_companies_batch(self, after_token: Optional[str] = None, limit: int = 100) -> Dict:
        """Get a batch of companies from HubSpot API."""
        try:
            params = {
                'properties': ','.join(self.basic_properties),
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

    def get_companies_list(self) -> List[Dict]:
        """Get companies list with pagination."""
        all_companies = []
        after_token = None
        batch_size = 100
        
        if self.limit:
            batch_size = min(batch_size, self.limit)
        
        while True:
            batch_data = self.get_companies_batch(after_token, batch_size)
            
            if not batch_data or 'results' not in batch_data:
                break
                
            companies = batch_data['results']
            all_companies.extend(companies)
            
            # Check if we've reached test limit
            if self.limit and len(all_companies) >= self.limit:
                all_companies = all_companies[:self.limit]
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

    def format_value(self, value):
        """Format value for display."""
        if value is None:
            return "N/A"
        if isinstance(value, str) and len(value) > 50:
            return value[:47] + "..."
        return str(value)

    def list_companies(self):
        """List companies and create detailed logs."""
        companies = self.get_companies_list()
        
        if not companies:
            print("No companies found!")
            return
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create summary file
        summary_file = f"hubspot_companies_summary_{timestamp}.txt"
        detailed_file = f"hubspot_companies_detailed_{timestamp}.json"
        
        print(f"\n{'='*80}")
        print(f"HUBSPOT COMPANIES LIST ({len(companies)} companies)")
        print(f"{'='*80}")
        
        with open(summary_file, 'w') as f:
            f.write(f"HubSpot Companies Summary\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Companies: {len(companies)}\n")
            f.write("="*80 + "\n\n")
            
            print(f"{'#':<3} {'ID':<12} {'Name':<30} {'Domain':<25} {'Industry':<20}")
            print("-" * 90)
            f.write(f"{'#':<3} {'ID':<12} {'Name':<30} {'Domain':<25} {'Industry':<20}\n")
            f.write("-" * 90 + "\n")
            
            for i, company in enumerate(companies, 1):
                company_id = company.get('id', 'N/A')
                properties = company.get('properties', {})
                
                name = self.format_value(properties.get('name'))
                domain = self.format_value(properties.get('domain'))
                industry = self.format_value(properties.get('industry'))
                
                # Truncate for display
                name_display = name[:29] if len(name) > 29 else name
                domain_display = domain[:24] if len(domain) > 24 else domain
                industry_display = industry[:19] if len(industry) > 19 else industry
                
                line = f"{i:<3} {company_id:<12} {name_display:<30} {domain_display:<25} {industry_display:<20}"
                print(line)
                f.write(line + "\n")
                
                # Additional details
                if i <= 10:  # Show details for first 10
                    details = []
                    city = properties.get('city')
                    state = properties.get('state')
                    country = properties.get('country')
                    
                    location_parts = [city, state, country]
                    location = ", ".join([part for part in location_parts if part])
                    if location:
                        details.append(f"Location: {location}")
                    
                    lifecycle = properties.get('lifecyclestage')
                    if lifecycle:
                        details.append(f"Stage: {lifecycle}")
                    
                    revenue = properties.get('annualrevenue')
                    if revenue:
                        try:
                            revenue_float = float(revenue)
                            details.append(f"Revenue: ${revenue_float:,.0f}")
                        except (ValueError, TypeError):
                            details.append(f"Revenue: {revenue}")
                    
                    employees = properties.get('numberofemployees')
                    if employees:
                        details.append(f"Employees: {employees}")
                    
                    wrike_id = properties.get('wrikeid')
                    if wrike_id:
                        details.append(f"Wrike ID: {wrike_id}")
                    
                    if details:
                        detail_line = "    " + " | ".join(details)
                        print(detail_line)
                        f.write(detail_line + "\n")
                
                if i == 10 and len(companies) > 10:
                    remaining = len(companies) - 10
                    print(f"    ... and {remaining} more companies")
                    f.write(f"    ... and {remaining} more companies\n")
            
            f.write(f"\nSummary by Industry:\n")
            f.write("-" * 40 + "\n")
            
            # Industry breakdown
            industries = {}
            for company in companies:
                industry = company.get('properties', {}).get('industry', 'Unknown')
                industries[industry] = industries.get(industry, 0) + 1
            
            print(f"\nIndustry Breakdown:")
            for industry, count in sorted(industries.items(), key=lambda x: x[1], reverse=True):
                line = f"  {industry}: {count}"
                print(line)
                f.write(line + "\n")
        
        # Create detailed JSON file
        with open(detailed_file, 'w') as f:
            json.dump(companies, f, indent=2, default=str)
        
        print(f"\nFiles created:")
        print(f"  📄 {summary_file} - Human-readable summary")
        print(f"  📄 {detailed_file} - Full JSON data")
        
        # Show integration IDs for first few companies
        print(f"\nIntegration IDs (first 5 companies):")
        print("-" * 60)
        for i, company in enumerate(companies[:5], 1):
            properties = company.get('properties', {})
            name = properties.get('name', 'Unknown')[:25]
            
            integrations = []
            wrike_id = properties.get('wrikeid')
            if wrike_id:
                integrations.append(f"Wrike: {wrike_id}")
            
            ziflow_id = properties.get('ziflowcompanyid')
            if ziflow_id:
                integrations.append(f"Ziflow: {ziflow_id}")
            
            qb_id = properties.get('quickbooksclientid')
            if qb_id:
                integrations.append(f"QB: {qb_id}")
            
            integration_text = " | ".join(integrations) if integrations else "None"
            print(f"  {i}. {name:<25} {integration_text}")


def main():
    """Main function."""
    import sys
    
    # Check for limit argument
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"Listing first {limit} companies...")
        except ValueError:
            print("Limit must be a number. Usage: python list_hubspot_companies.py [limit]")
            return
    
    if not os.getenv('HUBSPOT_API_TOKEN'):
        print("Error: HUBSPOT_API_TOKEN environment variable not set.")
        print("Please add it to your .env file or set it as an environment variable.")
        return

    lister = HubSpotCompaniesLister(limit=limit)
    lister.list_companies()


if __name__ == '__main__':
    main() 