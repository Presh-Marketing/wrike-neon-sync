# HubSpot Line Items Sync System

This system synchronizes HubSpot line items to a Neon PostgreSQL database. Based on comprehensive analysis of 80+ HubSpot line item properties with deal associations.

## System Overview

- **HubSpot API Analysis**: Discovered 80+ line item properties across 6 data types
- **Database Table**: `hubspot.line_item` with comprehensive field mapping
- **Deal Associations**: Line items linked to deals via HubSpot association typeId 20
- **Sync Strategy**: Batch processing (25 line items per batch) with upsert operations
- **Error Handling**: Batch-level rollback with detailed logging

## Property Distribution Analysis

From the HubSpot API analysis:
- **STRING**: 30+ properties (names, descriptions, categories, URLs)
- **NUMBER**: 35+ properties (pricing, quantities, margins, revenue metrics)
- **DATETIME**: 4 properties (creation and modification timestamps)
- **BOOLEAN**: 8 properties (configuration flags and options)
- **ENUMERATION**: 15+ properties (categories, billing terms, owner assignments)
- **DATE**: 6 properties (billing period dates)

## Field Mapping Strategy

All HubSpot properties are mapped to database fields with the `property_` prefix:

### Core Line Item Fields
- `name` → `property_name` (TEXT) - Product name
- `description` → `property_description` (TEXT) - Full product description
- `hs_sku` → `property_hs_sku` (TEXT) - Unique product identifier
- `category` → `property_category` (TEXT) - Product category
- `hs_line_item_currency_code` → `property_hs_line_item_currency_code` (TEXT)

### Product Relationship Fields
- `hs_product_id` → `property_hs_product_id` (BIGINT) - Associated product ID
- `hs_product_type` → `property_hs_product_type` (TEXT) - Product type classification
- `hs_variant_id` → `property_hs_variant_id` (BIGINT) - Product variant ID
- `hs_bundle_id` → `property_hs_bundle_id` (BIGINT) - Bundle product ID

### Pricing & Financial Fields (NUMERIC)
- `price` → `property_price` - Unit price
- `quantity` → `property_quantity` - Quantity
- `amount` → `property_amount` - Net total amount
- `discount` → `property_discount` - Unit discount
- `hs_cost_of_goods_sold` → `property_hs_cost_of_goods_sold` - Unit cost

### Revenue Metrics (NUMERIC)
- `hs_acv` → `property_hs_acv` - Annual contract value
- `hs_arr` → `property_hs_arr` - Annual recurring revenue
- `hs_mrr` → `property_hs_mrr` - Monthly recurring revenue
- `hs_tcv` → `property_hs_tcv` - Total contract value

### Deal Association
- **Special Field**: `deal_id` (BIGINT) - Populated from HubSpot associations, not a direct property
- **Association Type**: HUBSPOT_DEFINED typeId 20 (line_items → deals)

## Database Schema

### Core System Fields
```sql
id BIGINT PRIMARY KEY,                     -- HubSpot Line Item ID
portal_id INTEGER DEFAULT 1849303,        -- HubSpot Portal ID
is_deleted BOOLEAN DEFAULT FALSE,          -- Deletion flag
_fivetran_deleted BOOLEAN DEFAULT FALSE,   -- Fivetran deletion flag
_fivetran_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- Last sync timestamp
deal_id BIGINT,                           -- Associated Deal ID (from associations)
```

### Database Table Creation

Run the SQL file to create the table:

```bash
# Execute the table creation SQL
psql -h your-neon-host -U your-user -d your-database -f docs/create_hubspot_line_items_table.sql
```

Or copy and execute the SQL content from `docs/create_hubspot_line_items_table.sql` in your database client.

## Key Field Categories

### 1. **Pricing Fields** (15+ fields)
- **Core Pricing**: Unit price, quantity, net amount
- **Discounts**: Unit discount, percentage discount, total discount
- **Effective Pricing**: Pre-discount amount, effective unit price for tiered pricing

### 2. **Tax Management** (8 fields)
- **Tax Amounts**: Tax amount, automatic tax amount, post-tax amount
- **Tax Configuration**: Tax rate, tax label, tax category, tax rate group

### 3. **Recurring Revenue** (15+ fields)
- **Revenue Metrics**: ACV, ARR, MRR, TCV with margin calculations
- **Billing Configuration**: Billing period, terms, number of payments
- **Billing Dates**: Start date, end date, delay configurations

### 4. **Product Integration** (10+ fields)
- **Product Links**: Product ID, variant ID, bundle ID
- **Classification**: Product type, category, SKU
- **External Systems**: External ID, sync amount, origin key

### 5. **Advanced Features** (12+ fields)
- **Tiered Pricing**: Pricing model, tier amounts, tier configurations (JSON)
- **Quote Management**: Position on quote, points system
- **Buyer Controls**: Buyer-selected quantity with min/max limits

## Setup Instructions

### 1. Environment Variables

Ensure your `.env` file contains:

```bash
# HubSpot API Configuration
HUBSPOT_API_TOKEN=your_hubspot_api_token_here

# Neon Database Configuration
NEON_HOST=your_neon_host_here.aws.neon.tech
NEON_DATABASE=your_database_name_here
NEON_USER=your_username_here
NEON_PASSWORD=your_password_here
NEON_PORT=5432
```

### 2. HubSpot API Permissions

Ensure your HubSpot API token has these required scopes:
- `crm.objects.line_items.read`
- `crm.objects.line_items.write`
- `crm.schemas.line_items.read`
- `crm.objects.deals.read` (for associations)

### 3. Database Setup

1. **Create the table**: Execute the SQL from `docs/create_hubspot_line_items_table.sql`
2. **Verify creation**: 
   ```sql
   SELECT COUNT(*) FROM information_schema.columns 
   WHERE table_schema = 'hubspot' AND table_name = 'line_item';
   -- Should return ~85 columns
   ```

### 4. Optional: Foreign Key Constraint

To enforce referential integrity with deals:

```sql
ALTER TABLE hubspot.line_item ADD CONSTRAINT fk_line_item_deal 
    FOREIGN KEY (deal_id) REFERENCES hubspot.deal (id);
```

## Data Relationships

### Line Items → Deals Relationship
- **Type**: Many-to-One (multiple line items can belong to one deal)
- **Implementation**: `deal_id` field populated from HubSpot associations
- **Association**: HubSpot typeId 20 (HUBSPOT_DEFINED)

### Join Queries

```sql
-- Line items with deal information
SELECT 
    li.property_name as line_item_name,
    li.property_amount,
    li.property_quantity,
    d.property_dealname as deal_name,
    d.property_amount as deal_total
FROM hubspot.line_item li
LEFT JOIN hubspot.deal d ON li.deal_id = d.id
WHERE li.property_amount > 1000
ORDER BY li.property_amount DESC;

-- Deal revenue breakdown by line items
SELECT 
    d.property_dealname,
    COUNT(li.id) as line_item_count,
    SUM(li.property_amount) as total_line_item_amount,
    d.property_amount as deal_amount
FROM hubspot.deal d
LEFT JOIN hubspot.line_item li ON d.id = li.deal_id
WHERE d.property_amount IS NOT NULL
GROUP BY d.id, d.property_dealname, d.property_amount
ORDER BY total_line_item_amount DESC;
```

## Performance Considerations

### Indexes Created
- **Primary Performance**: deal_id, product_id, name, amount
- **Search Optimization**: SKU, product_type, owner_id
- **Time-based Queries**: createdate, lastmodifieddate, _fivetran_synced

### Query Optimization Tips
```sql
-- Use indexes for common queries
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM hubspot.line_item 
WHERE deal_id = 123456 AND property_amount > 1000;

-- Index usage for product searches
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM hubspot.line_item 
WHERE property_hs_product_id = 789 OR property_hs_sku = 'SKU123';
```

## Data Quality Monitoring

### Key Metrics to Track
```sql
-- Completeness metrics
SELECT 
    COUNT(*) as total_line_items,
    COUNT(property_name) as with_name,
    COUNT(property_amount) as with_amount,
    COUNT(deal_id) as with_deal_association,
    COUNT(property_hs_product_id) as with_product_link,
    ROUND(100.0 * COUNT(deal_id) / COUNT(*), 2) as deal_association_pct
FROM hubspot.line_item;

-- Recent sync activity
SELECT 
    DATE_TRUNC('day', _fivetran_synced) as sync_date,
    COUNT(*) as line_items_synced
FROM hubspot.line_item 
WHERE _fivetran_synced > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('day', _fivetran_synced)
ORDER BY sync_date DESC;

-- Revenue distribution
SELECT 
    property_hs_product_type,
    COUNT(*) as line_item_count,
    SUM(property_amount) as total_revenue,
    AVG(property_amount) as avg_line_item_value
FROM hubspot.line_item 
WHERE property_amount IS NOT NULL
GROUP BY property_hs_product_type
ORDER BY total_revenue DESC;
```

## Common Use Cases

### 1. **Deal Revenue Analysis**
```sql
-- Compare deal amount vs line item totals
SELECT 
    d.property_dealname,
    d.property_amount as deal_amount,
    SUM(li.property_amount) as line_items_total,
    d.property_amount - COALESCE(SUM(li.property_amount), 0) as variance
FROM hubspot.deal d
LEFT JOIN hubspot.line_item li ON d.id = li.deal_id
WHERE d.property_amount IS NOT NULL
GROUP BY d.id, d.property_dealname, d.property_amount
HAVING ABS(d.property_amount - COALESCE(SUM(li.property_amount), 0)) > 100
ORDER BY ABS(variance) DESC;
```

### 2. **Product Performance**
```sql
-- Top performing products by revenue
SELECT 
    property_name,
    property_hs_sku,
    COUNT(*) as times_sold,
    SUM(property_quantity) as total_quantity,
    SUM(property_amount) as total_revenue
FROM hubspot.line_item
WHERE property_amount IS NOT NULL
GROUP BY property_name, property_hs_sku
ORDER BY total_revenue DESC
LIMIT 20;
```

### 3. **Margin Analysis**
```sql
-- Line items with margin data
SELECT 
    property_name,
    property_amount,
    property_hs_cost_of_goods_sold,
    property_hs_margin,
    (property_amount - COALESCE(property_hs_cost_of_goods_sold, 0)) as calculated_margin
FROM hubspot.line_item
WHERE property_amount IS NOT NULL 
  AND property_hs_cost_of_goods_sold IS NOT NULL
ORDER BY calculated_margin DESC;
```

## Future Sync Script Development

When creating a sync script (`hubspot_line_items_sync.py`), remember to:

1. **Handle Associations**: Fetch deal associations for each line item
2. **Property Mapping**: Use the comprehensive property list from this analysis
3. **Batch Processing**: Process in batches of 25 line items
4. **Error Handling**: Robust error handling for missing products or deals
5. **Type Safety**: Use proper data type conversions for numeric and date fields

### Flask App Integration

Add to `SYNC_SCRIPTS` in `app.py`:
```python
'hubspot_line_items': {
    'script': 'hubspot_line_items_sync.py',
    'name': 'HubSpot Line Items',
    'color': 'purple',
    'estimated_duration': 120,  # 2 minutes
    'object_type': 'line_items'
}
```

## Troubleshooting

### Common Issues

**"No line items found"**
- Verify HubSpot API token has line items permissions
- Check if your account has line items data
- Ensure deals exist and have associated line items

**"Association errors"**
- Verify deals table exists and has data
- Check association permissions in HubSpot API token
- Review association typeId (should be 20)

**"Revenue discrepancies"**
- Line item amounts vs deal amounts may differ legitimately
- Line items may not cover the full deal value
- Check for manual deal amount adjustments

### Debug Queries
```sql
-- Check line items without deal associations
SELECT COUNT(*) as orphaned_line_items
FROM hubspot.line_item
WHERE deal_id IS NULL;

-- Check for data type issues
SELECT 
    id,
    property_name,
    property_amount,
    property_quantity,
    property_price
FROM hubspot.line_item
WHERE property_amount IS NOT NULL 
  AND (property_quantity IS NULL OR property_price IS NULL);
```

## Benefits

1. **🔗 Complete Deal Analysis**: Full line item breakdown for every deal
2. **💰 Revenue Tracking**: Detailed product-level revenue and margin analysis
3. **📊 Product Insights**: Performance metrics for individual products/services
4. **🎯 Pricing Intelligence**: Understand pricing patterns and discount effectiveness
5. **📈 Forecasting**: Better revenue forecasting with line-item granularity
6. **🔄 Integration Ready**: Seamless integration with existing deal and product data

## Support

For issues with line items setup:
1. Verify HubSpot API permissions include line items scopes
2. Check deal associations are working properly
3. Review product catalog integration if using product IDs
4. Ensure numeric fields handle different currency formats correctly

---

**Status**: ✅ **SCHEMA READY**  
**Last Updated**: December 2024  
**Table**: `hubspot.line_item` with 80+ properties and deal associations 