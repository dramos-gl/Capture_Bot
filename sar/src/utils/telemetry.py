"""SAR Performance Telemetry Utilities.

Provides lightweight, zero-overhead execution time benchmarking
for database queries, UI service calls, and API requests.
"""

import sys
import time
import logging
from contextlib import contextmanager

# Create dedicated performance logger
perf_logger = logging.getLogger("SAR.Performance")
perf_logger.setLevel(logging.INFO)

# Ensure console output without duplicating handlers
if not perf_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    _handler.setFormatter(_formatter)
    perf_logger.addHandler(_handler)
    perf_logger.propagate = False


@contextmanager
def track_perf(operation_name: str, transport: str = "LOCAL"):
    """Context manager to measure and log execution duration in milliseconds.
    
    Usage:
        with track_perf("InventarioUIService.get_referencias", transport="LOCAL"):
            ...
    """
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        perf_logger.info(f"[PERF-{transport}] {operation_name}: {elapsed_ms:.2f} ms")
