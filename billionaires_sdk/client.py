from __future__ import annotations

import asyncio
import copy
import functools
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SDK_VERSION = "1.0.0"
VALID_ACTIONS = {"BUY", "SELL"}
VALID_PRICE_TYPES = {"MARKET", "LIMIT", "SL", "SL-M"}
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class BridgeConfigError(ValueError):
    """Raised when SDK configuration or order input is invalid."""


class BridgeAPIError(RuntimeError):
    """Raised when the Bridge API returns a non-success response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = dict(response or {})


@dataclass(frozen=True)
class BridgeResponse:
    """Normalized order response returned by BridgeClient order methods."""

    raw: Mapping[str, Any]
    success: bool
    target_count: int
    success_count: int
    failed_count: int
    dry_run: bool
    idempotency_key: Optional[str]
    idempotent_replay: bool
    order: Mapping[str, Any]
    results: List[Mapping[str, Any]]
    message: str = ""

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BridgeResponse":
        data = dict(payload or {})
        results = list(data.get("results") or [])
        success_count = int(data.get("successCount", sum(1 for item in results if item.get("success"))))
        failed_count = int(data.get("failedCount", max(len(results) - success_count, 0)))
        return cls(
            raw=data,
            success=bool(data.get("success")),
            target_count=int(data.get("targetCount", len(results))),
            success_count=success_count,
            failed_count=failed_count,
            dry_run=bool(data.get("dryRun")),
            idempotency_key=data.get("idempotencyKey"),
            idempotent_replay=bool(data.get("idempotentReplay")),
            order=dict(data.get("order") or {}),
            results=results,
            message=str(data.get("message") or ""),
        )

    @property
    def failed_results(self) -> List[Mapping[str, Any]]:
        return [item for item in self.results if not item.get("success")]

    @property
    def successful_results(self) -> List[Mapping[str, Any]]:
        return [item for item in self.results if item.get("success")]

    def raise_for_failures(self) -> "BridgeResponse":
        if not self.success:
            raise BridgeAPIError(self.message or "Bridge order failed", response=self.raw)
        if self.failed_count:
            raise BridgeAPIError("One or more target accounts failed", response=self.raw)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(dict(self.raw))

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]


@dataclass(frozen=True)
class BridgeStatus:
    """Status and compatibility response from /api/signals/status."""

    raw: Mapping[str, Any]
    success: bool
    api_version: str
    sdk_min_version: str
    paper: bool
    live: bool
    active_client_count: int
    group_count: int

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BridgeStatus":
        data = dict(payload or {})
        api = dict(data.get("api") or {})
        mode = dict(data.get("mode") or {})
        targets = dict(data.get("targets") or {})
        return cls(
            raw=data,
            success=bool(data.get("success")),
            api_version=str(api.get("version") or ""),
            sdk_min_version=str(api.get("sdkMinVersion") or ""),
            paper=bool(mode.get("paper")),
            live=bool(mode.get("live")),
            active_client_count=int(targets.get("activeClientCount") or 0),
            group_count=int(targets.get("groupCount") or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(dict(self.raw))

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]


class BridgeClient:
    """Production-oriented client for the Billionaires Bridge API.

    The SDK sends the same Signal API Contract accepted by TradingView and
    direct HTTP clients, while adding Python-side validation, idempotency keys,
    retry/backoff, status checks, typed responses, async wrappers, and basket
    helpers.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        mode_guard: str = "any",
        check_status_on_order: bool = False,
        user_agent: Optional[str] = None,
    ) -> None:
        self.base_url = self._clean_base_url(base_url)
        self.api_key = self._required_text(api_key, "api_key")
        self.timeout = self._positive_float(timeout, "timeout")
        self.max_retries = self._non_negative_int(max_retries, "max_retries")
        self.retry_backoff = self._positive_float(retry_backoff, "retry_backoff")
        self.mode_guard = self._clean_mode_guard(mode_guard)
        self.check_status_on_order = bool(check_status_on_order)
        self.user_agent = user_agent or f"billionaires-sdk-python/{SDK_VERSION}"

    @classmethod
    def from_env(
        cls,
        *,
        base_url_var: str = "BILLIONAIRES_BASE_URL",
        api_key_var: str = "BILLIONAIRES_API_KEY",
        timeout: float = 10.0,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        mode_guard: str = "any",
        check_status_on_order: bool = False,
    ) -> "BridgeClient":
        """Create a client from environment variables."""

        return cls(
            base_url=os.environ.get(base_url_var, ""),
            api_key=os.environ.get(api_key_var, ""),
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            mode_guard=mode_guard,
            check_status_on_order=check_status_on_order,
        )

    def status(self) -> BridgeStatus:
        """Fetch Bridge API compatibility and paper/live status."""

        return BridgeStatus.from_dict(self._get_json("/api/signals/status"))

    def ensure_ready(
        self,
        *,
        require_paper: bool = False,
        require_live: bool = False,
        min_active_clients: int = 1,
    ) -> BridgeStatus:
        """Validate the remote Bridge API is usable before strategy execution."""

        if require_paper and require_live:
            raise BridgeConfigError("require_paper and require_live cannot both be true")

        status = self.status()
        if not status.success:
            raise BridgeAPIError("Bridge API status check failed", response=status.raw)
        if require_paper and not status.paper:
            raise BridgeConfigError("Paper Trade mode is required but the platform is LIVE")
        if require_live and not status.live:
            raise BridgeConfigError("Live mode is required but Paper Trade is ON")
        if status.active_client_count < int(min_active_clients):
            raise BridgeConfigError("No active client accounts are available for Bridge API execution")
        return status

    def buy(self, **payload: Any) -> BridgeResponse:
        """Send a BUY signal."""

        return self.order(action="BUY", **payload)

    def sell(self, **payload: Any) -> BridgeResponse:
        """Send a SELL signal."""

        return self.order(action="SELL", **payload)

    def order(
        self,
        *,
        action: str,
        symbol: str,
        exchange: str = "NFO",
        quantity: int = 1,
        product: str = "MIS",
        pricetype: str = "MARKET",
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        group: Optional[str] = None,
        groups: Optional[Iterable[str]] = None,
        group_id: Optional[str] = None,
        group_ids: Optional[Iterable[str]] = None,
        account_ids: Optional[Iterable[str]] = None,
        deployment_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        source: str = "python_sdk",
        require_paper: bool = False,
        require_live: bool = False,
        **extra: Any,
    ) -> BridgeResponse:
        """Send a strategy signal to the Bridge API."""

        self._run_mode_guard(require_paper=require_paper, require_live=require_live)
        payload = self._build_payload(
            action=action,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            product=product,
            pricetype=pricetype,
            price=price,
            trigger_price=trigger_price,
            group=group,
            groups=groups,
            group_id=group_id,
            group_ids=group_ids,
            account_ids=account_ids,
            deployment_id=deployment_id,
            idempotency_key=idempotency_key,
            source=source,
            extra=extra,
        )
        return BridgeResponse.from_dict(self._post_json("/api/signals/order", payload))

    def basket(
        self,
        orders: Iterable[Mapping[str, Any]],
        *,
        stop_on_error: bool = True,
        require_paper: bool = False,
        require_live: bool = False,
    ) -> List[BridgeResponse]:
        """Send multiple order signals sequentially.

        This uses the same single-order endpoint for each item so broker logs
        remain simple and idempotency is preserved per order.
        """

        responses: List[BridgeResponse] = []
        for index, order_payload in enumerate(orders):
            try:
                responses.append(
                    self.order(
                        require_paper=require_paper,
                        require_live=require_live,
                        **dict(order_payload),
                    )
                )
            except (BridgeAPIError, BridgeConfigError) as exc:
                if stop_on_error:
                    raise
                responses.append(
                    BridgeResponse.from_dict(
                        {
                            "success": False,
                            "message": f"Basket order {index + 1} failed: {exc}",
                            "results": [],
                        }
                    )
                )
        return responses

    async def async_status(self) -> BridgeStatus:
        return await self._to_thread(self.status)

    async def async_ensure_ready(self, **kwargs: Any) -> BridgeStatus:
        return await self._to_thread(functools.partial(self.ensure_ready, **kwargs))

    async def async_buy(self, **payload: Any) -> BridgeResponse:
        return await self.async_order(action="BUY", **payload)

    async def async_sell(self, **payload: Any) -> BridgeResponse:
        return await self.async_order(action="SELL", **payload)

    async def async_order(self, **payload: Any) -> BridgeResponse:
        return await self._to_thread(functools.partial(self.order, **payload))

    async def async_basket(
        self,
        orders: Iterable[Mapping[str, Any]],
        *,
        stop_on_error: bool = True,
        require_paper: bool = False,
        require_live: bool = False,
    ) -> List[BridgeResponse]:
        return await self._to_thread(
            functools.partial(
                self.basket,
                orders,
                stop_on_error=stop_on_error,
                require_paper=require_paper,
                require_live=require_live,
            )
        )

    def _run_mode_guard(self, *, require_paper: bool, require_live: bool) -> None:
        guard_requires_paper = self.mode_guard == "paper" or require_paper
        guard_requires_live = self.mode_guard == "live" or require_live
        if self.check_status_on_order or guard_requires_paper or guard_requires_live:
            self.ensure_ready(require_paper=guard_requires_paper, require_live=guard_requires_live)

    def _build_payload(
        self,
        *,
        action: str,
        symbol: str,
        exchange: str,
        quantity: int,
        product: str,
        pricetype: str,
        price: Optional[float],
        trigger_price: Optional[float],
        group: Optional[str],
        groups: Optional[Iterable[str]],
        group_id: Optional[str],
        group_ids: Optional[Iterable[str]],
        account_ids: Optional[Iterable[str]],
        deployment_id: Optional[str],
        idempotency_key: Optional[str],
        source: str,
        extra: Mapping[str, Any],
    ) -> Dict[str, Any]:
        action_value = self._required_text(action, "action").upper()
        if action_value not in VALID_ACTIONS:
            raise BridgeConfigError("action must be BUY or SELL")

        quantity_value = self._positive_quantity(quantity)
        pricetype_value = self._required_text(pricetype, "pricetype").upper()
        if pricetype_value not in VALID_PRICE_TYPES:
            raise BridgeConfigError("pricetype must be MARKET, LIMIT, SL, or SL-M")

        price_value = self._optional_float(price, "price")
        trigger_value = self._optional_float(trigger_price, "trigger_price")
        if pricetype_value in {"LIMIT", "SL"} and not price_value:
            raise BridgeConfigError("price is required for LIMIT and SL orders")
        if pricetype_value in {"SL", "SL-M"} and not trigger_value:
            raise BridgeConfigError("trigger_price is required for SL and SL-M orders")

        payload: Dict[str, Any] = {
            "action": action_value,
            "symbol": self.normalize_symbol(symbol),
            "exchange": self._required_text(exchange, "exchange").upper(),
            "quantity": quantity_value,
            "product": self._required_text(product, "product").upper(),
            "pricetype": pricetype_value,
            "source": source,
            "idempotencyKey": idempotency_key or str(uuid.uuid4()),
        }

        if price_value is not None:
            payload["price"] = price_value
        if trigger_value is not None:
            payload["trigger_price"] = trigger_value
        if group:
            payload["group"] = str(group).strip()
        if groups:
            payload["groups"] = self._clean_list(groups, "groups")
        if group_id:
            payload["groupId"] = str(group_id).strip()
        if group_ids:
            payload["groupIds"] = self._clean_list(group_ids, "group_ids")
        if account_ids:
            payload["accountIds"] = self._clean_list(account_ids, "account_ids")
        deployment_value = deployment_id or extra.get("deploymentId") or extra.get("deployment_id")
        if deployment_value:
            payload["deploymentId"] = str(deployment_value).strip()

        for key, value in extra.items():
            if key in {"deploymentId", "deployment_id"}:
                continue
            if value is not None:
                payload[key] = value

        return payload

    def _post_json(self, path: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        return self._request_json("POST", path, payload)

    def _get_json(self, path: str) -> Dict[str, Any]:
        return self._request_json("GET", path, None)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        last_error: Optional[BridgeAPIError] = None

        for attempt in range(self.max_retries + 1):
            request = Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": self.user_agent,
                    "x-bt-api-key": self.api_key,
                },
                method=method,
            )

            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return self._decode_response(response.read())
            except HTTPError as exc:
                decoded = self._decode_response_safely(exc.read())
                message = str(decoded.get("message") or decoded.get("error") or exc.reason)
                last_error = BridgeAPIError(message, status_code=exc.code, response=decoded)
                if exc.code not in RETRYABLE_STATUS_CODES or attempt >= self.max_retries:
                    raise last_error from exc
            except (URLError, TimeoutError) as exc:
                last_error = BridgeAPIError(f"Could not reach Bridge API: {exc}")
                if attempt >= self.max_retries:
                    raise last_error from exc

            self._sleep_before_retry(attempt)

        raise last_error or BridgeAPIError("Bridge API request failed")

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(self.retry_backoff * (2 ** attempt))

    @staticmethod
    async def _to_thread(callable_obj: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, callable_obj)

    @staticmethod
    def _decode_response(raw: bytes) -> Dict[str, Any]:
        if not raw:
            return {}
        text = raw.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BridgeAPIError("Bridge API returned invalid JSON", response={"raw": text}) from exc
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}

    @staticmethod
    def _decode_response_safely(raw: bytes) -> Dict[str, Any]:
        try:
            return BridgeClient._decode_response(raw)
        except BridgeAPIError as exc:
            return dict(exc.response or {})

    @staticmethod
    def normalize_symbol(symbol: Any) -> str:
        """Normalize common client-side symbol formatting mistakes."""

        clean = BridgeClient._required_text(symbol, "symbol")
        return clean.replace(" ", "").upper()

    @staticmethod
    def _clean_base_url(value: str) -> str:
        clean = BridgeClient._required_text(value, "base_url").rstrip("/")
        if not clean.startswith(("http://", "https://")):
            raise BridgeConfigError("base_url must start with http:// or https://")
        return clean

    @staticmethod
    def _clean_mode_guard(value: str) -> str:
        clean = str(value or "any").strip().lower()
        if clean not in {"any", "paper", "live"}:
            raise BridgeConfigError("mode_guard must be any, paper, or live")
        return clean

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        clean = str(value or "").strip()
        if not clean:
            raise BridgeConfigError(f"{field} is required")
        return clean

    @staticmethod
    def _clean_list(values: Iterable[Any], field: str) -> List[str]:
        clean = [str(value).strip() for value in values if str(value or "").strip()]
        if not clean:
            raise BridgeConfigError(f"{field} cannot be empty")
        return clean

    @staticmethod
    def _positive_float(value: Any, field: str) -> float:
        try:
            clean = float(value)
        except (TypeError, ValueError) as exc:
            raise BridgeConfigError(f"{field} must be a number") from exc
        if clean <= 0:
            raise BridgeConfigError(f"{field} must be greater than zero")
        return clean

    @staticmethod
    def _non_negative_int(value: Any, field: str) -> int:
        try:
            clean = int(value)
        except (TypeError, ValueError) as exc:
            raise BridgeConfigError(f"{field} must be an integer") from exc
        if clean < 0:
            raise BridgeConfigError(f"{field} cannot be negative")
        return clean

    @staticmethod
    def _positive_quantity(value: Any) -> int:
        try:
            quantity = int(value)
        except (TypeError, ValueError) as exc:
            raise BridgeConfigError("quantity must be an integer") from exc
        if quantity <= 0:
            raise BridgeConfigError("quantity must be greater than zero")
        return quantity

    @staticmethod
    def _optional_float(value: Any, field: str) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            clean = float(value)
        except (TypeError, ValueError) as exc:
            raise BridgeConfigError(f"{field} must be a number") from exc
        if clean <= 0:
            raise BridgeConfigError(f"{field} must be greater than zero")
        return clean
