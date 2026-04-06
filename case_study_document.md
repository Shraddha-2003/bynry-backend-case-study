#Submitted by: Shraddha Patole 
#Role Applied For: Backend Engineering Intern

—--------------------------------------------------------------------------------------------

Assumptions Used Across the Case Study 

Since some of the requirements were intentionally incomplete, I made a few reasonable assumptions while designing the solution.
A company can have multiple warehouses.
A product belongs to a company, but the same product can be stored in more than one warehouse.
SKU should be unique across the entire platform, because the prompt specifically mentions that requirement.
Inventory should be tracked separately for each warehouse.
Price should be stored using a decimal type to avoid precision issues.
Some fields like description, supplier, or reorder threshold may be optional.
Bundle products can contain other products.
“Recent sales activity” means at least one sale in the last 30 days.
Low stock threshold may come either from product type or warehouse-level settings.
Not every product is guaranteed to have supplier information attached.

Part 1: Code Review & Debugging
1. Given Code -

@app.route('/api/products', methods=['POST'])
def create_product():
  data = request.json
# Create new product
  product = Product
(
      name=data['name'],
      sku=data['sku'],
      price=data['price'],
      warehouse_id=data['warehouse_id']
  )
  db.session.add(product)
  db.session.commit()
  # Update inventory count
  inventory = Inventory(
      product_id=product.id,
      warehouse_id=data['warehouse_id'],
      quantity=data['initial_quantity']
  )
  db.session.add(inventory)
  db.session.commit()
return {"message": "Product created", "product_id": product.id}

2. Issues Identified -

The first thing that stood out to me was that product creation and warehouse inventory were being mixed together in a way that does not scale well for a multi-warehouse          inventory system.                                                                                                                      
Issue 1: Product incorrectly stores warehouse_id
A product can exist in multiple warehouses, so warehouse_id should not be directly stored in the Product table.
This should instead be handled through the Inventory table, where each product can have a separate stock entry for each warehouse.
—------------------------------------------------------------------------------------------------------------------
Issue 2: No input validation
The code assumes all required fields are always present in the request.
If fields like name, sku, price, or initial_quantity are missing, the API may fail with a server error instead of returning a proper validation message.
—------------------------------------------------------------------------------------------------------------------
Issue 3: No SKU uniqueness check
The prompt clearly mentions that SKU must be unique across the platform.
However, this code does not check whether the SKU already exists before creating the product.
—------------------------------------------------------------------------------------------------------------------
Issue 4: Price is not validated properly
Price is being used directly from input without checking:-
whether it is numeric.
whether it is negative.
whether it should be stored safely as a decimal value.
 For pricing-related fields, decimal handling is important to avoid precision issues.
—------------------------------------------------------------------------------------------------------------------
Issue 5: Two separate commits are used
The code commits once after product creation and again after inventory creation.
This means if the product is created successfully but the inventory step fails, the database can end up in an incomplete state.
That is a data consistency problem.
—------------------------------------------------------------------------------------------------------------------
Issue 6: No warehouse existence check
The code assumes that the given warehouse_id exists and is valid.
But in a real system, the API should first verify that the warehouse exists and belongs to the correct company.
—----------------------------------------------------------------------------------------------------------------------------
Issue 7: No validation for initial quantity
initial_quantity should be validated before saving.
For example:
It should be numeric.
 It should not be negative.                          
Otherwise, incorrect inventory values may get stored.
—------------------------------------------------------------------------------------------------------------------
Issue 8: No support for optional fields
The prompt mentions that some fields might be optional.
The current code does not account for that and assumes a rigid request format.
—------------------------------------------------------------------------------------------------------------------
Issue 9: No error handling or rollback
If something fails during the database operation, there is no rollback or structured exception handling.
This can make debugging harder and may leave the database session in a bad state.
—------------------------------------------------------------------------------------------------------------------
Issue 10: No proper HTTP status codes
The endpoint always returns a success-style JSON response.
A better API should return appropriate status codes such as:
201 for created
400 for bad request
404 for not found
409 for duplicate SKU
500 for internal error

3. Production Impact -
If this code goes to production as it is, it can create a lot of practical problems.
For example, duplicate SKUs can get created, invalid product data may be stored, and the API can fail if any required field is missing. Another serious issue is that the product and inventory are being saved in two separate commits, so if the second step fails, the database may end up in a half-saved state.
Overall, this can lead to inventory mismatches, debugging difficulty, and poor reliability for businesses using the platform.

4. Corrected Version -
    Language / Framework Chosen - Python + Flask + SQLAlchemy.

from decimal import Decimal, InvalidOperation
from flask import request,  jsonify
@app.route('/api/products', methods=['POST'])
def create_product():
  data = request.get_json()
  if not data:
      return jsonify({"error": "Request body must be valid JSON"}), 400
  required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity', 'company_id']
  missing_fields = [field for field in required_fields if field not in data]
  if missing_fields:
      return jsonify(
{
          "error": "Missing required fields",
          "missing_fields": missing_fields
 }), 400
  name = str(data['name']).strip()
  sku = str(data['sku']).strip().upper()
  if not name:
      return jsonify({"error": "Product name cannot be empty"}), 400
  if not sku:
      return jsonify({"error": "SKU cannot be empty"}), 400
  try:
      price = Decimal(str(data['price']))
      if price < 0:
          return jsonify({"error": "Price cannot be negative"}), 400
  except (InvalidOperation, TypeError):
      return jsonify({"error": "Invalid price format"}), 400
  try:
      initial_quantity = int(data['initial_quantity'])
      if initial_quantity < 0:
          return jsonify({"error": "Initial quantity cannot be negative"}), 400
  except (ValueError, TypeError):
      return jsonify({"error": "Initial quantity must be a non-negative integer"}), 400
  warehouse_id = data['warehouse_id']
  company_id = data['company_id']
  description = data.get('description')
  product_type = data.get('product_type', 'standard')
  try:
      existing_product = Product.query.filter_by(sku=sku).first()
      if existing_product:
          return jsonify({"error": f"SKU '{sku}' already exists"}), 409
      warehouse = Warehouse.query.filter_by(id=warehouse_id, company_id=company_id).first()
      if not warehouse:
          return jsonify({"error": "Warehouse not found for this company"}), 404
      product = Product(
          company_id=company_id,
          name=name,
          sku=sku,
          price=price,
          description=description,
          product_type=product_type
      )
      db.session.add(product)
      db.session.flush()
      inventory = Inventory(
          product_id=product.id,
          warehouse_id=warehouse_id,
          quantity=initial_quantity
      )
      db.session.add(inventory)
      db.session.commit()
      return jsonify(
{
          "message": "Product created successfully",
          "product_id": product.id
 }), 201
  except Exception as e:
      db.session.rollback()
      return jsonify(
{
          "error": "Internal server error",
          "details": str(e)
 }), 500

5. Explanation of Fixes -
In the corrected version, I focused mainly on making the endpoint safer and closer to real production behavior.
I added validation for required fields, SKU uniqueness checks, warehouse validation, and proper price/quantity handling. I also removed the incorrect direct warehouse mapping from the product creation logic.
Most importantly, I kept the product creation and inventory creation inside one database transaction so that partial data does not get saved if something fails in between.


Part 2: Database Design
1. Schema Overview -
I tried to keep the schema simple enough to explain clearly, while still covering the important business requirements.
The system needs to support:
multiple companies
multiple warehouses per company
products stored in multiple warehouses
supplier relationships
inventory change tracking
product bundles
recent sales activity




2. Proposed Database Schema -
 Companies
CREATE TABLE companies
 (
 id BIGSERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
—------------------------------------------------------------------------------------------------------------------
 Warehouses
CREATE TABLE warehouses
 (
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  address TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
—------------------------------------------------------------------------------------------------------------------

 Suppliers
CREATE TABLE suppliers 
(
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  contact_email VARCHAR(255),
  phone VARCHAR(50),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
—------------------------------------------------------------------------------------------------------------------
 Product Types
CREATE TABLE product_types 
(
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  low_stock_threshold INT NOT NULL DEFAULT 10,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
—------------------------------------------------------------------------------------------------------------------


 Products
CREATE TABLE products (
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  supplier_id BIGINT REFERENCES suppliers(id) ON DELETE SET NULL,
  product_type_id BIGINT REFERENCES product_types(id) ON DELETE SET NULL,
  name VARCHAR(255) NOT NULL,
  sku VARCHAR(100) NOT NULL UNIQUE,
  description TEXT,
  price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
  is_bundle BOOLEAN NOT NULL DEFAULT FALSE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
—------------------------------------------------------------------------------------------------------------------
 Inventory
CREATE TABLE inventory (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  warehouse_id BIGINT NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
  quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
  reorder_threshold INT,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (product_id, warehouse_id)
);
—----------------------------------------------------------------------------------------------------------------------------
 Inventory Transactions
CREATE TABLE inventory_transactions (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  warehouse_id BIGINT NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
  change_type VARCHAR(50) NOT NULL,
  quantity_change INT NOT NULL,
  previous_quantity INT NOT NULL,
  new_quantity INT NOT NULL,
  reference_id VARCHAR(100),
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
—---------------------------------------------------------------------------------------------------------------------------
 Bundle Components
CREATE TABLE bundle_components (
  id BIGSERIAL PRIMARY KEY,
  bundle_product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  component_product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  component_quantity INT NOT NULL CHECK (component_quantity > 0),
  UNIQUE (bundle_product_id, component_product_id)
);
—----------------------------------------------------------------------------------------------------------------------------
 Sales Orders
CREATE TABLE sales_orders (
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  warehouse_id BIGINT REFERENCES warehouses(id) ON DELETE SET NULL,
  order_date TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
—----------------------------------------------------------------------------------------------------------------------------
 Sales Order Items
CREATE TABLE sales_order_items (
  id BIGSERIAL PRIMARY KEY,
  sales_order_id BIGINT NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  quantity INT NOT NULL CHECK (quantity > 0),
  unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0)
);



3. Why This Schema Was Chosen
I designed the schema by trying to keep the product data, warehouse data, and inventory data clearly separated.
One important decision was not to store warehouse information directly inside the product table, because the same product can exist in multiple warehouses. That relationship fits better through an inventory table.
I also added separate tables for inventory history, suppliers, bundles, and sales, because those become important very quickly in a real inventory system. Even though the prompt did not explicitly ask for every table, I included them where they support the business rules more realistically.

4. Suggested Indexes -
CREATE INDEX idx_warehouses_company_id ON warehouses(company_id);
CREATE INDEX idx_products_company_id ON products(company_id);
CREATE INDEX idx_products_supplier_id ON products(supplier_id);
CREATE INDEX idx_inventory_product_id ON inventory(product_id);
CREATE INDEX idx_inventory_warehouse_id ON inventory(warehouse_id);
CREATE INDEX idx_inventory_transactions_product_id ON inventory_transactions(product_id);
CREATE INDEX idx_inventory_transactions_created_at ON inventory_transactions(created_at);
CREATE INDEX idx_sales_orders_company_id ON sales_orders(company_id);
CREATE INDEX idx_sales_orders_order_date ON sales_orders(order_date);
CREATE INDEX idx_sales_order_items_product_id ON sales_order_items(product_id);

5. Questions I Would Ask the Product Team -
Before implementing this in a real product, I would want to clarify a few things with the product team, because some business rules are still open to interpretation.
 Is SKU unique globally or only per company?
 Can inventory go negative for backorders?
 Should reserved stock and available stock be tracked separately?
Can a product have multiple suppliers?
Should low-stock threshold be set per product, product type, or warehouse?
Can bundles contain other bundles?
Should bundle stock be calculated dynamically or stored separately?
What qualifies as “recent sales activity”?
Should inactive or discontinued products be excluded from alerts?
Should products be archived instead of deleted?

Part 3: API Implementation
1. Endpoint
GET /api/companies/{company_id}/alerts/low-stock

2. Business Logic
This endpoint should return low-stock alerts for a company.
Rules :
Only include products with recent sales activity
Low-stock threshold varies by product type or warehouse-specific setting
Support multiple warehouses
Include supplier information for reordering
Assumptions :
“Recent sales activity” means at least one sale in the last 30 days
days_until_stockout is estimated using average daily sales
If no supplier is assigned, supplier can be null
One thing I had to assume here was how “recent sales activity” should be defined, since the prompt does not specify an exact time window.

3. Implementation -

from flask import jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, and_
@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
  """
  Returns low-stock alerts for a company.
  """
  try:
      company = Company.query.get(company_id)
      if not company:
          return jsonify({"error": "Company not found"}), 404
      recent_cutoff = datetime.utcnow() - timedelta(days=30)
      recent_sales_subquery = (
          db.session.query(
              SalesOrderItem.product_id.label("product_id"),
              SalesOrder.warehouse_id.label("warehouse_id"),
              func.sum(SalesOrderItem.quantity).label("total_sold_30d")
          )
          .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
          .filter(
              SalesOrder.company_id == company_id,
              SalesOrder.order_date >= recent_cutoff
          )
          .group_by(SalesOrderItem.product_id, SalesOrder.warehouse_id)
          .subquery()
      )
      results = (
          db.session.query(
              Product.id.label("product_id"),
              Product.name.label("product_name"),
              Product.sku.label("sku"),
              Warehouse.id.label("warehouse_id"),
              Warehouse.name.label("warehouse_name"),
              Inventory.quantity.label("current_stock"),
              Supplier.id.label("supplier_id"),
              Supplier.name.label("supplier_name"),
              Supplier.contact_email.label("supplier_email"),
              ProductType.low_stock_threshold.label("type_threshold"),
              Inventory.reorder_threshold.label("inventory_threshold"),
              recent_sales_subquery.c.total_sold_30d.label("total_sold_30d")
          )
          .join(Inventory, Inventory.product_id == Product.id)
          .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
          .outerjoin(Supplier, Supplier.id == Product.supplier_id)
          .outerjoin(ProductType, ProductType.id == Product.product_type_id)
          .join(
              recent_sales_subquery,
              and_(
                  recent_sales_subquery.c.product_id == Product.id,
                  recent_sales_subquery.c.warehouse_id == Warehouse.id
              )
          )
          .filter(
              Product.company_id == company_id,
              Product.is_active == True,
              Warehouse.company_id == company_id
          )
          .all()
      )
      alerts = []
      for row in results:
          threshold = row.inventory_threshold if row.inventory_threshold is not None else row.type_threshold

          if threshold is None:
              continue
          if row.current_stock >= threshold:
              continue
          total_sold_30d = row.total_sold_30d or 0
          avg_daily_sales = total_sold_30d / 30 if total_sold_30d > 0 else 0
          if avg_daily_sales > 0:
              days_until_stockout = round(row.current_stock / avg_daily_sales)
          else:
              days_until_stockout = None
          alerts.append({
              "product_id": row.product_id,
              "product_name": row.product_name,
              "sku": row.sku,
              "warehouse_id": row.warehouse_id,
              "warehouse_name": row.warehouse_name,
              "current_stock": row.current_stock,
              "threshold": threshold,
              "days_until_stockout": days_until_stockout,
              "supplier": {
                  "id": row.supplier_id,
                  "name": row.supplier_name,
                  "contact_email": row.supplier_email
              } if row.supplier_id else None
          })
      alerts.sort(
          key=lambda x: (
              x["days_until_stockout"] if x["days_until_stockout"] is not None else 999999,
              x["current_stock"]
          )
      )
      return jsonify({
          "alerts": alerts,
          "total_alerts": len(alerts)
      }), 200
  except Exception as e:
      return jsonify({
          "error": "Internal server error",
          "details": str(e)
      }), 500

4. Explanation of Approach
For this endpoint, I first thought about what the business is actually trying to solve.
The goal is not just to show low inventory, but to show inventory that is actually important right now — meaning products that are selling recently and may need reordering soon.
Because of that, I filtered for recent sales activity first, then compared current stock against the configured threshold. I also included supplier information because low-stock alerts are usually most useful when they directly help with reordering decisions.
This design also works well for companies managing multiple warehouses, since stock can be evaluated warehouse-wise instead of only at product level.

5. Edge Cases Considered
             The following edge cases were considered:
 Company does not exist - The API should return 404 Not Found.
No recent sales -Products with no recent sales should not appear in alerts, because the requirement specifically says alerts should only be shown for products with recent sales activity.
No supplier assigned-If a product does not have a supplier, the supplier field can be returned as null.
No threshold configured- If no threshold is configured at either product type or warehouse level, the product is skipped.
Same product is low in multiple warehouses-A separate alert should be returned for each warehouse, since stock is tracked warehouse-wise.
Zero average daily sales-If average daily sales cannot be calculated meaningfully, days_until_stockout should be returned as null.


6. Possible Improvements
If I were building this beyond the scope of the case study, there are a few improvements I would consider next.
For example, I would add pagination if the alert list becomes large, filtering by warehouse or supplier, and maybe background jobs for generating alerts more efficiently. I would also look into handling reserved stock, multiple suppliers, and more detailed reorder logic.
These are not necessary for the first version, but they would matter in a production B2B SaaS system.

Conclusion
This case study was a good example of how backend work often involves incomplete requirements and business rules that need interpretation.
My approach was to first identify the data model and API issues, then design a cleaner structure that would work better in a real multi-warehouse inventory system.
While there are still areas that would need product clarification before full implementation, I tried to make decisions that are practical, scalable, and aligned with how a B2B SaaS inventory platform would likely work.


