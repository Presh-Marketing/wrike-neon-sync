-- HubSpot Entity Database Schema Template
-- Replace 'entity' with actual entity name (e.g., line_item, ticket, product)
-- Replace ENTITY with capitalized version (e.g., LINE_ITEM, TICKET, PRODUCT)

-- Create HubSpot schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS hubspot;

-- Drop table if exists (use with caution in production)
-- DROP TABLE IF EXISTS hubspot.entity CASCADE;

-- Create the main entity table
CREATE TABLE hubspot.entity (
    -- Core system fields (ALWAYS include these for every HubSpot entity)
    id BIGINT PRIMARY KEY,                     -- HubSpot Entity ID
    portal_id INTEGER DEFAULT 1849303,        -- Your HubSpot Portal ID
    is_deleted BOOLEAN DEFAULT FALSE,          -- Deletion flag
    _fivetran_deleted BOOLEAN DEFAULT FALSE,   -- Fivetran compatibility flag
    _fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- Last sync timestamp
    
    -- Standard HubSpot audit fields (common to most entities)
    property_hs_createdate TIMESTAMP WITH TIME ZONE,      -- Creation timestamp
    property_hs_lastmodifieddate TIMESTAMP WITH TIME ZONE, -- Last modified timestamp
    property_hs_created_by_user_id INTEGER,               -- Created by user ID
    property_hs_updated_by_user_id INTEGER,               -- Updated by user ID
    
    -- Entity-specific core fields (customize based on analysis)
    -- Example core fields for different entities:
    
    -- For line items:
    -- property_name TEXT,                    -- Line item name
    -- property_hs_product_id BIGINT,        -- Associated product ID
    -- property_hs_line_item_currency_code TEXT, -- Currency code
    -- property_quantity NUMERIC,            -- Quantity
    -- property_price NUMERIC,               -- Unit price
    -- property_amount NUMERIC,              -- Total amount
    -- property_discount_amount NUMERIC,     -- Discount amount
    -- property_tax NUMERIC,                 -- Tax amount
    -- property_deal_id BIGINT,              -- Associated deal ID (relationship)
    
    -- For tickets:
    -- property_subject TEXT,                -- Ticket subject
    -- property_content TEXT,                -- Ticket content/description
    -- property_hs_ticket_priority TEXT,     -- Priority level
    -- property_hs_ticket_category TEXT,     -- Category
    -- property_hs_ticket_id BIGINT,         -- Ticket ID
    -- property_hubspot_owner_id INTEGER,    -- Owner ID
    -- property_hs_pipeline TEXT,            -- Pipeline
    -- property_hs_pipeline_stage TEXT,      -- Pipeline stage
    
    -- For products:
    -- property_name TEXT,                   -- Product name
    -- property_description TEXT,            -- Product description
    -- property_price NUMERIC,               -- Product price
    -- property_hs_sku TEXT,                 -- SKU
    -- property_hs_cost_of_goods_sold NUMERIC, -- Cost of goods sold
    -- property_hs_recurring_billing_period TEXT, -- Billing period
    -- property_tax_rate NUMERIC,            -- Tax rate
    
    -- String fields (TEXT) - Add based on your entity analysis
    -- property_[field_name] TEXT,
    
    -- Numeric fields (NUMERIC) - Add based on your entity analysis
    -- property_[field_name] NUMERIC,
    
    -- Integer fields (INTEGER) - Add based on your entity analysis
    -- property_[field_name] INTEGER,
    
    -- Boolean fields (BOOLEAN) - Add based on your entity analysis
    -- property_[field_name] BOOLEAN,
    
    -- DateTime fields (TIMESTAMP WITH TIME ZONE) - Add based on your entity analysis
    -- property_[field_name] TIMESTAMP WITH TIME ZONE,
    
    -- Relationship fields (for foreign keys to other HubSpot entities)
    -- property_companyid_hs_sync INTEGER,   -- Link to hubspot.company
    -- property_associatedcompanyid INTEGER, -- Alternative company relationship
    -- property_deal_id BIGINT,              -- Link to hubspot.deal
    -- property_contact_id BIGINT,           -- Link to hubspot.contact
    
    -- HubSpot owner and team fields (common pattern)
    property_hubspot_owner_id INTEGER,        -- Owner ID
    property_hubspot_team_id INTEGER          -- Team ID
);

-- Performance indexes (customize based on your query patterns)
-- Always create these standard indexes:

-- Primary performance indexes
CREATE INDEX idx_hubspot_entity_portal_id ON hubspot.entity (portal_id);
CREATE INDEX idx_hubspot_entity_fivetran_synced ON hubspot.entity (_fivetran_synced);
CREATE INDEX idx_hubspot_entity_created ON hubspot.entity (property_hs_createdate);
CREATE INDEX idx_hubspot_entity_modified ON hubspot.entity (property_hs_lastmodifieddate);

-- Owner and team indexes (for common queries)
CREATE INDEX idx_hubspot_entity_owner ON hubspot.entity (property_hubspot_owner_id);
CREATE INDEX idx_hubspot_entity_team ON hubspot.entity (property_hubspot_team_id);

-- Entity-specific indexes (customize based on your entity)
-- Examples for different entities:

-- For line items:
-- CREATE INDEX idx_hubspot_line_item_deal_id ON hubspot.line_item (property_deal_id);
-- CREATE INDEX idx_hubspot_line_item_product_id ON hubspot.line_item (property_hs_product_id);
-- CREATE INDEX idx_hubspot_line_item_amount ON hubspot.line_item (property_amount);

-- For tickets:
-- CREATE INDEX idx_hubspot_ticket_priority ON hubspot.ticket (property_hs_ticket_priority);
-- CREATE INDEX idx_hubspot_ticket_category ON hubspot.ticket (property_hs_ticket_category);
-- CREATE INDEX idx_hubspot_ticket_pipeline ON hubspot.ticket (property_hs_pipeline);
-- CREATE INDEX idx_hubspot_ticket_stage ON hubspot.ticket (property_hs_pipeline_stage);

-- For products:
-- CREATE INDEX idx_hubspot_product_name ON hubspot.product (property_name);
-- CREATE INDEX idx_hubspot_product_sku ON hubspot.product (property_hs_sku);
-- CREATE INDEX idx_hubspot_product_price ON hubspot.product (property_price);

-- Foreign key constraints (optional - adds referential integrity)
-- Enable these if you want strict referential integrity between HubSpot entities:

-- Example foreign key constraints:
-- ALTER TABLE hubspot.entity ADD CONSTRAINT fk_entity_company 
--     FOREIGN KEY (property_companyid_hs_sync) REFERENCES hubspot.company (id);

-- ALTER TABLE hubspot.entity ADD CONSTRAINT fk_entity_deal 
--     FOREIGN KEY (property_deal_id) REFERENCES hubspot.deal (id);

-- ALTER TABLE hubspot.entity ADD CONSTRAINT fk_entity_contact 
--     FOREIGN KEY (property_contact_id) REFERENCES hubspot.contact (id);

-- Table comments (helpful for documentation)
COMMENT ON TABLE hubspot.entity IS 'HubSpot ENTITY data synced from HubSpot API - contains all entity properties with property_ prefix';
COMMENT ON COLUMN hubspot.entity.id IS 'HubSpot Entity ID (primary key)';
COMMENT ON COLUMN hubspot.entity.portal_id IS 'HubSpot Portal ID (1849303)';
COMMENT ON COLUMN hubspot.entity._fivetran_synced IS 'Last sync timestamp for monitoring data freshness';

-- Verify table creation
SELECT 
    schemaname,
    tablename,
    tableowner,
    tablespace,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'hubspot' AND tablename = 'entity';

-- Check column information
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'hubspot' AND table_name = 'entity'
ORDER BY ordinal_position;

-- Check indexes
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'hubspot' AND tablename = 'entity';

-- Sample queries for validation (customize based on entity)
-- COUNT check:
-- SELECT COUNT(*) as total_entities FROM hubspot.entity;

-- Recent records check:
-- SELECT id, property_hs_createdate, _fivetran_synced 
-- FROM hubspot.entity 
-- ORDER BY _fivetran_synced DESC 
-- LIMIT 10;

-- Relationship validation (if applicable):
-- SELECT e.id, c.property_name as company_name 
-- FROM hubspot.entity e
-- LEFT JOIN hubspot.company c ON e.property_companyid_hs_sync = c.id
-- WHERE e.property_companyid_hs_sync IS NOT NULL
-- LIMIT 10;

-- Data quality checks:
-- SELECT 
--     COUNT(*) as total,
--     COUNT(property_name) as with_name,
--     COUNT(property_hubspot_owner_id) as with_owner,
--     COUNT(property_hs_createdate) as with_created_date
-- FROM hubspot.entity; 