# Inventory Manager

A beginner-friendly Flask project for keeping track of products. The API stores items in a Python list while it is running. Restarting the server clears the list.

## Run it

Install the packages:

```bash
pip install -r requirements.txt
```

Start the API in one terminal:

```bash
python app.py
```

Open another terminal and run the menu:

```bash
python cli.py
```

The menu lets you list, add, update, or delete an item, look up an OpenFoodFacts product, and import a product into the inventory.

## Try the API

The API is available at `http://127.0.0.1:5000`.

| Method | Address | What it does |
| --- | --- | --- |
| `GET` | `/api/items` | Show all items |
| `GET` | `/api/items/1` | Show item 1 |
| `POST` | `/api/items` | Add an item |
| `PATCH` | `/api/items/1` | Change item 1 |
| `DELETE` | `/api/items/1` | Delete item 1 |
| `GET` | `/api/products/lookup?barcode=123` | Find a product |
| `POST` | `/api/items/import` | Find a product and add it |

An item can have a name, barcode, category, quantity, price, and description. OpenFoodFacts supplies product details; the store supplies its quantity and price.

## Run the tests

```bash
python -m unittest discover -s tests
```

The tests use sample product responses, so they do not need to connect to OpenFoodFacts.
