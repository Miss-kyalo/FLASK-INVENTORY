import unittest
from unittest.mock import Mock, patch

from app import app, items


class InventoryApiTests(unittest.TestCase):
    def setUp(self):
        items.clear()
        self.client = app.test_client()

    def test_add_list_update_and_delete_item(self):
        added = self.client.post(
            "/api/items",
            json={"name": "Oat milk", "quantity": 5, "price": 3.5},
        )
        self.assertEqual(added.status_code, 201)
        item_id = added.json["id"]
        self.assertEqual(self.client.get("/api/items").json[0]["name"], "Oat milk")

        updated = self.client.patch(
            f"/api/items/{item_id}", json={"quantity": 3}
        )
        self.assertEqual(updated.json["quantity"], 3)
        self.assertEqual(self.client.delete(f"/api/items/{item_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/items/{item_id}").status_code, 404)

    def test_add_item_requires_a_name(self):
        response = self.client.post("/api/items", json={"quantity": 2})
        self.assertEqual(response.status_code, 400)

    @patch("app.requests.get")
    def test_lookup_product_by_barcode(self, get):
        get.return_value = Mock(
            json=lambda: {
                "status": 1,
                "product": {
                    "product_name": "Beans",
                    "code": "123",
                    "categories": "Canned food",
                },
            }
        )

        response = self.client.get("/api/products/lookup?barcode=123")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "Beans")

    @patch("app.requests.get")
    def test_import_product_adds_it_to_inventory(self, get):
        get.return_value = Mock(
            json=lambda: {
                "status": 1,
                "product": {
                    "product_name": "Beans",
                    "code": "123",
                    "categories": "Canned food",
                },
            }
        )

        response = self.client.post(
            "/api/items/import", json={"barcode": "123", "quantity": 4}
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["name"], "Beans")
        self.assertEqual(len(items), 1)


if __name__ == "__main__":
    unittest.main()
