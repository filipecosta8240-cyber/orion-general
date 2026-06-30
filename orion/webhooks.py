"""
Webhook System
==============
Provides webhook integration for external event notifications.
Based on 2026 patterns for event-driven integrations.

Features:
- Webhook registration and management
- Event filtering and routing
- Retry logic with exponential backoff
- Webhook delivery tracking
- Secret verification for security
"""

from __future__ import annotations

import json
import logging
import hashlib
import hmac
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import threading

logger = logging.getLogger("orion.webhooks")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEBHOOK_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "WEBHOOKS"


class WebhookStatus(str, Enum):
    """Webhook status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    PENDING = "pending"


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Webhook:
    """Webhook registration."""
    webhook_id: str
    url: str
    secret: str
    events: List[str]
    status: str = WebhookStatus.ACTIVE
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    failure_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebhookEvent:
    """Event to be sent via webhook."""
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeliveryAttempt:
    """Record of a webhook delivery attempt."""
    attempt_id: str
    webhook_id: str
    event_id: str
    status: str
    response_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WebhookSecurity:
    """Security utilities for webhooks."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a secure webhook secret."""
        return hashlib.sha256(str(time.time()).encode()).hexdigest()
    
    @staticmethod
    def sign_payload(payload: str, secret: str) -> str:
        """Sign a payload with HMAC-SHA256."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_signature(payload: str, secret: str, signature: str) -> bool:
        """Verify a webhook signature."""
        expected = WebhookSecurity.sign_payload(payload, secret)
        return hmac.compare_digest(expected, signature)


class WebhookDelivery:
    """Handle webhook delivery with retry logic."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._delivery_history: List[DeliveryAttempt] = []
    
    def deliver(self, webhook: Webhook, event: WebhookEvent) -> DeliveryAttempt:
        """Deliver a webhook event with retry logic."""
        import hashlib
        from urllib.request import urlopen, Request
        from urllib.error import URLError
        
        attempt_id = f"attempt_{hashlib.md5(f'{webhook.webhook_id}_{event.event_id}'.encode()).hexdigest()[:8]}"
        
        payload = json.dumps(event.to_dict(), default=str)
        signature = WebhookSecurity.sign_payload(payload, webhook.secret)
        
        for attempt in range(self.max_retries + 1):
            try:
                req = Request(
                    webhook.url,
                    data=payload.encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'X-Webhook-Signature': signature,
                        'X-Webhook-ID': webhook.webhook_id,
                        'X-Event-Type': event.event_type,
                        'User-Agent': 'ORION-Webhook/1.0'
                    },
                    method='POST'
                )
                
                with urlopen(req, timeout=10) as response:
                    response_code = response.getcode()
                    
                    attempt = DeliveryAttempt(
                        attempt_id=f"{attempt_id}_{attempt}",
                        webhook_id=webhook.webhook_id,
                        event_id=event.event_id,
                        status=DeliveryStatus.DELIVERED,
                        response_code=response_code
                    )
                    self._delivery_history.append(attempt)
                    
                    logger.info(f"Webhook delivered: {webhook.webhook_id} -> {response_code}")
                    return attempt
                    
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Webhook delivery failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    attempt_record = DeliveryAttempt(
                        attempt_id=f"{attempt_id}_{attempt}",
                        webhook_id=webhook.webhook_id,
                        event_id=event.event_id,
                        status=DeliveryStatus.FAILED,
                        error=str(e)
                    )
                    self._delivery_history.append(attempt_record)
                    
                    logger.error(f"Webhook delivery failed after {self.max_retries} retries: {e}")
                    return attempt_record
        
        return DeliveryAttempt(
            attempt_id=attempt_id,
            webhook_id=webhook.webhook_id,
            event_id=event.event_id,
            status=DeliveryStatus.FAILED,
            error="Max retries exceeded"
        )
    
    def get_history(self, webhook_id: Optional[str] = None, limit: int = 100) -> List[DeliveryAttempt]:
        """Get delivery history."""
        history = self._delivery_history
        if webhook_id:
            history = [h for h in history if h.webhook_id == webhook_id]
        return history[-limit:]


class WebhookManager:
    """
    Webhook Management System
    
    Manages webhook registrations, event routing, and delivery tracking.
    """
    
    def __init__(self, webhook_root: Optional[Path] = None):
        self._root = webhook_root or WEBHOOK_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        
        self._webhooks: Dict[str, Webhook] = {}
        self._delivery = WebhookDelivery()
        self._event_filters: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()
        
        self._load_webhooks()
    
    def _load_webhooks(self) -> None:
        """Load webhooks from disk."""
        webhooks_file = self._root / "webhooks.json"
        if webhooks_file.exists():
            try:
                data = json.loads(webhooks_file.read_text(encoding="utf-8"))
                for wid, wdata in data.items():
                    self._webhooks[wid] = Webhook(**wdata)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save_webhooks(self) -> None:
        """Save webhooks to disk."""
        webhooks_file = self._root / "webhooks.json"
        data = {wid: w.to_dict() for wid, w in self._webhooks.items()}
        webhooks_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    def register_webhook(self, url: str, events: List[str], 
                        description: str = "") -> Webhook:
        """Register a new webhook."""
        import hashlib
        
        webhook_id = f"wh_{hashlib.md5(url.encode()).hexdigest()[:12]}"
        secret = WebhookSecurity.generate_secret()
        
        webhook = Webhook(
            webhook_id=webhook_id,
            url=url,
            secret=secret,
            events=events,
            description=description
        )
        
        with self._lock:
            self._webhooks[webhook_id] = webhook
            self._save_webhooks()
        
        logger.info(f"Webhook registered: {webhook_id} for {events}")
        return webhook
    
    def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister a webhook."""
        with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                self._save_webhooks()
                logger.info(f"Webhook unregistered: {webhook_id}")
                return True
        return False
    
    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)
    
    def list_webhooks(self, status: Optional[str] = None) -> List[Webhook]:
        """List all webhooks."""
        webhooks = list(self._webhooks.values())
        if status:
            webhooks = [w for w in webhooks if w.status == status]
        return webhooks
    
    def trigger_event(self, event_type: str, payload: Dict[str, Any]) -> List[DeliveryAttempt]:
        """Trigger an event to all matching webhooks."""
        event = WebhookEvent(
            event_id=f"evt_{int(time.time() * 1000)}",
            event_type=event_type,
            payload=payload
        )
        
        matching_webhooks = [
            w for w in self._webhooks.values()
            if w.status == WebhookStatus.ACTIVE and event_type in w.events
        ]
        
        results = []
        for webhook in matching_webhooks:
            result = self._delivery.deliver(webhook, event)
            results.append(result)
            
            if result.status == DeliveryStatus.DELIVERED:
                webhook.last_triggered = datetime.now(timezone.utc)
                webhook.failure_count = 0
            else:
                webhook.failure_count += 1
                if webhook.failure_count >= 5:
                    webhook.status = WebhookStatus.FAILED
        
        with self._lock:
            self._save_webhooks()
        
        return results
    
    def get_delivery_history(self, webhook_id: Optional[str] = None, 
                            limit: int = 100) -> List[DeliveryAttempt]:
        """Get delivery history."""
        return self._delivery.get_history(webhook_id, limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get webhook statistics."""
        total = len(self._webhooks)
        active = sum(1 for w in self._webhooks.values() if w.status == WebhookStatus.ACTIVE)
        failed = sum(1 for w in self._webhooks.values() if w.status == WebhookStatus.FAILED)
        
        return {
            "total_webhooks": total,
            "active_webhooks": active,
            "failed_webhooks": failed,
            "total_deliveries": len(self._delivery._delivery_history),
            "successful_deliveries": sum(
                1 for d in self._delivery._delivery_history 
                if d.status == DeliveryStatus.DELIVERED
            )
        }
