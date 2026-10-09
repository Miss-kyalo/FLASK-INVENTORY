# Inventory Management API

A small Flask service for tracking stock, with a command-line client and product lookups through OpenFoodFacts.

## Setup

Use Python 3.10 or newer. Install the dependencies and start the server:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The service listens at `http://127.0.0.1:5000`. Inventory is stored in `instance/inventory.sqlite3`.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/items` | List inventory |
| `GET` | `/api/items/<id>` | Read one item |
| `POST` | `/api/items` | Create an item |
| `PATCH` | `/api/items/<id>` | Update supplied fields |
| `DELETE` | `/api/items/<id>` | Delete an item |
| `GET` | `/api/products/lookup?barcode=<code>` | Look up a barcode |
| `GET` | `/api/products/lookup?name=<name>` | Search by product name |
| `POST` | `/api/items/import` | Look up a product and add it to inventory |

Inventory item fields are `name`, `barcode`, `category`, `quantity`, `price`, and `description`. A name is required; quantity and price default to zero. Quantity and price cannot be negative, and barcodes must be unique.

For example, create an item with:

```bash
curl -X POST http://127.0.0.1:5000/api/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"Oat milk","category":"Drinks","quantity":12,"price":3.5}'
```

To import a product, send its barcode and optional stock details:

```bash
curl -X POST http://127.0.0.1:5000/api/items/import \
  -H 'Content-Type: application/json' \
  -d '{"barcode":"3017620422003","quantity":8,"price":4.25}'
```

The import endpoint uses OpenFoodFacts to fill in product name, category, and description. Price and stock are supplied by the store, not the product database.

## CLI

With the server running, use `cli.py` to issue API requests:

```bash
python cli.py list
python cli.py add --name "Oat milk" --category Drinks --quantity 12 --price 3.5
python cli.py update 1 --quantity 9
python cli.py lookup --barcode 3017620422003
python cli.py import --barcode 3017620422003 --quantity 8 --price 4.25
python cli.py show 1
python cli.py delete 1
```

Set `INVENTORY_API_URL` or pass `--url` to target a different server.

## Tests

Run the test suite with:

```bash
python -m unittest discover -s tests
```

External requests are mocked in tests, so running them does not require access to OpenFoodFacts.
