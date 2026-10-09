import unittest
from unittest.mock import patch

import cli


class InventoryCliTests(unittest.TestCase):
    @patch("cli.send_request")
    @patch("builtins.input", side_effect=["1"])
    def test_menu_can_list_items(self, user_input, send_request):
        cli.main()
        send_request.assert_called_once_with("GET", "/api/items")


if __name__ == "__main__":
    unittest.main()
