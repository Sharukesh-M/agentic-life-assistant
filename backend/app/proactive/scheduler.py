"""
Local Proactive Scheduler.
Provides deterministic run_once() execution and optional background polling thread.
"""

import time
import threading
from datetime import datetime
from typing import Optional, Callable, Any
from app.proactive.models import ProactiveCycleResult

class LocalProactiveScheduler:
    """
    Lightweight Local Scheduler for JARVIX Proactive Engine.
    """

    def __init__(
        self,
        service: Any,
        clock_fn: Optional[Callable[[], datetime]] = None
    ):
        self.service = service
        self.clock_fn = clock_fn or datetime.utcnow
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._interval_seconds = 300.0  # Default 5 minutes

    def run_once(
        self,
        user_id: str,
        current_time: Optional[datetime] = None,
        db_session: Optional[Any] = None
    ) -> ProactiveCycleResult:
        """
        Runs a single deterministic proactive monitoring cycle.
        Main entry point for unit tests and direct execution.
        """
        now = current_time or self.clock_fn()
        return self.service.run_cycle(user_id=user_id, current_time=now, db_session=db_session)

    def start(self, user_id: str = "default_user", interval_seconds: float = 300.0) -> None:
        """Starts background polling thread for local development runtime."""
        if self._running:
            return
        self._running = True
        self._interval_seconds = interval_seconds
        self._thread = threading.Thread(target=self._worker_loop, args=(user_id,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops background polling thread cleanly."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

    def _worker_loop(self, user_id: str) -> None:
        while self._running:
            try:
                self.run_once(user_id=user_id)
            except Exception as e:
                print(f"[Proactive Scheduler Error] Worker cycle failed: {e}")
            
            # Sleep in short slices to allow clean stop() interrupt
            elapsed = 0.0
            while elapsed < self._interval_seconds and self._running:
                time.sleep(0.5)
                elapsed += 0.5
