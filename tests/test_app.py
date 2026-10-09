import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app import create_app


class InventoryApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {"TESTING": True, "DATABASE": str(Path(self.temp_dir.name) / "test.sqlite3")}
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_item(self, **overrides):
        payload = {
            "name": "Oat milk",
            "barcode": "123456789",
            "category": "Drinks",
            "quantity": 12,
            "price": 3.5,
            "description": "Unsweetened",
        }
        payload.update(overrides)
        return self.client.post("/api/items", json=payload)

    def test_create_list_get_update_and_delete_item(self):
        created = self.create_item()
        self.assertEqual(created.status_code, 201)
        item_id = created.json["id"]
        self.assertEqual(self.client.get("/api/items").json[0]["name"], "Oat milk")
        self.assertEqual(self.client.get(f"/api/items/{item_id}").status_code, 200)

        updated = self.client.patch(
            f"/api/items/{item_id}", json={"quantity": 7, "price": 4}
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["quantity"], 7)
        self.assertEqual(updated.json["price"], 4)

        self.assertEqual(self.client.delete(f"/api/items/{item_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/items/{item_id}").status_code, 404)

    def test_create_rejects_invalid_data_and_duplicate_barcode(self):
        self.assertEqual(self.client.post("/api/items", json={}).status_code, 400)
        self.assertEqual(self.create_item(quantity=-1).status_code, 400)
        self.assertEqual(self.create_item(price=-1).status_code, 400)
        sparse_item = self.client.post("/api/items", json={"name": "Rice"})
        self.assertEqual(sparse_item.status_code, 201)
        self.assertEqual(sparse_item.json["quantity"], 0)
        self.assertEqual(self.create_item().status_code, 201)
        self.assertEqual(self.create_item().status_code, 409)

    def test_patch_rejects_empty_body_unknown_fields_and_missing_item(self):
        self.assertEqual(self.client.patch("/api/items/1", json={}).status_code, 400)
        self.assertEqual(
            self.client.patch("/api/items/1", json={"unexpected": True}).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch("/api/items/1", json={"quantity": 1}).status_code, 404
        )

    @patch("app.requests.get")
    def test_lookup_by_barcode_normalizes_openfoodfacts_product(self, get):
        get.return_value = Mock(
            json=lambda: {
                "status": 1,
                "product": {
                    "product_name": "Chickpeas",
                    "code": "987",
                    "categories": "Canned foods, Legumes",
                    "generic_name": "Cooked chickpeas",
                    "image_url": "https://example.test/image.jpg",
                },
            }
        )
        response = self.client.get("/api/products/lookup?barcode=987")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "Chickpeas")
        self.assertEqual(response.json["category"], "Canned foods")
        self.assertEqual(response.json["barcode"], "987")

    @patch("app.requests.get")
    def test_lookup_by_name_handles_no_result(self, get):
        get.return_value = Mock(json=lambda: {"products": []})
        response = self.client.get("/api/products/lookup?name=unknown")
        self.assertEqual(response.status_code, 404)

    @patch("app.requests.get")
    def test_lookup_by_name_returns_first_matching_product(self, get):
        get.return_value = Mock(
            json=lambda: {
                "products": [
                    {
                        "product_name": "Rolled oats",
                        "code": "555",
                        "categories": "Cereals, Breakfast",
                    }
                ]
            }
        )

        response = self.client.get("/api/products/lookup?name=rolled%20oats")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "Rolled oats")
        self.assertEqual(response.json["barcode"], "555")
        self.assertEqual(
            get.call_args.kwargs["params"]["search_terms"], "rolled oats"
        )

    @patch("app.requests.get")
    def test_import_adds_external_product_to_inventory(self, get):
        get.return_value = Mock(
            json=lambda: {
                "status": 1,
                "product": {
                    "product_name": "Black beans",
                    "code": "111",
                    "categories": "Canned foods",
                },
            }
        )
        response = self.client.post(
            "/api/items/import", json={"barcode": "111", "quantity": 5, "price": 2.25}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["name"], "Black beans")
        self.assertEqual(response.json["quantity"], 5)
        self.assertEqual(len(self.client.get("/api/items").json), 1)

    @patch("app.requests.get")
    def test_external_service_failure_is_reported(self, get):
        import requests

        get.side_effect = requests.Timeout
        response = self.client.get("/api/products/lookup?barcode=987")
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
