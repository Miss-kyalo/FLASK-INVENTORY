import argparse
import json
import os
import sys

import requests


def api_request(method, path, payload=None, base_url=None, params=None):
    url = f"{(base_url or os.environ.get('INVENTORY_API_URL', 'http://127.0.0.1:5000')).rstrip('/')}{path}"
    try:
        response = requests.request(
            method, url, json=payload, params=params, timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Request failed: {error}", file=sys.stderr)
        return 1
    if response.content:
        print(json.dumps(response.json(), indent=2))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Manage inventory through the Flask API")
    parser.add_argument(
        "--url",
        default=os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000"),
        help="API base URL",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="List all inventory items")

    show = commands.add_parser("show", help="Show one inventory item")
    show.add_argument("id", type=int)

    add = commands.add_parser("add", help="Create an inventory item")
    add.add_argument("--name", required=True)
    add.add_argument("--barcode")
    add.add_argument("--category", default="")
    add.add_argument("--quantity", type=int, default=0)
    add.add_argument("--price", type=float, default=0)
    add.add_argument("--description", default="")

    update = commands.add_parser("update", help="Update inventory item fields")
    update.add_argument("id", type=int)
    update.add_argument("--name")
    update.add_argument("--barcode")
    update.add_argument("--category")
    update.add_argument("--quantity", type=int)
    update.add_argument("--price", type=float)
    update.add_argument("--description")

    delete = commands.add_parser("delete", help="Delete an inventory item")
    delete.add_argument("id", type=int)

    lookup = commands.add_parser("lookup", help="Search OpenFoodFacts")
    lookup.add_argument("--barcode")
    lookup.add_argument("--name")

    import_product = commands.add_parser("import", help="Import an OpenFoodFacts product")
    import_product.add_argument("--barcode")
    import_product.add_argument("--name")
    import_product.add_argument("--quantity", type=int, default=0)
    import_product.add_argument("--price", type=float, default=0)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        return api_request("GET", "/api/items", base_url=args.url)
    if args.command == "show":
        return api_request("GET", f"/api/items/{args.id}", base_url=args.url)
    if args.command == "add":
        payload = {
            field: getattr(args, field)
            for field in (
                "name",
                "barcode",
                "category",
                "quantity",
                "price",
                "description",
            )
        }
        return api_request("POST", "/api/items", payload, args.url)
    if args.command == "update":
        payload = {
            field: getattr(args, field)
            for field in (
                "name",
                "barcode",
                "category",
                "quantity",
                "price",
                "description",
            )
            if getattr(args, field) is not None
        }
        if not payload:
            parser.error("update requires at least one field option")
        return api_request("PATCH", f"/api/items/{args.id}", payload, args.url)
    if args.command == "delete":
        return api_request("DELETE", f"/api/items/{args.id}", base_url=args.url)
    if args.command == "lookup":
        if bool(args.barcode) == bool(args.name):
            parser.error("lookup requires exactly one of --barcode or --name")
        params = {"barcode": args.barcode} if args.barcode else {"name": args.name}
        return api_request(
            "GET", "/api/products/lookup", base_url=args.url, params=params
        )
    if args.command == "import":
        if bool(args.barcode) == bool(args.name):
            parser.error("import requires exactly one of --barcode or --name")
        payload = {
            "barcode": args.barcode,
            "name": args.name,
            "quantity": args.quantity,
            "price": args.price,
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        return api_request("POST", "/api/items/import", payload, args.url)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
