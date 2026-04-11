"""
最小测试代码 - 只测试检索和agent流程，不调用API
使用mock替代所有外部依赖
"""

import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


# ==================== Mock类 ====================

class MockLLMClient:
    """Mock LLM客户端，不调用任何API"""

    def __init__(self):
        self.call_count = 0

    def generate_json(self, system_prompt="", user_prompt="", **kwargs):
        """模拟JSON生成"""
        self.call_count += 1
        print(f"    [Mock LLM] 调用 #{self.call_count}: {user_prompt[:50]}...")

        # 根据prompt返回不同的模拟结果
        if "搜索词" in user_prompt:
            return {"keywords": ["关键词1", "关键词2", "关键词3"]}
        elif "报告结构" in user_prompt or "outline" in user_prompt.lower():
            return {
                "title": "测试报告标题",
                "sections": [
                    {"title": "背景介绍", "description": "背景说明"},
                    {"title": "核心分析", "description": "核心分析内容"},
                    {"title": "结论建议", "description": "总结和建议"}
                ]
            }
        elif "搜索查询" in user_prompt or "search query" in user_prompt.lower():
            return {
                "search_query": "模拟搜索查询",
                "reasoning": "模拟推理过程"
            }
        else:
            return {"result": "模拟结果"}

    def invoke(self, system_prompt="", user_prompt="", **kwargs):
        """模拟普通调用"""
        self.call_count += 1
        return "模拟LLM回复"

    def get_model_info(self):
        return "Mock LLM Model"


class MockTavilySearch:
    """Mock搜索工具，不调用Tavily API"""

    def __init__(self):
        self.search_count = 0

    def search(self, query, max_results=5, timeout=30, api_key=None):
        """模拟搜索"""
        self.search_count += 1
        print(f"    [Mock Search] 调用 #{self.search_count}: {query}")

        return [
            {
                "title": f"模拟搜索结果 {i+1} - {query}",
                "url": f"https://example.com/result{i+1}",
                "content": f"这是关于 {query} 的模拟内容 {i+1}。" * 10,
                "score": 0.9 - i * 0.1
            }
            for i in range(max_results)
        ]


# ==================== 检索模块测试 ====================

def test_retrieval():
    """测试检索模块的BM25功能"""
    print("\n" + "="*60)
    print("【测试1】检索模块 (BM25)")
    print("="*60)

    from retrieval import compute_bm25_score, retrieve_documents

    # 准备测试文档
    documents = [
        {
            "title": "人工智能基础",
            "content": "人工智能是计算机科学的一个分支，致力于创建能够执行需要人类智能任务的系统。"
        },
        {
            "title": "机器学习入门",
            "content": "机器学习是人工智能的核心技术，通过数据训练模型来做出预测或决策。"
        },
        {
            "title": "深度学习应用",
            "content": "深度学习是机器学习的一个子集，使用神经网络来模拟人脑的学习过程。"
        }
    ]

    # 测试BM25分数计算
    print("\n1. BM25分数计算:")
    score = compute_bm25_score("机器学习", documents[1]["content"])
    print(f"   查询: '机器学习' 对文档 '{documents[1]['title']}' 的分数: {score:.4f}")

    # 测试文档检索
    print("\n2. 文档检索:")
    query = "人工智能"
    results = retrieve_documents(query, documents, top_k=2, max_content_length=50)

    for i, result in enumerate(results, 1):
        print(f"   结果{i}: {result['title']} (分数: {result['score']:.4f})")
        print(f"   内容: {result['content'][:50]}...")

    print("\n[OK] 检索模块测试完成")


# ==================== 状态模块测试 ====================

def test_state():
    """测试状态管理模块"""
    print("\n" + "="*60)
    print("【测试2】状态管理")
    print("="*60)

    from state.state import State, Paragraph, Research, Search

    # 创建状态
    state = State(query="测试查询", report_title="测试报告")

    # 添加段落
    state.add_paragraph("段落1", "段落1的初始内容")
    state.add_paragraph("段落2", "段落2的初始内容")

    print(f"\n1. 状态初始化:")
    print(f"   查询: {state.query}")
    print(f"   报告标题: {state.report_title}")
    print(f"   段落数: {len(state.paragraphs)}")

    # 添加搜索结果
    search1 = Search(
        query="测试搜索",
        url="https://test.com",
        title="测试标题",
        content="测试内容",
        score=0.9
    )

    paragraph = state.get_paragraph(0)
    paragraph.research.add_search(search1)
    paragraph.research.latest_summary = "这是第一个段落的总结"

    print(f"\n2. 段落研究状态:")
    print(f"   搜索次数: {paragraph.research.get_search_count()}")
    print(f"   最新总结: {paragraph.research.latest_summary[:30]}...")

    # 获取进度摘要
    progress = state.get_progress_summary()
    print(f"\n3. 进度摘要:")
    print(f"   总段落: {progress['total_paragraphs']}")
    print(f"   已完成: {progress['completed_paragraphs']}")
    print(f"   进度: {progress['progress_percentage']:.1f}%")

    print("\n[OK] 状态管理测试完成")


# ==================== Agent流程测试 ====================

def test_agent_flow():
    """测试Agent的完整流程（使用mock）"""
    print("\n" + "="*60)
    print("【测试3】Agent流程 (全Mock)")
    print("="*60)

    # 创建mock实例
    mock_llm = MockLLMClient()
    mock_search = MockTavilySearch()

    print("\n1. 初始化Agent组件...")

    # 手动创建State
    from state.state import State

    state = State(query="测试查询", report_title="测试报告")
    state.add_paragraph("背景介绍", "背景说明")
    state.add_paragraph("核心分析", "核心分析内容")
    state.add_paragraph("结论建议", "总结和建议")

    print(f"   初始化了 {len(state.paragraphs)} 个段落")

    # 模拟处理段落
    print("\n2. 处理段落流程:")

    for i, paragraph in enumerate(state.paragraphs):
        print(f"\n   --- 段落 {i+1}: {paragraph.title} ---")

        # 模拟生成搜索查询
        search_output = mock_llm.generate_json(
            user_prompt=f"为段落 '{paragraph.title}' 生成搜索查询"
        )
        search_query = search_output.get("search_query", "默认查询")

        # 模拟搜索
        search_results = mock_search.search(search_query, max_results=2)

        # 模拟生成总结
        summary_input = {
            "title": paragraph.title,
            "content": paragraph.content,
            "search_results": search_results
        }
        mock_llm.generate_json(user_prompt="生成总结")

        # 更新状态
        paragraph.research.add_search_results(search_query, search_results)
        paragraph.research.latest_summary = f"这是关于{paragraph.title}的总结，基于{len(search_results)}个搜索结果。"
        paragraph.research.mark_completed()

        print(f"   段落处理完成")

    # 生成最终报告
    print("\n3. 生成最终报告:")

    report_sections = []
    for para in state.paragraphs:
        report_sections.append(f"## {para.title}\n\n{para.research.latest_summary}\n")

    final_report = f"# {state.report_title}\n\n" + "\n".join(report_sections)
    state.final_report = final_report
    state.mark_completed()

    print("\n" + "-"*60)
    print("最终报告预览:")
    print("-"*60)
    print(final_report[:200] + "...")
    print("-"*60)

    # 统计信息
    print(f"\n4. 执行统计:")
    print(f"   LLM调用次数: {mock_llm.call_count}")
    print(f"   搜索次数: {mock_search.search_count}")
    print(f"   完成段落数: {state.get_completed_paragraphs_count()}/{state.get_total_paragraphs_count()}")

    print("\n[OK] Agent流程测试完成")


# ==================== 节点流程测试 ====================

def test_node_flow():
    """测试节点的独立流程"""
    print("\n" + "="*60)
    print("【测试4】节点流程")
    print("="*60)

    # 测试各个节点类的基本功能
    from nodes.base_node import BaseNode, StateMutationNode

    # 创建一个测试节点
    class TestNode(StateMutationNode):
        def run(self, input_data, **kwargs):
            print(f"   [TestNode] 处理输入: {input_data}")
            return {"result": f"处理了: {input_data}"}

        def mutate_state(self, input_data, state, **kwargs):
            # 在状态中添加一个段落
            state.add_paragraph("测试段落", input_data)
            print(f"   [TestNode] 状态已更新，现在有 {len(state.paragraphs)} 个段落")
            return state

    from state.state import State

    state = State(query="节点测试")
    test_node = TestNode(llm_client=MockLLMClient(), node_name="TestNode")

    print("\n1. 测试run方法:")
    result = test_node.run("测试输入")
    print(f"   结果: {result}")

    print("\n2. 测试mutate_state方法:")
    state = test_node.mutate_state("段落内容", state)
    print(f"   状态中的段落数: {len(state.paragraphs)}")

    print("\n[OK] 节点流程测试完成")


# ==================== 主函数 ====================

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("最小测试套件 - 不调用API")
    print("="*60)
    print("本测试使用mock替代所有外部API调用")
    print("测试内容: 检索模块、状态管理、Agent流程、节点流程")

    try:
        test_retrieval()
        test_state()
        test_agent_flow()
        test_node_flow()

        print("\n" + "="*60)
        print("[OK] 所有测试通过！")
        print("="*60)

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
