import logging
from typing import Optional
from py_clob_client.clob_types import OrderArgs, OrderType
from app.core.client import PolyClient

logger = logging.getLogger("GhostOrderManager")

class OrderManager:
    def __init__(self):
        self.client = PolyClient.get_instance()

    def create_and_post_order(
        self, 
        token_id: str, 
        price: float, 
        size: float, 
        side: str, 
        order_type: OrderType = OrderType.GTC
    ) -> dict:
        """
        Creates, signs, and posts an order to the Polymarket CLOB.
        """
        try:
            logger.info(f"Creating {side} order for {token_id}: {size} @ {price}")
            
            # 1. Prepare Order Arguments
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side
            )
            
            # 2. Create and Sign the order
            # Note: create_order handles the signing using the client's internal signer
            signed_order = self.client.create_order(order_args)
            
            # 3. Post the order
            response = self.client.post_order(signed_order, orderType=order_type)
            
            if response and response.get("success"):
                order_id = response.get("orderID")
                logger.info(f"Order posted successfully. ID: {order_id}")
                return {"status": "success", "order_id": order_id, "response": response}
            else:
                error_msg = response.get("errorMsg") if response else "Unknown submission error"
                logger.error(f"Failed to post order: {error_msg}")
                return {"status": "error", "message": error_msg}

        except Exception as e:
            logger.error(f"Exception in order placement: {str(e)}")
            return {"status": "error", "message": str(e)}

    def cancel_order(self, order_id: str) -> dict:
        """
        Cancels an existing order.
        """
        try:
            logger.info(f"Cancelling order: {order_id}")
            response = self.client.cancel_order(order_id)
            return {"status": "success", "response": response}
        except Exception as e:
            logger.error(f"Exception in order cancellation: {str(e)}")
            return {"status": "error", "message": str(e)}

    def cancel_all_orders(self) -> dict:
        """
        Cancels all open orders for the authenticated address.
        """
        try:
            logger.info("Cancelling all open orders...")
            response = self.client.cancel_all()
            return {"status": "success", "response": response}
        except Exception as e:
            logger.error(f"Exception in bulk cancellation: {str(e)}")
            return {"status": "error", "message": str(e)}
