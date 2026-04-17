from .base_agent import BaseAgent
from src.llms.zhipu import ZhipuLLM
from src.prompts.academic_prompts import CROSSREF_QUERY_PROMPT
import re
import json

# 医学相关关键词列表（用于判断是否为医学问题）
MEDICAL_KEYWORDS = [
    '疾病', '治疗', '症状', '诊断', '药物', '药', '医', '医学', '健康',
    'heart', 'cardiovascular', 'blood pressure', 'diabetes', 'cancer', 'tumor',
    'stroke', 'stroke', 'hypertension', 'medicine', 'drug', 'therapy', 'treatment',
    'disease', 'illness', 'health', 'exercise', 'fitness', 'diet', 'nutrition',
    '症状', '预防', '康复', '手术', '血压', '血糖', '胆固醇',
    '头痛', '失眠', '疼痛', '感冒', '发烧', '咳嗽', '哮喘', '过敏',
    '病毒', '细菌', '感染', '炎症', '抗生素', '疫苗', '免疫'
]

# PICO分析提示词
PICO_ANALYSIS_PROMPT = """用户问题：{question}

请分析该问题是否为医学/健康相关的研究问题，并按PICO框架拆解。

要求：
1. 首先判断是否为医学问题（回答"是"或"否"）
2. 如果是医学问题，按以下格式输出PICO拆解：
   - P (Population/Problem)：研究人群/问题（如果没有明确，标注"未明确"）
   - I (Intervention)：干预措施（如果没有明确，标注"未明确"）
   - C (Comparison)：对照（如果没有明确，标注"未明确"）
   - O (Outcome)：结局指标（如果没有明确，标注"未明确"）
3. 绝对禁止编造任何不确定的内容，无法确定的内容必须标注"未明确"
4. 宽泛问题（如"运动对健康的影响"）也要尝试拆解，P可以是"一般人群"，I是核心概念

输出格式（严格遵循）：
是否医学问题：是/否
P: [内容]
I: [内容]
C: [内容]
O: [内容]

请输出："""

# 基于PICO生成检索词提示词
PICO_KEYWORDS_PROMPT = """基于以下PICO拆解，生成3-5个优化的学术检索关键词短语（英文），用逗号分隔。

P: {pico_p}
I: {pico_i}
C: {pico_c}
O: {pico_o}

要求：
- 使用英文，每个短语由2-4个关键词组成
- 核心概念优先使用P和I
- 不要使用 AND/OR 等布尔运算符
- 针对"注意事项"、"安全性"等问题，使用 safety, risk, guideline 等词
- 只输出关键词短语列表，用逗号分隔

请输出："""

class QueryAnalyzerAgent(BaseAgent):
    def __init__(self, name: str, llm: ZhipuLLM):
        super().__init__(name)
        self.llm = llm

    def _is_medical_query(self, query: str) -> bool:
        """判断查询是否为医学/健康相关问题"""
        query_lower = query.lower()
        for keyword in MEDICAL_KEYWORDS:
            if keyword.lower() in query_lower:
                return True
        return False

    def _parse_pico_response(self, response: str) -> dict:
        """解析PICO拆解结果"""
        result = {
            'is_medical': False,
            'P': '未明确',
            'I': '未明确',
            'C': '未明确',
            'O': '未明确'
        }

        # 判断是否为医学问题
        if '是否医学问题：是' in response or '是否医学问题:是' in response:
            result['is_medical'] = True
        elif '是否医学问题：否' in response or '是否医学问题:否' in response:
            result['is_medical'] = False
        else:
            # 根据内容判断
            result['is_medical'] = self._is_medical_query(response)

        # 提取PICO各要素
        pico_patterns = [
            (r'P:\s*(.+?)(?=\n|$)', 'P'),
            (r'I:\s*(.+?)(?=\n|$)', 'I'),
            (r'C:\s*(.+?)(?=\n|$)', 'C'),
            (r'O:\s*(.+?)(?=\n|$)', 'O'),
            (r'P:\s*(.+?)(?=[A-Z]:|$)', 'P'),
            (r'I:\s*(.+?)(?=[A-Z]:|$)', 'I'),
            (r'C:\s*(.+?)(?=[A-Z]:|$)', 'C'),
            (r'O:\s*(.+?)(?=[A-Z]:|$)', 'O'),
        ]

        for pattern, key in pico_patterns:
            match = re.search(pattern, response)
            if match:
                value = match.group(1).strip()
                # 如果解析到的内容是"未明确"，保留这个标记
                if value and value != '未明确':
                    result[key] = value
                else:
                    result[key] = '未明确'

        return result

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

        # 限制在5个以内
        keywords = keywords[:5]

        return keywords

    def _generate_keywords_from_pico(self, pico: dict, original_query: str) -> list:
        """基于PICO拆解生成检索关键词"""
        # 如果PICO都没有有效信息，回退到原始查询
        if all(v == '未明确' or not v for v in pico.values()):
            return self._generate_fallback_keywords(original_query)

        # 构建PICO关键词生成提示词
        pico_keywords_prompt = PICO_KEYWORDS_PROMPT.format(
            pico_p=pico['P'] if pico['P'] != '未明确' else 'general population',
            pico_i=pico['I'] if pico['I'] != '未明确' else original_query,
            pico_c=pico['C'] if pico['C'] != '未明确' else 'not specified',
            pico_o=pico['O'] if pico['O'] != '未明确' else 'outcome'
        )

        try:
            response = self.llm.invoke("", pico_keywords_prompt).strip()
            keywords = self._extract_keywords(response)

            # 如果生成的关键词太少，回退到原始逻辑
            if len(keywords) < 3:
                return self._generate_fallback_keywords(original_query)

            return keywords
        except Exception as e:
            print(f"基于PICO生成关键词失败: {e}，回退到原始逻辑")
            return self._generate_fallback_keywords(original_query)

    def _generate_fallback_keywords(self, query: str) -> list:
        """生成回退关键词（原始逻辑）"""
        keywords_prompt = CROSSREF_QUERY_PROMPT.format(question=query)
        try:
            response = self.llm.invoke("", keywords_prompt).strip()
            keywords = self._extract_keywords(response)
            return keywords if len(keywords) >= 3 else [f"{query} research"]
        except Exception as e:
            print(f"生成回退关键词失败: {e}")
            return [f"{query} research"]

    def process(self, input_data: dict) -> dict:
        query = input_data.get('query', '')
        if not query:
            return {'keywords': ['health research'], 'status': 'error', 'message': '查询为空'}

        # 1. 判断是否为医学问题并进行PICO拆解
        pico_prompt = PICO_ANALYSIS_PROMPT.format(question=query)
        try:
            pico_response = self.llm.invoke("", pico_prompt).strip()
            pico_result = self._parse_pico_response(pico_response)
        except Exception as e:
            print(f"PICO分析失败: {e}，使用普通关键词生成")
            pico_result = {'is_medical': False, 'P': '未明确', 'I': '未明确', 'C': '未明确', 'O': '未明确'}

        # 2. 根据是否为医学问题生成关键词
        if pico_result['is_medical']:
            # 医学问题：基于PICO生成优化检索词
            keywords = self._generate_keywords_from_pico(pico_result, query)
        else:
            # 非医学问题：使用原有普通关键词逻辑
            keywords = self._generate_fallback_keywords(query)

        # 3. 返回结果，包含PICO信息（供后续使用）和关键词
        return {
            'keywords': keywords,
            'status': 'success',
            'message': '关键词生成完成',
            'pico_analysis': pico_result
        }
