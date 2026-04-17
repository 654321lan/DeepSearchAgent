"""
循证医学证据分级工具
严格遵循GRADE (Grading of Recommendations Assessment, Development and Evaluation) 官方标准
"""
import re
import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# ==================== GRADE 核心定义 ====================
class StudyType(Enum):
    """研究类型枚举（按GRADE证据质量优先级排序）"""
    SYSTEMATIC_REVIEW_META = "systematic_review_meta"  # 系统综述/Meta分析（最高级）
    RCT = "rct"                                            # 随机对照试验
    COHORT = "cohort"                                      # 队列研究
    CASE_CONTROL = "case_control"                          # 病例对照研究
    OBSERVATIONAL = "observational"                        # 观察性研究
    EXPERT_OPINION = "expert_opinion"                      # 专家意见/病例报告（最低级）

class GRADELevel(Enum):
    """GRADE证据质量等级"""
    HIGH = "GRADE 高级"      # 随机对照试验/高质量系统综述
    MODERATE = "GRADE 中级"  # 队列研究/降级后的RCT
    LOW = "GRADE 低级"        # 病例对照/降级后的队列研究
    VERY_LOW = "GRADE 极低级" # 观察性研究/专家意见

# ==================== 配置常量（可抽离到config.py） ====================
GRADE_CONFIG = {
    # 按研究类型的初始证据等级（遵循GRADE官方标准）
    "initial_level": {
        StudyType.SYSTEMATIC_REVIEW_META: GRADELevel.HIGH,
        StudyType.RCT: GRADELevel.HIGH,
        StudyType.COHORT: GRADELevel.MODERATE,
        StudyType.CASE_CONTROL: GRADELevel.LOW,
        StudyType.OBSERVATIONAL: GRADELevel.VERY_LOW,
        StudyType.EXPERT_OPINION: GRADELevel.VERY_LOW,
    },
    # 不精确性：按研究类型的样本量阈值
    "sample_size_threshold": {
        StudyType.SYSTEMATIC_REVIEW_META: 1000,
        StudyType.RCT: 300,
        StudyType.COHORT: 500,
        StudyType.CASE_CONTROL: 200,
        StudyType.OBSERVATIONAL: 100,
        StudyType.EXPERT_OPINION: 50,
    },
    # 核心期刊列表（简化版，可扩展）
    "core_journals": ["lancet", "nejm", "jama", "bmj", "nature", "science", "cell", "circulation", "diabetes care"],
    # 临床注册平台前缀
    "clinical_registry_prefixes": ["nct", "chi-ctr", "isrctn", "jprn", "umin-ctr"],
}

# ==================== 研究类型分类（LLM小样本+正则兜底） ====================
def classify_study_type(paper: Dict[str, Any], llm_client=None) -> Tuple[StudyType, float]:
    """
    分类研究类型
    优先用LLM小样本分类，失败则用正则兜底
    返回：(研究类型, 置信度)
    """
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    full_text = f"{title} {abstract}"

    # 1. 优先尝试LLM小样本分类（如果有LLM客户端）
    if llm_client:
        try:
            study_type, confidence = _classify_with_llm(full_text, llm_client)
            if confidence > 0.7:  # 置信度足够高，直接返回
                return study_type, confidence
        except Exception as e:
            logger.warning(f"LLM分类失败，降级到正则: {e}")

    # 2. 正则兜底（按优先级匹配）
    return _classify_with_regex(full_text)

def _classify_with_llm(text: str, llm_client) -> Tuple[StudyType, float]:
    """用LLM小样本分类研究类型"""
    system_prompt = """你是循证医学研究类型分类专家，仅根据提供的标题和摘要，判断研究类型。
严格按以下格式输出JSON，不要输出其他内容：
{
    "study_type": "rct/cohort/case_control/systematic_review_meta/observational/expert_opinion",
    "confidence": 0.0-1.0之间的浮点数
}

研究类型定义：
- systematic_review_meta: 系统综述、Meta分析、荟萃分析
- rct: 随机对照试验、Randomized Controlled Trial
- cohort: 队列研究、前瞻性研究
- case_control: 病例对照研究、回顾性研究
- observational: 其他观察性研究、横断面研究
- expert_opinion: 专家意见、病例报告、综述（非系统综述）

示例：
输入："一项随机、双盲、安慰剂对照试验，纳入300名2型糖尿病患者..."
输出：{"study_type": "rct", "confidence": 0.95}

输入："系统综述和Meta分析，纳入15项RCT共5000名患者..."
输出：{"study_type": "systematic_review_meta", "confidence": 0.98}
"""
    
    user_prompt = f"现在开始分类：\n{text}"
    
    # 使用正确的LLM调用方法
    try:
        response = llm_client.invoke(system_prompt, user_prompt)
    except AttributeError:
        # 如果llm_client没有invoke方法，尝试使用generate方法
        try:
            response = llm_client.generate(system_prompt, user_prompt)
        except Exception as e:
            raise ValueError(f"LLM调用失败: {str(e)}")
    
    # 解析JSON
    import json
    try:
        result = json.loads(response)
        study_type_str = result.get("study_type", "observational")
        confidence = result.get("confidence", 0.5)
        
        # 映射到枚举
        type_mapping = {
            "rct": StudyType.RCT,
            "cohort": StudyType.COHORT,
            "case_control": StudyType.CASE_CONTROL,
            "systematic_review_meta": StudyType.SYSTEMATIC_REVIEW_META,
            "observational": StudyType.OBSERVATIONAL,
            "expert_opinion": StudyType.EXPERT_OPINION,
        }
        return type_mapping.get(study_type_str, StudyType.OBSERVATIONAL), confidence
    except:
        raise ValueError("LLM返回格式错误")

def _classify_with_regex(text: str) -> Tuple[StudyType, float]:
    """正则兜底分类研究类型（优化匹配逻辑，减少误判）"""
    # 按优先级匹配，优化正则表达式精准度
    patterns = [
        (StudyType.SYSTEMATIC_REVIEW_META, r"(systematic review|meta[- ]analysis|荟萃分析|系统综述|guideline|指南)", 0.8),
        (StudyType.RCT, r"(randomized|randomised|rct|随机对照试验|随机.*双盲|随机.*安慰剂)", 0.75),
        (StudyType.COHORT, r"(cohort study|队列研究|前瞻性队列|回顾性队列)", 0.7),
        (StudyType.CASE_CONTROL, r"(case[- ]control study|病例对照研究|回顾性病例对照)", 0.7),
        (StudyType.OBSERVATIONAL, r"(observational study|cross[- ]sectional|横断面研究|描述性研究)", 0.6),
        (StudyType.EXPERT_OPINION, r"(expert opinion|case report|专家意见|病例报告|非系统综述)", 0.5),
    ]
    
    for study_type, pattern, confidence in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return study_type, confidence
    
    # 优化：默认返回前先检查是否有高等级关键词遗漏，避免直接返回低等级
    # 若文本中无任何匹配，优先标记为observational（而非直接极低级），但增加日志
    logger.warning(f"未匹配到明确研究类型，文本：{text[:100]}")
    return StudyType.OBSERVATIONAL, 0.3

# ==================== GRADE 5大核心降级因素判断 ====================
def _assess_risk_of_bias(paper: Dict[str, Any], study_type: StudyType) -> int:
    """
    评估研究局限性（Risk of Bias）
    返回降级数：0-2
    """
    abstract = paper.get("abstract", "").lower()
    title = paper.get("title", "").lower()
    full_text = f"{title} {abstract}"

    downgrade = 0

    # 仅对RCT评估研究局限性（系统综述/指南通常基于已有研究，不评估此因素）
    if study_type != StudyType.RCT:
        return 0

    # 检查是否随机
    if not re.search(r"(random|randomized|randomised|随机对照)", full_text, re.IGNORECASE):
        downgrade += 1

    # 检查是否盲法
    if not re.search(r"(blind|blind?ed|双盲|单盲|盲法)", full_text, re.IGNORECASE):
        downgrade += 1

    # 检查失访率（如果提到）
    loss_to_followup = re.search(r"(\d+%)\s*(loss|失访|脱落|withdrawal)", full_text, re.IGNORECASE)
    if loss_to_followup:
        try:
            rate = float(loss_to_followup.group(1).strip('%'))
            if rate > 20:
                downgrade += 1
        except:
            pass

    return min(downgrade, 2)  # 最多降2级

def _assess_imprecision(paper: Dict[str, Any], study_type: StudyType) -> int:
    """
    评估不精确性（Imprecision）
    按研究类型设置不同样本量阈值
    返回降级数：0-1
    """
    abstract = paper.get("abstract", "").lower()
    title = paper.get("title", "").lower()
    full_text = f"{title} {abstract}"

    # 系统综述/指南不评估不精确性（基于已有研究）
    if study_type == StudyType.SYSTEMATIC_REVIEW_META:
        return 0

    # 提取样本量
    sample_size = 0
    # 匹配 "n=100"、"纳入100名"、"共100例"
    matches = re.findall(r"(\d{2,5})\s*(patients|subjects|participants|名|例)", full_text, re.IGNORECASE)
    if matches:
        # 取最大的数字
        sample_size = max(int(m[0]) for m in matches)

    # 获取阈值
    threshold = GRADE_CONFIG["sample_size_threshold"].get(study_type, 100)

    # 样本量不足，降1级
    if sample_size < threshold:
        return 1
    return 0

def _assess_publication_bias(paper: Dict[str, Any]) -> int:
    """
    评估发表偏倚（Publication Bias）
    返回降级数：0-1
    """
    journal = paper.get("journal", "").lower()
    abstract = paper.get("abstract", "").lower()
    title = paper.get("title", "").lower()
    full_text = f"{title} {abstract}"

    # 扩展核心期刊列表（包括医学主要期刊和指南发布机构）
    extended_core_journals = GRADE_CONFIG["core_journals"] + [
        'hepatology', 'gastroenterology', 'american journal of gastroenterology',
        'clinical gastroenterology', 'gut', 'journal of hepatology',
        'who', 'cdc', 'nih', 'aasld', 'easl', 'apa', 'esa'
    ]

    # 加分项（不降）
    has_core_journal = any(cj in journal for cj in extended_core_journals)
    has_clinical_registry = any(rp in full_text for rp in GRADE_CONFIG["clinical_registry_prefixes"])
    has_funding = re.search(r"(fund|grant|基金|资助|supported by|funded by)", full_text, re.IGNORECASE)

    # 如果有核心期刊、临床注册或基金支持，不降
    if has_core_journal or has_clinical_registry or has_funding:
        return 0

    # 否则降1级
    return 1

# ==================== 主函数：GRADE证据分级 ====================
def get_evidence_level(paper: Dict[str, Any], llm_client=None) -> Tuple[GRADELevel, Dict[str, Any]]:
    """
    严格遵循GRADE官方标准进行证据分级
    返回：(GRADE等级, 分级详情字典)
    """
    # 初始化详情字典（防止为空）
    downgrade_details = {
        "study_type": "",
        "classification_confidence": 0.0,
        "initial_level": "",
        "risk_of_bias": 0,
        "imprecision": 0,
        "publication_bias": 0,
        "inconsistency": 0,
        "indirectness": 0,
        "total_downgrade": 0,
        "final_level": ""
    }
    
    try:
        # 1. 分类研究类型
        study_type, confidence = classify_study_type(paper, llm_client)
        downgrade_details["study_type"] = study_type.value
        downgrade_details["classification_confidence"] = confidence
        
        # 2. 获取初始证据等级
        initial_level = GRADE_CONFIG["initial_level"].get(study_type, GRADELevel.VERY_LOW)
        downgrade_details["initial_level"] = initial_level.value
        
        # 3. 计算降级因素
        downgrade_details["risk_of_bias"] = _assess_risk_of_bias(paper, study_type)
        downgrade_details["imprecision"] = _assess_imprecision(paper, study_type)
        downgrade_details["publication_bias"] = _assess_publication_bias(paper)

        # 计算总降级数
        total_downgrade = sum([
            downgrade_details["risk_of_bias"],
            downgrade_details["imprecision"],
            downgrade_details["publication_bias"],
            downgrade_details["inconsistency"],
            downgrade_details["indirectness"]
        ])
        downgrade_details["total_downgrade"] = total_downgrade

        # 4. 计算最终等级（修复降级逻辑）
        level_order = [GRADELevel.HIGH, GRADELevel.MODERATE, GRADELevel.LOW, GRADELevel.VERY_LOW]
        initial_index = level_order.index(initial_level)

        # 核心修复：level_order是从高到低排序，降级应该是加上降级数（不是减去）
        # 例如：高级(索引0) + 降3级 = 极低级(索引3)
        final_index = initial_index + total_downgrade
        # 确保索引在有效范围内 [0, len(level_order) - 1]
        final_index = max(0, min(final_index, len(level_order) - 1))

        final_level = level_order[final_index]
        downgrade_details["final_level"] = final_level.value
        
    except Exception as e:
        # 异常时兜底，确保详情不为空 + 日志记录
        logger.error(f"GRADE分级计算失败: {e}", exc_info=True)
        final_level = GRADELevel.VERY_LOW
        downgrade_details["final_level"] = final_level.value
        downgrade_details["initial_level"] = GRADELevel.VERY_LOW.value
    
    return final_level, downgrade_details

def get_evidence_priority(level: GRADELevel) -> int:
    """获取证据优先级（用于排序，数字越大优先级越高）"""
    priority_map = {
        GRADELevel.HIGH: 4,
        GRADELevel.MODERATE: 3,
        GRADELevel.LOW: 2,
        GRADELevel.VERY_LOW: 1,
    }
    return priority_map.get(level, 0)

# ==================== 证据溯源辅助函数 ====================
def extract_evidence_snippets(paper: Dict[str, Any], query: str) -> list:
    """
    从论文中提取与查询相关的证据片段
    用于证据溯源
    """
    abstract = paper.get("abstract", "")
    title = paper.get("title", "")
    full_text = f"{title} {abstract}"
    
    # 简单的关键词匹配提取片段
    # 后续可升级为语义相似度匹配
    query_keywords = query.lower().split()
    snippets = []
    
    # 按句子分割
    sentences = re.split(r'[.。！？!?]', full_text)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        # 检查是否包含查询关键词
        if any(kw in sentence.lower() for kw in query_keywords):
            snippets.append(sentence)
    
    return snippets[:3]  # 最多返回3个片段


# ==================== 敏感词过滤（学术模式） ====================
SENSITIVE_KEYWORDS = [
    # 医疗敏感词
    "治疗", "治愈", "诊断", "处方", "药方", "药物", "药品",
    # 其他需要过滤的关键词
    "自杀", "自残", "暴力", "毒品", "赌博",
    # 其他敏感内容
    "极端", "恐怖", "反动", "非法", "违法"
]

def filter_sensitive(query: str) -> bool:
    """
    检查查询是否包含敏感内容

    Args:
        query: 用户查询字符串

    Returns:
        bool: True 表示包含敏感内容，False 表示不包含
    """
    if not query:
        return False

    query_lower = query.lower()

    for keyword in SENSITIVE_KEYWORDS:
        if keyword in query_lower:
            return True

    return False