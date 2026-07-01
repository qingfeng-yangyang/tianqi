import os
import requests
import smtplib
from email.mime.text import MIMEText
from openai import OpenAI

def run_agent():
    # ===== 1. 获取 GitHub 保险柜里的密钥 =====
    email = os.environ["EMAIL"]
    app_password = os.environ["APP_PASSWORD"]
    ark_key = os.environ["ARK_API_KEY"]

    # ===== 2. 气象数据深度抓取 (保留云量、能见度等追光指标) =====
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=22.35&longitude=113.30"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability,cloud_cover,visibility"
        "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&timezone=Asia%2FShanghai"
    )
    
    try:
        weather_res = requests.get(url).json()
        
        # 提取【实时】数据
        current = weather_res["current"]
        cur_temp = current["temperature_2m"]
        cur_humidity = current["relative_humidity_2m"]
        cur_wind = current["wind_speed_10m"]
        
        # 提取【未来一小时】与【宏观追光】数据
        hourly = weather_res["hourly"]
        next_temp = hourly["temperature_2m"][1]       
        next_pop = hourly["precipitation_probability"][1] 
        next_cloud = hourly["cloud_cover"][1]         
        next_vis = hourly["visibility"][1]            
        
        # 提取【全天大局】
        daily = weather_res["daily"]
        temp_max = daily["temperature_2m_max"][0]
        temp_min = daily["temperature_2m_min"][0]
        sunrise = daily["sunrise"][0].split("T")[-1] 
        sunset = daily["sunset"][0].split("T")[-1]

        # 封装给 AI 的数据流
        user_weather_data = f"""
- 目标区域经纬度: 22.35, 113.30
- 实时天气: 温度 {cur_temp}°C / 湿度 {cur_humidity}% / 风速 {cur_wind} km/h
- 今日极端温差: {temp_min}°C ~ {temp_max}°C
- 日出时刻: {sunrise} | 日落时刻: {sunset}
- 未来一小时精细预报: 温度 {next_temp}°C / 降水概率 {next_pop}% / 云量 {next_cloud}% / 能见度 {next_vis / 1000:.1f} km
"""
    except Exception as e:
        print(f"气象数据抓取失败：{e}")
        return

    # ===== 3. AI 核心推演 =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""# Role
你是一个兼具顶级气象学家视角、风光摄影师灵魂、以及极简主义管家属性的智能体。

# Task
稍后你将通过工具读取今日的完整气象数据。你需要完成两个维度的分析：
1. 【结构化基础看板】：提取并精炼当前的实时数据与短时数据，给出最直观的体感、穿衣和随身物品建议。
2. 【大自然追光预测】：自主推演今日的气象数字（云量、能见度、湿度等）是否会产生化学反应，在本地触发罕见自然奇观（如彩虹、火烧云、平流雾、耶稣光、特殊天象）。

# Rules (硬性约束)
1. 【极简与克制】：字数总共控制在 200 字以内。拒绝一切“好的”、“经过分析”等废话前缀，严格按照格式直接输出。
2. 【看板流必出】：严格按照下方指定的 [基础看板] 模板输出，不允许合并或漏掉字段。
   - “实际体感温度”必须根据当前温度、湿度和风速综合评估得出。
   - “未来一小时状况”必须精准指出接下来一小时是否有突发降水或天气剧变。
3. 【奇观流按需】：
   - 如果评估后今天没有任何值得特意推开窗、抬头、或出门捕捉的自然奇观，关于奇观的部分【必须保持绝对空白】，不返回任何文字，严格节省 token。
   - 只有当某项奇观的触发几率大于 70% 时，才在看板下方空一行单独输出：【奇观预警】、触发时刻、以及极具画面感的视觉描述。

# 今日原始气象数据流：
[DATA_START]
{user_weather_data}
[DATA_END]

# 严格输出格式：
[基础看板]
- 城市：(根据坐标自行判断，通常为珠海)
- 实时天气：(当前温度 / 湿度 / 风速)
- 实际体感温度：(计算后的体感温度，并用一两个词形容如：闷热/凉爽/刺骨寒冷)
- 未来一小时状况：(给出接下来一小时的天气趋势，如：持续多云/有渐进性小雨/狂风大作)
- 出行建议：(针对今天整体和当下的出行提示)
- 穿衣建议：(精炼的穿衣指南)
- 随身物品：(如：遮阳伞/雨伞/墨镜/无需特别携带)

(如果有奇观，在此处空一行输出奇观预警；若无奇观，下面直接留白，什么都不写)"""

    try:
        completion = client.chat.completions.create(
            model="ep-20260628222322-mstpq",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3 
        )
        advice = completion.choices[0].message.content
    except Exception as e:
        advice = f"AI调用失败：{e}"

    # ===== 4. 彻底抛弃弹窗，接回原本的邮件发送模块 =====
    print(advice)  # 方便你在 GitHub 运行日志里直接肉眼查看
    
    try:
        msg = MIMEText(advice, "plain", "utf-8")
        msg["Subject"] = "⏰ 您的实时气象与追光看板"
        msg["From"] = email
        msg["To"] = email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email, app_password)
        server.send_message(msg)
        server.quit()
        print("EMAIL SENT SUCCESS")
    except Exception as e:
        print(f"邮件发送失败：{e}")

if __name__ == "__main__":
    run_agent()
