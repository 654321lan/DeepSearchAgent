from .base_agent import BaseAgent
from src.llms.zhipu import ZhipuLLM
from src.prompts.academic_prompts import CROSSREF_QUERY_PROMPT
import re

class QueryAnalyzerAgent(BaseAgent):
    def __init__(self, name: str, llm: ZhipuLLM):
        super().__init__(name)
        self.llm = llm

    def _extract_keywords(self, text: str) -> list:
        """从LLM返回的文本中提取关键词短语"""
        # 移除多余的空白和换行
        text = text.strip()

        # 尝试按逗号分隔
        keywords = [k.strip() for k in text.split(',') if k.strip()]

        # 如果逗号分隔失败，尝试按换行分隔
        if len(keywords) <= 1:
            keywords = [k.strip() for k in text.split('\n') if k.strip()]

        # 如果仍然只有一个，尝试按空格分隔（但保留短语）
        if len(keywords) <= 1:
            # 尝试按AND/OR分隔
            keywords = [k.strip() for k in re.split(r'\s+and\s+|\s+or\s+|\s+', text) if k.strip() and len(k.strip()) > 1]

        # 过滤掉单字符和空字符串
        keywords = [k for k in keywords if len(k) > 1]

        # 确保至少有3个关键词，如果没有则用原始查询生成
        if len(keywords) < 3:
            # 从原始查询生成多个变体
            query = text if text else "health"
            query = query.replace('\n', ' ').strip()
            words = [w for w in query.split() if len(w) > 1]

            if len(words) >= 2:
                # 生成关键词组合
                keywords = []
                for i in range(len(words)):
                    # 单词组合
                    phrase = ' '.join(words[max(0, i-1):i+2])
                    if len(phrase) > 2:
                        keywords.append(phrase)

            # 如果还是不够，添加默认关键词
            while len(keywords) < 3:
                keywords.append(f"{query} research")

        # 限制在5个以内
        keywords = keywords[:5]

        return keywords

    def process(self, input_data: dict) -> dict:
        query = input_data.get('query', '')
        if not query:
            return {'keywords': ['health research'], 'status': 'error', 'message': '查询为空'}

        keywords_prompt = CROSSREF_QUERY_PROMPT.format(question=query)
        response = self.llm.invoke("", keywords_prompt).strip()

        # 提取关键词列表
        keywords = self._extract_keywords(response)

        return {
            'keywords': keywords,
            'status': 'success',
            'message': '关键词生成完成'
        }
