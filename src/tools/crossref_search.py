import requests
from typing import List, Dict

class CrossrefSearch:
    BASE_URL = "https://api.crossref.org/works"

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        params = {
            "query": query,
            "rows": max_results,
            "sort": "relevance",
            "order": "desc"
        }
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"Crossref 请求失败: {resp.status_code}")
                return []
            data = resp.json()
            items = data.get("message", {}).get("items", [])
            papers = []
            for item in items:
                # 过滤非期刊文章（可选）
                # if item.get("type") != "journal-article":
                #     continue
                title = item.get("title", [""])[0]
                if not title:
                    continue
                # 提取年份
                year = 0
                issued = item.get("issued", {})
                date_parts = issued.get("date-parts", [[]])
                if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                    try:
                        year = int(date_parts[0][0])
                    except (ValueError, TypeError):
                        year = 0
                # 作者
                authors = []
                for author in item.get("author", [])[:3]:
                    given = author.get("given", "")
                    family = author.get("family", "")
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)
                author_str = ", ".join(authors) if authors else "无作者"
                # 期刊
                journal = item.get("container-title", [""])[0]
                # DOI
                doi = item.get("DOI", "")
                # 摘要（可能为 HTML）
                abstract = item.get("abstract", "")
                if abstract:
                    # 简单去除 HTML 标签
                    import re
                    abstract = re.sub(r'<.*?>', '', abstract).strip()
                papers.append({
                    "title": title,
                    "authors": author_str,
                    "year": year,
                    "journal": journal,
                    "doi": doi,
                    "abstract": abstract[:600],
                    "relevance_score": item.get("score", 0) / 100  # 归一化到 0-1
                })
            return papers
        except Exception as e:
            print(f"Crossref 请求异常: {e}")
            return []