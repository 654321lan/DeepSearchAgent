#!/usr/bin/env python3
"""
Simple test script to verify imports work correctly
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from agent import DeepSearchAgent
    print("Error:", e)
    print("✓ Successfully imported DeepSearchAgent")

    # Test basic initialization
    try:
        from utils import Config
        config = Config()
        agent = DeepSearchAgent(config)
        print("Error:", e)
    print("✓ Successfully created DeepSearchAgent instance")
    except Exception as e:
        print("Error:", e)
    print(f"✗ Failed to create DeepSearchAgent: {e}")

    # Test cache methods exist
    cache_methods = [
        '_get_cache_key',
        '_load_query_cache',
        '_save_query_cache',
        '_get_cached_result',
        '_cache_result',
        'clear_query_cache',
        'get_cache_info',
        'set_cache_enabled',
        'show_cache_status',
        'list_cached_queries',
        'get_cached_queries_count',
        'get_cache_hit_rate',
        'cache_query'
    ]

    for method in cache_methods:
        if hasattr(agent, method):
            print("Error:", e)
    print(f"✓ Method {method} exists")
        else:
            print("Error:", e)
    print(f"✗ Method {method} missing")

except ImportError as e:
    print("Error:", e)
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print("Error:", e)
    print_exc()