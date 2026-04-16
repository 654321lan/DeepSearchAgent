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

    def process(self, input_data: dict) -> dict:
        keywords = input_data.get('keywords', '')
        if not keywords:
            return {'papers': [], 'status': 'error', 'message': '关键词为空'}

        def search_crossref():
            try:
                return self.crossref_search.search(keywords, max_results=8)
            except Exception as e:
                print(f"Crossref 搜索失败: {e}")
                return []

        def search_openalex():
            try:
                return self.openalex_search.search(keywords, max_results=8)
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