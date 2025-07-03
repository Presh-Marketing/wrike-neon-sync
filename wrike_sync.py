#!/usr/bin/env python3
"""
Wrike to Neon DB Sync Script
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

class WrikeNeonSync:
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
            'clients': 'IEAGEMDVPIABX4FV',
            'parent_projects': 'IEAGEMDVPIABXIU5',
            'child_projects': 'IEAGEMDVPIABXIVA',
            'deliverables': 'IEAGEMDVPIABWGFL'
        }
        
        # Custom field mappings from blueprint
        self.custom_fields = {
            'google_drive_folder_id': 'IEAGEMDVJUAGD64G',
            'approver_email': 'IEAGEMDVJUAFZXR5',
            'ziflow_id': 'IEAGEMDVJUAFZXVS',
            'hubspot_id': 'IEAGEMDVJUAFZN76',
            'brand_guide_url': 'IEAGEMDVJUAF2QEK',
            'parent_category': 'IEAGEMDVJUAFZXR6',
            'program_name': 'IEAGEMDVJUAF2R5G',
            'co_marketing': 'IEAGEMDVJUAF2QNP',
            'hs_company_id': 'IEAGEMDVJUAHBOIL',
            'comarketing_required': 'IEAGEMDVJUAGTTIR',
            'child_type': 'IEAGEMDVJUAFZXSB',
            'deliverable_type': 'IEAGEMDVJUAFX3LA',
            'deliverable_category': 'IEAGEMDVJUAGOJU2',
            'proof_id': 'IEAGEMDVJUAFZN7T',
            'proof_url': 'IEAGEMDVJUAFZQQX',
            'proof_version': 'IEAGEMDVJUAFZN7V',
            'proof_status': 'IEAGEMDVJUAFZN6T',
            'proof_error': 'IEAGEMDVJUAFZ3KF',
            'company': 'IEAGEMDVJUAHIQEQ',
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

    def process_clients(self, space_id: str, conn):
        """Process and sync client data."""
        logger.info("Processing clients...")
        clients = self.get_folders_by_type(space_id, self.custom_item_types['clients'])
        
        if self.test_limit:
            clients = clients[:self.test_limit]
            logger.info(f"Limited to {len(clients)} clients for testing")
        
        with conn.cursor() as cursor:
            for client in clients:
                # Extract custom fields
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

                # Prepare SQL
                sql = """
                    INSERT INTO projects.clients (
                        wrike_id, title, created_date, updated_date, approver_email,
                        hubspot_id, ziflow_id, owner_id, status, custom_status_id,
                        brand_guide_url, google_drive_folder_id, brief_description,
                        description, active
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

                cursor.execute(sql, (
                    client.get('id'),
                    self.safe_string(client.get('title')),
                    client.get('createdDate'),
                    client.get('updatedDate'),
                    self.safe_string(approver_email),
                    self.safe_string(hubspot_id),
                    self.safe_string(ziflow_id),
                    owner_id,
                    'Active',
                    project_info.get('customStatusId'),
                    self.safe_string(brand_guide_url),
                    self.safe_string(google_drive_folder_id),
                    self.safe_string(client.get('briefDescription')),
                    self.safe_string(client.get('description')),
                    True
                ))

        conn.commit()
        logger.info(f"Processed {len(clients)} clients")

    def process_parent_projects(self, space_id: str, conn):
        """Process and sync parent project data."""
        logger.info("Processing parent projects...")
        parent_projects = self.get_folders_by_type(space_id, self.custom_item_types['parent_projects'])
        
        if self.test_limit:
            parent_projects = parent_projects[:self.test_limit]
            logger.info(f"Limited to {len(parent_projects)} parent projects for testing")
        
        with conn.cursor() as cursor:
            for project in parent_projects:
                # Extract custom fields
                custom_fields_map = {}
                for field_name, field_id in self.custom_fields.items():
                    custom_fields_map[field_name] = self.get_custom_field_value(
                        project.get('customFields', []), field_id
                    )

                # Get project info
                project_info = project.get('project', {})
                owner_ids = project_info.get('ownerIds', [])
                owner_id = owner_ids[0] if owner_ids else None
                parent_ids = project.get('parentIds', [])
                parent_id = parent_ids[0] if parent_ids else None
                child_ids = project.get('childIds', [])
                has_children = len(child_ids) > 0

                # Prepare SQL with ON CONFLICT upsert
                sql = """
                    INSERT INTO projects.parentprojects (
                        wrike_id, title, created_date, updated_date, parent_wrike_id,
                        client_wrike_id, status, custom_status_id, parent_category,
                        program_name, co_marketing, approver_email, owner_id, ziflow_id,
                        hs_deal_id, hs_company_id, permalink, workflow_id, custom_item_type_id,
                        brand_guide_url, google_drive_folder_id, brief_description,
                        description, comarketing_required, has_children, active
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (wrike_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        updated_date = EXCLUDED.updated_date,
                        parent_wrike_id = EXCLUDED.parent_wrike_id,
                        client_wrike_id = EXCLUDED.client_wrike_id,
                        status = EXCLUDED.status,
                        custom_status_id = EXCLUDED.custom_status_id,
                        parent_category = EXCLUDED.parent_category,
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
                        brand_guide_url = EXCLUDED.brand_guide_url,
                        google_drive_folder_id = EXCLUDED.google_drive_folder_id,
                        brief_description = EXCLUDED.brief_description,
                        description = EXCLUDED.description,
                        comarketing_required = EXCLUDED.comarketing_required,
                        has_children = EXCLUDED.has_children,
                        active = EXCLUDED.active;
                """

                cursor.execute(sql, (
                    project.get('id'),
                    self.safe_string(project.get('title')),
                    project.get('createdDate'),
                    project.get('updatedDate'),
                    parent_id,
                    parent_id,  # client_wrike_id same as parent_wrike_id in blueprint
                    'Active',
                    project_info.get('customStatusId'),
                    self.safe_string(custom_fields_map.get('parent_category')),
                    self.safe_string(custom_fields_map.get('program_name')),
                    self.safe_string(custom_fields_map.get('co_marketing')),
                    self.safe_string(custom_fields_map.get('approver_email')),
                    owner_id,
                    self.safe_string(custom_fields_map.get('ziflow_id')),
                    self.safe_string(custom_fields_map.get('hubspot_id')),
                    self.safe_string(custom_fields_map.get('hs_company_id')),
                    project.get('permalink'),
                    project.get('workflowId'),
                    project.get('customItemTypeId'),
                    self.safe_string(custom_fields_map.get('brand_guide_url')),
                    self.safe_string(custom_fields_map.get('google_drive_folder_id')),
                    self.safe_string(project.get('briefDescription')),
                    self.safe_string(project.get('description')),
                    self.safe_string(custom_fields_map.get('comarketing_required')),
                    has_children,
                    True
                ))

        conn.commit()
        logger.info(f"Processed {len(parent_projects)} parent projects")

    def process_child_projects(self, space_id: str, conn):
        """Process and sync child project data."""
        logger.info("Processing child projects...")
        child_projects = self.get_folders_by_type(space_id, self.custom_item_types['child_projects'])
        
        if self.test_limit:
            child_projects = child_projects[:self.test_limit]
            logger.info(f"Limited to {len(child_projects)} child projects for testing")
        
        with conn.cursor() as cursor:
            for project in child_projects:
                # Extract custom fields
                custom_fields_map = {}
                for field_name, field_id in self.custom_fields.items():
                    custom_fields_map[field_name] = self.get_custom_field_value(
                        project.get('customFields', []), field_id
                    )

                # Get project info
                project_info = project.get('project', {})
                owner_ids = project_info.get('ownerIds', [])
                owner_id = owner_ids[0] if owner_ids else None
                parent_ids = project.get('parentIds', [])
                parent_id = parent_ids[0] if parent_ids else None

                # Prepare SQL with ON CONFLICT upsert
                sql = """
                    INSERT INTO projects.childprojects (
                        wrike_id, title, brief_description, description, created_date,
                        updated_date, parent_id, status, child_type, program_name,
                        co_marketing, approver_email, owner_id, ziflow_id, hs_deal_id,
                        hs_company_id, permalink, workflow_id, custom_item_type_id,
                        brand_guide, google_drive_folder_id, comarketing_required, active
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s
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

                cursor.execute(sql, (
                    project.get('id'),
                    self.safe_string(project.get('title')),
                    self.safe_string(project.get('briefDescription')),
                    self.safe_string(project.get('description')),
                    project.get('createdDate'),
                    project.get('updatedDate'),
                    parent_id,
                    project_info.get('customStatusId'),
                    self.safe_string(custom_fields_map.get('child_type')),
                    self.safe_string(custom_fields_map.get('program_name')),
                    self.safe_string(custom_fields_map.get('co_marketing')),
                    self.safe_string(custom_fields_map.get('approver_email')),
                    owner_id,
                    self.safe_string(custom_fields_map.get('ziflow_id')),
                    self.safe_string(custom_fields_map.get('hubspot_id')),
                    self.safe_string(custom_fields_map.get('hs_company_id')),
                    project.get('permalink'),
                    project.get('workflowId'),
                    project.get('customItemTypeId'),
                    self.safe_string(custom_fields_map.get('brand_guide_url')),
                    self.safe_string(custom_fields_map.get('google_drive_folder_id')),
                    self.safe_string(custom_fields_map.get('comarketing_required')),
                    True
                ))

                # Process tasks and deliverables for this child project
                self.process_tasks_and_deliverables(project.get('id'), conn)

        conn.commit()
        logger.info(f"Processed {len(child_projects)} child projects")

    def parent_exists(self, parent_id: str, cursor) -> bool:
        """Check if parent_id exists in childprojects table."""
        if not parent_id:
            return True  # Allow null parent_id
            
        cursor.execute(
            "SELECT 1 FROM projects.childprojects WHERE wrike_id = %s LIMIT 1",
            (parent_id,)
        )
        return cursor.fetchone() is not None

    def process_tasks_and_deliverables(self, folder_id: str, conn):
        """Process tasks and deliverables for a specific folder."""
        tasks = self.get_folder_tasks(folder_id)
        
        if self.test_limit:
            tasks = tasks[:self.test_limit]
            logger.info(f"Limited to {len(tasks)} tasks/deliverables for testing")
        
        with conn.cursor() as cursor:
            for task in tasks:
                # Extract custom fields
                custom_fields_map = {}
                for field_name, field_id in self.custom_fields.items():
                    custom_fields_map[field_name] = self.get_custom_field_value(
                        task.get('customFields', []), field_id
                    )

                # Get task details - handle required fields with defaults
                responsible_ids = task.get('responsibleIds', [])
                responsible_id = responsible_ids[0] if responsible_ids else None
                parent_ids = task.get('parentIds', [])
                parent_id = parent_ids[0] if parent_ids else None
                super_parent_ids = task.get('superParentIds', [])
                super_parent_id = super_parent_ids[0] if super_parent_ids else None
                super_task_ids = task.get('superTaskIds', [])
                super_task_id = super_task_ids[0] if super_task_ids else ''  # Empty string for required field

                # Handle effort allocation - store raw minutes from Wrike API
                effort_allocation = task.get('effortAllocation', {})
                total_effort = effort_allocation.get('totalEffort', 0)
                if total_effort is None or total_effort == '':
                    total_effort = 0

                # Handle proof version
                proof_version = custom_fields_map.get('proof_version')
                if proof_version is None or proof_version == '':
                    proof_version = 0
                
                # Handle other required fields that might be null
                task_scope = task.get('scope') or ''
                task_importance = task.get('importance') or ''
                task_priority = task.get('priority') or ''
                task_status = task.get('status') or ''

                # Handle dependency IDs
                dependency_ids = task.get('dependencyIds', [])
                dependency_ids_str = '{' + ','.join(dependency_ids) + '}' if dependency_ids else '{}'

                # Check if this is a deliverable or task
                is_deliverable = task.get('customItemTypeId') == self.custom_item_types['deliverables']

                if is_deliverable:
                    # Check if parent exists before processing deliverable
                    if not self.parent_exists(parent_id, cursor):
                        logger.warning(f"Parent ID {parent_id} not found for deliverable {task.get('id')} - skipping")
                        continue
                        
                    # Handle subtask IDs for deliverables
                    sub_task_ids = task.get('subTaskIds', [])
                    sub_task_ids_str = '{' + ','.join(sub_task_ids) + '}' if sub_task_ids else '{}'

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

                    dates = task.get('dates', {})
                    
                    # Parameters for UPDATE
                    update_params = [
                        self.safe_string(task.get('title')),
                        self.safe_string(task.get('briefDescription')),
                        self.safe_string(task.get('description')),
                        task_status,
                        task.get('customStatusId'),
                        task.get('updatedDate'),
                        parent_id,
                        super_parent_id,
                        super_task_id,
                        responsible_id,
                        dates.get('start'),
                        dates.get('due'),
                        task_scope,
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
                        task.get('hasAttachments', False),
                        task_importance,
                        task.get('permalink'),
                        task_priority,
                        task.get('billingType'),
                        task.get('customItemTypeId'),
                        True,
                        task.get('id')  # WHERE condition
                    ]
                    
                    # Parameters for INSERT
                    insert_params = [
                        task.get('id'),
                        self.safe_string(task.get('title')),
                        self.safe_string(task.get('briefDescription')),
                        self.safe_string(task.get('description')),
                        task_status,
                        task.get('customStatusId'),
                        task.get('createdDate'),
                        task.get('updatedDate'),
                        parent_id,
                        super_parent_id,
                        super_task_id,
                        responsible_id,
                        dates.get('start'),
                        dates.get('due'),
                        task_scope,
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
                        task.get('hasAttachments', False),
                        task_importance,
                        task.get('permalink'),
                        task_priority,
                        task.get('billingType'),
                        task.get('customItemTypeId'),
                        True
                    ]

                    cursor.execute(sql, update_params + insert_params)

                else:
                    # Check if parent exists before processing task
                    if not self.parent_exists(parent_id, cursor):
                        logger.warning(f"Parent ID {parent_id} not found for task {task.get('id')} - skipping")
                        continue
                        
                    # Insert/update task using the new upsert pattern from the updated blueprint
                    sql = """
                        WITH up AS (
                          UPDATE projects.tasks
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
                        INSERT INTO projects.tasks (
                            wrike_id, title, brief_description, description,
                            status, custom_status_id, created_date, updated_date,
                            parent_id, super_parent_id, super_task_id, owner_id,
                            due_date, scope, deliverable_type, deliverable_category,
                            proof_id, proof_url, proof_version, proof_status,
                            proof_error, drive_id, publish_owner, total_effort,
                            effort_mode, dependency_ids, has_attachments, importance,
                            permalink, priority, billing_type, custom_item_type_id,
                            active
                        ) SELECT
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        WHERE NOT EXISTS (SELECT 1 FROM up);
                    """

                    dates = task.get('dates', {})
                    
                    # Parameters for UPDATE
                    update_params = [
                        self.safe_string(task.get('title')),
                        self.safe_string(task.get('briefDescription')),
                        self.safe_string(task.get('description')),
                        task_status,
                        task.get('customStatusId'),
                        task.get('updatedDate'),
                        parent_id,
                        super_parent_id,
                        super_task_id,
                        responsible_id,
                        dates.get('due'),
                        task_scope,
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
                        dependency_ids_str,
                        task.get('hasAttachments', False),
                        task_importance,
                        task.get('permalink'),
                        task_priority,
                        task.get('billingType'),
                        task.get('customItemTypeId'),
                        True,
                        task.get('id')  # WHERE condition
                    ]
                    
                    # Parameters for INSERT
                    insert_params = [
                        task.get('id'),
                        self.safe_string(task.get('title')),
                        self.safe_string(task.get('briefDescription')),
                        self.safe_string(task.get('description')),
                        task_status,
                        task.get('customStatusId'),
                        task.get('createdDate'),
                        task.get('updatedDate'),
                        parent_id,
                        super_parent_id,
                        super_task_id,
                        responsible_id,
                        dates.get('due'),
                        task_scope,
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
                        dependency_ids_str,
                        task.get('hasAttachments', False),
                        task_importance,
                        task.get('permalink'),
                        task_priority,
                        task.get('billingType'),
                        task.get('customItemTypeId'),
                        True
                    ]

                    cursor.execute(sql, update_params + insert_params)

        logger.info(f"Processed tasks and deliverables for folder {folder_id}")

    def run_sync(self):
        """Main sync process."""
        logger.info("Starting Wrike to Neon sync...")
        
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
                # Process all entity types
                self.process_clients(space_id, conn)
                self.process_parent_projects(space_id, conn)
                self.process_child_projects(space_id, conn)
                
                logger.info("Sync completed successfully!")

            finally:
                conn.close()
                logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise


def main():
    """Main function."""
    import sys
    
    # Check for test limit argument
    test_limit = None
    if len(sys.argv) > 1:
        try:
            test_limit = int(sys.argv[1])
            logger.info(f"Running in test mode with limit: {test_limit} records per entity type")
        except ValueError:
            logger.error("Test limit must be a number. Usage: python wrike_sync.py [limit]")
            return
    
    required_vars = ['WRIKE_API_TOKEN', 'NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Create a .env file or set these environment variables:")
        for var in missing_vars:
            logger.info(f"  {var}=your_value_here")
        return

    sync = WrikeNeonSync(test_limit=test_limit)
    sync.run_sync()


if __name__ == '__main__':
    main()
