"""
Deep Search Agent主类
整合所有模块，实现完整的深度搜索流程
"""

import json
import os
import pickle
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List

from .llms import DeepSeekLLM, OpenAILLM, ZhipuLLM, BaseLLM
from .nodes import (
    ReportStructureNode,
    FirstSearchNode,
    ReflectionNode,
    FirstSummaryNode,
    ReflectionSummaryNode,
    ReportFormattingNode
)
from .state.state import State
from .tools import tavily_search
from .utils import Config, load_config, format_search_results_for_prompt


class DeepSearchAgent:
    """Deep Search Agent主类"""

    # 评估指标常量
    QUALITY_SCORE = "质量分"
    COMPLETENESS = "完整度"
    ACCURACY = "准确率"

    def __init__(self, config: Optional[Config] = None):
        """
        初始化Deep Search Agent

        Args:
            config: 配置对象，如果不提供则自动加载
        """
        # 加载配置
        self.config = config or load_config()

        # 初始化LLM客户端
        self.llm_client = self._initialize_llm()

        # 初始化节点
        self._initialize_nodes()

        # 状态
        self.state = State()

        # 新增属性：擅长领域
        self.domain_tags = ["科技", "综合"]

        # 新增属性：缓存配置
        self.enable_cache = True  # 默认启用缓存

        # 新增属性：历史质量评分
        self.history_score = 0.5

        # 新增属性：空闲/忙碌状态
        self.is_busy = False

        # 新增属性：搜索缓存
        self.search_cache = {}

        # 新增属性：查询缓存
        self.query_cache = {}
        self.query_cache_file = os.path.join(self.config.output_dir, "query_cache.pkl")

        # 缓存配置
        self.cache_ttl = None  # 缓存永不过期
        self.max_cache_size = 1000  # 最大缓存条目数

        # 尝试加载缓存的查询结果
        self._load_query_cache()

        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)

        print(f"Deep Search Agent 已初始化")
        print(f"使用LLM: {self.llm_client.get_model_info()}")
        print(f"本地缓存已启用: {self.query_cache_file}")

    def _generate_cache_key(self, query: str) -> str:
        """
        生成查询的唯一缓存键

        Args:
            query: 查询内容

        Returns:
            缓存键字符串
        """
        # 处理None值
        if query is None:
            query = ""
        # 使用SHA256哈希算法生成唯一键
        query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()
        return query_hash

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """
        检查缓存条目是否有效

        Args:
            cache_entry: 缓存条目

        Returns:
            bool: 是否有效
        """
        # 如果设置了TTL，检查是否过期
        if self.cache_ttl and 'timestamp' in cache_entry:
            cache_time = datetime.fromisoformat(cache_entry['timestamp'])
            elapsed = (datetime.now() - cache_time).total_seconds()
            return elapsed < self.cache_ttl

        # 默认永不过期
        return True

    def _load_query_cache(self):
        """
        从本地文件加载查询缓存
        """
        try:
            if os.path.exists(self.query_cache_file):
                with open(self.query_cache_file, 'rb') as f:
                    self.query_cache = pickle.load(f)
                print(f"已加载 {len(self.query_cache)} 条查询缓存")
            else:
                print("未找到缓存文件，将创建新的缓存")
                self.query_cache = {}
        except Exception as e:
            print(f"加载查询缓存失败: {str(e)}")
            self.query_cache = {}

    def _save_query_cache(self):
        """
        保存查询缓存到本地文件
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.query_cache_file), exist_ok=True)

            # 如果缓存过大，删除最旧的条目
            if len(self.query_cache) > self.max_cache_size:
                # 按时间排序，删除最旧的
                sorted_items = sorted(
                    self.query_cache.items(),
                    key=lambda x: x[1].get('timestamp', '1970-01-01T00:00:00')
                )
                items_to_remove = len(self.query_cache) - self.max_cache_size
                for key, _ in sorted_items[:items_to_remove]:
                    del self.query_cache[key]
                print(f"缓存清理：删除了 {items_to_remove} 条旧记录")

            # 保存到文件
            with open(self.query_cache_file, 'wb') as f:
                pickle.dump(self.query_cache, f)
        except Exception as e:
            print(f"保存查询缓存失败: {str(e)}")

    def get_cached_result(self, query: str) -> Optional[str]:
        """
        从缓存中获取查询结果

        Args:
            query: 查询内容

        Returns:
            缓存的结果，如果没有则返回None
        """
        if not self.enable_cache:
            return None

        cache_key = self._generate_cache_key(query)
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if self._is_cache_valid(cache_entry) and 'result' in cache_entry:
                print(f"缓存命中: {query[:30]}..." if len(query) > 30 else f"缓存命中: {query}")
                return cache_entry['result']

        return None

    def cache_result(self, query: str, result: str):
        """
        将查询结果存入缓存

        Args:
            query: 查询内容
            result: 要缓存的结果
        """
        try:
            if not self.enable_cache:
                return

            cache_key = self._generate_cache_key(query)
            self.query_cache[cache_key] = {
                'result': result,
                'timestamp': datetime.now().isoformat(),
                'query': query  # 保存原始查询用于调试
            }

            # 立即保存到文件
            self._save_query_cache()
            print(f"已缓存结果: {query[:30]}..." if len(query) > 30 else f"已缓存结果: {query}")
        except Exception as e:
            print(f"缓存结果时发生错误: {str(e)}")

    def clear_cache(self):
        """
        清空所有缓存
        """
        try:
            self.query_cache = {}
            if os.path.exists(self.query_cache_file):
                os.remove(self.query_cache_file)
            print("查询缓存已清空")
        except Exception as e:
            print(f"清空缓存失败: {str(e)}")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            缓存统计信息
        """
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
            'cache_file': self.query_cache_file,
            'cache_enabled': self.enable_cache,
            'cache_exists': os.path.exists(self.query_cache_file),
            'max_cache_size': self.max_cache_size,
            'cache_ttl': self.cache_ttl
        }

    def set_cache_config(self, enabled: bool = True, ttl: Optional[int] = None, max_size: int = 1000):
        """
        设置缓存配置

        Args:
            enabled: 是否启用缓存
            ttl: 缓存过期时间（秒），None表示永不过期
            max_size: 最大缓存条目数
        """
        self.enable_cache = enabled
        self.cache_ttl = ttl
        self.max_cache_size = max_size

        if ttl:
            print(f"缓存配置：启用={enabled}, TTL={ttl}秒, 最大条目={max_size}")
        else:
            print(f"缓存配置：启用={enabled}, TTL=永不过期, 最大条目={max_size}")

    def list_cached_queries(self, limit: int = 10) -> List[str]:
        """
        列出缓存的查询（显示部分内容）

        Args:
            limit: 最大显示数量

        Returns:
            缓存查询列表
        """
        queries = []
        count = 0

        for cache_entry in self.query_cache.values():
            if 'query' in cache_entry and count < limit:
                query = cache_entry['query']
                # 截断长查询
                display_query = query[:50] + "..." if len(query) > 50 else query
                queries.append(display_query)
                count += 1

        return queries

    def has_cached_result(self, query: str) -> bool:
        """
        检查查询是否在缓存中

        Args:
            query: 查询内容

        Returns:
            bool: 是否缓存了该查询
        """
        if not self.enable_cache:
            return False

        cache_key = self._generate_cache_key(query)
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            return self._is_cache_valid(cache_entry) and 'result' in cache_entry

        return False
    
    def _initialize_llm(self) -> BaseLLM:
        """初始化LLM客户端"""
        if self.config.default_llm_provider == "deepseek":
            return DeepSeekLLM(
                api_key=self.config.deepseek_api_key,
                model_name=self.config.deepseek_model
            )
        elif self.config.default_llm_provider == "openai":
            return OpenAILLM(
                api_key=self.config.openai_api_key,
                model_name=self.config.openai_model
            )
        elif self.config.default_llm_provider == "zhipu":
            return ZhipuLLM(
                api_key=self.config.zhipu_api_key,
                model_name=self.config.zhipu_model
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {self.config.default_llm_provider}")
    
    def _initialize_nodes(self):
        """初始化处理节点"""
        self.first_search_node = FirstSearchNode(self.llm_client)
        self.reflection_node = ReflectionNode(self.llm_client)
        self.first_summary_node = FirstSummaryNode(self.llm_client)
        self.reflection_summary_node = ReflectionSummaryNode(self.llm_client)
        self.report_formatting_node = ReportFormattingNode(self.llm_client)

    def _decompose_query(self, query: str) -> List[Dict[str, Any]]:
        """
        将复杂查询拆分为带优先级的子任务

        Args:
            query: 用户查询，如"分析2024新能源汽车销量及政策影响"

        Returns:
            子任务列表，每个子任务包含content、priority(1-3)、type(搜索/分析/验证)
        """
        # 极简Prompt，减少Token消耗
        prompt = f'将查询拆分为带优先级(1-3)的子任务，返回JSON格式（仅JSON，无多余文字）：{{"sub_tasks":[{{"content":"","priority":1,"type":"搜索"}}]}}\n查询：{query}'

        # 默认子任务（API调用失败时返回）
        default_sub_tasks = [
            {"content": query, "priority": 1, "type": "搜索"}
        ]

        try:
            # 复用现有的LLM客户端调用智谱API
            result = self.llm_client.generate_json(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500  # GLM-4.5-Air需要足够的token输出推理和JSON
            )

            # 提取子任务列表
            if "sub_tasks" in result and isinstance(result["sub_tasks"], list):
                # 验证并规范化每个子任务
                sub_tasks = []
                for task in result["sub_tasks"]:
                    if "content" in task:
                        sub_tasks.append({
                            "content": task["content"],
                            "priority": task.get("priority", 2),
                            "type": task.get("type", "搜索")
                        })
                return sub_tasks if sub_tasks else default_sub_tasks

            return default_sub_tasks

        except Exception as e:
            print(f"查询分解失败: {str(e)}，使用默认子任务")
            return default_sub_tasks

    def _generate_search_query(self, sub_task_content: str) -> List[str]:
        """
        根据子任务内容生成3个精准搜索词

        Args:
            sub_task_content: 子任务内容

        Returns:
            搜索词列表（最多3个，无重复）
        """
        prompt = f'生成3个精准无重复搜索词，返回JSON：{{"keywords":[]}}\n任务：{sub_task_content}'

        # 默认搜索词
        default_keywords = [sub_task_content]

        try:
            result = self.llm_client.generate_json(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1200  # GLM-4.5-Air需要足够token
            )

            if "keywords" in result and isinstance(result["keywords"], list):
                # 去重并限制最多3个
                keywords = list(dict.fromkeys(result["keywords"]))[:3]
                return keywords if keywords else default_keywords

            return default_keywords

        except Exception as e:
            print(f"搜索词生成失败: {str(e)}，使用默认搜索词")
            return default_keywords

    def _validate_content(self, search_content: str, original_query: str) -> Dict[str, Any]:
        """
        验证搜索内容与原始查询的相关性和质量

        Args:
            search_content: 搜索到的内容
            original_query: 原始查询

        Returns:
            包含score(0-1)和conclusion的字典
        """
        prompt = f'评估内容与查询的相关性，返回JSON：{{"score":0.0,"conclusion":"简短描述"}}\n查询：{original_query}\n内容：{search_content}'

        default_result = {"score": 0.5, "conclusion": "验证失败"}

        try:
            result = self.llm_client.generate_json(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )

            if "score" in result:
                return {
                    "score": min(max(float(result["score"]), 0.0), 1.0),
                    "conclusion": result.get("conclusion", "验证完成")
                }

            return default_result

        except Exception as e:
            print(f"内容验证失败: {str(e)}")
            return default_result

    def research(self, query: str, save_report: bool = True) -> str:
        """
        执行深度研究

        Args:
            query: 研究查询
            save_report: 是否保存报告到文件

        Returns:
            最终报告内容
        """
        print(f"\n{'='*60}")
        print(f"开始深度研究: {query}")
        print(f"{'='*60}")

        # 检查缓存 - 优先从缓存获取结果，不调用任何API
        cached_result = self.get_cached_result(query)
        if cached_result is not None:
            print("⚡ 从缓存获取结果，无需重新搜索！")
            if save_report:
                # 缓存的结果是最终报告
                self._save_report(cached_result)
                print(f"报告已保存（来自缓存）")
            return cached_result

        try:
            # Step 1: 生成报告结构
            self._generate_report_structure(query)

            # Step 2: 处理每个段落
            self._process_paragraphs()

            # Step 3: 生成最终报告
            final_report = self._generate_final_report()

            # Step 4: 保存报告
            if save_report:
                self._save_report(final_report)

            print(f"\n{'='*60}")
            print("深度研究完成！")
            print(f"{'='*60}")

            # 保存结果到缓存
            self.cache_result(query, final_report)
            print(f"研究结果已缓存")

            return final_report

        except Exception as e:
            print(f"研究过程中发生错误: {str(e)}")
            raise e
    
    def _generate_report_structure(self, query: str):
        """生成报告结构"""
        print(f"\n[步骤 1] 生成报告结构...")
        
        # 创建报告结构节点
        report_structure_node = ReportStructureNode(self.llm_client, query)
        
        # 生成结构并更新状态
        self.state = report_structure_node.mutate_state(state=self.state)
        
        print(f"报告结构已生成，共 {len(self.state.paragraphs)} 个段落:")
        for i, paragraph in enumerate(self.state.paragraphs, 1):
            print(f"  {i}. {paragraph.title}")
    
    def _process_paragraphs(self):
        """处理所有段落"""
        total_paragraphs = len(self.state.paragraphs)
        
        for i in range(total_paragraphs):
            print(f"\n[步骤 2.{i+1}] 处理段落: {self.state.paragraphs[i].title}")
            print("-" * 50)
            
            # 初始搜索和总结
            self._initial_search_and_summary(i)
            
            # 反思循环
            self._reflection_loop(i)
            
            # 标记段落完成
            self.state.paragraphs[i].research.mark_completed()
            
            progress = (i + 1) / total_paragraphs * 100
            print(f"段落处理完成 ({progress:.1f}%)")
    
    def _initial_search_and_summary(self, paragraph_index: int):
        """执行初始搜索和总结"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        # 准备搜索输入
        search_input = {
            "title": paragraph.title,
            "content": paragraph.content
        }
        
        # 生成搜索查询
        print("  - 生成搜索查询...")
        search_output = self.first_search_node.run(search_input)
        search_query = search_output["search_query"]
        reasoning = search_output["reasoning"]
        
        print(f"  - 搜索查询: {search_query}")
        print(f"  - 推理: {reasoning}")
        
        # 执行搜索
        print("  - 执行网络搜索...")
        search_results = tavily_search(
            search_query,
            max_results=self.config.max_search_results,
            timeout=self.config.search_timeout,
            api_key=self.config.tavily_api_key
        )
        
        if search_results:
            print(f"  - 找到 {len(search_results)} 个搜索结果")
            for j, result in enumerate(search_results, 1):
                try:
                    print(f"    {j}. {result['title'][:50]}...")
                except UnicodeEncodeError:
                    print(f"    {j}. {result['title'][:50].encode('utf-8', 'replace').decode('utf-8')}...")
        else:
            print("  - 未找到搜索结果")
        
        # 更新状态中的搜索历史
        paragraph.research.add_search_results(search_query, search_results)
        
        # 生成初始总结
        print("  - 生成初始总结...")
        summary_input = {
            "title": paragraph.title,
            "content": paragraph.content,
            "search_query": search_query,
            "search_results": format_search_results_for_prompt(
                search_results, self.config.max_content_length
            )
        }
        
        # 更新状态
        self.state = self.first_summary_node.mutate_state(
            summary_input, self.state, paragraph_index
        )
        
        print("  - 初始总结完成")
    
    def _reflection_loop(self, paragraph_index: int):
        """执行反思循环"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        for reflection_i in range(self.config.max_reflections):
            print(f"  - 反思 {reflection_i + 1}/{self.config.max_reflections}...")
            
            # 准备反思输入
            reflection_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # 生成反思搜索查询
            reflection_output = self.reflection_node.run(reflection_input)
            search_query = reflection_output["search_query"]
            reasoning = reflection_output["reasoning"]
            
            print(f"    反思查询: {search_query}")
            print(f"    反思推理: {reasoning}")
            
            # 执行反思搜索
            search_results = tavily_search(
                search_query,
                max_results=self.config.max_search_results,
                timeout=self.config.search_timeout,
                api_key=self.config.tavily_api_key
            )
            
            if search_results:
                print(f"    找到 {len(search_results)} 个反思搜索结果")
            
            # 更新搜索历史
            paragraph.research.add_search_results(search_query, search_results)
            
            # 生成反思总结
            reflection_summary_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "search_query": search_query,
                "search_results": format_search_results_for_prompt(
                    search_results, self.config.max_content_length
                ),
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # 更新状态
            self.state = self.reflection_summary_node.mutate_state(
                reflection_summary_input, self.state, paragraph_index
            )
            
            print(f"    反思 {reflection_i + 1} 完成")
    
    def _generate_final_report(self) -> str:
        """生成最终报告"""
        print(f"\n[步骤 3] 生成最终报告...")
        
        # 准备报告数据
        report_data = []
        for paragraph in self.state.paragraphs:
            report_data.append({
                "title": paragraph.title,
                "paragraph_latest_state": paragraph.research.latest_summary
            })
        
        # 格式化报告
        try:
            final_report = self.report_formatting_node.run(report_data)
        except Exception as e:
            print(f"LLM格式化失败，使用备用方法: {str(e)}")
            final_report = self.report_formatting_node.format_report_manually(
                report_data, self.state.report_title
            )
        
        # 更新状态
        self.state.final_report = final_report
        self.state.mark_completed()
        
        print("最终报告生成完成")
        return final_report
    
    def _save_report(self, report_content: str):
        """保存报告到文件"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in self.state.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        query_safe = query_safe.replace(' ', '_')[:30]
        
        filename = f"deep_search_report_{query_safe}_{timestamp}.md"
        filepath = os.path.join(self.config.output_dir, filename)
        
        # 保存报告
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"报告已保存到: {filepath}")
        
        # 保存状态（如果配置允许）
        if self.config.save_intermediate_states:
            state_filename = f"state_{query_safe}_{timestamp}.json"
            state_filepath = os.path.join(self.config.output_dir, state_filename)
            self.state.save_to_file(state_filepath)
            print(f"状态已保存到: {state_filepath}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return self.state.get_progress_summary()
    
    def load_state(self, filepath: str):
        """从文件加载状态"""
        self.state = State.load_from_file(filepath)
        print(f"状态已从 {filepath} 加载")
    
    def save_state(self, filepath: str):
        """保存状态到文件"""
        self.state.save_to_file(filepath)
        print(f"状态已保存到 {filepath}")

    def _match_task_to_agent(self, sub_task_content: str) -> bool:
        """
        判断子任务内容是否匹配当前Agent的domain_tags擅长领域

        Args:
            sub_task_content: 子任务内容

        Returns:
            bool: 是否匹配（True/False）
        """
        # 简单的关键词匹配逻辑
        task_content_lower = sub_task_content.lower()

        # 检查任务内容是否包含任何domain_tags中的关键词
        for tag in self.domain_tags:
            if tag.lower() in task_content_lower:
                return True

        return False

    def _need_research(self, validation_score: float) -> bool:
        """
        判断是否需要重新搜索

        Args:
            validation_score: 验证分数

        Returns:
            bool: 是否需要重新搜索（True=需要，False=通过）
        """
        return validation_score < 0.7

    def _evaluate_task(self, quality_score: float, completeness: float, accuracy: float) -> float:
        """
        计算任务的综合得分

        Args:
            quality_score: 质量分 (0-1)
            completeness: 完整度 (0-1)
            accuracy: 准确率 (0-1)

        Returns:
            float: 综合得分 (0-1)
        """
        # 确保输入值在0-1范围内
        quality_score = max(0.0, min(1.0, quality_score))
        completeness = max(0.0, min(1.0, completeness))
        accuracy = max(0.0, min(1.0, accuracy))

        # 权重：质量分0.5、完整度0.3、准确率0.2
        weighted_score = (
            quality_score * 0.5 +
            completeness * 0.3 +
            accuracy * 0.2
        )

        # 确保结果在0-1范围内
        return max(0.0, min(1.0, weighted_score))

    def _log_experiment(self, query: str, score: float, mode: str, duration: float) -> Dict[str, Any]:
        """
        记录实验数据

        Args:
            query: 查询内容
            score: 得分
            mode: 模式（如：normal, fast, detailed）
            duration: 耗时（秒）

        Returns:
            Dict[str, Any]: 实验数据字典
        """
        experiment_data = {
            "query": query,
            "score": score,
            "mode": mode,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "agent_info": {
                "domain_tags": self.domain_tags,
                "history_score": self.history_score,
                "is_busy": self.is_busy
            }
        }

        return experiment_data

  
    def _api_retry(self, max_retries: int, base_wait_time: float) -> Dict[str, Any]:
        """
        指数退避重试逻辑模拟

        Args:
            max_retries: 最大重试次数
            base_wait_time: 基础等待时间（秒）

        Returns:
            Dict[str, Any]: 重试策略信息
        """
        retry_strategy = {
            "max_retries": max_retries,
            "base_wait_time": base_wait_time,
            "retry_sequence": []
        }

        try:
            for i in range(max_retries):
                # 指数退避：等待时间 = base_wait_time * 2^i
                wait_time = base_wait_time * (2 ** i)
                retry_strategy["retry_sequence"].append({
                    "attempt": i + 1,
                    "wait_time": wait_time,
                    "total_wait": sum(base_wait_time * (2 ** j) for j in range(i + 1))
                })
        except Exception as e:
            print(f"生成重试策略时发生错误: {str(e)}")

        return retry_strategy

    def _simulate_task_migration(self, target_agent_id: str) -> Dict[str, Any]:
        """
        根据Agent负载状态，模拟任务迁移

        Args:
            target_agent_id: 目标Agent ID

        Returns:
            Dict[str, Any]: 迁移决策信息
        """
        try:
            migration_decision = {
                "source_agent_id": "current",
                "target_agent_id": target_agent_id,
                "is_migratable": False,
                "reason": "",
                "estimated_gain": 0.0,
                "estimated_cost": 0.0
            }

            # 判断是否可以迁移
            if self.is_busy:
                # 当前Agent忙碌，可以尝试迁移负载
                if target_agent_id != "current":
                    # 模拟计算迁移收益和成本
                    migration_decision["is_migratable"] = True
                    migration_decision["reason"] = "当前Agent繁忙，负载过高"

                    # 基于历史质量评分计算迁移收益
                    base_gain = self.history_score * 0.8
                    migration_decision["estimated_gain"] = round(base_gain, 2)

                    # 迁移成本：基于网络延迟和数据大小（这里简化为固定值）
                    migration_decision["estimated_cost"] = 0.2
                else:
                    migration_decision["reason"] = "目标Agent是当前Agent，无需迁移"
            else:
                migration_decision["reason"] = "当前Agent空闲，无需迁移"
                migration_decision["estimated_gain"] = 0.0
                migration_decision["estimated_cost"] = 0.0

            return migration_decision
        except Exception as e:
            print(f"模拟任务迁移时发生错误: {str(e)}")
            # 返回默认的迁移决策
            return {
                "source_agent_id": "current",
                "target_agent_id": target_agent_id,
                "is_migratable": False,
                "reason": f"迁移评估失败: {str(e)}",
                "estimated_gain": 0.0,
                "estimated_cost": 0.0
            }

    def _integrate_results(self, task_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        整合子任务结果，去重、排序、生成结构化报告

        Args:
            task_results: 子任务结果列表，每项包含:
                - sub_task: 子任务信息(content, priority, type)
                - search_results: 搜索结果列表
                - validation: 验证结果(score, conclusion)

        Returns:
            结构化报告字典，包含总览、分任务详情、验证总结
        """
        default_report = {
            "overview": "整合失败",
            "tasks": [],
            "validation_summary": {"avg_score": 0.0, "conclusions": []}
        }

        try:
            if not task_results:
                return default_report

            # 去重：基于子任务content
            seen_contents = set()
            unique_results = []
            for result in task_results:
                content = result.get("sub_task", {}).get("content", "")
                if content and content not in seen_contents:
                    seen_contents.add(content)
                    unique_results.append(result)

            # 按优先级排序(1最高)
            sorted_results = sorted(
                unique_results,
                key=lambda x: x.get("sub_task", {}).get("priority", 3)
            )

            # 按验证分数从高到低排序，高分内容优先展示
            sorted_results = sorted(
                sorted_results,
                key=lambda x: x.get("validation", {}).get("score", 0.0),
                reverse=True
            )

            # 构建分任务详情
            tasks_detail = []
            total_score = 0.0
            conclusions = []

            for result in sorted_results:
                sub_task = result.get("sub_task", {})
                validation = result.get("validation", {})
                search_results = result.get("search_results", [])

                # 提取搜索结果摘要
                search_summary = [
                    {"title": r.get("title", ""), "url": r.get("url", "")}
                    for r in search_results[:3] if isinstance(r, dict)
                ]

                tasks_detail.append({
                    "content": sub_task.get("content", ""),
                    "priority": sub_task.get("priority", 3),
                    "type": sub_task.get("type", ""),
                    "search_count": len(search_results),
                    "search_summary": search_summary,
                    "score": validation.get("score", 0.0),
                    "conclusion": validation.get("conclusion", "")
                })

                score = validation.get("score", 0.0)
                if isinstance(score, (int, float)):
                    total_score += score

                conclusion = validation.get("conclusion", "")
                if conclusion:
                    conclusions.append(conclusion)

            # 生成总览
            task_count = len(sorted_results)
            avg_score = total_score / task_count if task_count > 0 else 0.0

            overview = f"共整合{task_count}个子任务，平均验证分数{avg_score:.2f}"

            return {
                "overview": overview,
                "tasks": tasks_detail,
                "validation_summary": {
                    "avg_score": round(avg_score, 2),
                    "conclusions": list(dict.fromkeys(conclusions))
                }
            }

        except Exception as e:
            print(f"结果整合失败: {str(e)}")
            return default_report

    

def create_agent(config_file: Optional[str] = None) -> DeepSearchAgent:
    """
    创建Deep Search Agent实例的便捷函数
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        DeepSearchAgent实例
    """
    config = load_config(config_file)
    return DeepSearchAgent(config)
