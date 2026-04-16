import requests
import re
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
                # 过滤非期刊文章（可选，如需保留注释掉）
                # if item.get("type") != "journal-article":
                #     continue
                
                # 修复：重复赋值title的问题
                title = item.get("title", [""])[0]
                if title:
                    title = re.sub(r'<.*?>', '', title)  # 去除所有 HTML 标签
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
                
                # 作者（取前3位）
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
                
                # 摘要（去除HTML标签，截断600字符）
                abstract = item.get("abstract", "")
                if abstract:
                    abstract = re.sub(r'<.*?>', '', abstract).strip()[:600]
                
                # 新增：提取样本量（Crossref 不一定有，需根据实际字段调整）
                sample_size = 0
                # 尝试从摘要/标题中提取数字（示例逻辑，可根据需求优化）
                if abstract:
                    sample_size_match = re.search(r'sample size (\d+)', abstract.lower())
                    if sample_size_match:
                        sample_size = int(sample_size_match.group(1))
                
                papers.append({
                    "title": title,
                    "authors": author_str,
                    "year": year,
                    "journal": journal,
                    "doi": doi,
                    "abstract": abstract,
                    "sample_size": sample_size,  # 新增字段
                    "relevance_score": item.get("score", 0) / 100  # 归一化到 0-1
                })
            return papers
        except Exception as e:
            print(f"Crossref 请求异常: {e}")
            return []