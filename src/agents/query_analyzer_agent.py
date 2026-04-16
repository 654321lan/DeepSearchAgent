from .base_agent import BaseAgent
from src.llms.zhipu import ZhipuLLM
from src.prompts.academic_prompts import CROSSREF_QUERY_PROMPT

class QueryAnalyzerAgent(BaseAgent):
    def __init__(self, name: str, llm: ZhipuLLM):
        super().__init__(name)
        self.llm = llm

    def process(self, input_data: dict) -> dict:
        query = input_data.get('query', '')
        if not query:
            return {'keywords': 'health', 'status': 'error', 'message': '查询为空'}

        keywords_prompt = CROSSREF_QUERY_PROMPT.format(question=query)
        keywords = self.llm.invoke("", keywords_prompt).strip()

        return {
            'keywords': keywords if keywords else 'health',
            'status': 'success',
            'message': '关键词生成完成'
        }