#!/usr/bin/env python3
"""Verify IProxy fix works correctly."""

import sys

sys.path.append("ide-plugins/pycharm")

try:
    from pinjected import IProxy

    proxy1 = IProxy(42)
    proxy2 = IProxy("test")

    print("✓ IProxy fix verified - no TypeError on construction")
    print(f"proxy1: {proxy1}")
    print(f"proxy2: {proxy2}")

    sys.path.append("ide-plugins/pycharm")
    from test_iproxy import some_func, user_proxy

    print("✓ test_iproxy imports work correctly")
    print(f"some_func(): {some_func()}")
    print(f"user_proxy: {user_proxy}")

except Exception as e:
    print(f"✗ IProxy fix failed: {e}")
    sys.exit(1)
