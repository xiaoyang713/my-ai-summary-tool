import streamlit as st
from zhipuai import ZhipuAI

# 从 secrets 读取 API Key（如果你已配置 .streamlit/secrets.toml）
# 或者临时直接写（仅本地测试，不要上传到 GitHub）
client = ZhipuAI(api_key=st.secrets["ZHIPUAI_API_KEY"])  # 推荐
# 或者直接写 client = ZhipuAI(api_key="你的智谱API Key")

st.set_page_config(page_title="AI 文件总结工具", page_icon="📄")
st.title("📄 AI 文件总结工具")
st.markdown("上传一个 **.txt** 文件，AI 会自动为你总结内容。")

uploaded_file = st.file_uploader("选择文本文件", type=["txt"])

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8")
    with st.expander("查看文件内容预览"):
        st.text(content[:500] + ("..." if len(content) > 500 else ""))
    if st.button("✨ 开始总结", type="primary"):
        with st.spinner("AI 正在思考中..."):
            prompt = f"请对以下内容进行简洁的总结：\n\n{content}"
            try:
                response = client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5
                )
                summary = response.choices[0].message.content
                st.success("总结结果：")
                st.write(summary)
            except Exception as e:
                st.error(f"调用AI时出错：{e}")