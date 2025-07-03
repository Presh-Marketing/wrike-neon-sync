-- HubSpot Line Items Table Schema
-- Based on analysis of 80+ HubSpot line item properties
-- Run this SQL in your Neon database to create the hubspot.line_item table

-- Step 1: Create hubspot schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS hubspot;

-- Step 2: Create the hubspot.line_item table with all mapped fields
CREATE TABLE IF NOT EXISTS hubspot.line_item (
    -- Core system fields
    id BIGINT PRIMARY KEY,                      -- HubSpot Line Item ID
    portal_id INTEGER DEFAULT 1849303,         -- HubSpot Portal ID
    is_deleted BOOLEAN DEFAULT FALSE,           -- Deletion flag
    _fivetran_deleted BOOLEAN DEFAULT FALSE,    -- Fivetran deletion flag
    _fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- Last sync timestamp
    
    -- Deal relationship (populated from associations)
    deal_id BIGINT,                            -- Associated Deal ID (from associations)
    
    -- Core line item information (string fields)
    property_name TEXT,                         -- Product name
    property_description TEXT,                  -- Full description of product
    property_hs_sku TEXT,                      -- Unique product identifier (SKU)
    property_category TEXT,                     -- Category: Product
    property_hs_line_item_currency_code TEXT,  -- Currency code
    
    -- Product relationship and classification
    property_hs_product_id BIGINT,             -- ID of the product this was copied from
    property_hs_product_type TEXT,             -- Product Type (Inventory, Non-Inventory, Service)
    property_hs_variant_id BIGINT,             -- Variant id of the product
    property_hs_bundle_id BIGINT,              -- Associated bundle Product
    
    -- Pricing fields (numeric)
    property_price NUMERIC,                     -- Unit price
    property_quantity NUMERIC,                  -- Quantity
    property_amount NUMERIC,                    -- Net price (total amount)
    property_discount NUMERIC,                  -- Unit discount
    property_hs_discount_percentage NUMERIC,   -- Discount Percentage
    property_hs_pre_discount_amount NUMERIC,   -- Pre Discount Amount
    property_hs_total_discount NUMERIC,        -- Calculated Total Discount
    property_hs_effective_unit_price NUMERIC,  -- Effective Unit Price (tiered pricing)
    
    -- Tax fields
    property_tax NUMERIC,                       -- Tax amount applied
    property_hs_tax_amount NUMERIC,            -- Tax Amount (calculated)
    property_hs_auto_tax_amount NUMERIC,       -- Automatic Tax Amount
    property_hs_tax_rate NUMERIC,              -- Resolved Tax Rate (percent)
    property_hs_tax_label TEXT,                -- Tax Label name
    property_hs_tax_category TEXT,             -- Tax Category
    property_hs_tax_rate_group_id TEXT,        -- Tax Rate ID
    property_hs_post_tax_amount NUMERIC,       -- Net Price after tax
    
    -- Cost and margin fields
    property_hs_cost_of_goods_sold NUMERIC,    -- Unit cost
    property_hs_margin NUMERIC,                -- Margin value
    property_hs_margin_acv NUMERIC,            -- Annual contract value margin
    property_hs_margin_arr NUMERIC,            -- Annual recurring revenue margin
    property_hs_margin_mrr NUMERIC,            -- Monthly recurring revenue margin
    property_hs_margin_tcv NUMERIC,            -- Total contract value margin
    
    -- Recurring revenue fields
    property_hs_acv NUMERIC,                    -- Annual contract value
    property_hs_arr NUMERIC,                    -- Annual recurring revenue
    property_hs_mrr NUMERIC,                    -- Monthly recurring revenue
    property_hs_tcv NUMERIC,                    -- Total contract value
    property_hs_term_in_months NUMERIC,        -- Term in months
    
    -- Recurring billing configuration
    property_hs_recurring_billing_period TEXT,           -- Product recurring billing duration
    property_hs_recurring_billing_terms TEXT,            -- Fixed payments or until cancelled
    property_hs_recurring_billing_number_of_payments NUMERIC, -- Number of payments
    property_recurringbillingfrequency TEXT,             -- Billing frequency
    
    -- Billing dates
    property_hs_recurring_billing_start_date DATE,       -- Billing start date
    property_hs_recurring_billing_end_date DATE,         -- Billing end date
    property_hs_billing_period_start_date DATE,          -- Fixed billing period start
    property_hs_billing_period_end_date DATE,            -- Fixed billing period end
    property_hs_billing_start_delay_days NUMERIC,        -- Delayed billing start by days
    property_hs_billing_start_delay_months NUMERIC,      -- Delayed billing start by months
    property_hs_billing_start_delay_type TEXT,           -- Start billing terms type
    
    -- Tiered pricing fields
    property_hs_pricing_model TEXT,            -- Pricing model (flat, tiered)
    property_hs_tier_amount NUMERIC,           -- Tiered Pricing amount
    property_hs_tier_prices TEXT,              -- Tier Prices (JSON)
    property_hs_tier_ranges TEXT,              -- Tier Ranges (JSON)
    property_hs_tiers TEXT,                    -- Tiers as JSON
    
    -- Quote and positioning
    property_hs_position_on_quote NUMERIC,     -- Order on quotes
    property_points NUMERIC,                    -- Points
    
    -- External system integration
    property_hs_external_id BIGINT,            -- External LineItem id
    property_hs_sync_amount NUMERIC,           -- Amount set by Ecommerce sync
    property_hs_origin_key TEXT,               -- Origin identifier
    property_hs_group_key TEXT,                -- Grouped line items key
    property_ip__sync_extension__external_source_account_id TEXT, -- Source account ID
    property_ip__sync_extension__external_source_app_id TEXT,     -- Source app ID
    
    -- Media and presentation
    property_hs_images TEXT,                   -- Product images URL
    property_hs_url TEXT,                      -- Product URL
    
    -- Boolean configuration flags
    property_hs_is_editable_price BOOLEAN,     -- Is price editable
    property_hs_is_optional BOOLEAN,           -- Is optional item
    property_hs_read_only BOOLEAN,             -- Read only object
    property_hs_was_imported BOOLEAN,          -- Performed in an import
    property_hs_allow_buyer_selected_quantity BOOLEAN, -- Allow buyer selected quantity
    
    -- Buyer quantity controls
    property_hs_buyer_selected_quantity_min NUMERIC,   -- Buyer quantity minimum
    property_hs_buyer_selected_quantity_max NUMERIC,   -- Buyer quantity maximum
    
    -- System ownership and teams
    property_hubspot_owner_id INTEGER,         -- Owner ID
    property_hubspot_team_id INTEGER,          -- Owner's main team
    property_hs_all_owner_ids TEXT,            -- All owner IDs (enumeration)
    property_hs_all_team_ids TEXT,             -- All team IDs (enumeration)
    property_hs_all_accessible_team_ids TEXT,  -- All accessible teams
    property_hs_owning_teams TEXT,             -- Owning Teams
    property_hs_shared_team_ids TEXT,          -- Shared teams
    property_hs_shared_user_ids TEXT,          -- Shared users
    property_hs_all_assigned_business_unit_ids TEXT, -- Business units
    
    -- Audit and tracking fields
    property_hs_object_id BIGINT,              -- Record ID (same as id)
    property_hs_created_by_user_id INTEGER,    -- Created by user ID
    property_hs_updated_by_user_id INTEGER,    -- Updated by user ID
    property_hs_object_source TEXT,            -- Record creation source
    property_hs_object_source_id TEXT,         -- Record creation source ID
    property_hs_object_source_label TEXT,      -- Record source label
    property_hs_object_source_detail_1 TEXT,   -- Record source detail 1
    property_hs_object_source_detail_2 TEXT,   -- Record source detail 2
    property_hs_object_source_detail_3 TEXT,   -- Record source detail 3
    property_hs_object_source_user_id INTEGER, -- Record creation source user ID
    property_hs_merged_object_ids TEXT,        -- Merged record IDs
    property_hs_unique_creation_key TEXT,      -- Unique creation key
    
    -- Notification and following
    property_hs_user_ids_of_all_notification_followers TEXT,    -- Notification followers
    property_hs_user_ids_of_all_notification_unfollowers TEXT,  -- Notification unfollowers
    property_hs_user_ids_of_all_owners TEXT,                    -- All owners user IDs
    
    -- Important timestamps
    property_createdate TIMESTAMP WITH TIME ZONE,               -- Create Date
    property_hs_createdate TIMESTAMP WITH TIME ZONE,           -- Object create date/time
    property_hs_lastmodifieddate TIMESTAMP WITH TIME ZONE,     -- Last Modified Date
    property_hubspot_owner_assigneddate TIMESTAMP WITH TIME ZONE -- Owner assigned date
);

-- Step 3: Create performance indexes
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_deal_id ON hubspot.line_item (deal_id);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_product_id ON hubspot.line_item (property_hs_product_id);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_name ON hubspot.line_item (property_name);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_amount ON hubspot.line_item (property_amount);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_owner ON hubspot.line_item (property_hubspot_owner_id);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_created ON hubspot.line_item (property_createdate);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_modified ON hubspot.line_item (property_hs_lastmodifieddate);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_fivetran_synced ON hubspot.line_item (_fivetran_synced);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_sku ON hubspot.line_item (property_hs_sku);
CREATE INDEX IF NOT EXISTS idx_hubspot_line_item_product_type ON hubspot.line_item (property_hs_product_type);

-- Step 4: Foreign key constraint to deals table (optional)
-- ALTER TABLE hubspot.line_item ADD CONSTRAINT fk_line_item_deal 
--     FOREIGN KEY (deal_id) REFERENCES hubspot.deal (id);

-- Step 5: Add table comments for documentation
COMMENT ON TABLE hubspot.line_item IS 'HubSpot line items data synchronized from HubSpot API - contains 80+ mapped properties including deal associations';
COMMENT ON COLUMN hubspot.line_item.id IS 'HubSpot line item ID (primary key)';
COMMENT ON COLUMN hubspot.line_item.portal_id IS 'HubSpot portal/account ID (1849303)';
COMMENT ON COLUMN hubspot.line_item.deal_id IS 'Associated deal ID populated from HubSpot associations';
COMMENT ON COLUMN hubspot.line_item._fivetran_synced IS 'Timestamp of last sync operation';

-- Step 6: Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON hubspot.line_item TO your_sync_user;

-- Verification queries (run these after creating the table)
-- SELECT COUNT(*) FROM hubspot.line_item;
-- SELECT property_name, property_amount, deal_id FROM hubspot.line_item LIMIT 10;

-- Example join query with deals
-- SELECT 
--     li.property_name as line_item_name,
--     li.property_amount,
--     li.property_quantity,
--     d.property_dealname as deal_name
-- FROM hubspot.line_item li
-- LEFT JOIN hubspot.deal d ON li.deal_id = d.id
-- WHERE li.property_amount > 1000
-- ORDER BY li.property_amount DESC; 