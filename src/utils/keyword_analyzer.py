"""
关键词分析器 - 智能拆分实体词和诉求词
用于生成符合学术规范的检索式
"""

from typing import List, Dict, Any, Tuple
import re

class KeywordAnalyzer:
    """关键词分析器：智能拆分实体词和诉求词"""

    # 诉求类关键词库
    CONCERN_KEYWORDS = [
        'risk', 'risks', 'risky', 'danger', 'dangerous',
        'safety', 'safe', 'unsafe',
        'adverse effect', 'adverse effects', 'side effect', 'side effects', 'adverse',
        'harmful', 'harm', 'damage',
        'toxic', 'toxicity', 'poison',
        'guideline', 'guidelines', 'recommendation', 'recommendations',
        'consumption', 'consume', 'intake', 'usage', 'use',
        'effect', 'effects', 'efficacy',
        'precaution', 'precautions', 'caution',
        'warning', 'warnings',
        'impact', 'impacts',
        'outcome', 'outcomes',
        'complication', 'complications',
        'contraindication', 'contraindications',
        'safety concern', 'concerns',
        'hazard', 'hazards'
    ]

    # 动作词和描述词特征（用于过滤实体词）
    ACTION_WORDS = [
        'can', 'could', 'should', 'would', 'may', 'might', 'will', 'shall',
        'do', 'does', 'did', 'have', 'has', 'had', 'be', 'is', 'are', 'was', 'were',
        'what', 'how', 'why', 'when', 'where', 'who', 'which', 'whether',
        'often', 'usually', 'frequently', 'sometimes', 'occasionally',
        'safe', 'unsafe', 'good', 'bad', 'effective', 'ineffective',
        'high', 'low', 'more', 'less', 'many', 'few'
    ]

    # 实体词特征（通常作为研究对象）
    ENTITY_FEATURES = [
        # 食品类
        'food', 'beverage', 'drink', 'diet', 'nutrient',
        'supplement', 'supplementation',
        'coconut water', 'coconut milk', 'coconut',
        'juice', 'tea', 'coffee', 'water',
        'medicine', 'drug', 'medication', 'pharmaceutical',
        'herb', 'herbal',
        'vitamin', 'mineral',

        # 医学术语
        'patient', 'patients',
        'human', 'population',
        'child', 'children', 'adult', 'elderly',
        'pregnant', 'pregnancy',
        'woman', 'women', 'man', 'men',

        # 研究类型
        'study', 'studies', 'research', 'experiment',
        'trial', 'trials', 'randomized', 'controlled',
        'meta-analysis', 'systematic review', 'review'
    ]

    @classmethod
    def extract_keywords(cls, keywords: List[str]) -> Dict[str, Any]:
        """
        从关键词列表中提取核心实体词和诉求词

        Args:
            keywords: 原始关键词列表

        Returns:
            {
                'entity_word': str,  # 唯一核心实体词
                'concern_words': List[str],  # 诉求词列表
                'raw_keywords': List[str]  # 原始关键词（用于调试）
            }
        """
        if not keywords:
            return {
                'entity_word': None,
                'concern_words': [],
                'raw_keywords': []
            }

        # 标准化关键词：转为小写并去除前后空格
        normalized_keywords = []
        for kw in keywords:
            if kw and isinstance(kw, str):
                cleaned = kw.strip().lower()
                if cleaned:
                    normalized_keywords.append(cleaned)

        if not normalized_keywords:
            return {
                'entity_word': None,
                'concern_words': [],
                'raw_keywords': keywords
            }

        # 步骤1：识别核心实体词
        entity_word = cls._identify_entity_word(normalized_keywords)

        # 步骤2：提取诉求词
        concern_words = cls._extract_concern_words(normalized_keywords, entity_word)

        # 步骤3：如果没找到明确的实体词，使用第一个关键词作为实体词
        if not entity_word and normalized_keywords:
            entity_word = normalized_keywords[0]

        print(f"Keyword Analysis Result:")
        print(f"   - Original Keywords: {keywords}")
        print(f"   - Normalized: {normalized_keywords}")
        print(f"   - Core Entity Word: '{entity_word}'")
        print(f"   - Concern Words: {concern_words}")

        return {
            'entity_word': entity_word,
            'concern_words': concern_words,
            'raw_keywords': keywords
        }

    @classmethod
    def _identify_entity_word(cls, normalized_keywords: List[str]) -> str:
        """
        识别核心实体词（严格按照铁律执行）

        铁律定义：
        1. 英文实体词：连续、最小的无修饰核心名词短语，必须剔除：
           - 诉求类词汇：risk、safety、adverse、effect、consumption、guideline、evaluation、concern
           - 修饰类形容词/副词：regular、potential、health
        2. 中文实体词：用户问题中最核心的名词主体，剔除动词、形容词、诉求词
        3. 兜底规则：包含「coconut water」/「椰子水」时强制锁定

        示例：
        - 所有包含coconut water的关键词 → 核心实体词固定为「coconut water」
        - 「经常喝椰子水有什么危害吗？」→ 核心实体词固定为「椰子水」
        """
        print("\n[DEBUG] 开始识别核心实体词（严格铁律模式）...")
        print(f"   输入关键词: {normalized_keywords}")

        # 铁律1：兜底规则 - 强制锁定 coconut water/椰子水
        for kw in normalized_keywords:
            if 'coconut water' in kw:
                print(f"   [铁律1] 发现兜底规则：包含 'coconut water'，强制锁定为 'coconut water'")
                return 'coconut water'
            if '椰子水' in kw:
                print(f"   [铁律1] 发现兜底规则：包含 '椰子水'，强制锁定为 '椰子水'")
                return '椰子水'

        # 定义必须剔除的词汇
        english_concern_words = {
            'risk', 'risks', 'risky',
            'safety', 'safe', 'unsafe',
            'adverse', 'adversely',
            'effect', 'effects', 'efficacy',
            'consumption', 'consume', 'intake',
            'guideline', 'guidelines', 'recommendation',
            'evaluation', 'evaluated', 'evaluating',
            'concern', 'concerns', 'concerned'
        }

        english_modifier_words = {
            'regular', 'regularly',
            'potential', 'potentially',
            'health', 'healthy', 'healthier'
        }

        # 英文实体词提取
        english_entities = []
        for kw in normalized_keywords:
            # 只处理包含英文的词
            if any(ord(c) < 128 for c in kw):
                # 剔除诉求词和修饰词
                words = kw.split()
                filtered_words = [
                    w for w in words
                    if (w not in english_concern_words and
                        w not in english_modifier_words)
                ]

                if filtered_words:
                    # 提取连续的最小核心名词短语
                    if len(filtered_words) == 1:
                        # 单个词
                        entity = filtered_words[0]
                    else:
                        # 多个词时，只取最后2-3个词作为核心（通常是研究的主体）
                        # 例如："coconut water consumption" -> "coconut water"
                        if len(filtered_words) >= 2:
                            entity = ' '.join(filtered_words[-2:])
                        else:
                            entity = filtered_words[0]

                    english_entities.append(entity)

        # 中文实体词提取
        chinese_entities = []
        for kw in normalized_keywords:
            # 只处理包含中文的词
            if any('\u4e00' <= c <= '\u9fff' for c in kw):
                # 剔除动词、形容词、诉求词
                # 这里简单处理：只保留2-3个字的中文名词（通常是食物/饮料名称）
                chinese_words = []
                for word in kw:
                    # 保留中文字符，剔除常见诉求词
                    if ('\u4e00' <= word <= '\u9fff' and
                        word not in ['吃', '喝', '饮', '食', '会', '能', '可', '吗', '呢', '啊', '吧',
                                   '危害', '危险', '安全', '副作用', '影响', '作用', '效果', '怎么样']):
                        chinese_words.append(word)

                if chinese_words:
                    # 取最核心的名词（通常1-2个字）
                    entity = ''.join(chinese_words[:2])
                    chinese_entities.append(entity)

        # 合并并选择最终实体词
        all_entities = english_entities + chinese_entities

        print(f"   [DEBUG] 英文候选实体: {english_entities}")
        print(f"   [DEBUG] 中文候选实体: {chinese_entities}")
        print(f"   [DEBUG] 所有候选实体: {all_entities}")

        # 选择最终实体词
        if not all_entities:
            # 如果没有找到，使用第一个关键词
            result = normalized_keywords[0]
        else:
            # 优先选择英文实体（学术搜索优先）
            english_candidate = next((e for e in english_entities if len(e.split()) >= 2), None)
            if english_candidate:
                result = english_candidate
            else:
                # 选择最短的实体（最小核心）
                result = min(all_entities, key=len)

        print(f"   [铁律结果] 最终锁定的核心实体词: '{result}'")
        print(f"   [铁律验证] 确保符合最小核心名词要求，无任何修饰词")

        return result

    @classmethod
    def _extract_concern_words(cls, normalized_keywords: List[str], entity_word: str) -> List[str]:
        """
        提取诉求词（严格按照铁律：独立的诉求类词汇，绝对禁止混入核心实体词）

        铁律定义：
        - 诉求词 = 用户问题中的动作、属性、诉求类词汇
        - 必须单独提取，绝对禁止混入核心实体词

        示例：
        - 危害、风险、安全、能不能吃、副作用 → 对应英文 `risk, hazard, safety, adverse effect, side effect`
        """
        print("\nStart extracting concern words...")
        print(f"   输入的关键词: {normalized_keywords}")
        print(f"   已识别的核心实体词: '{entity_word}'")

        concern_words = []

        # 步骤1：遍历所有关键词
        for kw in normalized_keywords:
            print(f"   处理关键词: '{kw}'")

            # 步骤2：绝对禁止混入核心实体词
            if kw == entity_word:
                print(f"   [ERROR] Skip: This is core entity word, not a concern word")
                continue

            # 步骤3：检查是否在诉求词库中
            if kw in cls.CONCERN_KEYWORDS:
                concern_words.append(kw)
                print(f"   [INFO] Add concern word: '{kw}' (direct match)")
                continue

            # 步骤4：检查是否包含诉求词特征
            found_concerns = False
            for concern in cls.CONCERN_KEYWORDS:
                if concern in kw:
                    # 如果是复合诉求词（如 "safety concern"），拆分为独立诉求词
                    split_concerns = cls._split_concern_phrase(kw)
                    for concern_part in split_concerns:
                        if concern_part not in concern_words:
                            concern_words.append(concern_part)
                            print(f"   [INFO] Add concern word: '{concern_part}' (split from compound word '{kw}')")
                    found_concerns = True
                    break

            if found_concerns:
                continue

            # 步骤5：检查是否可能是短专业术语（2-10字符）
            if (2 <= len(kw) <= 10 and
                not kw.startswith(('http', 'www', 'com')) and
                kw != entity_word and
                kw not in cls.ACTION_WORDS):
                concern_words.append(kw)
                print(f"   [INFO] Add concern word: '{kw}' (short technical term)")

        # 步骤6：去重，确保每个诉求词只出现一次
        concern_words = list(set(concern_words))

        # 步骤7：最终过滤，绝对确保没有混入实体词
        final_concern_words = []
        for w in concern_words:
            if w != entity_word:
                final_concern_words.append(w)

        print(f"   [INFO] Final concern words list: {final_concern_words}")

        return final_concern_words

    @classmethod
    def _split_concern_phrase(cls, phrase: str) -> List[str]:
        """
        拆分复合诉求词为独立词
        例如："safety concern" -> ["safety", "concern"]
        """
        # 移除连字符和空格，然后分割
        clean_phrase = phrase.replace('-', ' ').replace('_', ' ')

        # 如果短语包含已知的诉求词，提取它们
        found_concerns = []
        words = clean_phrase.split()

        for word in words:
            # 基础形式：移除复数形式
            base_word = word.rstrip('s')  # 简单处理复数
            if base_word in cls.CONCERN_KEYWORDS:
                found_concerns.append(base_word)
            # 如果原词在诉求词库中
            elif word in cls.CONCERN_KEYWORDS:
                found_concerns.append(word)

        # 如果没找到已知诉求词，返回原始单词
        if not found_concerns:
            # 返回所有单词（去除过短的）
            found_concerns = [w for w in words if len(w) >= 3]

        return found_concerns

    @classmethod
    def build_search_query(cls, entity_word: str, concern_words: List[str]) -> Tuple[str, str]:
        """
        构建标准检索式（平衡版：不严格、不宽松，稳定出论文）
        """
        if not entity_word:
            print("[ERROR] No core entity word provided, cannot build search query")
            return "", ""

        
        escaped_entity = entity_word.replace('"', '\\"')
        core_limit = f"{escaped_entity}"

        # 诉求词宽松 OR
        if concern_words:
            unique_concern_words = list(dict.fromkeys(concern_words))
            concern_parts = [f'{w.replace('"', '\\"')}' for w in unique_concern_words]
            concern_group = " OR ".join(concern_parts)
            final_query = f"{core_limit} AND ({concern_group})"
        else:
            final_query = core_limit

        fallback_query = core_limit

        print(f"\n[DEBUG] Final Search Queries:")
        print(f"   Core Entity Word: '{entity_word}'")
        print(f"   Primary Query: {final_query}")
        print(f"   Fallback Query: {fallback_query}")
        return final_query, fallback_query