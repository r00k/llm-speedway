"""Tests for timers module."""

import time
from harness.timers import ExperimentTimer


class TestExperimentTimer:
    def test_elapsed_without_start_returns_zero(self):
        timer = ExperimentTimer()
        assert timer.elapsed() == 0.0

    def test_start_and_elapsed(self):
        timer = ExperimentTimer()
        timer.start()
        time.sleep(0.1)
        elapsed = timer.elapsed()
        assert elapsed >= 0.1
        assert elapsed < 0.3

    def test_stop_freezes_elapsed(self):
        timer = ExperimentTimer()
        timer.start()
        time.sleep(0.1)
        timer.stop()
        elapsed1 = timer.elapsed()
        time.sleep(0.1)
        elapsed2 = timer.elapsed()
        assert elapsed1 == elapsed2

    def test_elapsed_rounds_to_two_decimals(self):
        timer = ExperimentTimer()
        timer.start()
        timer.stop()
        elapsed = timer.elapsed()
        assert elapsed == round(elapsed, 2)
