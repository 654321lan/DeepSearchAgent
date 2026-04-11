"""
Streamlit Web界面
为Deep Search Agent提供友好的Web界面
"""

import os
import sys
import streamlit as st
from datetime import datetime
import json

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import DeepSearchAgent, Config
from src.utils import load_config


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
        "zhipu": ["glm-4", "glm-4-plus", "glm-4v","glm-4.5-air"],
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

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
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

    with col2:
        st.header("状态信息")
        # 创建状态占位符，用于实时更新
        status_placeholder = st.empty()

    # 执行按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        start_research = st.button("开始研究", type="primary", use_container_width=True)

    # 验证配置
    if start_research:
        if not query.strip():
            st.error("请输入研究查询")
            return

        # 根据提供商验证对应的API Key
        if llm_provider == "zhipu" and not zhipu_key:
            st.error("请提供智谱 API Key")
            return

        if llm_provider == "deepseek" and not deepseek_key:
            st.error("请提供 DeepSeek API Key")
            return

        if llm_provider == "openai" and not openai_key:
            st.error("请提供 OpenAI API Key")
            return

        if not tavily_key:
            st.error("请提供 Tavily API Key")
            return

        # 创建配置
        config = Config(
            deepseek_api_key=deepseek_key if llm_provider == "deepseek" else None,
            openai_api_key=openai_key if llm_provider == "openai" else None,
            zhipu_api_key=zhipu_key if llm_provider == "zhipu" else None,
            tavily_api_key=tavily_key,
            default_llm_provider=llm_provider,
            deepseek_model=model_name if llm_provider == "deepseek" else "deepseek-chat",
            openai_model=model_name if llm_provider == "openai" else "gpt-4o-mini",
            zhipu_model=model_name if llm_provider == "zhipu" else "glm-4",
            max_reflections=max_reflections,
            max_search_results=max_search_results,
            max_content_length=max_content_length,
            output_dir="streamlit_reports"
        )

        # 执行研究
        execute_research(query, config, status_placeholder)


def update_status_display(placeholder, agent=None, message=None):
    """更新状态显示"""
    with placeholder.container():
        if agent and hasattr(agent, 'state'):
            progress = agent.get_progress_summary()
            st.metric("总段落数", progress['total_paragraphs'])
            st.metric("已完成", progress['completed_paragraphs'])
            st.progress(progress['progress_percentage'] / 100)
            if message:
                st.caption(f"📋 {message}")
        else:
            st.info(message if message else "尚未开始研究")


def execute_research(query: str, config: Config, status_placeholder):
    """执行研究"""
    try:
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 初始化Agent
        status_text.text("正在初始化Agent...")
        update_status_display(status_placeholder, message="正在初始化Agent...")
        agent = DeepSearchAgent(config)
        st.session_state.agent = agent

        progress_bar.progress(10)

        # 生成报告结构
        status_text.text("正在生成报告结构...")
        update_status_display(status_placeholder, agent, "正在生成报告结构...")
        agent._generate_report_structure(query)
        progress_bar.progress(20)

        # 处理段落
        total_paragraphs = len(agent.state.paragraphs)
        for i in range(total_paragraphs):
            paragraph_title = agent.state.paragraphs[i].title
            status_text.text(f"正在处理段落 {i+1}/{total_paragraphs}: {paragraph_title}")
            update_status_display(status_placeholder, agent, f"处理段落 {i+1}/{total_paragraphs}")

            # 初始搜索和总结
            agent._initial_search_and_summary(i)
            progress_value = 20 + (i + 0.5) / total_paragraphs * 60
            progress_bar.progress(int(progress_value))

            # 反思循环
            agent._reflection_loop(i)
            agent.state.paragraphs[i].research.mark_completed()

            progress_value = 20 + (i + 1) / total_paragraphs * 60
            progress_bar.progress(int(progress_value))

        # 生成最终报告
        status_text.text("正在生成最终报告...")
        update_status_display(status_placeholder, agent, "正在生成最终报告...")
        final_report = agent._generate_final_report()
        progress_bar.progress(90)

        # 保存报告
        status_text.text("正在保存报告...")
        update_status_display(status_placeholder, agent, "正在保存报告...")
        agent._save_report(final_report)
        progress_bar.progress(100)

        status_text.text("研究完成！")
        update_status_display(status_placeholder, agent, "✅ 研究完成！")

        # 显示结果
        display_results(agent, final_report)

    except Exception as e:
        st.error(f"研究过程中发生错误: {str(e)}")


def display_results(agent: DeepSearchAgent, final_report: str):
    """显示研究结果"""
    st.header("研究结果")

    # 结果标签页
    tab1, tab2, tab3 = st.tabs(["最终报告", "详细信息", "下载"])

    with tab1:
        st.markdown(final_report)

    with tab2:
        # 段落详情
        st.subheader("段落详情")
        for i, paragraph in enumerate(agent.state.paragraphs):
            with st.expander(f"段落 {i+1}: {paragraph.title}"):
                st.write("**预期内容:**", paragraph.content)
                st.write("**最终内容:**", paragraph.research.latest_summary[:300] + "..."
                        if len(paragraph.research.latest_summary) > 300
                        else paragraph.research.latest_summary)
                st.write("**搜索次数:**", paragraph.research.get_search_count())
                st.write("**反思次数:**", paragraph.research.reflection_iteration)

        # 搜索历史
        st.subheader("搜索历史")
        all_searches = []
        for paragraph in agent.state.paragraphs:
            all_searches.extend(paragraph.research.search_history)

        if all_searches:
            for i, search in enumerate(all_searches):
                with st.expander(f"搜索 {i+1}: {search.query}"):
                    st.write("**URL:**", search.url)
                    st.write("**标题:**", search.title)
                    st.write("**内容预览:**", search.content[:200] + "..." if len(search.content) > 200 else search.content)
                    if search.score:
                        st.write("**相关度评分:**", search.score)

    with tab3:
        # 下载选项
        st.subheader("下载报告")

        # Markdown下载
        st.download_button(
            label="下载Markdown报告",
            data=final_report,
            file_name=f"deep_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )

        # JSON状态下载
        state_json = agent.state.to_json()
        st.download_button(
            label="下载状态文件",
            data=state_json,
            file_name=f"deep_search_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


if __name__ == "__main__":
    main()
