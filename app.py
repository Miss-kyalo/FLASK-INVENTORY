from contextlib import contextmanager
import math
import os
import sqlite3
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Flask, current_app, jsonify, request


OFF_BASE_URL = "https://world.openfoodfacts.org"
OFF_HEADERS = {"User-Agent": "InventoryManagementSystem/1.0"}
ITEM_FIELDS = {
    "name",
    "barcode",
    "category",
    "quantity",
    "price",
    "description",
}


@contextmanager
def get_connection():
    connection = sqlite3.connect(current_app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(app):
    database_path = app.config["DATABASE"]
    if database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    with app.app_context(), get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE,
                category TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                price REAL NOT NULL DEFAULT 0 CHECK (price >= 0),
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "inventory.sqlite3")
    )
    if test_config:
        app.config.update(test_config)

    initialize_database(app)

    @app.get("/api/items")
    def list_items():
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM items ORDER BY id"
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/api/items/<int:item_id>")
    def get_item(item_id):
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM items WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            return jsonify(error="Item not found"), 404
        return jsonify(dict(row))

    @app.post("/api/items")
    def create_item():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="A JSON object is required"), 400
        if unknown_fields := set(data) - ITEM_FIELDS:
            return jsonify(error="Unknown fields", fields=sorted(unknown_fields)), 400
        if (
            "name" not in data
            or not isinstance(data["name"], str)
            or not data["name"].strip()
        ):
            return jsonify(error="A non-empty name is required"), 400

        error = validate_item_values(data)
        if error:
            return jsonify(error=error), 400

        values = normalize_item_values(data)
        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO items (name, barcode, category, quantity, price, description)
                    VALUES (:name, :barcode, :category, :quantity, :price, :description)
                    """,
                    values,
                )
                row = connection.execute(
                    "SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
        except sqlite3.IntegrityError:
            return jsonify(error="An item with this barcode already exists"), 409
        return jsonify(dict(row)), 201

    @app.patch("/api/items/<int:item_id>")
    def update_item(item_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="A JSON object is required"), 400
        if not data:
            return jsonify(error="At least one field is required"), 400
        if unknown_fields := set(data) - ITEM_FIELDS:
            return jsonify(error="Unknown fields", fields=sorted(unknown_fields)), 400
        if "name" in data and (
            not isinstance(data["name"], str) or not data["name"].strip()
        ):
            return jsonify(error="Name must be a non-empty string"), 400

        error = validate_item_values(data)
        if error:
            return jsonify(error=error), 400

        values = {
            field: value
            for field, value in normalize_item_values(data).items()
            if field in data
        }
        columns = ", ".join(f"{field} = :{field}" for field in values)
        values["id"] = item_id
        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    f"UPDATE items SET {columns}, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
                    values,
                )
                updated = cursor.rowcount > 0
                row = connection.execute(
                    "SELECT * FROM items WHERE id = ?", (item_id,)
                ).fetchone()
        except sqlite3.IntegrityError:
            return jsonify(error="An item with this barcode already exists"), 409
        if not updated:
            return jsonify(error="Item not found"), 404
        return jsonify(dict(row))

    @app.delete("/api/items/<int:item_id>")
    def delete_item(item_id):
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM items WHERE id = ?", (item_id,))
            deleted = cursor.rowcount > 0
        if not deleted:
            return jsonify(error="Item not found"), 404
        return jsonify(message="Item deleted")

    @app.get("/api/products/lookup")
    def lookup_product():
        barcode = request.args.get("barcode", "").strip()
        name = request.args.get("name", "").strip()
        if bool(barcode) == bool(name):
            return jsonify(error="Provide exactly one of barcode or name"), 400
        try:
            product = (
                fetch_product_by_barcode(barcode)
                if barcode
                else fetch_product_by_name(name)
            )
        except requests.RequestException:
            return jsonify(error="OpenFoodFacts is unavailable"), 502
        if product is None:
            return jsonify(error="Product not found"), 404
        return jsonify(product)

    @app.post("/api/items/import")
    def import_product():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="A JSON object is required"), 400
        if unknown_fields := set(data) - {"barcode", "name", "quantity", "price"}:
            return jsonify(error="Unknown fields", fields=sorted(unknown_fields)), 400
        barcode = data.get("barcode")
        name = data.get("name")
        has_barcode = isinstance(barcode, str) and bool(barcode.strip())
        has_name = isinstance(name, str) and bool(name.strip())
        if has_barcode == has_name:
            return jsonify(error="Provide exactly one of barcode or product name"), 400

        try:
            if has_barcode:
                product = fetch_product_by_barcode(barcode.strip())
            elif isinstance(name, str) and name.strip():
                product = fetch_product_by_name(name.strip())
            else:
                return jsonify(error="Provide exactly one of barcode or product name"), 400
        except requests.RequestException:
            return jsonify(error="OpenFoodFacts is unavailable"), 502
        if product is None:
            return jsonify(error="Product not found"), 404

        values = {
            "name": product["name"],
            "barcode": product["barcode"],
            "category": product["category"],
            "quantity": data.get("quantity", 0),
            "price": data.get("price", 0),
            "description": product["description"],
        }
        error = validate_item_values(values)
        if error:
            return jsonify(error=error), 400
        values = normalize_item_values(values)
        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO items (name, barcode, category, quantity, price, description)
                    VALUES (:name, :barcode, :category, :quantity, :price, :description)
                    """,
                    values,
                )
                row = connection.execute(
                    "SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
        except sqlite3.IntegrityError:
            return jsonify(error="An item with this barcode already exists"), 409
        return jsonify(dict(row)), 201

    return app


def validate_item_values(data):
    if (
        "barcode" in data
        and data["barcode"] is not None
        and not isinstance(data["barcode"], str)
    ):
        return "Barcode must be a string or null"
    if "category" in data and not isinstance(data["category"], str):
        return "Category must be a string"
    if "description" in data and not isinstance(data["description"], str):
        return "Description must be a string"
    if "quantity" in data and (
        isinstance(data["quantity"], bool)
        or not isinstance(data["quantity"], int)
        or data["quantity"] < 0
    ):
        return "Quantity must be a non-negative integer"
    if "price" in data and (
        isinstance(data["price"], bool)
        or not isinstance(data["price"], (int, float))
    ):
        return "Price must be a non-negative number"
    if "price" in data:
        try:
            valid_price = math.isfinite(float(data["price"])) and data["price"] >= 0
        except (OverflowError, ValueError):
            valid_price = False
        if not valid_price:
            return "Price must be a non-negative number"
    return None


def normalize_item_values(data):
    values = {
        "name": data.get("name", "").strip(),
        "barcode": data.get("barcode"),
        "category": data.get("category", ""),
        "quantity": data.get("quantity", 0),
        "price": data.get("price", 0),
        "description": data.get("description", ""),
    }
    if values["barcode"] is not None:
        values["barcode"] = values["barcode"].strip() or None
    return values


def product_details(product, barcode=None):
    product_name = product.get("product_name")
    if not isinstance(product_name, str) or not product_name.strip():
        return None
    categories = product.get("categories")
    if not isinstance(categories, str):
        categories = ""
    return {
        "name": product_name.strip(),
        "barcode": product.get("code") or barcode,
        "category": categories.split(",")[0].strip(),
        "description": product.get("generic_name", "").strip()
        if isinstance(product.get("generic_name"), str)
        else "",
        "image_url": product.get("image_url"),
    }


def fetch_product_by_barcode(barcode):
    response = requests.get(
        f"{OFF_BASE_URL}/api/v2/product/{quote(barcode, safe='')}.json",
        headers=OFF_HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if (
        not isinstance(payload, dict)
        or payload.get("status") != 1
        or not isinstance(payload.get("product"), dict)
    ):
        return None
    return product_details(payload["product"], barcode)


def fetch_product_by_name(name):
    response = requests.get(
        f"{OFF_BASE_URL}/cgi/search.pl",
        params={
            "search_terms": name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 1,
        },
        headers=OFF_HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    products = payload.get("products", [])
    if (
        not isinstance(products, list)
        or not products
        or not isinstance(products[0], dict)
    ):
        return None
    return product_details(products[0])


if __name__ == "__main__":
    create_app().run()
