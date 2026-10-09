import unittest
from unittest.mock import Mock, patch

import cli


class InventoryCliTests(unittest.TestCase):
    @patch("cli.api_request")
    def test_lookup_sends_search_as_encoded_params(self, api_request):
        api_request.return_value = 0

        result = cli.main(["lookup", "--name", "oat milk & cereal"])

        self.assertEqual(result, 0)
        api_request.assert_called_once_with(
            "GET",
            "/api/products/lookup",
            base_url="http://127.0.0.1:5000",
            params={"name": "oat milk & cereal"},
        )

    @patch("cli.requests.request")
    def test_api_request_reports_response_as_json(self, request):
        request.return_value = Mock(content=b'{"id": 4}', json=lambda: {"id": 4})

        with patch("builtins.print") as print_output:
            result = cli.api_request(
                "GET", "/api/items/4", base_url="http://api.test"
            )

        self.assertEqual(result, 0)
        request.assert_called_once_with(
            "GET", "http://api.test/api/items/4", json=None, params=None, timeout=10
        )
        print_output.assert_called_once_with('{\n  "id": 4\n}')


if __name__ == "__main__":
    unittest.main()
