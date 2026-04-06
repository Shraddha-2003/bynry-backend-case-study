CREATE TABLE companies (
   id BIGSERIAL PRIMARY KEY,
   name VARCHAR(255) NOT NULL,
   created_at TIMESTAMP NOT NULL DEFAULT NOW(),
   updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE warehouses (
   id BIGSERIAL PRIMARY KEY,
   company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
   name VARCHAR(255) NOT NULL,
   address TEXT,
   created_at TIMESTAMP NOT NULL DEFAULT NOW(),
   updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE suppliers (
   id BIGSERIAL PRIMARY KEY,
   company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
   name VARCHAR(255) NOT NULL,
   contact_email VARCHAR(255),
   phone VARCHAR(50),
   created_at TIMESTAMP NOT NULL DEFAULT NOW(),
   updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE product_types (
   id BIGSERIAL PRIMARY KEY,
   company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
   name VARCHAR(100) NOT NULL,
   low_stock_threshold INT NOT NULL DEFAULT 10,
   created_at TIMESTAMP NOT NULL DEFAULT NOW(),
   updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

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

CREATE TABLE inventory (
   id BIGSERIAL PRIMARY KEY,
   product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
   warehouse_id BIGINT NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
   quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
   reorder_threshold INT,
   updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
   UNIQUE (product_id, warehouse_id)
);

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

CREATE TABLE bundle_components (
   id BIGSERIAL PRIMARY KEY,
   bundle_product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
   component_product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
   component_quantity INT NOT NULL CHECK (component_quantity > 0),
   UNIQUE (bundle_product_id, component_product_id)
);

CREATE TABLE sales_orders (
   id BIGSERIAL PRIMARY KEY,
   company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
   warehouse_id BIGINT REFERENCES warehouses(id) ON DELETE SET NULL,
   order_date TIMESTAMP NOT NULL DEFAULT NOW(),
   created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE sales_order_items (
   id BIGSERIAL PRIMARY KEY,
   sales_order_id BIGINT NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
   product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
   quantity INT NOT NULL CHECK (quantity > 0),
   unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0)
);

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