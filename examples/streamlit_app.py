"""
Streamlit Web界面
为Deep Search Agent提供友好的Web界面
"""

import os
import sys
import logging
import streamlit as st
from datetime import datetime
import json
import hashlib
import pickle
from typing import Dict, Any, Optional
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import DeepSearchAgent, Config
from src.utils import load_config


class NodeStatus(Enum):
    """执行节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class LocalFileCache:
    """本地文件缓存 - 用于学术模式节点缓存"""

    def __init__(self, cache_dir: str = "streamlit_reports"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _generate_cache_key(self, query: str, node_id: int) -> str:
        """生成缓存键：使用query哈希+节点ID"""
        if query is None:
            query = ""
        query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()[:16]
        return f"node_{node_id}_{query_hash}"

    def _get_cache_file_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")

    def get(self, query: str, node_id: int) -> Optional[Dict[str, Any]]:
        """从缓存读取数据"""
        try:
            cache_key = self._generate_cache_key(query, node_id)
            cache_file = self._get_cache_file_path(cache_key)

            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    # 检查缓存是否有效（24小时）
                    from datetime import datetime, timedelta
                    cache_time = datetime.fromisoformat(cached_data.get('timestamp', '1970-01-01T00:00:00'))
                    if datetime.now() - cache_time < timedelta(hours=24):
                        logger.info(f"✅ 缓存命中: 节点{node_id}, query={query[:30]}...")
                        return cached_data.get('data')
                    else:
                        logger.info(f"⏰ 缓存已过期: 节点{node_id}")
            return None
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            return None

    def set(self, query: str, node_id: int, data: Dict[str, Any]):
        """保存数据到缓存"""
        try:
            cache_key = self._generate_cache_key(query, node_id)
            cache_file = self._get_cache_file_path(cache_key)

            cached_data = {
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'node_id': node_id
            }

            with open(cache_file, 'wb') as f:
                pickle.dump(cached_data, f)

            logger.info(f"💾 缓存已保存: 节点{node_id}, query={query[:30]}...")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def clear(self, query: str = None, node_id: int = None):
        """清空缓存"""
        try:
            if query is None and node_id is None:
                # 清空所有缓存
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.pkl'):
                        os.remove(os.path.join(self.cache_dir, filename))
                logger.info("🗑️ 已清空所有缓存")
            else:
                # 清空指定缓存
                cache_key = self._generate_cache_key(query, node_id)
                cache_file = self._get_cache_file_path(cache_key)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    logger.info(f"🗑️ 已清空缓存: 节点{node_id}")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

    def list_cache_info(self) -> Dict[str, Any]:
        """列出缓存信息"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            cache_info = []
            from datetime import datetime, timedelta
            now = datetime.now()

            for filename in cache_files:
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'rb') as f:
                        cached_data = pickle.load(f)
                        cache_time = datetime.fromisoformat(cached_data.get('timestamp', '1970-01-01T00:00:00'))
                        is_valid = now - cache_time < timedelta(hours=24)

                        cache_info.append({
                            'filename': filename,
                            'node_id': cached_data.get('node_id'),
                            'query': cached_data.get('query', '')[:50],
                            'timestamp': cached_data.get('timestamp'),
                            'is_valid': is_valid
                        })
                except:
                    pass

            return {
                'total_files': len(cache_files),
                'cache_dir': self.cache_dir,
                'caches': cache_info
            }
        except Exception as e:
            logger.error(f"列出缓存信息失败: {e}")
            return {'total_files': 0, 'cache_dir': self.cache_dir, 'caches': []}


class StreamlitUIOrchestrator:
    """Streamlit UI编排器 - 负责分步执行流程管理"""

    # 7个执行节点定义
    NODES = [
        {"id": 1, "name": "问题拆解与关键词生成", "key": "decompose"},
        {"id": 2, "name": "多源并发检索", "key": "search"},
        {"id": 3, "name": "数据去重与融合", "key": "deduplicate"},
        {"id": 4, "name": "证据等级标注", "key": "evidence"},
        {"id": 5, "name": "文献筛选与排序", "key": "filter"},
        {"id": 6, "name": "结论提取与生成", "key": "conclude"},
        {"id": 7, "name": "报告生成与导出", "key": "report"},
    ]

    def __init__(self, config: Config):
        """初始化编排器"""
        self.config = config
        self.agent = DeepSearchAgent(config)
        self.query = ""
        self.mode = "general"  # general 或 academic
        self.current_node = 0
        self.node_status = {node["id"]: NodeStatus.PENDING for node in self.NODES}
        self.node_results = {}
        self.node_errors = {}
        self.auto_execute = False  # 修改为默认不自动执行，保持手动点击
        self.cache = LocalFileCache()  # 本地文件缓存

        # 初始化会话状态
        self._init_session_state()

    def _init_session_state(self):
        """初始化Streamlit会话状态"""
        if "orchestrator_state" not in st.session_state:
            st.session_state.orchestrator_state = {
                "query": "",
                "mode": "general",
                "current_node": 0,
                "node_status": {node["id"]: NodeStatus.PENDING.value for node in self.NODES},
                "node_results": {},
                "node_errors": {},
                "agent_state": None,
                "final_report": "",
                "papers": [],
            }

    def _load_state(self):
        """从会话状态加载"""
        state = st.session_state.orchestrator_state
        self.query = state.get("query", "")
        self.mode = state.get("mode", "general")
        self.current_node = state.get("current_node", 0)
        self.node_status = {k: NodeStatus(v) for k, v in state.get("node_status", {}).items()}
        self.node_results = state.get("node_results", {})
        self.node_errors = state.get("node_errors", {})

        # 恢复agent状态
        if state.get("agent_state"):
            self.agent.state = state["agent_state"]

    def _save_state(self):
        """保存到会话状态"""
        st.session_state.orchestrator_state = {
            "query": self.query,
            "mode": self.mode,
            "current_node": self.current_node,
            "node_status": {k: v.value for k, v in self.node_status.items()},
            "node_results": self.node_results,
            "node_errors": self.node_errors,
            "agent_state": self.agent.state,
            "final_report": self.node_results.get(7, {}).get("report", ""),
            "papers": self.node_results.get(7, {}).get("papers", []),
        }

    def reset(self):
        """重置状态"""
        self.query = ""
        self.mode = "general"
        self.current_node = 0
        self.node_status = {node["id"]: NodeStatus.PENDING for node in self.NODES}
        self.node_results = {}
        self.node_errors = {}
        self.auto_execute = True
        self.agent.state = type(self.agent.state)()
        self._save_state()

    def set_query(self, query: str, mode: str = "general"):
        """设置查询和模式"""
        self.query = query
        self.mode = mode
        self.agent.state.query = query
        self._save_state()

    def execute_node(self, node_id: int) -> bool:
        """执行指定节点，成功后自动执行下一个节点"""
        try:
            self.node_status[node_id] = NodeStatus.RUNNING
            self._save_state()

            # 根据节点ID执行对应的逻辑
            if node_id == 1:
                self._execute_node1_decompose()
            elif node_id == 2:
                self._execute_node2_search()
            elif node_id == 3:
                self._execute_node3_deduplicate()
            elif node_id == 4:
                self._execute_node4_evidence()
            elif node_id == 5:
                self._execute_node5_filter()
            elif node_id == 6:
                self._execute_node6_conclude()
            elif node_id == 7:
                self._execute_node7_report()
            else:
                raise ValueError(f"未知的节点ID: {node_id}")

            # 只在节点结果存在时才标记为完成
            if node_id in self.node_results and self.node_results[node_id]:
                self.node_status[node_id] = NodeStatus.COMPLETED
                self.current_node = max(self.current_node, node_id)
                self._save_state()
            else:
                # 如果没有结果，标记为错误
                self.node_status[node_id] = NodeStatus.ERROR
                self.node_errors[node_id] = "节点执行失败，未生成结果"
                self._save_state()
                return False

            return True

        except Exception as e:
            logger.error(f"节点{node_id}执行失败: {str(e)}", exc_info=True)
            self.node_status[node_id] = NodeStatus.ERROR
            self.node_errors[node_id] = str(e)
            self._save_state()
            # 移除 st.rerun() 调用，让调用者决定是否重新运行
            return False

    def execute_all(self):
        """自动执行所有未完成的节点"""
        pass

    def _execute_node1_decompose(self):
        """节点1：问题拆解与关键词生成"""
        logger.info("执行节点1：问题拆解与关键词生成")

        if self.mode == "academic":
            # 学术模式：使用QueryAnalyzerAgent进行查询分析

            # 1. 先读取缓存
            cached_data = self.cache.get(self.query, 1)
            if cached_data is not None:
                logger.info("✅ 节点1从缓存读取成功")
                self.node_results[1] = cached_data
                return

            # 2. 缓存未命中，执行查询分析
            from src.agents.coordinator import AcademicCoordinator
            from src.tools.crossref_search import CrossrefSearch
            from src.tools.openalex_search import OpenAlexSearch

            coordinator = AcademicCoordinator(
                self.agent.llm_client,
                CrossrefSearch(),
                OpenAlexSearch()
            )

            analysis_result = coordinator.query_analyzer.process({"query": self.query})

            result = {
                "type": "academic",
                "keywords": analysis_result.get("keywords", []),
                "raw_response": analysis_result
            }

            # 3. 保存结果到缓存
            self.cache.set(self.query, 1, result)
            self.node_results[1] = result
            # 保存状态，确保后续节点能正确加载
            self._save_state()

        else:
            # 通用模式：使用原有逻辑
            self.agent._generate_report_structure(self.query)

            result = {
                "type": "general",
                "paragraphs": [
                    {"title": p.title, "content": p.content}
                    for p in self.agent.state.paragraphs
                ]
            }

            # 通用模式也缓存
            self.cache.set(self.query, 1, result)
            self.node_results[1] = result

    def _execute_node2_search(self):
        """节点2：多源并发检索"""
        logger.info("执行节点2：多源并发检索")

        if self.mode == "academic":
            # 学术模式：使用SearchAgent进行搜索

            # 1. 先读取缓存
            cached_data = self.cache.get(self.query, 2)
            if cached_data is not None:
                logger.info("✅ 节点2从缓存读取成功")
                self.node_results[2] = cached_data
                return

            # 2. 缓存未命中，执行搜索
            from src.agents.coordinator import AcademicCoordinator
            from src.tools.crossref_search import CrossrefSearch
            from src.tools.openalex_search import OpenAlexSearch

            coordinator = AcademicCoordinator(
                self.agent.llm_client,
                CrossrefSearch(),
                OpenAlexSearch()
            )

            keywords = self.node_results[1].get("keywords", [])
            search_result = coordinator.search_agent.process({"keywords": keywords})
            papers = search_result.get("papers", [])

            for paper in papers:
                # 优先从journal提取，无则取publisher/venue/container-title（兼容不同数据源）
                paper["journal"] = paper.get("journal") or paper.get("publisher") or paper.get("venue") or paper.get("container-title") or "未公开来源"
                # 年份兜底
                paper["year"] = paper.get("year") or paper.get("publication_year") or 0
                # DOI兜底
                paper["doi"] = paper.get("doi") or ""
                # 作者兜底
                paper["authors"] = paper.get("authors") or "未知作者"

            result = {
                "type": "academic",
                "papers": search_result.get("papers", []),
                "raw_response": search_result
            }

            # 3. 保存结果到缓存
            self.cache.set(self.query, 2, result)
            self.node_results[2] = result
            # 保存状态，确保后续节点能正确加载
            self._save_state()

        else:
            # 通用模式：处理所有段落的搜索
            self.agent._process_paragraphs()

            # 收集所有搜索结果
            all_searches = []
            for paragraph in self.agent.state.paragraphs:
                all_searches.extend([
                    {
                        "query": s.query,
                        "title": s.title,
                        "url": s.url,
                        "content": s.content,
                        "score": s.score
                    }
                    for s in paragraph.research.search_history
                ])

            result = {
                "type": "general",
                "searches": all_searches,
                "paragraphs": [
                    {
                        "title": p.title,
                        "latest_summary": p.research.latest_summary,
                        "search_count": p.research.get_search_count()
                    }
                    for p in self.agent.state.paragraphs
                ]
            }

            # 通用模式也缓存
            self.cache.set(self.query, 2, result)
            self.node_results[2] = result
            # 保存状态，确保后续节点能正确加载
            self._save_state()

    def _execute_node3_deduplicate(self):
        """节点3：数据去重与融合"""
        logger.info("执行节点3：数据去重与融合")

        if self.mode == "academic":
            # 学术模式：基于DOI或标题去重
            papers = self.node_results[2].get("papers", [])
            seen = set()
            unique_papers = []

            for p in papers:
                doi = p.get("doi", "")
                title = p.get("title", "")
                key = doi if doi else title[:50]
                if key and key not in seen:
                    seen.add(key)
                    unique_papers.append(p)

            self.node_results[3] = {
                "type": "academic",
                "original_count": len(papers),
                "unique_count": len(unique_papers),
                "papers": unique_papers
            }
        else:
            # 通用模式：搜索结果已在节点2中处理，这里主要做状态同步
            self.node_results[3] = {
                "type": "general",
                "message": "通用模式下搜索结果已在节点2中处理",
                "paragraphs": len(self.agent.state.paragraphs)
            }

    def _execute_node4_evidence(self):
        """节点4：证据等级标注"""
        logger.info("执行节点4：证据等级标注")

        if self.mode == "academic":
            # 1. 先读取缓存
            cached_data = self.cache.get(self.query, 4)
            if cached_data is not None:
                logger.info("✅ 节点4从缓存读取成功")
                self.node_results[4] = cached_data
                return

            # 2. 缓存未命中，执行证据等级标注
            from src.utils.evidence import get_evidence_level, get_evidence_priority

            papers = self.node_results[3].get("papers", [])

            for paper in papers:
                level_obj, details = get_evidence_level(paper)
                paper['evidence_level'] = str(level_obj)
                paper['grade_details'] = details
                # 修复：传入枚举对象而非字符串
                paper['evidence_priority'] = get_evidence_priority(level_obj)
                if 'year' not in paper or not paper['year']:
                    paper['year'] = 0

            result = {
                "type": "academic",
                "papers": papers,
                "stats": {
                    "total": len(papers),
                    "by_level": {}
                }
            }

            # 统计各等级数量
            for paper in papers:
                level = paper.get('evidence_level', '未知')
                result["stats"]["by_level"][level] = result["stats"]["by_level"].get(level, 0) + 1

            # 3. 保存结果到缓存
            self.cache.set(self.query, 4, result)
            self.node_results[4] = result
            # 保存状态，确保后续节点能正确加载
            self._save_state()

        else:
            # 通用模式：不需要证据等级标注
            result = {
                "type": "general",
                "message": "通用模式不需要证据等级标注"
            }

            # 通用模式也缓存
            self.cache.set(self.query, 4, result)
            self.node_results[4] = result
            # 保存状态，确保后续节点能正确加载
            self._save_state()

    def _execute_node5_filter(self):
        """节点5：文献筛选与排序"""
        logger.info("执行节点5：文献筛选与排序")

        if self.mode == "academic":
            papers = self.node_results[4].get("papers", [])

            # 按证据等级优先级+发表年份降序排序
            sorted_papers = sorted(
                papers,
                key=lambda x: (x.get('evidence_priority', 0), x.get('year', 0)),
                reverse=True
            )

            self.node_results[5] = {
                "type": "academic",
                "papers": sorted_papers,
                "top_10": sorted_papers[:10]
            }
            # 保存状态，确保后续节点能正确加载
            self._save_state()
        else:
            # 通用模式：按照段落的完成度排序
            completed_paragraphs = [
                {
                    "title": p.title,
                    "content": p.research.latest_summary,
                    "completed": p.is_completed()
                }
                for p in self.agent.state.paragraphs
            ]

            self.node_results[5] = {
                "type": "general",
                "paragraphs": completed_paragraphs
            }
            # 保存状态，确保后续节点能正确加载
            self._save_state()

    def _execute_node6_conclude(self):
        """节点6：结论提取与生成"""
        logger.info("执行节点6：结论提取与生成")

        if self.mode == "academic":
            # 1. 先读取本地缓存
            cached_data = self.cache.get(self.query, 6)
            if cached_data is not None:
                logger.info("✅ 节点6从缓存读取成功")
                self.node_results[6] = cached_data
                # 保存状态，确保后续节点能正确加载
                self._save_state()
                return

            # 2. 缓存未命中，执行结论提取与生成
            from src.agents.coordinator import AcademicCoordinator
            from src.tools.crossref_search import CrossrefSearch
            from src.tools.openalex_search import OpenAlexSearch
            import time

            coordinator = AcademicCoordinator(
                self.agent.llm_client,
                CrossrefSearch(),
                OpenAlexSearch()
            )

            papers = self.node_results[5].get("papers", [])

            # 为了避免429错误，在调用前添加延迟
            logger.info("⏳ 调用结论提取前等待3秒，避免限流")
            time.sleep(3)

            # 结论提取与生成 - 添加429错误处理
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 提取关键发现和结论
                    key_findings_result = coordinator.summary_agent._extract_key_findings(papers)
                    
                    # 生成结构化结论
                    conclusion_prompt = f"""
基于以下文献证据，生成专业、详细、结构化的循证医学结论：

查询问题：{self.query}

相关文献：
"""
                    
                    for i, paper in enumerate(papers[:10]):  # 最多处理前10篇高质量文献
                        title = paper.get('title', '')
                        year = paper.get('year', '')
                        evidence_level = paper.get('evidence_level', '')
                        key_finding = paper.get('key_finding', '')
                        journal = paper.get('journal', '')
                        
                        conclusion_prompt += f"""
{i+1}. 标题：{title}
    年份：{year} | 期刊：{journal} | 证据等级：{evidence_level}
    关键发现：{key_finding}
"""

                    conclusion_prompt += """

请生成以下结构化内容：

## 核心结论
基于上述高质量文献证据，总结主要发现和核心观点。

## 具体循证建议
提供基于证据的具体临床实践建议，包括诊断、治疗、预防等方面。

## 证据来源
列出主要证据来源及其质量等级。
"""

                    # 调用LLM生成专业结论
                    conclusion_result = coordinator.summary_agent._call_llm(
                        conclusion_prompt,
                        "你是循证医学专家，请基于文献证据生成专业、详细、结构化的医学结论。"
                    )

                    # 为每篇论文添加关键发现
                    for paper in papers:
                        if not paper.get('key_finding'):
                            # 从标题和摘要中提取简化的关键发现
                            title = paper.get('title', '')
                            abstract = paper.get('abstract', '')
                            if title and abstract:
                                text_snippet = f"{title} {abstract[:100]}"
                                paper['key_finding'] = text_snippet[:80] + "..." if len(text_snippet) > 80 else text_snippet
                            else:
                                paper['key_finding'] = "基于文献证据"

                    result = {
                        "type": "academic",
                        "conclusion": conclusion_result,
                        "papers": papers,
                        "key_findings": key_findings_result
                    }

                    # 3. 保存结果到缓存
                    self.cache.set(self.query, 6, result)
                    self.node_results[6] = result

                    # 保存状态，确保后续节点能正确加载
                    self._save_state()

                    logger.info("✅ 节点6执行成功")
                    return

                except Exception as e:
                    error_msg = str(e)
                    # 检查是否为429限流错误
                    if "429" in error_msg or "速率限制" in error_msg or "rate limit" in error_msg.lower():
                        wait_time = 15 * (attempt + 1)  # 15秒、30秒、45秒
                        logger.warning(f"⚠️ 检测到429限流错误，等待{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)

                        if attempt == max_retries - 1:
                            # 最后一次重试仍然失败，使用基础结论
                            logger.warning("⚠️ 达到最大重试次数，使用基础结论生成")
                            base_conclusion = f"""
## 核心结论
基于检索到的{len(papers)}篇相关文献，建议进一步分析具体文献内容。

## 具体循证建议
请结合临床实际情况和具体文献证据制定个体化治疗方案。

## 证据来源
详见上方文献表格中的具体论文信息。
"""
                            for paper in papers:
                                if not paper.get('key_finding'):
                                    paper['key_finding'] = "基于文献证据"
                            
                            result = {
                                "type": "academic",
                                "conclusion": base_conclusion,
                                "papers": papers,
                                "key_findings": papers
                            }
                            
                            self.cache.set(self.query, 6, result)
                            self.node_results[6] = result
                            self._save_state()
                            return
                    else:
                        # 非限流错误，直接抛出
                        raise
        else:
            # 通用模式：生成最终报告
            final_report = self.agent._generate_final_report()

            result = {
                "type": "general",
                "report": final_report
            }

            # 通用模式也缓存
            self.cache.set(self.query, 6, result)
            self.node_results[6] = result
            # 保存状态，确保后续节点能正确加载
            self._save_state()

    def _execute_node7_report(self):
        """节点7：报告生成与导出"""
        logger.info("执行节点7：报告生成与导出")

        if self.mode == "academic":
            # 1. 先读取本地缓存
            cached_data = self.cache.get(self.query, 7)
            if cached_data is not None:
                logger.info("✅ 节点7从缓存读取成功")
                self.node_results[7] = cached_data
                # 保存状态，确保后续节点能正确加载
                self._save_state()
                return

            from src.agents.coordinator import AcademicCoordinator
            from src.tools.crossref_search import CrossrefSearch
            from src.tools.openalex_search import OpenAlexSearch

            coordinator = AcademicCoordinator(
                self.agent.llm_client,
                CrossrefSearch(),
                OpenAlexSearch()
            )

            papers = self.node_results[6].get("papers", [])

            # 生成总结（添加错误处理）
            try:
                summary_result = coordinator.summary_agent.process({
                    "query": self.query,
                    "papers": papers
                })

                if summary_result['status'] != 'success':
                    raise Exception("总结生成失败")

                final_report = summary_result['summary']
            except Exception as e:
                logger.error(f"总结生成失败，生成基础报告: {str(e)}")
                # 生成一个基础的报告作为降级方案
                table = "| 标题 | 年份 | 证据等级 | 关键结论 |\n|------|------|----------|----------|\n"
                for p in papers:
                    title_short = p['title'][:50] + ('...' if len(p['title']) > 50 else '')
                    year = p['year']
                    level = p['evidence_level']
                    finding = p.get('key_finding', '基于文献证据')[:50] + ('...' if len(p.get('key_finding', '')) > 50 else '')
                    table += f"| {title_short} | {year} | {level} | {finding} |\n"
                
                # 基础总结
                base_summary = f"""## 核心结论
由于API调用限制，无法生成详细总结。建议基于上方文献表格自行分析。

## 具体循证建议
请结合临床实际情况制定个体化治疗方案。

## 证据来源
详见上方文献表格。"""
                
                final_report = f"# 文献证据表格\n\n{table}\n\n# 综合总结\n\n{base_summary}\n\n---\n⚠️ **免责声明**：本工具仅提供学术文献参考，不构成医疗建议。具体诊疗请咨询专业医生。"

            # 保存到状态
            self.agent.state.academic_papers = papers
            self.agent.state.final_report = final_report

            result = {
                "type": "academic",
                "report": final_report,
                "papers": papers
            }

            # 保存结果到本地缓存
            self.cache.set(self.query, 7, result)
            self.node_results[7] = result
            # 保存状态，确保后续节点能正确加载
            self._save_state()
        else:
            # 通用模式：报告已在节点6生成，这里保存
            report = self.node_results[6].get("report", "")

            self.node_results[7] = {
                "type": "general",
                "report": report,
                "papers": []
            }
            # 保存状态，确保后续节点能正确加载
            self._save_state()

    def rerun_from_node(self, node_id: int):
        """从指定节点重新执行（清除后续节点结果）"""
        for nid in range(node_id, 8):
            self.node_status[nid] = NodeStatus.PENDING
            if nid in self.node_results:
                del self.node_results[nid]
            if nid in self.node_errors:
                del self.node_errors[nid]

        self.current_node = node_id - 1
        self._save_state()

    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        completed = sum(1 for status in self.node_status.values() if status == NodeStatus.COMPLETED)
        total = len(self.node_status)

        return {
            "total": total,
            "completed": completed,
            "current_node": self.current_node,
            "progress": (completed / total * 100) if total > 0 else 0
        }


def load_default_config():
    """从config.py加载默认配置"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
        if os.path.exists(config_path):
            return Config.from_file(config_path)
    except Exception:
        pass
    return None


def main():
    """主函数"""
    st.set_page_config(
        page_title="Deep Search Agent",
        page_icon="🔍",
        layout="wide"
    )

    st.title("Deep Search Agent")
    st.markdown("基于大语言模型的无框架深度搜索AI代理")

    # 初始化会话状态
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None
    if "initialized" not in st.session_state:
        st.session_state.initialized = False

    # 加载默认配置
    default_config = load_default_config()

    # 提供商配置
    PROVIDERS = ["zhipu", "deepseek", "openai"]
    PROVIDER_NAMES = {
        "zhipu": "智谱AI (ZhipuAI)",
        "deepseek": "DeepSeek",
        "openai": "OpenAI"
    }
    PROVIDER_MODELS = {
        "zhipu": ["glm-4.7", "glm-4.6v", "glm-4", "glm-4.5-air"],
        "deepseek": ["deepseek-chat"],
        "openai": ["gpt-4o-mini", "gpt-4o"]
    }
    DEFAULT_MODELS = {
        "zhipu": "glm-4",
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-mini"
    }

    # 确定默认提供商索引
    if default_config and default_config.default_llm_provider in PROVIDERS:
        default_provider_index = PROVIDERS.index(default_config.default_llm_provider)
    else:
        default_provider_index = 0  # 默认选中第一个（zhipu）

    # 侧边栏配置
    with st.sidebar:
        st.header("配置")

        # API密钥配置
        st.subheader("API密钥")

        # 学术模式开关
        academic_mode = st.checkbox("🔬 健康溯源模式（学术证据）", value=False)

        # 根据学术模式动态调整UI
        if academic_mode:
            # 学术模式下锁定为智谱AI
            llm_provider = "zhipu"
            st.info("学术模式已启用，将强制使用智谱AI")

            # 禁用提供商选择
            llm_provider = st.selectbox(
                "LLM提供商",
                options=["zhipu"],
                format_func=lambda x: PROVIDER_NAMES[x],
                index=0,
                disabled=True
            )

            # 禁用模型选择
            model_name = st.selectbox(
                f"{PROVIDER_NAMES[llm_provider]} 模型",
                options=PROVIDER_MODELS[llm_provider],
                index=0,
                disabled=True
            )

            # 只显示智谱API Key
            default_zhipu_key = default_config.zhipu_api_key if default_config else ""
            zhipu_key = st.text_input(
                "智谱 API Key",
                type="password",
                value=default_zhipu_key,
                help="从智谱AI开放平台获取: https://open.bigmodel.cn/"
            )
            deepseek_key = ""
            openai_key = ""

            # 隐藏Tavily API Key
            tavily_key = ""
            st.empty()  # 占位，保持布局
        else:
            # 非学术模式：正常显示所有配置项
            # 提供商选择
            llm_provider = st.selectbox(
                "LLM提供商",
                options=PROVIDERS,
                format_func=lambda x: PROVIDER_NAMES[x],
                index=default_provider_index
            )

            # 根据提供商动态显示API Key输入框
            if llm_provider == "zhipu":
                default_zhipu_key = default_config.zhipu_api_key if default_config else ""
                zhipu_key = st.text_input(
                    "智谱 API Key",
                    type="password",
                    value=default_zhipu_key,
                    help="从智谱AI开放平台获取: https://open.bigmodel.cn/"
                )
                deepseek_key = ""
                openai_key = ""
            elif llm_provider == "deepseek":
                default_deepseek_key = default_config.deepseek_api_key if default_config else ""
                deepseek_key = st.text_input(
                    "DeepSeek API Key",
                    type="password",
                    value=default_deepseek_key,
                    help="从DeepSeek开放平台获取: https://platform.deepseek.com/"
                )
                zhipu_key = ""
                openai_key = ""
            else:  # openai
                default_openai_key = default_config.openai_api_key if default_config else ""
                openai_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    value=default_openai_key,
                    help="从OpenAI平台获取: https://platform.openai.com/"
                )
                zhipu_key = ""
                deepseek_key = ""

            # Tavily API Key
            default_tavily_key = default_config.tavily_api_key if default_config else ""
            tavily_key = st.text_input(
                "Tavily API Key",
                type="password",
                value=default_tavily_key,
                help="从Tavily获取: https://tavily.com/"
            )

            # 模型选择
            st.subheader("模型选择")
            model_options = PROVIDER_MODELS[llm_provider]
            default_model = DEFAULT_MODELS[llm_provider]

            # 确定默认模型
            if default_config:
                if llm_provider == "zhipu" and default_config.zhipu_model in model_options:
                    default_model = default_config.zhipu_model
                elif llm_provider == "deepseek" and default_config.deepseek_model in model_options:
                    default_model = default_config.deepseek_model
                elif llm_provider == "openai" and default_config.openai_model in model_options:
                    default_model = default_config.openai_model

            model_name = st.selectbox(
                f"{PROVIDER_NAMES[llm_provider]} 模型",
                options=model_options,
                index=model_options.index(default_model) if default_model in model_options else 0
            )

        # 高级配置
        st.subheader("高级配置")
        max_reflections = st.slider("反思次数", 1, 5,
                                    default_config.max_reflections if default_config else 2)
        max_search_results = st.slider("搜索结果数", 1, 10,
                                       default_config.max_search_results if default_config else 3)
        max_content_length = st.number_input("最大内容长度", 1000, 50000,
                                             default_config.max_content_length if default_config else 20000)

    # 创建两列布局：左侧进度导航，右侧主内容
    col_left, col_right = st.columns([1, 4])

    # 左侧：进度导航
    with col_left:
        st.subheader("执行流程")

        # 检查是否有正在进行的任务
        if st.session_state.orchestrator is not None:
            orchestrator = st.session_state.orchestrator
            orchestrator._load_state()

            # 显示进度条
            status = orchestrator.get_status_summary()
            st.progress(status["progress"] / 100)
            st.caption(f"进度: {status['completed']}/{status['total']}")

            # 显示节点导航
            for node in StreamlitUIOrchestrator.NODES:
                node_id = node["id"]
                node_status = orchestrator.node_status.get(node_id, NodeStatus.PENDING)

                # 状态图标
                status_icons = {
                    NodeStatus.PENDING: "⏳",
                    NodeStatus.RUNNING: "🔄",
                    NodeStatus.COMPLETED: "✅",
                    NodeStatus.ERROR: "❌"
                }
                icon = status_icons.get(node_status, "⏳")

                # 状态颜色
                status_colors = {
                    NodeStatus.PENDING: "secondary",
                    NodeStatus.RUNNING: "primary",
                    NodeStatus.COMPLETED: "off",
                    NodeStatus.ERROR: "off"
                }

                # 节点按钮
                if st.button(
                    f"{icon} {node_id}. {node['name']}",
                    key=f"nav_node_{node_id}",
                    type=status_colors.get(node_status, "secondary"),
                    use_container_width=True,
                    disabled=node_status == NodeStatus.RUNNING
                ):
                    if node_status == NodeStatus.COMPLETED:
                        # 已完成的节点，点击展开查看结果
                        st.session_state.expanded_node = node_id
                    elif node_status in [NodeStatus.PENDING, NodeStatus.ERROR]:
                        # 未完成或出错的节点，点击执行
                        st.session_state.node_to_execute = node_id

            # 缓存管理
            with st.expander("🗄️ 缓存管理"):
                col_cache1, col_cache2 = st.columns(2)

                with col_cache1:
                    if st.button("📊 查看本地缓存状态", use_container_width=True):
                        st.session_state.show_cache_info = True

                    if st.button("🗑️ 清空本地缓存", use_container_width=True):
                        orchestrator.cache.clear()
                        st.success("本地缓存已清空")
                        st.rerun()

                with col_cache2:
                    if st.button("📋 列出缓存文件", use_container_width=True):
                        st.session_state.show_cached_queries = True

                    if st.button("⚙️ 缓存配置", use_container_width=True):
                        st.session_state.show_cache_config = True

            # 重置按钮
            if st.button("🔄 重置流程", use_container_width=True):
                orchestrator.reset()
                st.rerun()

        else:
            st.info("暂无进行中的任务，请在右侧输入查询开始研究")

    # 右侧：主内容区
    with col_right:
        # 自动显示报告（7个节点全部完成就展开）
        if st.session_state.orchestrator and st.session_state.orchestrator.get_status_summary()["completed"] == 7:
            st.session_state.show_full_report = True

        st.header("研究查询")
        query = st.text_area(
            "请输入您要研究的问题",
            placeholder="例如：2025年人工智能发展趋势",
            height=100
        )

        # 预设查询示例
        st.subheader("示例查询")
        example_queries = [
            "2025年人工智能发展趋势",
            "深度学习在医疗领域的应用",
            "区块链技术的最新发展",
            "可持续能源技术趋势",
            "量子计算的发展现状"
        ]

        selected_example = st.selectbox("选择示例查询", ["自定义"] + example_queries)
        if selected_example != "自定义":
            query = selected_example

        # 开始研究按钮
        col1, col2,col3 = st.columns([1, 1, 1])
        with col2:
            start_research = st.button("开始研究", type="primary", use_container_width=True)

        # 处理开始研究
        if start_research:
            if not query.strip():
                st.error("请输入研究查询")
                return

            # 验证配置
            if llm_provider == "zhipu" and not zhipu_key:
                st.error("请提供智谱 API Key")
                return

            if llm_provider == "deepseek" and not deepseek_key:
                st.error("请提供 DeepSeek API Key")
                return

            if llm_provider == "openai" and not openai_key:
                st.error("请提供 OpenAI API Key")
                return

            if not academic_mode and not tavily_key:
                st.error("请提供 Tavily API Key")
                return

            # 学术模式敏感词过滤
            if academic_mode:
                try:
                    from src.utils.evidence import filter_sensitive
                    if filter_sensitive(query):
                        st.error("⚠️ 检测到敏感内容，无法提供相关学术信息。")
                        return
                except ImportError:
                    logger.warning("无法导入filter_sensitive函数，跳过敏感词过滤")

            # 创建配置
            config = Config(
                deepseek_api_key=deepseek_key if llm_provider == "deepseek" else None,
                openai_api_key=openai_key if llm_provider == "openai" else None,
                zhipu_api_key=zhipu_key if llm_provider == "zhipu" else None,
                tavily_api_key=tavily_key,
                default_llm_provider=llm_provider,
                deepseek_model=model_name if llm_provider == "deepseek" else "deepseek-chat",
                openai_model=model_name if llm_provider == "openai" else "gpt-4o-mini",
                zhipu_model=model_name if llm_provider == "zhipu" else "glm-4.7",
                max_reflections=max_reflections,
                max_search_results=max_search_results,
                max_content_length=max_content_length,
                output_dir="streamlit_reports",
                academic_mode=academic_mode
            )

            # 初始化编排器
            orchestrator = StreamlitUIOrchestrator(config)
            orchestrator.set_query(query, mode="academic" if academic_mode else "general")
            st.session_state.orchestrator = orchestrator
            st.session_state.initialized = True

            # 自动执行节点1
            st.session_state.node_to_execute = 1
            st.rerun()

        # 处理节点执行
        if st.session_state.orchestrator is not None and "node_to_execute" in st.session_state:
            node_id = st.session_state.node_to_execute
            del st.session_state.node_to_execute

            orchestrator = st.session_state.orchestrator
            orchestrator._load_state()

            with st.spinner(f"正在执行节点{node_id}..."):
                success = orchestrator.execute_node(node_id)

            if success:
                st.success(f"节点{node_id}执行完成！")
                # 自动展开当前节点结果
                st.session_state.expanded_node = node_id
            else:
                error_msg = orchestrator.node_errors.get(node_id, "未知错误")
                st.error(f"节点{node_id}执行失败: {error_msg}")

            st.rerun()

        # 显示节点结果
        if st.session_state.orchestrator is not None and "expanded_node" in st.session_state:
            node_id = st.session_state.expanded_node
            orchestrator = st.session_state.orchestrator
            orchestrator._load_state()

            node_info = next((n for n in StreamlitUIOrchestrator.NODES if n["id"] == node_id), None)
            if node_info:
                st.divider()
                st.subheader(f"节点{node_id}：{node_info['name']}")

                # 显示结果
                if node_id in orchestrator.node_results:
                    display_node_result(node_id, orchestrator.node_results[node_id], orchestrator.mode)

                    # 用户干预区域
                    st.subheader("用户干预")
                    col_a, col_b = st.columns(2)

                    with col_a:
                        if st.button(f"🔄 重新执行此节点及后续", key=f"rerun_{node_id}"):
                            orchestrator.rerun_from_node(node_id)
                            st.session_state.node_to_execute = node_id
                            del st.session_state.expanded_node
                            st.rerun()

                    with col_b:
                        next_node = node_id + 1
                        if next_node <= 7:
                            if st.button(f"▶️ 执行下一个节点", key=f"next_{node_id}"):
                                st.session_state.node_to_execute = next_node
                                del st.session_state.expanded_node
                                st.rerun()

                        # 如果是最后一个节点，显示完成选项
                        if node_id == 7:
                            if st.button("📄 查看完整报告", key=f"view_report"):
                                st.session_state.show_full_report = True
                                st.rerun()
                else:
                    st.info(f"节点{node_id}尚未执行")

        # 显示缓存信息
        if st.session_state.get("show_cache_info", False):
            st.divider()
            st.subheader("本地缓存状态")

            cache_info = orchestrator.cache.list_cache_info()
            st.json(cache_info)

            if st.button("关闭缓存信息"):
                st.session_state.show_cache_info = False
                st.rerun()

        # 显示缓存的查询列表
        if st.session_state.get("show_cached_queries", False):
            st.divider()
            st.subheader("本地缓存文件")

            cache_info = orchestrator.cache.list_cache_info()
            caches = cache_info.get('caches', [])

            if caches:
                for cache in caches:
                    with st.expander(f"节点{cache['node_id']}: {cache['query']} ({'有效' if cache['is_valid'] else '已过期'})"):
                        st.write(f"文件名: {cache['filename']}")
                        st.write(f"时间戳: {cache['timestamp']}")
                        st.write(f"查询: {cache['query']}")
                        st.write(f"状态: {'✅ 有效' if cache['is_valid'] else '❌ 已过期'}")
            else:
                st.info("暂无缓存文件")

            if st.button("关闭缓存列表"):
                st.session_state.show_cached_queries = False
                st.rerun()

        # 显示完整报告
        if st.session_state.orchestrator is not None and st.session_state.get("show_full_report", False):
            orchestrator = st.session_state.orchestrator
            orchestrator._load_state()

            final_report = orchestrator.node_results.get(7, {}).get("report", "")
            papers = orchestrator.node_results.get(7, {}).get("papers", [])

            st.divider()
            st.subheader("完整报告")

            tab1, tab2, tab3 = st.tabs(["最终报告", "详细信息", "下载"])

            with tab1:
                st.markdown(final_report)

            with tab2:
                if orchestrator.mode == "academic" and papers:
                    st.subheader("学术论文详情")
                    for i, paper in enumerate(papers):
                        cite_idx = paper.get('cite_index', i+1)
                        title = paper.get('title', '') or '无标题'
                        title_display = title[:80] + ('...' if len(title) > 80 else '')
                        with st.expander(f"论文 {i+1}: {title_display}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**标题:**", title)
                                st.write("**作者:**", paper.get('authors', '无作者'))
                                year = paper.get('year', 0) or 0
                                st.write("**年份:**", str(year) if year > 0 else "未知年份")
                            with col2:
                                journal = paper.get('journal', '') or ''
                                st.write("**期刊:**", journal if journal else "未指定期刊")
                                doi = paper.get('doi', '') or ''
                                st.write("**DOI:**", doi if doi else "无DOI")
                                if doi:
                                    st.write("**URL:**", f"https://doi.org/{doi}")

                            # 删除GRADE分级详情、核心证据片段、证据等级显示
                    st.caption(f"共找到 {len(papers)} 篇相关学术论文")
                else:
                    st.subheader("段落详情")
                    for i, paragraph in enumerate(orchestrator.agent.state.paragraphs):
                        with st.expander(f"段落 {i+1}: {paragraph.title}"):
                            st.write("**预期内容:**", paragraph.content)
                            final_summary = paragraph.research.latest_summary
                            if len(final_summary) > 300:
                                final_summary = final_summary[:300] + "..."
                            st.write("**最终内容:**", final_summary)
                            st.write("**搜索次数:**", paragraph.research.get_search_count())
                            st.write("**反思次数:**", paragraph.research.reflection_iteration)

            with tab3:
                st.subheader("下载报告")

                st.download_button(
                    label="下载Markdown报告",
                    data=final_report,
                    file_name=f"deep_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )

                if orchestrator.mode == "academic" and papers:
                    papers_json = json.dumps(papers, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="下载学术论文列表JSON",
                        data=papers_json,
                        file_name=f"academic_papers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

                state_json = orchestrator.agent.state.to_json()
                st.download_button(
                    label="下载状态文件",
                    data=state_json,
                    file_name=f"deep_search_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )


def display_node_result(node_id: int, result: Dict[str, Any], mode: str):
    """显示节点结果"""
    if node_id == 1:
        # 问题拆解与关键词生成
        if mode == "academic":
            keywords = result.get("keywords", [])
            st.write("**生成关键词:**", ", ".join(keywords) if keywords else "无")
        else:
            paragraphs = result.get("paragraphs", [])
            st.write(f"**生成段落数:** {len(paragraphs)}")
            for i, p in enumerate(paragraphs):
                with st.expander(f"段落 {i+1}: {p['title']}"):
                    st.write(p['content'])

    elif node_id == 2:
        # 多源并发检索
        if mode == "academic":
            papers = result.get("papers", [])
            st.write(f"**检索到论文数:** {len(papers)}")
            for i, paper in enumerate(papers[:5]):
                with st.expander(f"论文 {i+1}: {paper.get('title', '无标题')[:60]}"):
                    st.write("**作者:**", paper.get('authors', '无'))
                    year = paper.get('year', 0)
                    st.write("**年份:**", str(year) if year > 0 else "未知年份")
                    journal = paper.get('journal', '')
                    st.write("**期刊:**", journal if journal else "未指定期刊")
            if len(papers) > 5:
                st.caption(f"...还有 {len(papers) - 5} 篇论文")
        else:
            searches = result.get("searches", [])
            paragraphs = result.get("paragraphs", [])
            st.write(f"**搜索结果数:** {len(searches)}")
            st.write(f"**处理段落数:** {len(paragraphs)}")
            for i, search in enumerate(searches[:5]):
                with st.expander(f"搜索 {i+1}: {search.get('title', '无标题')[:60]}"):
                    st.write("**查询:**", search.get('query', ''))
                    st.write("**URL:**", search.get('url', ''))

    elif node_id == 3:
        # 数据去重与融合
        if mode == "academic":
            st.write("**原始数量:**", result.get("original_count", 0))
            st.write("**去重后数量:**", result.get("unique_count", 0))
            st.write(f"**去重率:** {((1 - result.get('unique_count', 1) / max(result.get('original_count', 1), 1)) * 100):.1f}%")
        else:
            st.info(result.get("message", ""))

    elif node_id == 4:
        # 证据等级标注
        if mode == "academic":
            stats = result.get("stats", {})
            st.write("**总论文数:**", stats.get("total", 0))
            st.write("**证据等级分布:**")
            for level, count in stats.get("by_level", {}).items():
                st.write(f"- {level}: {count} 篇")
        else:
            st.info(result.get("message", ""))

    elif node_id == 5:
        # 文献筛选与排序
        if mode == "academic":
            papers = result.get("top_10", [])
            st.write(f"**Top 10 文献:**")
            for i, paper in enumerate(papers):
                with st.expander(f"{i+1}. {paper.get('title', '无标题')[:60]}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**标题:**", paper.get('title', ''))
                        st.write("**作者:**", paper.get('authors', ''))
                    with col2:
                        year = paper.get('year', 0)
                        st.write("**年份:**", str(year) if year > 0 else "未知年份")
                        st.write("**证据等级:**", paper.get('evidence_level', ''))
        else:
            paragraphs = result.get("paragraphs", [])
            st.write(f"**段落数:** {len(paragraphs)}")
            for i, p in enumerate(paragraphs):
                st.write(f"{i+1}. {p['title']}: {'✅' if p['completed'] else '⏳'}")

    elif node_id == 6:
        # 结论提取与生成
        if mode == "academic":
            evidence_analysis = result.get("evidence_analysis", {})
            st.write("**证据分析状态:**", evidence_analysis.get("status", "未知"))
            st.write(f"**论文数:** {len(result.get('papers', []))}")
        else:
            report = result.get("report", "")
            st.write("**报告预览:**")
            st.markdown(report[:500] + "..." if len(report) > 500 else report)

    elif node_id == 7:
        # 报告生成与导出
        st.success("✅ 所有节点执行完成！")
        st.write("点击下方按钮查看完整报告或下载")


if __name__ == "__main__":
    main()