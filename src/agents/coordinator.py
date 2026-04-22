from .query_analyzer_agent import QueryAnalyzerAgent
from .search_agent import SearchAgent
from .evidence_agent import EvidenceAgent
from .summary_agent import SummaryAgent
from src.nodes.reflection_supplement_node import ReflectionSupplementNode
from src.llms.zhipu import ZhipuLLM
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from src.utils.cache import QueryCache
from src.utils.evidence import get_evidence_level, get_evidence_priority
from typing import Dict, Any, List, Tuple, Optional
import hashlib
import pickle
import os
from datetime import datetime

class AcademicCoordinator:
    def __init__(self, llm: ZhipuLLM, crossref_search: CrossrefSearch, openalex_search: OpenAlexSearch):
        self.query_analyzer = QueryAnalyzerAgent("QueryAnalyzer", llm)
        self.search_agent = SearchAgent("SearchAgent", crossref_search, openalex_search)
        self.evidence_agent = EvidenceAgent("EvidenceAgent", llm)
        self.summary_agent = SummaryAgent("SummaryAgent", llm)
        self.reflection_supplement_node = ReflectionSupplementNode(llm)
        self.cache = QueryCache()

        # 缓存配置
        self.enable_cache = True
        self.cache_ttl = 24 * 3600  # 24小时过期
        self.max_cache_size = 1000
        self.cache_file = "academic_cache.pkl"
        self.query_cache = {}

        # 加载现有缓存
        self._load_query_cache()

    def _generate_cache_key(self, query: str) -> str:
        """生成查询的唯一缓存键"""
        if query is None:
            query = ""
        query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()
        return f"academic_{query_hash}"

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存条目是否有效"""
        if self.cache_ttl and 'timestamp' in cache_entry:
            cache_time = datetime.fromisoformat(cache_entry['timestamp'])
            elapsed = (datetime.now() - cache_time).total_seconds()
            return elapsed < self.cache_ttl
        return True

    def _load_query_cache(self):
        """从本地文件加载查询缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    self.query_cache = pickle.load(f)
                print(f"已加载 {len(self.query_cache)} 条学术模式查询缓存")
            else:
                print("未找到学术模式缓存文件，将创建新的缓存")
                self.query_cache = {}
        except Exception as e:
            print(f"加载学术模式查询缓存失败: {str(e)}")
            self.query_cache = {}

    def _save_query_cache(self):
        """保存查询缓存到本地文件"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            if len(self.query_cache) > self.max_cache_size:
                sorted_items = sorted(
                    self.query_cache.items(),
                    key=lambda x: x[1].get('timestamp', '1970-01-01T00:00:00')
                )
                items_to_remove = len(self.query_cache) - self.max_cache_size
                for key, _ in sorted_items[:items_to_remove]:
                    del self.query_cache[key]
                print(f"学术模式缓存清理：删除了 {items_to_remove} 条旧记录")

            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.query_cache, f)
        except Exception as e:
            print(f"保存学术模式查询缓存失败: {str(e)}")

    def get_cached_result(self, query: str) -> Optional[tuple]:
        """从缓存中获取学术研究结果"""
        if not self.enable_cache:
            return None

        cache_key = self._generate_cache_key(query)
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if self._is_cache_valid(cache_entry) and 'result' in cache_entry:
                print(f"⚡ 学术模式缓存命中: {query[:30]}..." if len(query) > 30 else f"⚡ 学术模式缓存命中: {query}")
                return cache_entry['result']
        return None

    def cache_result(self, query: str, result: tuple):
        """将学术研究结果存入缓存"""
        try:
            if not self.enable_cache:
                return

            cache_key = self._generate_cache_key(query)
            self.query_cache[cache_key] = {
                'result': result,
                'timestamp': datetime.now().isoformat(),
                'query': query
            }

            self._save_query_cache()
            print(f"✅ 学术模式结果已缓存: {query[:30]}..." if len(query) > 30 else f"✅ 学术模式结果已缓存: {query}")
        except Exception as e:
            print(f"学术模式缓存结果时发生错误: {str(e)}")

    def clear_cache(self):
        """清空所有学术模式缓存"""
        try:
            self.query_cache = {}
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            print("学术模式查询缓存已清空")
        except Exception as e:
            print(f"清空学术模式缓存失败: {str(e)}")

    def get_cache_info(self) -> Dict[str, Any]:
        """获取学术模式缓存信息"""
        valid_entries = 0
        invalid_entries = 0

        for cache_entry in self.query_cache.values():
            if self._is_cache_valid(cache_entry):
                valid_entries += 1
            else:
                invalid_entries += 1

        return {
            'total_entries': len(self.query_cache),
            'valid_entries': valid_entries,
            'invalid_entries': invalid_entries,
            'cache_file': self.cache_file,
            'cache_enabled': self.enable_cache,
            'cache_exists': os.path.exists(self.cache_file),
            'max_cache_size': self.max_cache_size,
            'cache_ttl': self.cache_ttl
        }

    def set_cache_config(self, enabled: bool = True, ttl: Optional[int] = None, max_size: int = 1000):
        """设置学术模式缓存配置"""
        self.enable_cache = enabled
        self.cache_ttl = ttl
        self.max_cache_size = max_size

        if ttl:
            print(f"学术模式缓存配置：启用={enabled}, TTL={ttl}秒, 最大条目={max_size}")
        else:
            print(f"学术模式缓存配置：启用={enabled}, TTL=永不过期, 最大条目={max_size}")

    def list_cached_queries(self, limit: int = 10) -> List[str]:
        """列出学术模式缓存的查询"""
        queries = []
        count = 0

        for cache_entry in self.query_cache.values():
            if 'query' in cache_entry and count < limit:
                query = cache_entry['query']
                display_query = query[:50] + "..." if len(query) > 50 else query
                queries.append(display_query)
                count += 1

        return queries

    def has_cached_result(self, query: str) -> bool:
        """检查学术模式查询是否在缓存中"""
        if not self.enable_cache:
            return False

        cache_key = self._generate_cache_key(query)
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            return self._is_cache_valid(cache_entry) and 'result' in cache_entry

        return False

    def process(self, query: str) -> tuple:
        # 生成缓存键
        cache_key = self._generate_cache_key(query)

        # 1. 检查缓存
        cached_result = self.get_cached_result(query)
        if cached_result is not None:
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
                # 添加证据等级（解构元组）
                level, details = get_evidence_level(paper)
                paper['evidence_level'] = level.value  # 存储字符串
                paper['grade_details'] = details
                # 添加证据片段（从论文标题和摘要中提取）
                snippets = []
                if paper.get('title'):
                    snippets.append(paper['title'])
                if paper.get('abstract'):
                    # 从摘要中提取前100个字符作为证据片段
                    abstract_snippet = paper['abstract'][:100] + ('...' if len(paper['abstract']) > 100 else '')
                    snippets.append(abstract_snippet)
                paper['evidence_snippets'] = snippets if snippets else ["无可用证据片段"]
                # 添加证据优先级（用于排序）
                paper['evidence_priority'] = get_evidence_priority(level)
                # 添加发表年份（如果缺失）
                if 'year' not in paper or not paper['year']:
                    paper['year'] = 0

            # 6. 按证据等级优先级+发表年份降序排序
            sorted_papers = sorted(
                unique_papers,
                key=lambda x: (x.get('evidence_priority', 0), x.get('year', 0)),
                reverse=True
            )

            # 7. 反思补充检索（节点4.5）
            supplement_result = self.reflection_supplement_node.process({
                'query': query,
                'papers': sorted_papers
            })

            if supplement_result['status'] == 'success':
                sorted_papers = supplement_result['papers']
                print(f"📊 补充检索统计:")
                print(f"   前后文献数量: {supplement_result['comparison']['before']} → {supplement_result['comparison']['after']}")
                if supplement_result['comparison']['increase'] > 0:
                    print(f"   新增文献: {supplement_result['comparison']['increase']} 篇")
            else:
                print("⚠️ 反思补充检索失败，跳过此步骤")

            # 8. 证据分析
            evidence_result = self.evidence_agent.process({'papers': sorted_papers})
            if evidence_result['status'] != 'success':
                error_result = ("证据分析失败", [])
                self.cache.set(cache_key, error_result)
                return error_result

            # 9. 总结
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
            self.cache_result(query, final_result)

            return final_result

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_result = (f"⚠️ 处理过程中发生错误：{str(e)}。请稍后重试或尝试其他查询。", [])
            self.cache.set(cache_key, error_result)
            return error_result