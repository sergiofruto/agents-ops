from unittest.mock import patch

import tracker


# CLOB /data/order returns null once an order is matched and archived;
# the fill then has to be confirmed from trade history.

class FakeClient:
    def __init__(self, order, trades):
        self._order = order
        self._trades = trades

    def get_order(self, order_id):
        return self._order

    def get_trades(self, params):
        return self._trades


BET = {"id": 16, "order_id": "0xabc", "condition_id": "0xcond"}


def _run(client):
    with patch.object(tracker.config, "DRY_RUN", False), \
         patch.object(tracker.database, "get_pending_fill_bets", return_value=[BET]), \
         patch.object(tracker, "get_clob_client", return_value=client), \
         patch.object(tracker.database, "update_fill_status") as fill, \
         patch.object(tracker.database, "update_bet_result") as result:
        tracker.check_pending_fills()
    return fill, result


def test_archived_order_with_confirmed_maker_trade_is_filled():
    trades = [{"status": "CONFIRMED", "taker_order_id": "0xother",
               "maker_orders": [{"order_id": "0xabc"}]}]
    fill, result = _run(FakeClient(None, trades))
    fill.assert_called_once_with(16, "filled")
    result.assert_not_called()


def test_archived_order_with_confirmed_taker_trade_is_filled():
    trades = [{"status": "CONFIRMED", "taker_order_id": "0xabc", "maker_orders": []}]
    fill, _ = _run(FakeClient(None, trades))
    fill.assert_called_once_with(16, "filled")


def test_archived_order_without_trades_stays_pending():
    fill, result = _run(FakeClient(None, []))
    fill.assert_not_called()
    result.assert_not_called()


def test_live_order_fill_still_uses_size_matched():
    order = {"size_matched": "10", "original_size": "10", "status": "matched"}
    fill, _ = _run(FakeClient(order, []))
    fill.assert_called_once_with(16, "filled")
