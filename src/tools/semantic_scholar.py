"""
Semantic Scholar API 封装
文档：https://www.semanticscholar.org/product/api
免费：每秒 1 次请求，无需 API Key
"""

import time
import requests
from typing import List, Dict, Optional


class SemanticScholar:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 1.0  # 每秒最多1次

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def search(self, query: str, limit: int = 5, max_retries: int = 3) -> List[Dict]:
        """搜索论文，返回列表，遇到429会退避重试"""
        self._rate_limit()
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,year,authors,doi,tldr"  # 移除 venue 避免参数错误
        }

        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)  # 5, 10, 15 秒退避
                    print(f"Semantic Scholar 限流，等待 {wait} 秒后重试...")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    print(f"Semantic Scholar 请求失败: {resp.status_code}")
                    return []
                data = resp.json()
                papers = []
                for item in data.get("data", []):
                    tldr = item.get("tldr", {}).get("text", "") if item.get("tldr") else ""
                    papers.append({
                        "title": item.get("title", "无标题"),
                        "abstract": item.get("abstract", "")[:600],
                        "year": item.get("year", 0),
                        "authors": ", ".join([a.get("name", "") for a in item.get("authors", [])[:3]]) or "无作者",
                        "journal": item.get("venue", "无期刊"),
                        "doi": item.get("doi", ""),
                        "tldr": tldr,
                    })
                return papers
            except Exception as e:
                print(f"Semantic Scholar 请求异常: {e}")
                if attempt == max_retries - 1:
                    return []
                time.sleep(2)
        return []