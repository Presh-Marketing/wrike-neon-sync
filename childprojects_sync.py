#!/usr/bin/env python3
"""
Wrike Child Projects to Neon DB Sync Script
Standalone script for syncing only child projects
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

class WrikeChildProjectsSync:
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
            'child_projects': 'IEAGEMDVPIABXIVA',
            'deliverables': 'IEAGEMDVPIABWGFL'
        }
        
        # Custom field mappings from blueprint
        self.custom_fields = {
            'child_type': 'IEAGEMDVJUAFZXSB',
            'program_name': 'IEAGEMDVJUAF2R5G',
            'co_marketing': 'IEAGEMDVJUAF2QNP',
            'approver_email': 'IEAGEMDVJUAFZXR5',
            'ziflow_id': 'IEAGEMDVJUAFZXVS',
            'hs_deal_id': 'IEAGEMDVJUAFZN76',
            'hs_company_id': 'IEAGEMDVJUAHBOIL',
            'brand_guide_url': 'IEAGEMDVJUAF2QEK',
            'google_drive_folder_id': 'IEAGEMDVJUAGD64G',
            'comarketing_required': 'IEAGEMDVJUAGTTIR'
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

# Note: parent_exists function removed because we handle parent relationships
# through PostgreSQL foreign key constraints and ON CONFLICT behavior

    def process_childprojects(self, child_projects: List[Dict], conn):
        """Process child projects in batches."""
        if self.test_limit:
            child_projects = child_projects[:self.test_limit]
            logger.info(f"Limited to {len(child_projects)} child projects for testing")
        
        logger.info(f"Found {len(child_projects)} child projects")
        
        # Batch processing configuration
        BATCH_SIZE = 25
        total_batches = (len(child_projects) + BATCH_SIZE - 1) // BATCH_SIZE if child_projects else 0
        
        processed_count = 0
        skipped_count = 0
        failed_batches = []
        successful_batches = 0
        
        # Process child projects in batches
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(child_projects))
            batch = child_projects[start_idx:end_idx]
            batch_project_ids = []
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} child projects)")
            
            try:
                with conn.cursor() as cursor:
                    batch_processed = 0
                    batch_skipped = 0
                    
                    for child_project in batch:
                        try:
                            project_id = child_project.get('id')
                            batch_project_ids.append(project_id)
                            
                            # Extract custom fields
                            custom_fields_map = {}
                            for field_name, field_id in self.custom_fields.items():
                                custom_fields_map[field_name] = self.get_custom_field_value(
                                    child_project.get('customFields', []), field_id
                                )

                            # Get child project details
                            project_data = child_project.get('project', {})
                            owner_ids = project_data.get('ownerIds', [])
                            owner_id = owner_ids[0] if owner_ids else None
                            parent_ids = child_project.get('parentIds', [])
                            parent_id = parent_ids[0] if parent_ids else None

                            # Note: We don't validate parent existence here because:
                            # 1. Some child projects have other child projects as parents (nested hierarchy)
                            # 2. PostgreSQL will handle foreign key constraints gracefully
                            # 3. ON CONFLICT will update existing records appropriately

                            # Insert/update child project using ON CONFLICT pattern
                            sql = """
                                INSERT INTO projects.childprojects (
                                    wrike_id,
                                    title,
                                    brief_description,
                                    description,
                                    created_date,
                                    updated_date,
                                    parent_id,
                                    status,
                                    child_type,
                                    program_name,
                                    co_marketing,
                                    approver_email,
                                    owner_id,
                                    ziflow_id,
                                    hs_deal_id,
                                    hs_company_id,
                                    permalink,
                                    workflow_id,
                                    custom_item_type_id,
                                    brand_guide,
                                    google_drive_folder_id,
                                    comarketing_required,
                                    active
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                                ON CONFLICT (wrike_id) DO UPDATE SET
                                    title = EXCLUDED.title,
                                    brief_description = EXCLUDED.brief_description,
                                    description = EXCLUDED.description,
                                    updated_date = EXCLUDED.updated_date,
                                    parent_id = EXCLUDED.parent_id,
                                    status = EXCLUDED.status,
                                    child_type = EXCLUDED.child_type,
                                    program_name = EXCLUDED.program_name,
                                    co_marketing = EXCLUDED.co_marketing,
                                    approver_email = EXCLUDED.approver_email,
                                    owner_id = EXCLUDED.owner_id,
                                    ziflow_id = EXCLUDED.ziflow_id,
                                    hs_deal_id = EXCLUDED.hs_deal_id,
                                    hs_company_id = EXCLUDED.hs_company_id,
                                    permalink = EXCLUDED.permalink,
                                    workflow_id = EXCLUDED.workflow_id,
                                    custom_item_type_id = EXCLUDED.custom_item_type_id,
                                    brand_guide = EXCLUDED.brand_guide,
                                    google_drive_folder_id = EXCLUDED.google_drive_folder_id,
                                    comarketing_required = EXCLUDED.comarketing_required,
                                    active = EXCLUDED.active;
                            """

                            # Parameters for child project INSERT
                            params = [
                                child_project.get('id'),  # wrike_id
                                self.safe_string(child_project.get('title')),  # title
                                self.safe_string(child_project.get('briefDescription')),  # brief_description
                                self.safe_string(child_project.get('description')),  # description
                                child_project.get('createdDate'),  # created_date
                                child_project.get('updatedDate'),  # updated_date
                                parent_id,  # parent_id
                                project_data.get('customStatusId'),  # status
                                self.safe_string(custom_fields_map.get('child_type')),  # child_type
                                self.safe_string(custom_fields_map.get('program_name')),  # program_name
                                self.safe_string(custom_fields_map.get('co_marketing')),  # co_marketing
                                self.safe_string(custom_fields_map.get('approver_email')),  # approver_email
                                owner_id,  # owner_id
                                self.safe_string(custom_fields_map.get('ziflow_id')),  # ziflow_id
                                self.safe_string(custom_fields_map.get('hs_deal_id')),  # hs_deal_id
                                self.safe_string(custom_fields_map.get('hs_company_id')),  # hs_company_id
                                child_project.get('permalink'),  # permalink
                                child_project.get('workflowId'),  # workflow_id
                                child_project.get('customItemTypeId'),  # custom_item_type_id
                                self.safe_string(custom_fields_map.get('brand_guide_url')),  # brand_guide
                                self.safe_string(custom_fields_map.get('google_drive_folder_id')),  # google_drive_folder_id
                                self.safe_string(custom_fields_map.get('comarketing_required')),  # comarketing_required
                                True  # active
                            ]

                            cursor.execute(sql, params)
                            batch_processed += 1
                            
                        except psycopg2.errors.ForeignKeyViolation as e:
                            logger.warning(f"Foreign key violation for child project {child_project.get('id')} in batch {batch_num + 1} - parent {parent_id} may not exist yet: {e}")
                            batch_skipped += 1
                            continue
                        except Exception as e:
                            logger.error(f"Error processing child project {child_project.get('id')} in batch {batch_num + 1}: {e}")
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
                    'project_ids': batch_project_ids,
                    'error': str(e),
                    'projects_count': len(batch)
                }
                failed_batches.append(failed_batch_info)
                
                logger.error(f"❌ Batch {batch_num + 1} FAILED: {e}")
                logger.error(f"Failed child project IDs: {batch_project_ids}")
                
                # Skip all projects in this batch
                skipped_count += len(batch)

        return processed_count, skipped_count, failed_batches, successful_batches

    def run_sync(self):
        """Main child projects sync process."""
        logger.info("Starting Wrike Child Projects sync...")
        
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
                # Get child projects
                child_projects = self.get_folders_by_type(space_id, self.custom_item_types['child_projects'])
                
                processed, skipped, failed_batches, successful_batches = self.process_childprojects(child_projects, conn)
                
                # No need for final commit since batches are committed individually
                
                logger.info("Child Projects sync completed successfully!")
                logger.info(f"Summary: {processed} child projects processed, {skipped} skipped")
                
                if failed_batches:
                    logger.warning(f"❌ {len(failed_batches)} batches FAILED!")
                    for failed_batch in failed_batches:
                        logger.error(f"Batch {failed_batch['batch_number']}: {failed_batch['projects_count']} projects failed - {failed_batch['error']}")
                else:
                    logger.info("✅ All batches completed successfully!")

            finally:
                conn.close()
                logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"Child Projects sync failed: {e}")
            raise


def main():
    """Main function."""
    import sys
    
    # Check for test limit argument
    test_limit = None
    if len(sys.argv) > 1:
        try:
            test_limit = int(sys.argv[1])
            logger.info(f"Running in test mode with limit: {test_limit} records per project")
        except ValueError:
            logger.error("Test limit must be a number. Usage: python childprojects_sync.py [limit]")
            return
    
    required_vars = ['WRIKE_API_TOKEN', 'NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Create a .env file or set these environment variables:")
        for var in missing_vars:
            logger.info(f"  {var}=your_value_here")
        return

    sync = WrikeChildProjectsSync(test_limit=test_limit)
    sync.run_sync()


if __name__ == '__main__':
    main() 