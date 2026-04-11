#!/usr/bin/env python3
"""
src/agent.py 修改示例
展示如何在 agent.py 中使用 optimized_retrieve 替换原有检索逻辑
"""

# === 修改位置 1：_initial_search_and_summary 函数 ===
"""
原代码 (大约在第307行):
        # 执行搜索
        print("  - 执行网络搜索...")
        search_results = tavily_search(
            search_query,
            max_results=self.config.max_search_results,
            timeout=self.config.search_timeout,
            api_key=self.config.tavily_api_key
        )

        if search_results:
            print(f"  - 找到 {len(search_results)} 个搜索结果")
            for j, result in enumerate(search_results, 1):
                try:
                    print(f"    {j}. {result['title'][:50]}...")
                except UnicodeEncodeError:
                    print(f"    {j}. {result['title'][:50].encode('utf-8', 'replace').decode('utf-8')}...")
        else:
            print("  - 未找到搜索结果")

        # 更新状态中的搜索历史
        paragraph.research.add_search_results(search_query, search_results)

修改后:
        # 执行搜索
        print("  - 执行网络搜索...")
        search_results = tavily_search(
            search_query,
            max_results=self.config.max_search_results,
            timeout=self.config.search_timeout,
            api_key=self.config.tavily_api_key
        )

        if search_results:
            print(f"  - 找到 {len(search_results)} 个搜索结果")
            for j, result in enumerate(search_results, 1):
                try:
                    print(f"    {j}. {result['title'][:50]}...")
                except UnicodeEncodeError:
                    print(f"    {j}. {result['title'][:50].encode('utf-8', 'replace').decode('utf-8')}...")
        else:
            print("  - 未找到搜索结果")

        # 使用optimized_retrieve进行优化筛选
        print("  - 优化检索结果...")
        optimized_docs = optimized_retrieve(search_query, search_results, top_k=3)
        print(f"  - 筛选出 {len(optimized_docs)} 个高相关文档")

        # 更新状态中的搜索历史（使用优化后的结果）
        paragraph.research.add_search_results(search_query, optimized_docs)

"""

# === 修改位置 2：_reflection_loop 函数 ===
"""
原代码 (大约在第368行):
            # 执行反思搜索
            search_results = tavily_search(
                search_query,
                max_results=self.config.max_search_results,
                timeout=self.config.search_timeout,
                api_key=self.config.tavily_api_key
            )

            if search_results:
                print(f"    找到 {len(search_results)} 个反思搜索结果")

            # 更新搜索历史
            paragraph.research.add_search_results(search_query, search_results)

修改后:
            # 执行反思搜索
            search_results = tavily_search(
                search_query,
                max_results=self.config.max_search_results,
                timeout=self.config.search_timeout,
                api_key=self.config.tavily_api_key
            )

            if search_results:
                print(f"    找到 {len(search_results)} 个反思搜索结果")

            # 使用optimized_retrieve进行优化筛选
            print("    优化反思搜索结果...")
            optimized_docs = optimized_retrieve(search_query, search_results, top_k=3)
            print(f"    筛选出 {len(optimized_docs)} 个高相关反思文档")

            # 更新搜索历史（使用优化后的结果）
            paragraph.research.add_search_results(search_query, optimized_docs)

"""

# === 需要添加的导入语句 ===
"""
在文件顶部添加:
from .retrieval import optimized_retrieve

（应该在其他导入语句附近，比如第21行左右）
"""

# === 注意事项 ===
"""
1. 类名 DeepSearchAgent 完全不变
2. 函数名 _initial_search_and_summary 和 _reflection_loop 完全不变
3. 返回值完全不变
4. 原有逻辑完全不变，只是增加了优化筛选步骤
5. 没有删除任何代码
6. 没有新增复杂逻辑，只是调用了optimized_retrieve函数
7. 保持了向后兼容性
"""

if __name__ == "__main__":
    print("=== src/agent.py 修改示例 ===")
    print("请参考上面的修改建议来更新 agent.py 文件")
    print("主要变化:")
    print("1. 添加导入: from .retrieval import optimized_retrieve")
    print("2. 在 _initial_search_and_summary 中使用 optimized_retrieve")
    print("3. 在 _reflection_loop 中使用 optimized_retrieve")
    print("4. 保持所有原有逻辑不变")