#!/usr/bin/env python3
"""
Wrike Deliverables to Neon DB Sync Script
Standalone script for syncing only deliverables
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

class WrikeDeliverablesSync:
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
            'deliverable_type': 'IEAGEMDVJUAFX3LA',
            'deliverable_category': 'IEAGEMDVJUAGOJU2',
            'proof_id': 'IEAGEMDVJUAFZN7T',
            'proof_url': 'IEAGEMDVJUAFZQQX',
            'proof_version': 'IEAGEMDVJUAFZN7V',
            'proof_status': 'IEAGEMDVJUAFZN6T',
            'proof_error': 'IEAGEMDVJUAFZ3KF',
            'google_drive_folder_id': 'IEAGEMDVJUAGD64G',
            'publish_owner': 'IEAGEMDVJUAGNW55',
            'target_pub_date': 'IEAGEMDVJUAHD4AP',
            'original_date': 'IEAGEMDVJUAHES5L'
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

    def parent_exists(self, parent_id: str, cursor) -> bool:
        """Check if parent_id exists in childprojects table."""
        if not parent_id:
            return True  # Allow null parent_id
            
        cursor.execute(
            "SELECT 1 FROM projects.childprojects WHERE wrike_id = %s LIMIT 1",
            (parent_id,)
        )
        return cursor.fetchone() is not None

    def process_deliverables_from_folder(self, folder_id: str, conn):
        """Process deliverables from a specific folder in batches."""
        tasks = self.get_folder_tasks(folder_id)
        
        # Filter only deliverables
        deliverables = [
            task for task in tasks 
            if task.get('customItemTypeId') == self.custom_item_types['deliverables']
        ]
        
        if self.test_limit:
            deliverables = deliverables[:self.test_limit]
            logger.info(f"Limited to {len(deliverables)} deliverables for testing")
        
        logger.info(f"Found {len(deliverables)} deliverables in folder {folder_id}")
        
        # Batch processing configuration
        BATCH_SIZE = 25
        total_batches = (len(deliverables) + BATCH_SIZE - 1) // BATCH_SIZE if deliverables else 0
        
        processed_count = 0
        skipped_count = 0
        failed_batches = []
        successful_batches = 0
        
        # Process deliverables in batches
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(deliverables))
            batch = deliverables[start_idx:end_idx]
            batch_deliverable_ids = []
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} deliverables) for folder {folder_id}")
            
            try:
                with conn.cursor() as cursor:
                    batch_processed = 0
                    batch_skipped = 0
                    
                    for deliverable in batch:
                        try:
                            deliverable_id = deliverable.get('id')
                            batch_deliverable_ids.append(deliverable_id)
                            
                            # Extract custom fields
                            custom_fields_map = {}
                            for field_name, field_id in self.custom_fields.items():
                                custom_fields_map[field_name] = self.get_custom_field_value(
                                    deliverable.get('customFields', []), field_id
                                )

                            # Get deliverable details
                            responsible_ids = deliverable.get('responsibleIds', [])
                            responsible_id = responsible_ids[0] if responsible_ids else None
                            parent_ids = deliverable.get('parentIds', [])
                            parent_id = parent_ids[0] if parent_ids else None
                            super_parent_ids = deliverable.get('superParentIds', [])
                            super_parent_id = super_parent_ids[0] if super_parent_ids else None
                            super_task_ids = deliverable.get('superTaskIds', [])
                            super_task_id = super_task_ids[0] if super_task_ids else ''

                            # Check if parent exists before processing deliverable
                            if not self.parent_exists(parent_id, cursor):
                                logger.warning(f"Parent ID {parent_id} not found for deliverable {deliverable.get('id')} - skipping")
                                batch_skipped += 1
                                continue

                            # Handle effort allocation - store raw minutes from Wrike API
                            effort_allocation = deliverable.get('effortAllocation', {})
                            total_effort = effort_allocation.get('totalEffort', 0)
                            if total_effort is None or total_effort == '':
                                total_effort = 0

                            # Handle proof version
                            proof_version = custom_fields_map.get('proof_version')
                            if proof_version is None or proof_version == '':
                                proof_version = 0

                            # Handle subtask IDs for deliverables
                            sub_task_ids = deliverable.get('subTaskIds', [])
                            sub_task_ids_str = '{' + ','.join(sub_task_ids) + '}' if sub_task_ids else '{}'

                            # Handle dependency IDs
                            dependency_ids = deliverable.get('dependencyIds', [])
                            dependency_ids_str = '{' + ','.join(dependency_ids) + '}' if dependency_ids else '{}'

                            # Handle other fields that might be null
                            importance = deliverable.get('importance') or ''
                            priority = deliverable.get('priority') or ''
                            status = deliverable.get('status') or ''
                            scope = deliverable.get('scope') or ''

                            # Insert/update deliverable using the same pattern as tasks
                            sql = """
                                WITH up AS (
                                  UPDATE projects.deliverables
                                     SET title               = %s,
                                         brief_description   = %s,
                                         description         = %s,
                                         status              = %s,
                                         custom_status_id    = %s,
                                         updated_date        = %s,
                                         parent_id           = %s,
                                         super_parent_id     = %s,
                                         super_task_id       = %s,
                                         owner_id            = %s,
                                         start_date          = %s,
                                         due_date            = %s,
                                         scope               = %s,
                                         deliverable_type    = %s,
                                         deliverable_category= %s,
                                         proof_id            = %s,
                                         proof_url           = %s,
                                         proof_version       = %s,
                                         proof_status        = %s,
                                         proof_error         = %s,
                                         drive_id            = %s,
                                         publish_owner       = %s,
                                         total_effort        = %s,
                                         effort_mode         = %s,
                                         subtask_ids         = %s,
                                         dependency_ids      = %s,
                                         has_attachments     = %s,
                                         importance          = %s,
                                         permalink           = %s,
                                         priority            = %s,
                                         billing_type        = %s,
                                         custom_item_type_id = %s,
                                         active              = %s
                                   WHERE wrike_id = %s
                                   RETURNING wrike_id
                                )
                                INSERT INTO projects.deliverables (
                                    wrike_id, title, brief_description, description,
                                    status, custom_status_id, created_date, updated_date,
                                    parent_id, super_parent_id, super_task_id, owner_id,
                                    start_date, due_date, scope, deliverable_type, deliverable_category,
                                    proof_id, proof_url, proof_version, proof_status,
                                    proof_error, drive_id, publish_owner, total_effort,
                                    effort_mode, subtask_ids, dependency_ids, has_attachments,
                                    importance, permalink, priority, billing_type,
                                    custom_item_type_id, active
                                ) SELECT
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s
                                WHERE NOT EXISTS (SELECT 1 FROM up);
                            """

                            dates = deliverable.get('dates', {})
                            
                            # Parameters for UPDATE
                            update_params = [
                                self.safe_string(deliverable.get('title')),
                                self.safe_string(deliverable.get('briefDescription')),
                                self.safe_string(deliverable.get('description')),
                                status,
                                deliverable.get('customStatusId'),
                                deliverable.get('updatedDate'),
                                parent_id,
                                super_parent_id,
                                super_task_id,
                                responsible_id,
                                dates.get('start'),
                                dates.get('due'),
                                scope,
                                self.safe_string(custom_fields_map.get('deliverable_type')),
                                self.safe_string(custom_fields_map.get('deliverable_category')),
                                self.safe_string(custom_fields_map.get('proof_id')),
                                self.safe_string(custom_fields_map.get('proof_url')),
                                proof_version,
                                self.safe_string(custom_fields_map.get('proof_status')),
                                self.safe_string(custom_fields_map.get('proof_error')),
                                self.safe_string(custom_fields_map.get('google_drive_folder_id')),
                                self.safe_string(custom_fields_map.get('publish_owner')),
                                total_effort,
                                effort_allocation.get('mode'),
                                sub_task_ids_str,
                                dependency_ids_str,
                                deliverable.get('hasAttachments', False),
                                importance,
                                deliverable.get('permalink'),
                                priority,
                                deliverable.get('billingType'),
                                deliverable.get('customItemTypeId'),
                                True,
                                deliverable.get('id')  # WHERE condition
                            ]
                            
                            # Parameters for INSERT
                            insert_params = [
                                deliverable.get('id'),
                                self.safe_string(deliverable.get('title')),
                                self.safe_string(deliverable.get('briefDescription')),
                                self.safe_string(deliverable.get('description')),
                                status,
                                deliverable.get('customStatusId'),
                                deliverable.get('createdDate'),
                                deliverable.get('updatedDate'),
                                parent_id,
                                super_parent_id,
                                super_task_id,
                                responsible_id,
                                dates.get('start'),
                                dates.get('due'),
                                scope,
                                self.safe_string(custom_fields_map.get('deliverable_type')),
                                self.safe_string(custom_fields_map.get('deliverable_category')),
                                self.safe_string(custom_fields_map.get('proof_id')),
                                self.safe_string(custom_fields_map.get('proof_url')),
                                proof_version,
                                self.safe_string(custom_fields_map.get('proof_status')),
                                self.safe_string(custom_fields_map.get('proof_error')),
                                self.safe_string(custom_fields_map.get('google_drive_folder_id')),
                                self.safe_string(custom_fields_map.get('publish_owner')),
                                total_effort,
                                effort_allocation.get('mode'),
                                sub_task_ids_str,
                                dependency_ids_str,
                                deliverable.get('hasAttachments', False),
                                importance,
                                deliverable.get('permalink'),
                                priority,
                                deliverable.get('billingType'),
                                deliverable.get('customItemTypeId'),
                                True
                            ]

                            cursor.execute(sql, update_params + insert_params)
                            batch_processed += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing deliverable {deliverable.get('id')} in batch {batch_num + 1}: {e}")
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
                    'deliverable_ids': batch_deliverable_ids,
                    'error': str(e),
                    'deliverables_count': len(batch),
                    'folder_id': folder_id
                }
                failed_batches.append(failed_batch_info)
                
                logger.error(f"❌ Batch {batch_num + 1} FAILED for folder {folder_id}: {e}")
                logger.error(f"Failed deliverable IDs: {batch_deliverable_ids}")
                
                # Skip all deliverables in this batch
                skipped_count += len(batch)

        return processed_count, skipped_count, failed_batches, successful_batches

    def run_sync(self):
        """Main deliverables sync process."""
        logger.info("Starting Wrike Deliverables sync...")
        
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
                # Get child projects (which contain deliverables)
                child_projects = self.get_folders_by_type(space_id, self.custom_item_types['child_projects'])
                
                if self.test_limit:
                    child_projects = child_projects[:self.test_limit]
                    logger.info(f"Limited to {len(child_projects)} child projects for testing")
                
                total_processed = 0
                total_skipped = 0
                
                total_failed_batches = []
                
                for i, project in enumerate(child_projects, 1):
                    project_title = project.get('title', 'Unknown')
                    logger.info(f"Processing project {i}/{len(child_projects)}: {project_title[:50]}...")
                    
                    processed, skipped, failed_batches, successful_batches = self.process_deliverables_from_folder(project.get('id'), conn)
                    total_processed += processed
                    total_skipped += skipped
                    total_failed_batches.extend(failed_batches)
                
                # No need for final commit since batches are committed individually
                
                logger.info("Deliverables sync completed successfully!")
                logger.info(f"Summary: {total_processed} deliverables processed, {total_skipped} skipped")

            finally:
                conn.close()
                logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"Deliverables sync failed: {e}")
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
            logger.error("Test limit must be a number. Usage: python deliverables_sync.py [limit]")
            return
    
    required_vars = ['WRIKE_API_TOKEN', 'NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Create a .env file or set these environment variables:")
        for var in missing_vars:
            logger.info(f"  {var}=your_value_here")
        return

    sync = WrikeDeliverablesSync(test_limit=test_limit)
    sync.run_sync()


if __name__ == '__main__':
    main() 