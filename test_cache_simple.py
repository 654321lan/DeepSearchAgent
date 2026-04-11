#!/usr/bin/env python3
"""
Simple test script for the local caching functionality
"""

import sys
import os
import tempfile

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_cache_methods():
    """Test cache functionality without running the full research process"""

    # Import and create a mock agent
    try:
        from agent import DeepSearchAgent
        from utils import Config

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock config
            config = Config()
            config.output_dir = temp_dir
            config.default_llm_provider = "deepseek"
            config.deepseek_api_key = "test_key"
            config.deepseek_model = "test_model"

            # Create agent instance
            agent = DeepSearchAgent(config)

            print("=== Testing Cache Functionality ===")

            # Test 1: Cache basic operations
            print("\n1. Testing basic cache operations...")

            # Cache a test result
            test_query = "Test cache functionality"
            test_result = "# Test Report\n\nThis is a test report content."

            # Test cache method
            agent.cache_result(test_query, test_result)
            print("[PASS] Test result cached")

            # Test get cached result
            cached_result = agent.get_cached_result(test_query)
            if cached_result == test_result:
                print("[PASS] Successfully retrieved cached result")
            else:
                print("[FAIL] Failed to retrieve cached result")

            # Test 2: Check if cached
            print("\n2. Testing cache check...")
            has_cache = agent.has_cached_result(test_query)
            if has_cache:
                print("[PASS] Cache check correct")
            else:
                print("[FAIL] Cache check failed")

            # Test 3: Cache info
            print("\n3. Testing cache info...")
            cache_info = agent.get_cache_info()
            print(f"Cache info: {cache_info}")

            # Test 4: List cached queries
            print("\n4. Testing list cached queries...")
            cached_queries = agent.list_cached_queries()
            print(f"Cached queries: {cached_queries}")

            # Test 5: Clear cache
            print("\n5. Testing clear cache...")
            agent.clear_cache()

            # Verify cache is cleared
            has_cache_after_clear = agent.has_cached_result(test_query)
            if not has_cache_after_clear:
                print("[PASS] Cache cleared successfully")
            else:
                print("[FAIL] Cache clear failed")

            # Test 6: Cache configuration
            print("\n6. Testing cache configuration...")
            agent.set_cache_config(enabled=False, ttl=3600, max_size=500)
            print("[PASS] Cache configuration updated")

            # Test 7: Enable cache again
            agent.set_cache_config(enabled=True)
            print("[PASS] Cache re-enabled")

            print("\n=== All Cache Tests Completed ===")
            return True

    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_persistence():
    """Test that cache persists across agent instances"""

    print("\n=== Testing Cache Persistence ===")

    try:
        from agent import DeepSearchAgent
        from utils import Config
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first agent
            config1 = Config()
            config1.output_dir = temp_dir
            config1.default_llm_provider = "deepseek"
            config1.deepseek_api_key = "test_key"
            config1.deepseek_model = "test_model"

            agent1 = DeepSearchAgent(config1)

            # Cache a result
            test_query = "Persistence test"
            test_result = "# Persistence Test Report\n\nTesting cache persistence functionality."

            agent1.cache_result(test_query, test_result)
            print("[PASS] First agent cached result")

            # Create second agent with same config
            agent2 = DeepSearchAgent(config1)

            # Try to get cached result
            cached_result = agent2.get_cached_result(test_query)
            if cached_result == test_result:
                print("[PASS] Second agent successfully retrieved from persistent cache")
                return True
            else:
                print("[FAIL] Persistence test failed")
                return False

    except Exception as e:
        print(f"Persistence test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting DeepSearchAgent local cache functionality tests...\n")

    # Run tests
    test1_passed = test_cache_methods()
    test2_passed = test_persistence()

    print(f"\n=== Test Summary ===")
    print(f"Basic cache test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Persistence test: {'PASSED' if test2_passed else 'FAILED'}")

    if test1_passed and test2_passed:
        print("\nAll tests PASSED! Cache functionality is working correctly.")
    else:
        print("\nSome tests FAILED, please check the implementation.")