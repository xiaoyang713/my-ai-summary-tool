import json
import requests
from datetime import datetime
import streamlit as st
from zhipuai import ZhipuAI

# 从 secrets 中读取 API 密钥（本地运行时也可直接填写，但部署时必须用 secrets）
try:
    zhipu_key = st.secrets["ZHIPUAI_API_KEY"]
    amap_key = st.secrets["AMAP_API_KEY"]
except:
    # 本地测试时可以直接写（注意不要提交到 GitHub）
    zhipu_key = "你的智谱API Key"   # 本地临时
    amap_key = "你的高德API Key"    # 本地临时

client = ZhipuAI(api_key=zhipu_key)

# ---------- 天气查询（高德地图）----------
def get_weather(city: str) -> str:
    # 1. 获取城市 adcode
    geocode_url = f"https://restapi.amap.com/v3/config/district?keywords={city}&subdistrict=0&key={amap_key}"
    try:
        resp = requests.get(geocode_url, timeout=5)
        data = resp.json()
        if data.get('status') == '1' and data.get('districts'):
            adcode = data['districts'][0].get('adcode')
            if not adcode:
                return f"未能找到城市 '{city}' 的编码"
        else:
            return f"城市 '{city}' 查询失败"
    except Exception as e:
        return f"查询城市编码出错: {e}"

    # 2. 查询天气
    weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={amap_key}"
    try:
        resp = requests.get(weather_url, timeout=5)
        data = resp.json()
        if data.get('status') == '1' and data.get('lives'):
            live = data['lives'][0]
            return (f"{live.get('city', city)}，天气：{live.get('weather')}，温度：{live.get('temperature')}°C，"
                    f"风向：{live.get('winddirection')}，风力：{live.get('windpower')}级，湿度：{live.get('humidity')}%")
        else:
            return f"获取天气失败: {data.get('info', '未知错误')}"
    except Exception as e:
        return f"查询天气出错: {e}"

# ---------- 计算器 ----------
def calculate(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "表达式包含非法字符"
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"

# ---------- 当前时间 ----------
def get_current_time() -> str:
    return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

# ---------- 工具描述 ----------
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式，如 '25*4'",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# ---------- Streamlit UI ----------
st.set_page_config(page_title="多工具 AI 助手", page_icon="🛠️")
st.title("🛠️ 多工具 AI 助手")
st.markdown("我可以帮你查天气、做计算、报时间。试试问：**北京天气** 或 **25*4等于多少**")

# 初始化会话历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
user_input = st.chat_input("输入你的问题...")
if user_input:
    # 显示用户消息
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 构建对话
    messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    # 第一次调用模型
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    msg = response.choices[0].message

    # 处理工具调用
    if msg.tool_calls:
        # 将 assistant 消息加入历史（需转换为字典）
        assistant_msg = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                } for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        for tc in msg.tool_calls:
            func_name = tc.function.name
            args = json.loads(tc.function.arguments)
            if func_name == "get_weather":
                city = args.get("city")
                result = get_weather(city)
            elif func_name == "calculate":
                expr = args.get("expression")
                result = calculate(expr)
            elif func_name == "get_current_time":
                result = get_current_time()
            else:
                result = "未知工具"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        final_resp = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
        )
        final_content = final_resp.choices[0].message.content
    else:
        final_content = msg.content

    # 显示助手回复
    with st.chat_message("assistant"):
        st.markdown(final_content)
    st.session_state.messages.append({"role": "assistant", "content": final_content})