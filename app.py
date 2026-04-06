from flask import Flask, request, jsonify
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from models import (
    db,
    Company,
    Warehouse,
    Supplier,
    ProductType,
    Product,
    Inventory,
    SalesOrder,
    SalesOrderItem
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stockflow.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


# ---------------------------------------------------------
# PART 1: FIXED PRODUCT CREATION ENDPOINT
# ---------------------------------------------------------
@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity', 'company_id']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({
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
            description=description
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

        return jsonify({
            "message": "Product created successfully",
            "product_id": product.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


# ---------------------------------------------------------
# PART 3: LOW STOCK ALERTS ENDPOINT
# ---------------------------------------------------------
@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
    """
    Returns low-stock alerts for a company.
    Assumption:
    - Recent sales activity = at least one sale in the last 30 days
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


@app.route('/')
def home():
    return jsonify({"message": "StockFlow Backend Case Study API Running"}), 200


if __name__ == '__main__':
    app.run(debug=True)