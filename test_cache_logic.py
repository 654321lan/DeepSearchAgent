#!/usr/bin/env python3
"""
测试缓存的逻辑功能
不依赖整个DeepSearchAgent，只测试缓存相关的方法
"""

import sys
import os
import pickle
import tempfile
import shutil
from typing import Dict, Any, Optional

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


class MockAgent:
    """模拟Agent类，只测试缓存功能"""

    def __init__(self, output_dir: str):
        self.query_cache = {}
        self.query_cache_file = os.path.join(output_dir, "query_cache.pkl")
        self.enable_cache = True
        self.output_dir = output_dir

        # 尝试加载缓存的查询结果
        self._load_query_cache()

    def _get_cache_key(self, query: str) -> int:
        """生成缓存键"""
        return hash(query)

    def _load_query_cache(self):
        """从文件加载查询缓存"""
        try:
            if os.path.exists(self.query_cache_file):
                with open(self.query_cache_file, 'rb') as f:
                    self.query_cache = pickle.load(f)
                print(f"已加载 {len(self.query_cache)} 条查询缓存")
        except Exception as e:
            print(f"加载查询缓存失败: {str(e)}")
            self.query_cache = {}

    def _save_query_cache(self):
        """保存查询缓存到文件"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            with open(self.query_cache_file, 'wb') as f:
                pickle.dump(self.query_cache, f)
        except Exception as e:
            print(f"保存查询缓存失败: {str(e)}")

    def _get_cached_result(self, query: str) -> Optional[Dict[str, Any]]:
        """从缓存中获取查询结果"""
        # 检查是否启用缓存
        if not self.enable_cache:
            return None

        cache_key = self._get_cache_key(query)
        if cache_key in self.query_cache:
            cached_data = self.query_cache[cache_key]
            # 简单验证缓存数据格式
            if isinstance(cached_data, dict) and 'result' in cached_data:
                print(f"缓存命中: {query[:30]}...")
                return cached_data['result']
        return None

    def _cache_result(self, query: str, result: Dict[str, Any]) -> None:
        """将查询结果存入缓存"""
        try:
            cache_key = self._get_cache_key(query)
            self.query_cache[cache_key] = {
                'result': result,
                'timestamp': "2026-04-11T12:00:00"  # 模拟时间戳
            }
            # 保存到文件
            self._save_query_cache()
        except Exception as e:
            print(f"缓存结果时发生错误: {str(e)}")

    def clear_query_cache(self):
        """清空查询缓存"""
        try:
            self.query_cache = {}
            if os.path.exists(self.query_cache_file):
                os.remove(self.query_cache_file)
            print("查询缓存已清空")
        except Exception as e:
            print(f"清空缓存失败: {str(e)}")

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            "cached_queries": len(self.query_cache),
            "cache_file": self.query_cache_file,
            "cache_exists": os.path.exists(self.query_cache_file),
            "cache_enabled": self.enable_cache
        }

    def set_cache_enabled(self, enabled: bool):
        """设置是否启用缓存"""
        self.enable_cache = enabled
        print(f"缓存已{'启用' if enabled else '禁用'}")

    def show_cache_status(self):
        """显示缓存状态"""
        info = self.get_cache_info()
        print(f"缓存状态:")
        print(f"  缓存启用: {info['cache_enabled']}")
        print(f"  缓存查询数: {info['cached_queries']}")
        print(f"  缓存文件: {info['cache_file']}")
        print(f"  缓存文件存在: {info['cache_exists']}")


def test_cache_functionality():
    """测试缓存功能"""
    print("=" * 60)
    print("测试缓存功能")
    print("=" * 60)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="cache_test_")
    print(f"临时目录: {temp_dir}")

    try:
        # 创建模拟Agent
        agent = MockAgent(temp_dir)

        print("\n1. 测试首次运行（应该生成缓存）...")
        query1 = "人工智能发展史"
        result1 = {"report": "这是人工智能发展史的报告"}

        # 清除之前的缓存
        agent.clear_query_cache()

        # 模拟首次运行
        print(f"处理查询: {query1}")
        cached_result = agent._get_cached_result(query1)
        if cached_result is None:
            print("未找到缓存，执行研究...")
            agent._cache_result(query1, result1)
            print("研究结果已缓存")
        else:
            print(f"使用缓存结果: {cached_result}")

        # 检查缓存
        cache_info1 = agent.get_cache_info()
        print(f"缓存信息: {cache_info1}")

        print("\n2. 测试第二次运行相同查询（应该使用缓存）...")
        print(f"再次处理查询: {query1}")
        cached_result = agent._get_cached_result(query1)
        if cached_result is not None:
            print(f"缓存命中！使用缓存结果: {cached_result}")
        else:
            print("未找到缓存，执行研究...")

        # 验证缓存
        assert cache_info1['cached_queries'] == 1, "应该有1个缓存查询"
        print("✅ 缓存工作正常")

        print("\n3. 测试不同查询...")
        query2 = "机器学习基础"
        result2 = {"report": "这是机器学习基础的报告"}

        print(f"处理查询: {query2}")
        cached_result = agent._get_cached_result(query2)
        if cached_result is None:
            print("未找到缓存，执行研究...")
            agent._cache_result(query2, result2)
            print("研究结果已缓存")
        else:
            print(f"使用缓存结果: {cached_result}")

        cache_info2 = agent.get_cache_info()
        assert cache_info2['cached_queries'] == 2, "应该有2个缓存查询"
        print("✅ 多查询缓存正常")

        print("\n4. 测试缓存持久化...")
        # 保存当前状态
        agent._save_query_cache()

        # 创建新Agent实例
        agent2 = MockAgent(temp_dir)
        # 应该加载缓存
        assert len(agent2.query_cache) == 2, "新实例应该加载2个缓存"
        print("✅ 缓存持久化正常")

        # 测试从新实例读取缓存
        cached_result = agent2._get_cached_result(query1)
        assert cached_result is not None, "应该能够读取缓存"
        print("✅ 新实例能读取缓存")

        print("\n5. 测试缓存管理功能...")
        # 显示缓存状态
        agent.show_cache_status()

        # 禁用缓存
        agent.set_cache_enabled(False)
        cached_result = agent._get_cached_result(query1)
        assert cached_result is None, "禁用缓存后不应返回缓存结果"
        print("✅ 缓存禁用功能正常")

        # 重新启用
        agent.set_cache_enabled(True)
        cached_result = agent._get_cached_result(query1)
        assert cached_result is not None, "重新启用后应该返回缓存结果"
        print("✅ 缓存重新启用功能正常")

        print("\n6. 测试缓存清除...")
        agent.clear_query_cache()
        cache_info_after_clear = agent.get_cache_info()
        assert cache_info_after_clear['cached_queries'] == 0, "清除后缓存数应为0"
        print("✅ 缓存清除功能正常")

        print("\n7. 测试特殊字符...")
        special_query = "查询 @#$%^&*()"
        special_result = {"report": "特殊字符查询结果"}
        agent._cache_result(special_query, special_result)
        cached_result = agent._get_cached_result(special_query)
        assert cached_result is not None, "应该能够处理特殊字符"
        print("✅ 特殊字符处理正常")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")

    print("\n" + "=" * 60)
    print("所有测试通过！缓存功能正常工作")
    print("=" * 60)


def test_pickle_format():
    """测试pickle格式兼容性"""
    print("\n" + "=" * 60)
    print("测试pickle格式兼容性")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="pickle_test_")

    try:
        # 创建测试数据
        test_cache = {
            hash("查询1"): {
                "result": {"report": "报告内容"},
                "timestamp": "2026-04-11T12:00:00"
            },
            hash("查询2"): {
                "result": {"report": "另一个报告"},
                "timestamp": "2026-04-11T12:01:00"
            }
        }

        # 保存到pickle文件
        cache_file = os.path.join(temp_dir, "test_cache.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(test_cache, f)

        # 读取pickle文件
        with open(cache_file, 'rb') as f:
            loaded_cache = pickle.load(f)

        # 验证数据
        assert len(loaded_cache) == 2, "应该加载2个缓存"
        assert hash("查询1") in loaded_cache, "应该包含查询1"
        assert hash("查询2") in loaded_cache, "应该包含查询2"
        assert loaded_cache[hash("查询1")]["result"]["report"] == "报告内容", "数据应该完整"

        print("✅ pickle格式兼容性测试通过")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_cache_functionality()
    test_pickle_format()