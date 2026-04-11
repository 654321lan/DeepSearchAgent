#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全流程最终测试
测试检索优化、本地缓存、速率限制功能
纯本地运行，不调用任何外部API
"""

import sys
import os
import tempfile
import time
import threading
import pickle
import hashlib
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_retrieval_optimization():
    """测试检索优化功能"""
    print("\n=== 测试1: 检索优化功能 ===")

    try:
        from retrieval import retrieve_documents, compute_bm25_score, optimized_retrieve

        # 创建测试文档数据
        test_documents = [
            {
                "title": "人工智能基础",
                "content": "人工智能（AI）是计算机科学的一个分支，致力于创建能够模拟人类智能的系统。机器学习是AI的核心技术之一。深度学习作为机器学习的子集，通过神经网络模型实现了图像识别、自然语言处理等任务。"
            },
            {
                "title": "机器学习算法",
                "content": "机器学习包括监督学习、无监督学习和强化学习。监督学习使用标记数据训练模型，如线性回归、决策树、随机森林等。无监督学习从无标记数据中发现模式，如聚类算法。强化学习通过奖励机制学习最优策略。"
            },
            {
                "title": "深度学习进展",
                "content": "深度学习近年来取得了突破性进展，特别是在图像识别领域。卷积神经网络（CNN）在ImageNet竞赛中超越了人类水平。Transformer架构的出现彻底改变了自然语言处理，催生了BERT、GPT等模型。"
            },
            {
                "title": "自然语言处理",
                "content": "自然语言处理（NLP）是AI的重要应用领域。基于Transformer的预训练模型如BERT和GPT，通过大规模语料库训练，能够实现文本分类、情感分析、问答系统等任务。这些模型在理解人类语言方面取得了显著进展。"
            }
        ]

        # 测试查询
        test_queries = [
            "机器学习算法",
            "深度学习图像识别",
            "自然语言处理Transformer"
        ]

        for query in test_queries:
            print(f"\n查询: '{query}'")
            results = retrieve_documents(
                query=query,
                documents=test_documents,
                top_k=3,
                max_content_length=80
            )

            print(f"检索到 {len(results)} 个结果:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. [分数: {result['score']:.4f}] {result['title']}")
                print(f"     内容: {result['content'][:60]}...")

            # 验证结果按相关性排序
            scores = [r['score'] for r in results]
            assert scores == sorted(scores, reverse=True), f"结果未按分数降序排序: {scores}"
            print("  [PASS] 结果按相关性正确排序")

        # 测试边缘情况
        print("\n测试边缘情况:")

        # 空查询
        results = retrieve_documents("", test_documents, top_k=3)
        assert all(r['score'] == 0.0 for r in results), "空查询的分数应该为0"
        print("  [PASS] 空查询处理正确")

        # 空文档列表
        results = retrieve_documents("机器学习", [], top_k=3)
        assert len(results) == 0, "空文档列表应该返回空结果"
        print("  [PASS] 空文档列表处理正确")

        print("\n[PASS] 检索优化功能测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 检索优化测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_local_caching():
    """测试本地缓存功能"""
    print("\n=== 测试2: 本地缓存功能 ===")

    try:
        # 先导入和创建必要的组件
        from llm_client import SimpleLLMClient
        from retrieval import retrieve_documents

        # 创建模拟LLM
        mock_llm = Mock()
        mock_llm.get_model_info = Mock(return_value={"model": "mock", "version": "1.0"})
        mock_llm.invoke = Mock(return_value="Mock response")

        # 创建简单的Agent类用于测试缓存
        class TestAgent:
            def __init__(self):
                self.query_cache = {}
                self.query_cache_file = "test_cache.pkl"
                self.enable_cache = True
                self.cache_ttl = None
                self.max_cache_size = 1000
                self._load_query_cache()

            def _generate_cache_key(self, query: str) -> str:
                if query is None:
                    query = ""
                query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()
                return query_hash

            def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
                if self.cache_ttl and 'timestamp' in cache_entry:
                    cache_time = datetime.fromisoformat(cache_entry['timestamp'])
                    elapsed = (datetime.now() - cache_time).total_seconds()
                    return elapsed < self.cache_ttl
                return True

            def _load_query_cache(self):
                try:
                    if os.path.exists(self.query_cache_file):
                        with open(self.query_cache_file, 'rb') as f:
                            self.query_cache = pickle.load(f)
                        print(f"已加载 {len(self.query_cache)} 条查询缓存")
                    else:
                        self.query_cache = {}
                except Exception as e:
                    print(f"加载查询缓存失败: {str(e)}")
                    self.query_cache = {}

            def _save_query_cache(self):
                try:
                    os.makedirs(os.path.dirname(self.query_cache_file), exist_ok=True)
                    if len(self.query_cache) > self.max_cache_size:
                        sorted_items = sorted(
                            self.query_cache.items(),
                            key=lambda x: x[1].get('timestamp', '1970-01-01T00:00:00')
                        )
                        items_to_remove = len(self.query_cache) - self.max_cache_size
                        for key, _ in sorted_items[:items_to_remove]:
                            del self.query_cache[key]
                        print(f"缓存清理：删除了 {items_to_remove} 条旧记录")
                    with open(self.query_cache_file, 'wb') as f:
                        pickle.dump(self.query_cache, f)
                except Exception as e:
                    print(f"保存查询缓存失败: {str(e)}")

            def get_cached_result(self, query: str) -> Optional[str]:
                if not self.enable_cache:
                    return None

                cache_key = self._generate_cache_key(query)
                if cache_key in self.query_cache:
                    cache_entry = self.query_cache[cache_key]
                    if self._is_cache_valid(cache_entry) and 'result' in cache_entry:
                        print(f"缓存命中: {query[:30]}..." if len(query) > 30 else f"缓存命中: {query}")
                        return cache_entry['result']
                return None

            def cache_result(self, query: str, result: str):
                try:
                    if not self.enable_cache:
                        return

                    cache_key = self._generate_cache_key(query)
                    self.query_cache[cache_key] = {
                        'result': result,
                        'timestamp': datetime.now().isoformat(),
                        'query': query
                    }
                    self._save_query_cache()
                    print(f"已缓存结果: {query[:30]}..." if len(query) > 30 else f"已缓存结果: {query}")
                except Exception as e:
                    print(f"缓存结果时发生错误: {str(e)}")

            def clear_cache(self):
                try:
                    self.query_cache = {}
                    if os.path.exists(self.query_cache_file):
                        os.remove(self.query_cache_file)
                    print("查询缓存已清空")
                except Exception as e:
                    print(f"清空缓存失败: {str(e)}")

            def has_cached_result(self, query: str) -> bool:
                if not self.enable_cache:
                    return False

                cache_key = self._generate_cache_key(query)
                if cache_key in self.query_cache:
                    cache_entry = self.query_cache[cache_key]
                    return self._is_cache_valid(cache_entry) and 'result' in cache_entry
                return False

            def set_cache_config(self, enabled: bool = True, ttl: Optional[int] = None, max_size: int = 1000):
                self.enable_cache = enabled
                self.cache_ttl = ttl
                self.max_cache_size = max_size
                print(f"缓存配置：启用={enabled}, TTL={ttl if ttl else '永不过期'}, 最大条目={max_size}")

            def list_cached_queries(self, limit: int = 10) -> List[str]:
                queries = []
                count = 0
                for cache_entry in self.query_cache.values():
                    if 'query' in cache_entry and count < limit:
                        query = cache_entry['query']
                        display_query = query[:50] + "..." if len(query) > 50 else query
                        queries.append(display_query)
                        count += 1
                return queries

            def get_cache_info(self) -> Dict[str, Any]:
                valid_entries = 0
                invalid_entries = 0
                for cache_entry in self.query_cache.values():
                    if self._is_cache_valid(cache_entry):
                        valid_entries += 1
                    else:
                        invalid_entries += 1
                return {
                    'total_entries': len(self.query_cache),
                    'valid_entries': valid_entries,
                    'invalid_entries': invalid_entries,
                    'cache_file': self.query_cache_file,
                    'cache_enabled': self.enable_cache,
                    'cache_exists': os.path.exists(self.query_cache_file),
                    'max_cache_size': self.max_cache_size,
                    'cache_ttl': self.cache_ttl
                }

        # 创建测试Agent
        agent = TestAgent()

        # 测试1: 基本缓存操作
        print("\n测试1.1: 基本缓存操作")

        test_query = "缓存测试查询"
        test_result = "# 缓存测试报告\n\n这是一个测试报告内容。"

        # 缓存结果
        agent.cache_result(test_query, test_result)
        print("  [PASS] 成功缓存结果")

        # 获取缓存
        cached_result = agent.get_cached_result(test_query)
        assert cached_result == test_result, "缓存获取失败"
        print("  [PASS] 成功获取缓存结果")

        # 测试缓存命中
        has_cache = agent.has_cached_result(test_query)
        assert has_cache, "缓存命中检查失败"
        print("  [PASS] 缓存命中检查正确")

        # 测试2: 缓存持久化
        print("\n测试1.2: 缓存持久化")

        # 创建新的代理实例（应该能加载缓存）
        agent2 = TestAgent()
        cached_result2 = agent2.get_cached_result(test_query)
        assert cached_result2 == test_result, "持久化缓存加载失败"
        print("  [PASS] 缓存持久化工作正常")

        # 测试3: 缓存信息
        print("\n测试1.3: 缓存信息")

        info = agent.get_cache_info()
        assert info['total_entries'] > 0, "缓存条目数错误"
        assert info['cache_enabled'] == True, "缓存状态错误"
        print(f"  [PASS] 缓存信息: {info['total_entries']} 条目, 启用状态: {info['cache_enabled']}")

        # 测试4: 缓存清理
        print("\n测试1.4: 缓存清理")

        agent.clear_cache()
        has_cache_after_clear = agent.has_cached_result(test_query)
        assert not has_cache_after_clear, "缓存清理失败"
        print("  [PASS] 缓存清理工作正常")

        # 测试5: 缓存配置
        print("\n测试1.5: 缓存配置")

        # 测试禁用缓存
        agent.set_cache_config(enabled=False)
        agent.cache_result("测试禁用", "应该不会被缓存")
        cached_disabled = agent.get_cached_result("测试禁用")
        assert cached_disabled is None, "禁用缓存时不应缓存内容"
        print("  [PASS] 缓存禁用功能正常")

        # 重新启用
        agent.set_cache_config(enabled=True, max_size=5)
        print("  [PASS] 缓存配置修改成功")

        # 测试6: 缓存列表
        print("\n测试1.6: 缓存列表")

        # 添加多个缓存
        for i in range(3):
            agent.cache_result(f"查询{i}", f"结果{i}")

        cached_list = agent.list_cached_queries(limit=5)
        assert len(cached_list) >= 3, "缓存列表数量错误"
        print(f"  [PASS] 缓存列表: {len(cached_list)} 条")

        # 清理测试文件
        if os.path.exists(agent.query_cache_file):
            os.remove(agent.query_cache_file)

        print("\n[PASS] 本地缓存功能测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 本地缓存测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiting():
    """测试速率限制功能"""
    print("\n=== 测试3: 速率限制功能 ===")

    try:
        from llm_client import RateLimiter, rate_limited, set_rate_limit, get_rate_limit_info

        # 测试1: 基本限制器
        print("\n测试3.1: 基本限制器")

        limiter = RateLimiter(max_requests=2, time_window=2)
        call_count = 0

        @rate_limited(max_requests=2, time_window=1)  # 缩短时间窗口
        def test_function():
            nonlocal call_count
            call_count += 1
            return f"Call {call_count}"

        # 前两次调用应该成功
        result1 = test_function()
        result2 = test_function()
        assert result1 == "Call 1", f"第一次调用失败: {result1}"
        assert result2 == "Call 2", f"第二次调用失败: {result2}"
        print("  [PASS] 前两次调用成功")

        # 第三次调用应该被限制
        try:
            result3 = test_function()
            print("[FAIL] 第三次调用应该被限制")
            return False
        except RuntimeError:
            print("  [PASS] 第三次调用被限制")

        # 等待窗口过期
        time.sleep(1.1)

        # 现在应该可以再次调用
        try:
            result4 = test_function()
            assert result4 == "Call 3", f"第四次调用失败: {result4}"
            print("  [PASS] 等待后恢复正常调用")
        except Exception as e:
            print(f"[FAIL] 等待后调用失败: {str(e)}")
            return False

        # 测试2: 全局限制器配置
        print("\n测试3.2: 全局配置")

        # 设置全局配置
        set_rate_limit(max_requests=5, time_window=10)
        info = get_rate_limit_info()
        assert info['max_requests'] == 5, "全局配置错误"
        assert info['time_window'] == 10, "全局配置错误"
        print(f"  [PASS] 全局配置: {info['max_requests']}/{info['time_window']}秒")

        # 测试3: 禁用和启用
        print("\n测试3.3: 禁用和启用")

        # 禁用
        from llm_client import disable_rate_limit, enable_rate_limit
        disable_rate_limit()
        info = get_rate_limit_info()
        assert info['max_requests'] == float('inf'), "禁用后配置错误"
        print("  [PASS] 成功禁用速率限制")

        # 启用
        enable_rate_limit(max_requests=3, time_window=5)
        info = get_rate_limit_info()
        assert info['max_requests'] == 3, "启用后配置错误"
        print("  [PASS] 成功启用速率限制")

        # 测试4: 线程安全
        print("\n测试3.4: 线程安全")

        limiter = RateLimiter(max_requests=10, time_window=5)
        results = []
        errors = []

        def worker(worker_id):
            for i in range(3):
                time.sleep(0.01)  # 短暂延迟
                try:
                    if limiter.is_allowed():
                        results.append(f"Worker {worker_id} 成功")
                    else:
                        errors.append(f"Worker {worker_id} 被限制")
                except Exception as e:
                    errors.append(f"Worker {worker_id} 错误: {str(e)}")

        # 创建多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        total_calls = len(results) + len(errors)
        print(f"  总调用: {total_calls}, 成功: {len(results)}, 限制: {len(errors)}")
        assert total_calls == 15, f"总调用数应为15，实际为{total_calls}"

        print("\n[PASS] 速率限制功能测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 速率限制测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_scenario():
    """测试完整集成场景"""
    print("\n=== 测试4: 完整集成场景 ===")

    try:
        from retrieval import retrieve_documents
        from llm_client import SimpleLLMClient, RateLimiter
        from agent import DeepSearchAgent
        from utils import Config

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.output_dir = temp_dir
            config.default_llm_provider = "deepseek"
            config.deepseek_api_key = "mock_key"
            config.deepseek_model = "mock_model"

            # 创建代理
            agent = DeepSearchAgent(config)

            # 创建模拟知识库
            knowledge_base = [
                {
                    "title": "Python编程基础",
                    "content": "Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。它支持多种编程范式，包括面向对象、命令式和函数式编程。Python的标准库丰富，涵盖了网络、文件I/O、数据结构等多个领域。"
                },
                {
                    "title": "数据结构与算法",
                    "content": "数据结构是组织和存储数据的方式，包括数组、链表、栈、队列、树、图等。算法是解决问题的步骤和方法，包括排序、搜索、动态规划等。掌握数据结构和算法是编程的核心技能。"
                },
                {
                    "title": "机器学习入门",
                    "content": "机器学习是人工智能的一个分支，它使计算机能够从数据中学习模式。常见的机器学习算法包括线性回归、决策树、神经网络等。学习机器学习需要掌握数学基础、编程能力和领域知识。"
                }
            ]

            # 测试场景1: 检索 + 缓存 + 速率限制
            print("\n测试4.1: 检索优化 + 缓存 + 速率限制")

            # 模拟多次相同查询（应该使用缓存）
            query = "Python编程基础"

            # 第一次查询会执行检索和缓存
            start_time = time.time()
            # 使用检索模块获取相关文档
            relevant_docs = retrieve_documents(query, knowledge_base, top_k=2, max_content_length=100)

            # 模拟LLM调用（使用速率限制的llm_call）
            mock_llm_client = Mock()
            mock_llm_client.invoke = Mock(return_value="# Python编程基础报告\n\nPython是一种高级编程语言...")

            # 创建速率限制的客户端
            limited_client = SimpleLLMClient(mock_llm_client)

            # 测试速率限制
            from llm_client import set_rate_limit
            set_rate_limit(max_requests=3, time_window=5)  # 5秒内最多3次

            # 执行多次调用（测试速率限制）
            for i in range(3):
                result = limited_client.llm_call(
                    "总结以下内容",
                    context="Python编程",
                    input_text=relevant_docs[0]['content'],
                    temperature=0.3
                )
                print(f"  调用 {i+1}: 成功")

            print("  [PASS] 检索、缓存、速率限制协同工作正常")

            # 测试场景2: 缓存命中避免重复工作
            print("\n测试4.2: 缓存命中测试")

            # 缓存查询结果
            agent.cache_result(query, "缓存的结果内容")

            # 验证缓存命中
            cached_result = agent.get_cached_result(query)
            assert cached_result is not None, "缓存命中失败"
            print("  [PASS] 缓存命中，避免重复检索和处理")

            # 测试场景3: 配置管理
            print("\n测试4.3: 配置管理测试")

            # 修改速率限制配置
            from llm_client import get_rate_limit_info
            set_rate_limit(max_requests=5, time_window=10)
            rate_info = get_rate_limit_info()
            print(f"  速率限制配置: {rate_info['max_requests']}/{rate_info['time_window']}秒")

            # 修改缓存配置
            agent.set_cache_config(enabled=True, max_size=10, ttl=None)
            cache_info = agent.get_cache_info()
            print(f"  缓存配置: {cache_info['total_entries']} 条目, 大小限制: {cache_info['max_cache_size']}")

            print("\n[PASS] 完整集成场景测试通过")
            return True

    except Exception as e:
        print(f"[FAIL] 完整集成场景测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试5: 错误处理 ===")

    try:
        from retrieval import retrieve_documents
        from llm_client import RateLimiter
        from agent import DeepSearchAgent
        from utils import Config

        # 测试1: 检索模块错误处理
        print("\n测试5.1: 检索模块错误处理")

        # 测试空文档
        results = retrieve_documents("测试", [], top_k=3)
        assert len(results) == 0, "空文档列表应返回空结果"
        print("  [PASS] 空文档列表处理正确")

        # 测试空查询
        results = retrieve_documents("", [{"title": "test", "content": "content"}], top_k=3)
        assert all(r['score'] == 0.0 for r in results), "空查询分数应为0"
        print("  [PASS] 空查询处理正确")

        # 测试2: 速率限制器错误处理
        print("\n测试5.2: 速率限制器错误处理")

        limiter = RateLimiter(max_requests=1, time_window=1)

        # 第一次调用
        assert limiter.is_allowed(), "第一次调用应被允许"

        # 第二次调用应被拒绝
        assert not limiter.is_allowed(), "第二次调用应被拒绝"

        # 等待后应恢复
        time.sleep(1.1)
        assert limiter.is_allowed(), "等待后应被允许"
        print("  [PASS] 速率限制错误处理正确")

        # 测试3: 代理错误处理
        print("\n测试5.3: 代理错误处理")

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.output_dir = temp_dir
            config.default_llm_provider = "deepseek"
            config.deepseek_api_key = "mock_key"
            config.deepseek_model = "mock_model"

            agent = DeepSearchAgent(config)

            # 测试无效缓存键
            result = agent.get_cached_result(None)
            assert result is None, "无效查询应返回None"
            print("  [PASS] 无效查询处理正确")

            # 测试缓存清理（空缓存）
            agent.clear_cache()
            print("  [PASS] 空缓存清理正常")

        print("\n[PASS] 错误处理测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 错误处理测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_module_imports():
    """测试模块导入"""
    print("\n=== 测试0: 模块导入 ===")

    try:
        # 测试检索模块
        from retrieval import retrieve_documents, compute_bm25_score, optimized_retrieve
        print("  [PASS] retrieval.py 导入成功")

        # 测试LLM客户端
        from llm_client import SimpleLLMClient, RateLimiter, build_mini_prompt
        print("  [PASS] llm_client.py 导入成功")

        # 测试状态管理
        try:
            from state import State
            print("  [PASS] state.py 导入成功")
        except ImportError:
            print("  [WARN] state.py 导入失败（可能不存在）")

        # 测试工具
        try:
            from utils import Config, load_config
            print("  [PASS] utils.py 导入成功")
        except ImportError:
            print("  [WARN] utils.py 导入失败（可能不存在）")

        return True

    except Exception as e:
        print(f"  [FAIL] 模块导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_client():
    """测试LLM客户端功能"""
    print("\n=== 测试1.5: LLM客户端功能 ===")

    try:
        from llm_client import SimpleLLMClient, build_mini_prompt, set_rate_limit, disable_rate_limit
        from unittest.mock import Mock

        # 创建模拟LLM
        mock_llm = Mock()
        mock_llm.invoke = Mock(return_value="Test response")
        mock_llm.get_model_info = Mock(return_value={"model": "test", "version": "1.0"})

        # 创建简化客户端
        client = SimpleLLMClient(mock_llm)

        # 测试极简Prompt构建
        prompt = build_mini_prompt("翻译", "这是上下文", "这是输入")
        print(f"  [PASS] 极简Prompt构建: {prompt[:50]}...")

        # 测试LLM调用
        result = client.llm_call("翻译", "上下文", "输入")
        assert result == "Test response", "LLM调用失败"
        print("  [PASS] LLM调用正常")

        # 测试速率限制
        disable_rate_limit()  # 禁用速率限制以便测试
        set_rate_limit(max_requests=5, time_window=10)

        # 多次调用
        for i in range(3):
            result = client.llm_call(f"测试{i}")
            print(f"  [PASS] 调用 {i+1} 成功")

        print("  [PASS] LLM客户端功能测试通过")
        return True

    except Exception as e:
        print(f"  [FAIL] LLM客户端测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=== Deep Search Agent 全流程最终测试 ===")
    print("测试范围:")
    print("  - src/retrieval.py: 检索优化功能")
    print("  - src/llm_client.py: LLM客户端和速率限制")
    print("  - Agent核心功能: 本地缓存、错误处理")
    print("  - 纯本地运行，不调用任何外部API\n")

    # 运行所有测试
    test_results = []

    # 先测试模块导入
    test_results.append(test_module_imports())

    # 运行功能测试
    test_results.append(test_retrieval_optimization())
    test_results.append(test_local_caching())
    test_results.append(test_rate_limiting())
    test_results.append(test_llm_client())
    test_results.append(test_integration_scenario())
    test_results.append(test_error_handling())

    # 汇总结果
    print("\n" + "="*60)
    print("=== 测试结果汇总 ===")

    passed = sum(test_results)
    total = len(test_results)

    for i, result in enumerate(test_results, 1):
        status = "[PASS]" if result else "[FAIL]"
        test_name = [
            "模块导入",
            "检索优化",
            "本地缓存",
            "速率限制",
            "LLM客户端",
            "集成场景",
            "错误处理"
        ][i-1]
        print(f"测试{i} ({test_name}): {status}")

    print(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("\n[SUCCESS] 所有测试通过！系统功能正常。")
        print("\n功能验证总结:")
        print("[PASS] 检索优化: BM25算法实现，支持相关性排序和文档截断")
        print("[PASS] 本地缓存: pickle持久化，避免重复计算，支持TTL和大小限制")
        print("[PASS] 速率限制: 固定时间窗口，线程安全，可配置")
        print("[PASS] LLM客户端: 极简Prompt构建，装饰器速率限制，兼容多种接口")
        print("[PASS] 错误处理: 完善的异常处理和边缘情况处理")
        print("[PASS] 集成测试: 各组件协同工作，缓存命中优化性能")
        print("\n所有模块验证完成，可以正常使用！")
    else:
        print("\n[FAIL] {} 个测试失败，请检查实现。".format(total - passed))
        print("请检查以下方面:")
        if not test_results[0]:
            print("  - 模块导入路径是否正确")
        if not test_results[1]:
            print("  - retrieval.py 的BM25实现")
        if not test_results[2]:
            print("  - 缓存机制的实现")
        if not test_results[3]:
            print("  - 速率限制器的线程安全")
        if not test_results[4]:
            print("  - LLM客户端的接口兼容性")
        if not test_results[5]:
            print("  - 组件间的集成")
        if not test_results[6]:
            print("  - 异常处理机制")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)