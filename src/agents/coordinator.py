from .query_analyzer_agent import QueryAnalyzerAgent
from .search_agent import SearchAgent
from .evidence_agent import EvidenceAgent
from .summary_agent import SummaryAgent
from src.llms.zhipu import ZhipuLLM
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from src.utils.cache import QueryCache
from src.utils.evidence import get_evidence_level, get_evidence_priority
from typing import Dict, Any, List, Tuple

class AcademicCoordinator:
    def __init__(self, llm: ZhipuLLM, crossref_search: CrossrefSearch, openalex_search: OpenAlexSearch):
        self.query_analyzer = QueryAnalyzerAgent("QueryAnalyzer", llm)
        self.search_agent = SearchAgent("SearchAgent", crossref_search, openalex_search)
        self.evidence_agent = EvidenceAgent("EvidenceAgent")
        self.summary_agent = SummaryAgent("SummaryAgent", llm)
        self.cache = QueryCache()

    def process(self, query: str) -> tuple:
        # 生成缓存键
        cache_key = f"academic_{hash(query)}"

        # 1. 检查缓存
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            print("⚡ 从缓存获取学术研究结果")
            return cached_result

        try:
            # 2. 查询分析
            analysis_result = self.query_analyzer.process({'query': query})
            if analysis_result['status'] != 'success':
                error_result = (analysis_result['message'], [])
                self.cache.set(cache_key, error_result)
                return error_result

            # 3. 搜索
            search_result = self.search_agent.process({'keywords': analysis_result['keywords']})
            if search_result['status'] != 'success' or not search_result['papers']:
                error_result = ("未找到相关学术论文，请尝试其他关键词。", [])
                self.cache.set(cache_key, error_result)
                return error_result

            # 4. 去重（基于 DOI 或标题前50字符）
            seen = set()
            unique_papers = []
            for p in search_result['papers']:
                doi = p.get('doi', '')
                title = p.get('title', '')
                key = doi if doi else title[:50]
                if key and key not in seen:
                    seen.add(key)
                    unique_papers.append(p)

            if not unique_papers:
                error_result = ("未找到相关学术论文，请尝试其他关键词。", [])
                self.cache.set(cache_key, error_result)
                return error_result

            # 5. 证据分析 - 添加证据等级标注
            for paper in unique_papers:
                # 添加证据等级
                paper['evidence_level'] = get_evidence_level(paper)
                # 添加证据优先级（用于排序）
                paper['evidence_priority'] = get_evidence_priority(paper)
                # 添加发表年份（如果缺失）
                if 'year' not in paper or not paper['year']:
                    paper['year'] = 0

            # 6. 按证据等级优先级+发表年份降序排序
            sorted_papers = sorted(
                unique_papers,
                key=lambda x: (x.get('evidence_priority', 0), x.get('year', 0)),
                reverse=True
            )

            # 7. 证据分析
            evidence_result = self.evidence_agent.process({'papers': sorted_papers})
            if evidence_result['status'] != 'success':
                error_result = ("证据分析失败", [])
                self.cache.set(cache_key, error_result)
                return error_result

            # 8. 总结
            summary_result = self.summary_agent.process({
                'query': query,
                'papers': evidence_result['papers']
            })
            if summary_result['status'] != 'success':
                error_result = ("总结生成失败", [])
                self.cache.set(cache_key, error_result)
                return error_result

            # 9. 保存结果到缓存
            final_result = (summary_result['summary'], summary_result['papers'])
            self.cache.set(cache_key, final_result)
            print("✅ 学术研究结果已缓存")

            return final_result

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_result = (f"⚠️ 处理过程中发生错误：{str(e)}。请稍后重试或尝试其他查询。", [])
            self.cache.set(cache_key, error_result)
            return error_result
