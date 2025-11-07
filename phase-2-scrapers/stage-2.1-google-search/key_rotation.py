"""
Google Search API Key Rotation Manager

This module handles rotation of multiple API keys to:
1. Distribute load across multiple keys
2. Maximize free tier usage (100 queries/key/day = 300 total)
3. Automatically handle rate limit errors
4. Track key usage and health

Rotation Strategies:
- round_robin: Cycle through keys sequentially
- least_used: Use the key with fewest requests
- random: Random key selection
- adaptive: Switch keys when hitting rate limits
"""

import os
import logging
import random
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class APIKeyRotationManager:
    """Manages rotation of multiple Google API keys with health tracking."""

    def __init__(self, strategy: str = "round_robin"):
        """
        Initialize the key rotation manager.

        Args:
            strategy: Rotation strategy (round_robin, least_used, random, adaptive)
        """
        self.strategy = strategy
        self.current_index = 0
        self.keys = self._load_keys()
        self.key_stats = {key: {"requests": 0, "errors": 0, "last_error": None} for key in self.keys}
        self.rate_limit_threshold = int(os.environ.get('RATE_LIMIT_THRESHOLD', '95'))

        logger.info(f"Initialized KeyRotationManager with {len(self.keys)} keys using '{strategy}' strategy")

    def _load_keys(self) -> List[str]:
        """
        Load API keys from environment variables.

        Supports two formats:
        1. Individual keys: GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, GOOGLE_API_KEY_3
        2. Combined format: GOOGLE_API_KEYS=key1|key2|key3

        Returns:
            List of API keys (filtered for non-empty values)
        """
        keys = []

        # Try individual key format first
        for i in range(1, 10):  # Support up to 9 keys
            key = os.environ.get(f'GOOGLE_API_KEY_{i}')
            if key and key != 'your_first_api_key_here' and key.startswith('AIza'):
                keys.append(key)

        # If no individual keys found, try combined format
        if not keys:
            combined = os.environ.get('GOOGLE_API_KEYS')
            if combined and combined != 'key1|key2|key3':
                keys = [k.strip() for k in combined.split('|') if k.strip()]

        # Fallback to single key format
        if not keys:
            single_key = os.environ.get('GOOGLE_API_KEY')
            if single_key and single_key != 'your_api_key_here':
                keys = [single_key]

        if not keys:
            logger.warning("No valid API keys found in environment variables")
            return []

        logger.info(f"Loaded {len(keys)} API keys for rotation")
        return keys

    def get_next_key(self) -> Optional[str]:
        """
        Get the next API key based on configured strategy.

        Returns:
            Next API key to use, or None if no keys available
        """
        if not self.keys:
            logger.error("No API keys available for rotation")
            return None

        if self.strategy == "round_robin":
            return self._get_round_robin_key()
        elif self.strategy == "least_used":
            return self._get_least_used_key()
        elif self.strategy == "random":
            return self._get_random_key()
        elif self.strategy == "adaptive":
            return self._get_adaptive_key()
        else:
            logger.warning(f"Unknown strategy '{self.strategy}', falling back to round_robin")
            return self._get_round_robin_key()

    def _get_round_robin_key(self) -> str:
        """Rotate through keys in order (1, 2, 3, 1, 2, 3, ...)."""
        key = self.keys[self.current_index % len(self.keys)]
        self.current_index += 1
        return key

    def _get_least_used_key(self) -> str:
        """Select the key with fewest requests."""
        least_used_key = min(self.keys, key=lambda k: self.key_stats[k]["requests"])
        logger.debug(f"Selecting least_used key (requests: {self.key_stats[least_used_key]['requests']})")
        return least_used_key

    def _get_random_key(self) -> str:
        """Select a random key."""
        key = random.choice(self.keys)
        logger.debug(f"Selecting random key")
        return key

    def _get_adaptive_key(self) -> str:
        """
        Adaptively select keys based on recent rate limit errors.
        Switches to a different key if the current one is hitting limits.
        """
        # Find keys without recent rate limit errors
        available_keys = [
            k for k in self.keys
            if self.key_stats[k]["last_error"] != "RATE_LIMIT"
            or self._is_error_stale(self.key_stats[k])
        ]

        if available_keys:
            key = available_keys[self.current_index % len(available_keys)]
            self.current_index += 1
            logger.debug(f"Adaptive selection using healthy key")
            return key
        else:
            # All keys have recent rate limit errors, reset and use round_robin
            logger.warning("All keys have recent rate limit errors, resetting and trying again")
            self._reset_error_tracking()
            return self._get_round_robin_key()

    def _is_error_stale(self, stats: Dict) -> bool:
        """Check if the last error is older than 1 hour."""
        if not stats["last_error"] or not stats.get("last_error_time"):
            return True
        return datetime.now() - stats["last_error_time"] > timedelta(hours=1)

    def record_request(self, key: str, success: bool = True, error_type: Optional[str] = None):
        """
        Record API request statistics.

        Args:
            key: API key used
            success: Whether request succeeded
            error_type: Type of error (e.g., 'TIMEOUT', 'RATE_LIMIT', 'INVALID_KEY')
        """
        if key not in self.key_stats:
            return

        stats = self.key_stats[key]
        stats["requests"] += 1

        if not success:
            stats["errors"] += 1
            stats["last_error"] = error_type
            stats["last_error_time"] = datetime.now()
            logger.warning(f"Key {key[:10]}... error: {error_type} (total errors: {stats['errors']})")

    def get_statistics(self) -> Dict:
        """
        Get usage statistics for all keys.

        Returns:
            Dictionary with per-key statistics
        """
        stats = {}
        for key in self.keys:
            key_short = key[:10] + "..."
            key_stats = self.key_stats[key]
            error_rate = (
                (key_stats["errors"] / key_stats["requests"] * 100)
                if key_stats["requests"] > 0
                else 0
            )
            stats[key_short] = {
                "requests": key_stats["requests"],
                "errors": key_stats["errors"],
                "error_rate": f"{error_rate:.1f}%",
                "last_error": key_stats["last_error"],
            }
        return stats

    def _reset_error_tracking(self):
        """Reset error tracking for all keys (when all are rate limited)."""
        for key in self.keys:
            self.key_stats[key]["last_error"] = None
            self.key_stats[key]["last_error_time"] = None
        logger.info("Reset error tracking for all keys")

    def should_skip_key(self, key: str) -> bool:
        """
        Check if a key should be skipped due to too many errors.

        Args:
            key: API key to check

        Returns:
            True if key should be skipped, False otherwise
        """
        if key not in self.key_stats:
            return False

        stats = self.key_stats[key]
        if stats["requests"] == 0:
            return False

        error_rate = (stats["errors"] / stats["requests"]) * 100
        return error_rate >= self.rate_limit_threshold

    def log_summary(self):
        """Log a summary of key rotation statistics."""
        stats = self.get_statistics()
        logger.info("=== Key Rotation Statistics ===")
        for key_short, key_stats in stats.items():
            logger.info(
                f"{key_short}: {key_stats['requests']} requests, "
                f"{key_stats['errors']} errors ({key_stats['error_rate']})"
            )
        logger.info("=== End Statistics ===")


# Global instance for use in lambda_function.py
_rotation_manager = None


def get_rotation_manager() -> Optional[APIKeyRotationManager]:
    """Get or create the global key rotation manager instance."""
    global _rotation_manager
    if _rotation_manager is None:
        strategy = os.environ.get('KEY_ROTATION_STRATEGY', 'round_robin')
        _rotation_manager = APIKeyRotationManager(strategy=strategy)
    return _rotation_manager


def initialize_rotation_manager(strategy: str = "round_robin") -> APIKeyRotationManager:
    """
    Initialize the key rotation manager with a specific strategy.

    Args:
        strategy: Rotation strategy to use

    Returns:
        Initialized APIKeyRotationManager instance
    """
    global _rotation_manager
    _rotation_manager = APIKeyRotationManager(strategy=strategy)
    return _rotation_manager
