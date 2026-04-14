"""
OpenAlex 学术搜索（完全免费，无需代理，国内可用）
API 文档：https://docs.openalex.org/
"""

import requests
import time
from typing import List, Dict


class OpenAlexSearch:
    BASE_URL = "https://api.openalex.org/works"

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        根据关键词搜索论文
        :param query: 英文关键词（例如 "hypertension treatment"）
        :param max_results: 最大返回数量
        :return: 论文列表，每篇包含 title, authors, year, journal, abstract, doi
        """
        params = {
            "search": query,
            "per-page": max_results,
            #"sort": "relevance_score",
            #"select": "title,publication_date,authorships,primary_location,abstract,doi"
        }

        max_retries = 2
        timeout = 30  # 增加超时时间到30秒

        for attempt in range(max_retries):
            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=timeout)
                if resp.status_code != 200:
                    print(f"OpenAlex 请求失败: {resp.status_code}")
                    if attempt == max_retries - 1:
                        return []
                    continue
                data = resp.json()
                break
            except requests.Timeout:
                print(f"OpenAlex 请求超时 (尝试 {attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    return []
                time.sleep(attempt + 1)
            except Exception as e:
                print(f"OpenAlex 请求异常: {e}")
                if attempt == max_retries - 1:
                    return []
                time.sleep(1)

        papers = []
        for item in data.get("results", []):
            # 提取年份
            pub_date = item.get("publication_date", "")
            year = 0
            if pub_date and len(pub_date) >= 4 and pub_date[:4].isdigit():
                year = int(pub_date[:4])

            # 提取作者（最多显示3个）
            authors = []
            for auth in item.get("authorships", []):
                author = auth.get("author", {})
                name = author.get("display_name", "")
                if name:
                    authors.append(name)
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."

            # 提取期刊名
            primary_location = item.get("primary_location")
            if primary_location:
                source = primary_location.get("source")
                journal = source.get("display_name", "无期刊") if source else "无期刊"
            else:
                journal = "无期刊"

            # 摘要
            abstract = item.get("abstract", "")
            if not abstract:
                abstract = "无摘要"

            # DOI
            doi_raw = item.get("doi")
            doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""

            papers.append({
                "title": item.get("title", "无标题"),
                "authors": author_str or "无作者",
                "year": year,
                "journal": journal,
                "abstract": abstract[:600],
                "doi": doi,
                "relevance_score": item.get("relevance_score", 0)
            })

        return papers