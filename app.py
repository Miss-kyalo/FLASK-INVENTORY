import requests
from flask import Flask, jsonify, request


app = Flask(__name__)
items = []
next_id = 1


def save_item(data):
    global next_id
    item = {
        "id": next_id,
        "name": data["name"],
        "barcode": data.get("barcode"),
        "category": data.get("category", ""),
        "quantity": data.get("quantity", 0),
        "price": data.get("price", 0),
        "description": data.get("description", ""),
    }
    items.append(item)
    next_id += 1
    return item


def find_product(barcode=None, name=None):
    if barcode:
        response = requests.get(
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("status") != 1:
            return None
        product = result.get("product", {})
    else:
        response = requests.get(
            "https://world.openfoodfacts.org/cgi/search.pl",
            params={
                "search_terms": name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
        products = response.json().get("products", [])
        if not products:
            return None
        product = products[0]

    product_name = product.get("product_name")
    if not product_name:
        return None

    return {
        "name": product_name,
        "barcode": product.get("code", barcode),
        "category": product.get("categories", "").split(",")[0],
        "description": product.get("generic_name", ""),
    }


@app.get("/api/items")
def list_items():
    return jsonify(items)


@app.get("/api/items/<int:item_id>")
def get_item(item_id):
    for item in items:
        if item["id"] == item_id:
            return jsonify(item)
    return jsonify({"error": "Item not found"}), 404


@app.post("/api/items")
def add_item():
    data = request.get_json()

    if not data or not data.get("name"):
        return jsonify({"error": "A product name is required"}), 400

    return jsonify(save_item(data)), 201


@app.patch("/api/items/<int:item_id>")
def update_item(item_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Send at least one field to update"}), 400

    for item in items:
        if item["id"] == item_id:
            for field in ("name", "barcode", "category", "quantity", "price", "description"):
                if field in data:
                    item[field] = data[field]
            return jsonify(item)
    return jsonify({"error": "Item not found"}), 404


@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    for item in items:
        if item["id"] == item_id:
            items.remove(item)
            return jsonify({"message": "Item deleted"})
    return jsonify({"error": "Item not found"}), 404


@app.get("/api/products/lookup")
def lookup_product():
    barcode = request.args.get("barcode")
    name = request.args.get("name")
    if bool(barcode) == bool(name):
        return jsonify({"error": "Send a barcode or a product name"}), 400

    try:
        product = find_product(barcode=barcode, name=name)
    except requests.RequestException:
        return jsonify({"error": "Could not connect to OpenFoodFacts"}), 502

    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


@app.post("/api/items/import")
def import_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Send a barcode or a product name"}), 400

    barcode = data.get("barcode")
    name = data.get("name")
    if bool(barcode) == bool(name):
        return jsonify({"error": "Send a barcode or a product name"}), 400

    try:
        product = find_product(barcode=barcode, name=name)
    except requests.RequestException:
        return jsonify({"error": "Could not connect to OpenFoodFacts"}), 502

    if product is None:
        return jsonify({"error": "Product not found"}), 404

    data["name"] = product["name"]
    data["barcode"] = product["barcode"]
    data["category"] = product["category"]
    data["description"] = product["description"]
    return jsonify(save_item(data)), 201


if __name__ == "__main__":
    app.run(debug=True)
