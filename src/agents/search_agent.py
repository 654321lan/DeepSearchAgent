from .base_agent import BaseAgent
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

class SearchAgent(BaseAgent):
    def __init__(self, name: str, crossref_search: CrossrefSearch, openalex_search: OpenAlexSearch):
        super().__init__(name)
        self.crossref_search = crossref_search
        self.openalex_search = openalex_search

    def _format_keywords(self, keywords: Any) -> str:
        """格式化关键词为搜索查询字符串"""
        if isinstance(keywords, list):
            # 如果是列表，用空格连接前3个关键词
            valid_keywords = [str(k) for k in keywords if k and str(k).strip()]
            if not valid_keywords:
                return "health"
            # 只使用前3个关键词，避免查询过长
            return " ".join(valid_keywords[:3])
        elif isinstance(keywords, str):
            return keywords.strip() if keywords.strip() else "health"
        else:
            return str(keywords) if keywords else "health"

    def process(self, input_data: dict) -> dict:
        keywords = input_data.get('keywords', '')
        formatted_query = self._format_keywords(keywords)

        if not formatted_query:
            return {'papers': [], 'status': 'error', 'message': '关键词为空'}

        def search_crossref():
            try:
                return self.crossref_search.search(formatted_query, max_results=8)
            except Exception as e:
                print(f"Crossref 搜索失败: {e}")
                return []

        def search_openalex():
            try:
                return self.openalex_search.search(formatted_query, max_results=8)
            except Exception as e:
                print(f"OpenAlex 搜索失败: {e}")
                return []

        all_papers = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_crossref = executor.submit(search_crossref)
            future_openalex = executor.submit(search_openalex)
            for future in as_completed([future_crossref, future_openalex]):
                try:
                    papers = future.result()
                    if papers:
                        all_papers.extend(papers)
                except Exception as e:
                    print(f"搜索线程异常: {e}")

        return {
            'papers': all_papers,
            'status': 'success' if all_papers else 'error',
            'message': '搜索完成' if all_papers else '未找到相关论文'
        }
