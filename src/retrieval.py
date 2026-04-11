"""
文档检索模块
支持BM25粗筛和精筛功能
"""

from typing import List, Dict, Any, Optional
import math
from collections import Counter


def compute_bm25_score(query: str, document: str, k1: float = 1.2, b: float = 0.75) -> float:
    """
    计算BM25相关性分数

    Args:
        query: 查询字符串
        document: 文档字符串
        k1: BM25参数k1
        b: BM25参数b

    Returns:
        BM25分数
    """
    # 处理None值和非字符串类型
    if query is None:
        query = ""
    if document is None:
        document = ""

    if not query or not document:
        return 0.0

    # 处理非字符串类型
    query = str(query)
    document = str(document)

    # 分词
    query_terms = query.lower().split()
    doc_terms = document.lower().split()

    if not query_terms:
        return 0.0

    # 计算文档长度
    doc_length = len(doc_terms)
    avg_length = doc_length  # 这里使用文档自身长度作为平均长度

    # 计算词频
    term_freq = Counter(doc_terms)

    # 计算BM25分数
    score = 0.0
    for term in query_terms:
        if term in term_freq:
            tf = term_freq[term]
            idf = math.log((doc_length + 1) / (1 + doc_length)) + 1  # 简化的IDF计算

            # BM25公式
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_length / avg_length))
            score += (numerator / denominator) * idf

    return score


def optimized_retrieve(query: str, documents: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """
    优化的文档检索函数
    使用BM25进行粗筛，然后选择Top K个最相关的文档

    Args:
        query: 查询字符串
        documents: 文档列表，每个文档是包含'title'和'content'的字典
        top_k: 返回的文档数量

    Returns:
        最相关的文档列表，包含相关性分数
    """
    if not documents:
        return []

    # 计算每个文档的相关性分数
    scored_docs = []
    for doc in documents:
        if 'title' not in doc or 'content' not in doc:
            continue

        # 组合标题和内容作为搜索文本
        search_text = f"{doc['title']} {doc['content']}"
        score = compute_bm25_score(query, search_text)

        # 保留原始文档并添加分数
        doc_with_score = doc.copy()
        doc_with_score['score'] = score
        scored_docs.append(doc_with_score)

    # 按分数降序排序
    scored_docs.sort(key=lambda x: x.get('score', 0), reverse=True)

    # 返回Top K个文档
    return scored_docs[:top_k]


def truncate_long_doc(text: str, max_length: int = 200) -> str:
    """
    截断长文档到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    # 处理None值
    if text is None:
        text = ""

    # 处理非字符串类型
    if not isinstance(text, str):
        text = str(text)

    if len(text) <= max_length:
        return text

    # 处理极小长度情况
    if max_length <= 3:
        return text[:max_length]

    # 截断并添加省略号
    return text[:max_length - 3] + "..."


def retrieve_documents(query: str, documents: List[Dict[str, Any]], top_k: int = 3,
                      max_content_length: int = 200) -> List[Dict[str, Any]]:
    """
    原有检索函数，保持兼容性
    调用新函数实现优化检索和文档截断

    Args:
        query: 查询字符串
        documents: 文档列表
        top_k: 返回的文档数量
        max_content_length: 最大内容长度

    Returns:
        检索结果列表
    """
    # 使用优化检索
    retrieved_docs = optimized_retrieve(query, documents, top_k)

    # 对文档内容进行截断
    for doc in retrieved_docs:
        if 'content' in doc:
            if max_content_length <= 0:
                # 完全截断
                doc['content'] = "..."
            elif len(doc['content']) > max_content_length:
                doc['content'] = truncate_long_doc(doc['content'], max_content_length)

    return retrieved_docs


# 示例测试函数
def test_retrieval():
    """测试检索功能"""
    # 示例文档
    documents = [
        {
            "title": "人工智能发展史",
            "content": "人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。从1950年代的图灵测试开始，人工智能经历了多个发展阶段，包括符号主义、连接主义和深度学习时代。近年来，随着计算能力的提升和大数据的积累，深度学习技术取得了突破性进展。"
        },
        {
            "title": "机器学习算法",
            "content": "机器学习是人工智能的核心技术之一，主要包括监督学习、无监督学习和强化学习三大类。监督学习通过标记数据训练模型，常见算法包括线性回归、决策树、支持向量机等。无监督学习从无标记数据中发现模式，典型应用包括聚类分析和降维。强化学习通过试错学习最优策略，广泛应用于游戏AI和机器人控制。"
        },
        {
            "title": "自然语言处理技术",
            "content": "自然语言处理（NLP）是AI的重要应用领域，涉及计算机对人类语言的理解和生成。现代NLP技术主要基于Transformer架构，如BERT、GPT等预训练模型。这些模型通过大规模语料库训练，能够实现文本分类、情感分析、机器翻译、问答系统等多种任务。NLP技术在搜索引擎、智能助手、自动翻译等领域有广泛应用。"
        },
        {
            "title": "计算机视觉应用",
            "content": "计算机视觉是AI的另一个重要分支，致力于让计算机能够理解和解释视觉信息。从早期的图像识别到现代的目标检测、图像分割，计算机视觉技术不断发展。卷积神经网络（CNN）是计算机视觉的核心技术，在图像分类、物体检测、人脸识别等任务中表现出色。自动驾驶、医疗影像分析、安防监控等领域都广泛应用计算机视觉技术。"
        }
    ]

    print("=== 测试文档检索功能 ===")

    # 测试查询
    test_queries = [
        "机器学习算法",
        "深度学习进展",
        "人工智能应用"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 50)

        # 使用优化检索
        results = retrieve_documents(query, documents, top_k=3, max_content_length=100)

        if results:
            for i, result in enumerate(results, 1):
                print(f"\n结果 {i}:")
                print(f"标题: {result['title']}")
                print(f"内容: {result['content']}")
                print(f"相关度分数: {result['score']:.4f}")
        else:
            print("未找到相关文档")


if __name__ == "__main__":
    test_retrieval()