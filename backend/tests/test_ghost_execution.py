import unittest
from unittest.mock import MagicMock, patch
from app.engines.ghost.order_manager import OrderManager
from py_clob_client.clob_types import OrderArgs

class TestGhostExecution(unittest.TestCase):
    def setUp(self):
        # Patch PolyClient.get_instance to return a mock
        self.patcher = patch('app.engines.ghost.order_manager.PolyClient.get_instance')
        self.mock_get_instance = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_get_instance.return_value = self.mock_client
        self.order_manager = OrderManager()

    def tearDown(self):
        self.patcher.stop()

    def test_create_and_post_order_success(self):
        # Setup mocks
        self.mock_client.create_order.return_value = {"signed": "order"}
        self.mock_client.post_order.return_value = {"success": True, "orderID": "0x123"}

        # Execute
        res = self.order_manager.create_and_post_order(
            token_id="token_1",
            price=0.5,
            size=10.0,
            side="BUY"
        )

        # Verify
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["order_id"], "0x123")
        self.mock_client.create_order.assert_called_once()
        self.mock_client.post_order.assert_called_once_with({"signed": "order"}, orderType="GTC")

    def test_create_and_post_order_failure(self):
        # Setup mocks
        self.mock_client.create_order.return_value = {"signed": "order"}
        self.mock_client.post_order.return_value = {"success": False, "errorMsg": "Insufficient balance"}

        # Execute
        res = self.order_manager.create_and_post_order(
            token_id="token_1",
            price=0.5,
            size=10.0,
            side="BUY"
        )

        # Verify
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["message"], "Insufficient balance")

if __name__ == "__main__":
    unittest.main()
