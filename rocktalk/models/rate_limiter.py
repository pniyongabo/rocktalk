from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque


class TokenRateLimiter:
    """Manages token rate limiting for LLM API calls using datetime objects"""

    def __init__(self, tokens_per_minute: int = 100000):
        """Initialize the rate limiter

        Args:
            tokens_per_minute: Maximum tokens to allow per minute
        """
        self.tokens_per_minute = tokens_per_minute
        self.usage_window: Deque[tuple[datetime, int]] = (
            deque()
        )  # (timestamp, token_count)
        self.window_duration = timedelta(minutes=1)

    def update_usage(self, token_count: int) -> None:
        """Record token usage

        Args:
            token_count: Number of tokens consumed
        """
        now = datetime.now(timezone.utc)

        # Remove entries older than our window
        while (
            self.usage_window and (now - self.usage_window[0][0]) > self.window_duration
        ):
            self.usage_window.popleft()

        # Add current usage
        self.usage_window.append((now, token_count))

    def check_rate_limit(self, estimated_tokens: int) -> tuple[bool, float]:
        """Check if the request would exceed the rate limit

        Args:
            estimated_tokens: Estimated token usage for current request

        Returns:
            Tuple of (is_allowed, wait_time_seconds)
        """
        now = datetime.now(timezone.utc)

        # Clean up old entries
        while (
            self.usage_window and (now - self.usage_window[0][0]) > self.window_duration
        ):
            self.usage_window.popleft()

        # Calculate current usage in the time window
        current_usage = sum(tokens for _, tokens in self.usage_window)

        # If adding the new estimated tokens would exceed the limit
        if current_usage + estimated_tokens > self.tokens_per_minute:
            # Calculate time to wait until we're under limit
            if self.usage_window:
                # Wait until oldest entry falls out of the window
                oldest_entry_time = self.usage_window[0][0]
                wait_time = (
                    oldest_entry_time + self.window_duration - now
                ).total_seconds()
                return False, max(0, wait_time)

        return True, 0

    def get_current_usage(self) -> int:
        """Get the current token usage within the window"""
        now = datetime.now(timezone.utc)

        # Clean up old entries
        while (
            self.usage_window and (now - self.usage_window[0][0]) > self.window_duration
        ):
            self.usage_window.popleft()

        return sum(tokens for _, tokens in self.usage_window)

    def get_usage_percentage(self) -> float:
        """Get the current usage as a percentage of the limit"""
        return (self.get_current_usage() / self.tokens_per_minute) * 100
