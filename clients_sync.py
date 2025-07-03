#!/usr/bin/env python3
"""
Wrike Clients to Neon DB Sync Script
Standalone script for syncing only clients
"""

import os
import logging
import requests
import psycopg2
import psycopg2.errors
from typing import Dict, List, Optional, Any

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

class WrikeClientsSync:
    def __init__(self, test_limit=None):
        """Initialize with environment variables."""
        self.wrike_token = os.getenv('WRIKE_API_TOKEN')
        self.wrike_base_url = 'https://www.wrike.com/api/v4'
        self.test_limit = test_limit  # Limit for testing
        
        self.db_config = {
            'host': os.getenv('NEON_HOST'),
            'database': os.getenv('NEON_DATABASE'),
            'user': os.getenv('NEON_USER'),
            'password': os.getenv('NEON_PASSWORD'),
            'port': os.getenv('NEON_PORT', 5432),
            'sslmode': 'require'
        }
        
        # Custom item types from blueprint
        self.custom_item_types = {
            'clients': 'IEAGEMDVPIABX4FV'
        }
        
        # Custom field mappings from blueprint
        self.custom_fields = {
            'google_drive_folder_id': 'IEAGEMDVJUAGD64G',
            'approver_email': 'IEAGEMDVJUAFZXR5',
            'ziflow_id': 'IEAGEMDVJUAFZXVS',
            'hubspot_id': 'IEAGEMDVJUAFZN76',
            'brand_guide_url': 'IEAGEMDVJUAF2QEK'
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'bearer {self.wrike_token}',
            'Content-Type': 'application/json'
        })

    def get_custom_field_value(self, custom_fields: List[Dict], field_id: str) -> Any:
        """Extract custom field value by field ID."""
        for field in custom_fields:
            if field.get('id') == field_id:
                return field.get('value')
        return None

    def safe_string(self, value: Any) -> str:
        """Safely convert value to string and escape single quotes for SQL."""
        if value is None:
            return ''
        return str(value).replace("'", "''")

    def get_wrike_spaces(self) -> List[Dict]:
        """Get all Wrike spaces."""
        try:
            response = self.session.get(f'{self.wrike_base_url}/spaces')
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data.get('data', []))} spaces")
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching Wrike spaces: {e}")
            return []

    def get_production_space(self) -> Optional[Dict]:
        """Find the Production space."""
        spaces = self.get_wrike_spaces()
        for space in spaces:
            if space.get('title') == 'Production':
                logger.info(f"Found Production space: {space.get('id')}")
                return space
        logger.warning("Production space not found")
        return None

    def get_folders_by_type(self, space_id: str, custom_item_type: str) -> List[Dict]:
        """Get folders from a space filtered by custom item type."""
        try:
            params = {
                'customItemTypes': f'[{custom_item_type}]',
                'fields': '[customFields,metadata,description,briefDescription,attachmentCount,superParentIds,space,customItemTypeId,hasAttachments]',
                'project': 'true'
            }
            
            response = self.session.get(
                f'{self.wrike_base_url}/spaces/{space_id}/folders',
                params=params
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data.get('data', []))} folders for type {custom_item_type}")
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching folders for type {custom_item_type}: {e}")
            return []

    def get_folder_tasks(self, folder_id: str) -> List[Dict]:
        """Get all tasks and deliverables from a folder."""
        try:
            params = {
                'fields': '[customFields,recurrent,attachmentCount,effortAllocation,billingType,hasAttachments,attachmentCount,parentIds,superParentIds,responsibleIds,description,briefDescription,superTaskIds,subTaskIds,dependencyIds,customItemTypeId]',
                'descendants': 'true',
                'subTasks': 'true'
            }
            
            response = self.session.get(
                f'{self.wrike_base_url}/folders/{folder_id}/tasks',
                params=params
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data.get('data', []))} tasks from folder {folder_id}")
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching tasks for folder {folder_id}: {e}")
            return []

    def connect_db(self):
        """Connect to Neon PostgreSQL database."""
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to Neon database")
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def process_clients(self, clients: List[Dict], conn):
        """Process clients in batches."""
        if self.test_limit:
            clients = clients[:self.test_limit]
            logger.info(f"Limited to {len(clients)} clients for testing")
        
        logger.info(f"Found {len(clients)} clients")
        
        # Batch processing configuration
        BATCH_SIZE = 25
        total_batches = (len(clients) + BATCH_SIZE - 1) // BATCH_SIZE if clients else 0
        
        processed_count = 0
        skipped_count = 0
        failed_batches = []
        successful_batches = 0
        
        # Process clients in batches
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(clients))
            batch = clients[start_idx:end_idx]
            batch_client_ids = []
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} clients)")
            
            try:
                with conn.cursor() as cursor:
                    batch_processed = 0
                    batch_skipped = 0
                    
                    for client in batch:
                        try:
                            client_id = client.get('id')
                            batch_client_ids.append(client_id)
                            
                            # Extract custom fields (clients use individual extraction pattern)
                            google_drive_folder_id = self.get_custom_field_value(
                                client.get('customFields', []), 
                                self.custom_fields['google_drive_folder_id']
                            )
                            approver_email = self.get_custom_field_value(
                                client.get('customFields', []), 
                                self.custom_fields['approver_email']
                            )
                            ziflow_id = self.get_custom_field_value(
                                client.get('customFields', []), 
                                self.custom_fields['ziflow_id']
                            )
                            hubspot_id = self.get_custom_field_value(
                                client.get('customFields', []), 
                                self.custom_fields['hubspot_id']
                            )
                            brand_guide_url = self.get_custom_field_value(
                                client.get('customFields', []), 
                                self.custom_fields['brand_guide_url']
                            )

                            # Get project info
                            project_info = client.get('project', {})
                            owner_ids = project_info.get('ownerIds', [])
                            owner_id = owner_ids[0] if owner_ids else None

                            # Insert/update client using ON CONFLICT pattern
                            sql = """
                                INSERT INTO projects.clients (
                                    wrike_id,
                                    title,
                                    created_date,
                                    updated_date,
                                    approver_email,
                                    hubspot_id,
                                    ziflow_id,
                                    owner_id,
                                    status,
                                    custom_status_id,
                                    brand_guide_url,
                                    google_drive_folder_id,
                                    brief_description,
                                    description,
                                    active
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                                ON CONFLICT (wrike_id) DO UPDATE SET
                                    title = EXCLUDED.title,
                                    updated_date = EXCLUDED.updated_date,
                                    approver_email = EXCLUDED.approver_email,
                                    hubspot_id = EXCLUDED.hubspot_id,
                                    ziflow_id = EXCLUDED.ziflow_id,
                                    owner_id = EXCLUDED.owner_id,
                                    status = EXCLUDED.status,
                                    custom_status_id = EXCLUDED.custom_status_id,
                                    brand_guide_url = EXCLUDED.brand_guide_url,
                                    google_drive_folder_id = EXCLUDED.google_drive_folder_id,
                                    brief_description = EXCLUDED.brief_description,
                                    description = EXCLUDED.description,
                                    active = EXCLUDED.active;
                            """

                            # Parameters for client INSERT
                            params = [
                                client.get('id'),  # wrike_id
                                self.safe_string(client.get('title')),  # title
                                client.get('createdDate'),  # created_date
                                client.get('updatedDate'),  # updated_date
                                self.safe_string(approver_email),  # approver_email
                                self.safe_string(hubspot_id),  # hubspot_id
                                self.safe_string(ziflow_id),  # ziflow_id
                                owner_id,  # owner_id
                                'Active',  # status
                                project_info.get('customStatusId'),  # custom_status_id
                                self.safe_string(brand_guide_url),  # brand_guide_url
                                self.safe_string(google_drive_folder_id),  # google_drive_folder_id
                                self.safe_string(client.get('briefDescription')),  # brief_description
                                self.safe_string(client.get('description')),  # description
                                True  # active
                            ]

                            cursor.execute(sql, params)
                            batch_processed += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing client {client.get('id')} in batch {batch_num + 1}: {e}")
                            batch_skipped += 1
                            continue
                    
                    # Commit this batch
                    conn.commit()
                    processed_count += batch_processed
                    skipped_count += batch_skipped
                    successful_batches += 1
                    
                    logger.info(f"✅ Batch {batch_num + 1} completed successfully: {batch_processed} processed, {batch_skipped} skipped")
                        
            except Exception as e:
                # Batch failed - rollback and log the failure
                conn.rollback()
                failed_batch_info = {
                    'batch_number': batch_num + 1,
                    'client_ids': batch_client_ids,
                    'error': str(e),
                    'clients_count': len(batch)
                }
                failed_batches.append(failed_batch_info)
                
                logger.error(f"❌ Batch {batch_num + 1} FAILED: {e}")
                logger.error(f"Failed client IDs: {batch_client_ids}")
                
                # Skip all clients in this batch
                skipped_count += len(batch)

        return processed_count, skipped_count, failed_batches, successful_batches

    def run_sync(self):
        """Main clients sync process."""
        logger.info("Starting Wrike Clients sync...")
        
        try:
            # Get Production space
            production_space = self.get_production_space()
            if not production_space:
                logger.error("Production space not found. Exiting.")
                return

            space_id = production_space.get('id')

            # Connect to database
            conn = self.connect_db()

            try:
                # Get clients
                clients = self.get_folders_by_type(space_id, self.custom_item_types['clients'])
                
                processed, skipped, failed_batches, successful_batches = self.process_clients(clients, conn)
                
                # No need for final commit since batches are committed individually
                
                logger.info("Clients sync completed successfully!")
                logger.info(f"Summary: {processed} clients processed, {skipped} skipped")
                
                if failed_batches:
                    logger.warning(f"❌ {len(failed_batches)} batches FAILED!")
                    for failed_batch in failed_batches:
                        logger.error(f"Batch {failed_batch['batch_number']}: {failed_batch['clients_count']} clients failed - {failed_batch['error']}")
                else:
                    logger.info("✅ All batches completed successfully!")

            finally:
                conn.close()
                logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"Clients sync failed: {e}")
            raise


def main():
    """Main function."""
    import sys
    
    # Check for test limit argument
    test_limit = None
    if len(sys.argv) > 1:
        try:
            test_limit = int(sys.argv[1])
            logger.info(f"Running in test mode with limit: {test_limit} clients")
        except ValueError:
            logger.error("Test limit must be a number. Usage: python clients_sync.py [limit]")
            return
    
    required_vars = ['WRIKE_API_TOKEN', 'NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Create a .env file or set these environment variables:")
        for var in missing_vars:
            logger.info(f"  {var}=your_value_here")
        return

    sync = WrikeClientsSync(test_limit=test_limit)
    sync.run_sync()


if __name__ == '__main__':
    main() 