"""
学术研究节点（多数据源并发搜索，支持 Crossref + OpenAlex，综合排序）
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from src.llms.zhipu import ZhipuLLM
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from src.utils.evidence import get_evidence_level, filter_sensitive, get_evidence_priority
from src.prompts.academic_prompts import (
    OPENALEX_QUERY_PROMPT,
    CROSSREF_QUERY_PROMPT,
    BATCH_EXTRACT_PROMPT,
    SUMMARIZE_PROMPT
)
from src.agents.coordinator import AcademicCoordinator


class AcademicNode:
    def __init__(self, llm_client: ZhipuLLM, config=None):
        self.llm = llm_client
        self.config = config
        self.crossref_search = CrossrefSearch()
        self.openalex_search = OpenAlexSearch()
        self.coordinator = AcademicCoordinator(self.llm, self.crossref_search, self.openalex_search)

    def run(self, query: str) -> tuple:
        try:
            if filter_sensitive(query):
                return "⚠️ 检测到敏感内容，无法提供相关学术信息。", []

            result = self.coordinator.process(query)
            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"⚠️ 处理过程中发生错误：{str(e)}。请稍后重试或尝试其他查询。", []