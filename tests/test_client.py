import unittest

from billionaires_sdk import BridgeClient, BridgeConfigError, BridgeResponse, BridgeStatus


class BridgeClientTest(unittest.TestCase):
    def setUp(self):
        self.client = BridgeClient("https://example.com", "bt_test_key", max_retries=0)

    def test_builds_minimal_buy_payload(self):
        payload = self.client._build_payload(
            action="BUY",
            symbol=" reliance ",
            exchange="nse",
            quantity=1,
            product="mis",
            pricetype="market",
            price=None,
            trigger_price=None,
            group="Equity",
            groups=None,
            group_id=None,
            group_ids=None,
            account_ids=None,
            deployment_id="deploy-1",
            idempotency_key="test-key",
            source="python_sdk",
            extra={},
        )

        self.assertEqual(payload["action"], "BUY")
        self.assertEqual(payload["symbol"], "RELIANCE")
        self.assertEqual(payload["exchange"], "NSE")
        self.assertEqual(payload["quantity"], 1)
        self.assertEqual(payload["group"], "Equity")
        self.assertEqual(payload["deploymentId"], "deploy-1")
        self.assertEqual(payload["idempotencyKey"], "test-key")

    def test_builds_deployment_id_from_snake_case_extra(self):
        payload = self.client._build_payload(
            action="BUY",
            symbol="RELIANCE",
            exchange="NSE",
            quantity=1,
            product="MIS",
            pricetype="MARKET",
            price=None,
            trigger_price=None,
            group=None,
            groups=None,
            group_id=None,
            group_ids=None,
            account_ids=None,
            deployment_id=None,
            idempotency_key="test-key",
            source="python_sdk",
            extra={"deployment_id": "deploy-2"},
        )

        self.assertEqual(payload["deploymentId"], "deploy-2")
        self.assertNotIn("deployment_id", payload)

    def test_rejects_invalid_action(self):
        with self.assertRaises(BridgeConfigError):
            self.client._build_payload(
                action="HOLD",
                symbol="RELIANCE",
                exchange="NSE",
                quantity=1,
                product="MIS",
                pricetype="MARKET",
                price=None,
                trigger_price=None,
                group=None,
                groups=None,
                group_id=None,
                group_ids=None,
                account_ids=None,
                deployment_id=None,
                idempotency_key=None,
                source="python_sdk",
                extra={},
            )

    def test_rejects_limit_without_price(self):
        with self.assertRaises(BridgeConfigError):
            self.client._build_payload(
                action="BUY",
                symbol="RELIANCE",
                exchange="NSE",
                quantity=1,
                product="MIS",
                pricetype="LIMIT",
                price=None,
                trigger_price=None,
                group=None,
                groups=None,
                group_id=None,
                group_ids=None,
                account_ids=None,
                deployment_id=None,
                idempotency_key=None,
                source="python_sdk",
                extra={},
            )

    def test_rejects_missing_base_url_scheme(self):
        with self.assertRaises(BridgeConfigError):
            BridgeClient("example.com", "bt_test_key")

    def test_response_object_maps_counts_and_failures(self):
        response = BridgeResponse.from_dict(
            {
                "success": True,
                "dryRun": True,
                "targetCount": 2,
                "successCount": 1,
                "failedCount": 1,
                "idempotencyKey": "abc",
                "idempotentReplay": False,
                "order": {"symbol": "RELIANCE"},
                "results": [
                    {"accountId": "1", "success": True},
                    {"accountId": "2", "success": False, "message": "Rejected"},
                ],
            }
        )

        self.assertTrue(response.success)
        self.assertTrue(response.dry_run)
        self.assertEqual(response.success_count, 1)
        self.assertEqual(response.failed_count, 1)
        self.assertEqual(len(response.failed_results), 1)
        self.assertEqual(response["idempotencyKey"], "abc")

    def test_ensure_ready_honors_paper_guard(self):
        class FakeClient(BridgeClient):
            def status(self):
                return BridgeStatus.from_dict(
                    {
                        "success": True,
                        "api": {"version": "2026-06-24", "sdkMinVersion": "1.0.0"},
                        "mode": {"paper": False, "live": True},
                        "targets": {"activeClientCount": 1, "groupCount": 0},
                    }
                )

        with self.assertRaises(BridgeConfigError):
            FakeClient("https://example.com", "bt_test_key").ensure_ready(require_paper=True)

    def test_basket_can_continue_after_failed_item(self):
        class FakeClient(BridgeClient):
            def order(self, **payload):
                if payload["symbol"] == "BAD":
                    raise BridgeConfigError("bad symbol")
                return BridgeResponse.from_dict({"success": True, "results": [{"success": True}]})

        responses = FakeClient("https://example.com", "bt_test_key").basket(
            [
                {"action": "BUY", "symbol": "GOOD", "exchange": "NSE", "quantity": 1},
                {"action": "BUY", "symbol": "BAD", "exchange": "NSE", "quantity": 1},
            ],
            stop_on_error=False,
        )

        self.assertEqual(len(responses), 2)
        self.assertTrue(responses[0].success)
        self.assertFalse(responses[1].success)


if __name__ == "__main__":
    unittest.main()
