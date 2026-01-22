"""Timing utilities for experiments."""

import time


class ExperimentTimer:
    """Timer for tracking experiment duration."""
    
    def __init__(self):
        self._start: float | None = None
        self._end: float | None = None
    
    def start(self):
        """Start the timer."""
        self._start = time.monotonic()
    
    def stop(self):
        """Stop the timer."""
        self._end = time.monotonic()
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self._start is None:
            return 0.0
        end = self._end if self._end else time.monotonic()
        return round(end - self._start, 2)
