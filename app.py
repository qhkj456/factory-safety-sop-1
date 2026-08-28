from datetime import datetime
import streamlit as st
from sentence_transformers import SentenceTransformer
import numpy as np
import requests

# ========== 钉钉机器人推送配置（已填好你的地址）==========
DINGTALK_WEBHOOK = "jgdashjpojkpojjpoa[ppgjp[aogp[ikpae"


def push_log_to_dingtalk(log_text):
    """每次确认后，自动把日志推送到钉钉群"""
    if "这里填你的Token" in DINGTALK_WEBHOOK:
        return

    if "工厂SOP" not in log_text:
        content = f"🏭 工厂SOP使用记录\n\n{log_text}"
    else:
        content = log_text

    data = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    headers = {"Content-Type": "application/json"}

    try:
        requests.post(DINGTALK_WEBHOOK, json=data, timeout=5)
    except Exception:
        pass


# ========== 模型只加载一次 ==========
if 'model' not in st.session_state:
    st.write(">>> 正在加载模型，请稍候...")
    whitelist = ["张三", "李四", "王五"]

    docs = [
        "【操作】焊接前准备\n【步骤1】先检查焊机接地线是否连接牢固\n【步骤2】再确认焊枪绝缘层无破损\n【步骤3】最后佩戴防护面罩和皮手套",
        "【操作】火灾应急处理\n【步骤1】先按下最近位置的急停按钮\n【步骤2】再切断设备总电源\n【步骤3】最后使用干粉灭火器扑救初起火灾",
        "【操作】机器人异常处理\n【步骤1】先观察机器人振动幅度和报警代码\n【步骤2】再按下暂停键停止当前程序\n【步骤3】最后通知设备维护人员检查"
    ]

    model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

    doc_vecs = model.encode(docs)
    doc_vecs = doc_vecs / np.linalg.norm(doc_vecs, axis=1, keepdims=True)

    taboo_docs = [
        "❌ 严禁湿手操作电气设备",
        "❌ 严禁不戴防护面罩进行电弧焊",
        "❌ 严禁在油漆未干工件上直接焊接",
        "❌ 严禁用水扑救电气火灾",
        "❌ 严禁未切断电源进行设备维修",
        "❌ 严禁戴手套操作旋转主轴",
        "❌ 严禁单手操作大型工件",
        "❌ 严禁超载使用起重设备",
        "❌ 严禁在吊物下方站立或行走",
        "❌ 严禁未系安全带进行高空作业"
    ]

    taboo_vecs = model.encode(taboo_docs)
    taboo_vecs = taboo_vecs / np.linalg.norm(taboo_vecs, axis=1, keepdims=True)

    st.write(">>> 模型加载完成！现在可以循环提问。\n")

    st.session_state.whitelist = whitelist
    st.session_state.docs = docs
    st.session_state.model = model
    st.session_state.doc_vecs = doc_vecs
    st.session_state.taboo_docs = taboo_docs
    st.session_state.taboo_vecs = taboo_vecs

    st.session_state.logged_in = False
    st.session_state.current_name = None
    st.session_state.show_result = False

    st.session_state.total_queries = 0
    st.session_state.today_queries = 0
    st.session_state.today_date = datetime.now().strftime("%Y-%m-%d")
    st.session_state.recent_logs = []

# ========== 左侧管理后台 ==========
with st.sidebar:
    st.markdown("### 📊 管理后台")

    today = datetime.now().strftime("%Y-%m-%d")
    if today != st.session_state.today_date:
        st.session_state.today_date = today
        st.session_state.today_queries = 0

    st.info(f"总查询次数：**{st.session_state.total_queries}**")
    st.info(f"今日查询：**{st.session_state.today_queries}**")

    if len(st.session_state.recent_logs) > 0:
        st.markdown("### 📝 最近确认记录")
        for log in st.session_state.recent_logs[-5:][::-1]:
            st.caption(log)

# ========== 外层循环：姓名登录层 ==========
if not st.session_state.logged_in:
    st.title("工厂SOP智能查询系统")
    st.subheader("【员工登录】")

    name = st.text_input("请输入你的名字:")

    if st.button("登录"):
        whitelist = st.session_state.whitelist
        if name not in whitelist:
            st.error("名字无效")
        else:
            st.session_state.logged_in = True
            st.session_state.current_name = name
            st.success(f"欢迎{name},现在可以继续提问")
            st.rerun()

# ========== 内层循环：问题查询层 ==========
else:
    st.success(f"当前用户：{st.session_state.current_name}")

    if st.button("退出登录"):
        st.session_state.logged_in = False
        st.session_state.current_name = None
        st.session_state.show_result = False
        st.rerun()

    query = st.text_input("请输入问题（输入'退出'结束系统）：")

    if st.button("查询"):
        if query == "退出":
            st.session_state.logged_in = False
            st.session_state.current_name = None
            st.session_state.show_result = False
            st.rerun()
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            if today != st.session_state.today_date:
                st.session_state.today_date = today
                st.session_state.today_queries = 0

            st.session_state.total_queries += 1
            st.session_state.today_queries += 1

            model = st.session_state.model
            doc_vecs = st.session_state.doc_vecs
            docs = st.session_state.docs

            # ========== 查询扩展（Level 1）==========
            expand_dict = {
                "焊接": ["焊接", "电焊", "电弧焊", "点焊", "氩弧焊"],
                "电焊": ["焊接", "电焊", "电弧焊", "点焊", "氩弧焊"],
                "电弧焊": ["焊接", "电焊", "电弧焊", "点焊", "氩弧焊"],
                "CNC": ["CNC", "加工中心", "数控机床", "主轴"],
                "着火": ["着火", "火灾", "起火", "燃烧"],
                "火灾": ["着火", "火灾", "起火", "燃烧"],
                "吊装": ["吊装", "起重", "吊钩", "吊车"],
                "机器人": ["机器人", "机械臂", "机械手"]
            }

            expanded_queries = [query]
            for keyword, synonyms in expand_dict.items():
                if keyword in query:
                    for syn in synonyms:
                        if syn != keyword:
                            new_query = query.replace(keyword, syn)
                            if new_query not in expanded_queries:
                                expanded_queries.append(new_query)

            query_vecs_list = []
            for q in expanded_queries:
                q_vec = model.encode([q])
                q_vec = q_vec / np.linalg.norm(q_vec)
                query_vecs_list.append(q_vec)

            query_vec = np.mean(query_vecs_list, axis=0)
            query_vec = query_vec / np.linalg.norm(query_vec)

            scores = np.dot(doc_vecs, query_vec.T).flatten()
            best_idx = np.argmax(scores)

            taboo_vecs = st.session_state.taboo_vecs
            taboo_scores = np.dot(taboo_vecs, query_vec.T).flatten()

            # ========== 关键词双引擎融合 ==========
            taboo_docs = st.session_state.taboo_docs
            keyword_boost = np.zeros(len(taboo_docs))

            for keyword, synonyms in expand_dict.items():
                for syn in synonyms:
                    if syn in query:
                        for idx, doc in enumerate(taboo_docs):
                            if syn in doc:
                                keyword_boost[idx] += 0.15

            taboo_scores = taboo_scores + keyword_boost

            all_idx = np.argsort(taboo_scores)[::-1]
            high_risk = all_idx[0:20].tolist()
            medium_risk = all_idx[20:30].tolist()

            st.session_state.last_query = query
            st.session_state.last_best_idx = int(best_idx)
            st.session_state.last_scores = scores
            st.session_state.last_taboo_scores = taboo_scores
            st.session_state.high_risk = high_risk
            st.session_state.medium_risk = medium_risk
            st.session_state.show_result = True
            st.rerun()

    if st.session_state.show_result:
        docs = st.session_state.docs
        best_idx = st.session_state.last_best_idx

        st.write("最相关", docs[best_idx])
        st.write("最高分", st.session_state.last_scores[best_idx])

        taboo_docs = st.session_state.taboo_docs
        taboo_scores = st.session_state.last_taboo_scores
        high_risk = st.session_state.high_risk
        medium_risk = st.session_state.medium_risk

        st.subheader("【系统自动匹配的安全禁忌】")

        if len(high_risk) > 0:
            st.markdown("**🔴 高危禁忌（排名前20）**")
            for i, idx in enumerate(high_risk, 1):
                st.error(f"{i}. {taboo_docs[idx]} （相关度：{taboo_scores[idx]:.4f}）")

        if len(medium_risk) > 0:
            st.markdown("**🟡 中等建议（排名21-30）**")
            for i, idx in enumerate(medium_risk, 1):
                st.warning(f"{i}. {taboo_docs[idx]} （相关度：{taboo_scores[idx]:.4f}）")

        name = st.session_state.current_name

        confirm = st.text_input(f"{name},请阅读后输入‘确认’：")

        if st.button("提交确认"):
            if confirm == "确认":
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                query = st.session_state.last_query

                total_taboo = len(high_risk) + len(medium_risk)

                log_text = f"【系统日志】{name} | 查询：{query} | 结果：{docs[best_idx]} | 提取禁忌数：{total_taboo}条 | 确认：{confirm} | 时间：{now}"
                st.success(log_text)

                try:
                    with open("log.txt", "a", encoding="utf-8") as f:
                        f.write(log_text + "\n")
                except:
                    pass

                # ========== 推送到钉钉群 ==========
                push_log_to_dingtalk(log_text)

                st.session_state.recent_logs.append(
                    f"{name} | {query} | {now}"
                )
                if len(st.session_state.recent_logs) > 20:
                    st.session_state.recent_logs.pop(0)

                try:
                    with open("log.txt", "r", encoding="utf-8") as f:
                        log_content = f.read()
                    st.download_button(
                        label="📥 下载审计日志备份",
                        data=log_content,
                        file_name=f"工厂SOP日志_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
                except:
                    pass

                st.session_state.show_result = False
                st.rerun()
            else:
                st.error("请重新输入:")
