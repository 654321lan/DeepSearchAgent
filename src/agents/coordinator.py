from .query_analyzer_agent import QueryAnalyzerAgent
from .search_agent import SearchAgent
from .evidence_agent import EvidenceAgent
from .summary_agent import SummaryAgent
from src.llms.zhipu import ZhipuLLM
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from typing import Dict, Any

class AcademicCoordinator:
    def __init__(self, llm: ZhipuLLM, crossref_search: CrossrefSearch, openalex_search: OpenAlexSearch):
        self.query_analyzer = QueryAnalyzerAgent("QueryAnalyzer", llm)
        self.search_agent = SearchAgent("SearchAgent", crossref_search, openalex_search)
        self.evidence_agent = EvidenceAgent("EvidenceAgent")
        self.summary_agent = SummaryAgent("SummaryAgent", llm)

    def process(self, query: str) -> tuple:
        # 1. 查询分析
        analysis_result = self.query_analyzer.process({'query': query})
        if analysis_result['status'] != 'success':
            return analysis_result['message'], []

        # 2. 搜索
        search_result = self.search_agent.process({'keywords': analysis_result['keywords']})
        if search_result['status'] != 'success' or not search_result['papers']:
            return "未找到相关学术论文，请尝试其他关键词。", []

        # 3. 去重（基于 DOI 或标题前50字符）
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
            return "未找到相关学术论文，请尝试其他关键词。", []

        # 4. 证据分析
        evidence_result = self.evidence_agent.process({'papers': unique_papers})
        if evidence_result['status'] != 'success':
            return "证据分析失败", []

        # 4. 总结
        summary_result = self.summary_agent.process({
            'query': query,
            'papers': evidence_result['papers']
        })
        if summary_result['status'] != 'success':
            return "总结生成失败", []

        return summary_result['summary'], summary_result['papers']