"""
反思补充检索节点（节点4.5）
在证据分级后、排序前进行反思补充检索
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
from src.llms.zhipu import ZhipuLLM
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from src.utils.evidence import get_evidence_level, get_evidence_priority


class ReflectionSupplementNode:
    """反思补充检索节点"""

    def __init__(self, llm_client: ZhipuLLM, config=None):
        self.llm = llm_client
        self.config = config
        self.crossref_search = CrossrefSearch()
        self.openalex_search = OpenAlexSearch()

        # 超时配置
        self.supplement_timeout = 15  # 15秒超时

    def generate_supplement_queries(self, query: str, papers: List[Dict[str, Any]]) -> List[str]:
        """
        基于原始查询和已有论文生成补充检索查询

        Args:
            query: 原始查询
            papers: 已有的论文列表

        Returns:
            补充查询列表
        """
        # 构建已有论文的关键词提取
        existing_keywords = set()

        # 从论文标题中提取关键词
        for paper in papers:
            title = paper.get('title', '')
            if title:
                # 简单的关键词提取（取名词短语）
                words = title.lower().split()
                for i in range(len(words)-1):
                    phrase = f"{words[i]} {words[i+1]}"
                    if len(phrase) > 3:  # 过滤过短的词组
                        existing_keywords.add(phrase)

        # 构建反思提示
        prompt = f"""基于原始查询和已有论文，生成1-3个补充检索查询。
目标是查找可能被遗漏的重要研究或不同观点。

已有论文数量: {len(papers)}
已有论文关键词: {', '.join(list(existing_keywords)[:10])}

原始查询: {query}

返回JSON格式：
{{
    "supplement_queries": ["补充查询1", "补充查询2"]
}}

要求：
1. 查询应与主题相关但视角不同
2. 避免与已有论文关键词重复
3. 每个查询控制在15字以内
4. 优先考虑关键变量、对比组或方法学差异"""

        try:
            result = self.llm.generate_json(
                system_prompt="你是一个学术研究助手，擅长设计补充检索策略。",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1000
            )

            if "supplement_queries" in result and isinstance(result["supplement_queries"], list):
                queries = result["supplement_queries"][:2]  # 最多3个查询
                return queries if queries else []

            return []

        except Exception as e:
            print(f"生成补充查询失败: {str(e)}")
            return []

    def execute_supplement_search(self, query: str, papers: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行补充检索

        Args:
            query: 原始查询
            papers: 已有论文列表

        Returns:
            (补充论文列表, 统计信息)
        """
        # 生成补充查询
        supplement_queries = self.generate_supplement_queries(query, papers)

        if not supplement_queries:
            return [], {
                "supplement_queries": [],
                "search_count": 0,
                "new_papers_count": 0,
                "original_count": len(papers),
                "status": "no_queries"
            }

        print(f"🔄 生成 {len(supplement_queries)} 个补充检索查询...")

        # 执行补充搜索
        results = []
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_to_query = {
                    executor.submit(self._search_single_query, q): q
                    for q in supplement_queries
                }

                for future in as_completed(future_to_query, timeout=self.supplement_timeout):
                    query = future_to_query[future]
                    try:
                        query_results = future.result(timeout=5)  # 单个查询5秒超时
                        if query_results:
                            results.extend(query_results)
                    except Exception as e:
                        print(f"补充查询 '{query}' 执行失败: {str(e)}")
        except Exception as e:
            print(f"补充检索超时或失败: {str(e)}")
            return [], {
                "supplement_queries": supplement_queries,
                "search_count": 0,
                "new_papers_count": 0,
                "original_count": len(papers),
                "status": "timeout"
            }

        # 过滤和去重
        new_papers = []
        seen_dois = set()
        seen_titles = set()

        for paper in results:
            # 检查DOI
            doi = paper.get('doi', '')
            if doi and doi not in seen_dois:
                seen_dois.add(doi)
                new_papers.append(paper)
                continue

            # 检查标题（前50字符）
            title = paper.get('title', '')
            if title and title[:50] not in seen_titles:
                seen_titles.add(title[:50])
                new_papers.append(paper)

        # 限制反思补充的论文数量为5篇
        new_papers = new_papers[:5]

        return new_papers, {
            "supplement_queries": supplement_queries,
            "search_count": len(results),
            "new_papers_count": len(new_papers),
            "original_count": len(papers),
            "status": "success"
        }

    def _search_single_query(self, query: str) -> List[Dict[str, Any]]:
        """
        执行单个查询

        Args:
            query: 搜索查询

        Returns:
            搜索结果列表
        """
        try:
            # 使用Crossref搜索
            crossref_results = self.crossref_search.search(query, max_results=3)

            # 使用OpenAlex搜索
            openalex_results = self.openalex_search.search(query, max_results=3)

            # 合并结果
            all_results = []

            # 处理Crossref结果
            for paper in crossref_results:
                if paper:
                    paper['source'] = 'crossref'
                    all_results.append(paper)

            # 处理OpenAlex结果
            for paper in openalex_results:
                if paper:
                    paper['source'] = 'openalex'
                    all_results.append(paper)

            return all_results

        except Exception as e:
            print(f"搜索失败: {str(e)}")
            return []

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理反思补充检索

        Args:
            data: 包含query和papers的字典

        Returns:
            处理结果
        """
        query = data.get('query', '')
        papers = data.get('papers', [])

        if not papers:
            return {
                'status': 'error',
                'message': '没有论文可用于补充检索',
                'papers': [],
                'stats': {}
            }

        print(f"\n🔄 开始反思补充检索...")
        print(f"   原始论文数量: {len(papers)}")

        # 执行补充检索
        new_papers, stats = self.execute_supplement_search(query, papers)

        # 合并论文
        all_papers = papers + new_papers

        # 为补充论文添加标记
        for paper in new_papers:
            paper['is_reflection_supplement'] = True

        # 重新为所有论文添加证据信息
        for paper in all_papers:
            if 'evidence_level' not in paper:
                level, details = get_evidence_level(paper)
                paper['evidence_level'] = level.value
                paper['grade_details'] = details
                paper['evidence_priority'] = get_evidence_priority(level)

            if 'evidence_snippets' not in paper:
                snippets = []
                if paper.get('title'):
                    snippets.append(paper['title'])
                if paper.get('abstract'):
                    abstract_snippet = paper['abstract'][:100] + ('...' if len(paper['abstract']) > 100 else '')
                    snippets.append(abstract_snippet)
                paper['evidence_snippets'] = snippets if snippets else ["无可用证据片段"]

            if 'year' not in paper or not paper['year']:
                paper['year'] = 0

        # 按证据优先级+年份排序
        sorted_papers = sorted(
            all_papers,
            key=lambda x: (x.get('evidence_priority', 0), x.get('year', 0)),
            reverse=True
        )

        print(f"✅ 补充检索完成:")
        print(f"   补充查询: {len(stats.get('supplement_queries', []))} 个")
        print(f"   新增论文: {stats.get('new_papers_count', 0)} 篇")
        print(f"   总论文数: {len(sorted_papers)} 篇 ({stats.get('original_count', 0)} → {len(sorted_papers)})")

        return {
            'status': 'success',
            'papers': sorted_papers,
            'stats': stats,
            'comparison': {
                'before': stats.get('original_count', 0),
                'after': len(sorted_papers),
                'increase': len(sorted_papers) - stats.get('original_count', 0)
            }
        }