import os
import requests
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from openai import OpenAI

def run_agent():
    # ===== 1. 获取 GitHub 保险柜里的密钥 =====
    email = os.environ["EMAIL"]
    app_password = os.environ["APP_PASSWORD"]
    ark_key = os.environ["ARK_API_KEY"]

    # ===== 2. 获取当前系统时间 =====
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        time_tag = "7点"
    elif 12 <= current_hour < 18:
        time_tag = "午后"
    else:
        time_tag = "晚间"

    # ===== 3. 气象数据抓取 (广东省河源市古竹镇) =====
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=23.54&longitude=114.74"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability,cloud_cover,visibility"
        "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&timezone=Asia%2FShanghai"
    )
    
    try:
        weather_res = requests.get(url).json()
        
        current = weather_res["current"]
        cur_temp = current["temperature_2m"]
        cur_humidity = current["relative_humidity_2m"]
        cur_wind = current["wind_speed_10m"]
        
        hourly = weather_res["hourly"]
        next_temp = hourly["temperature_2m"][1]       
        next_pop = hourly["precipitation_probability"][1] 
        next_cloud = hourly["cloud_cover"][1]         
        next_vis = hourly["visibility"][1]            
        
        daily = weather_res["daily"]
        temp_max = daily["temperature_2m_max"][0]
        temp_min = daily["temperature_2m_min"][0]
        sunrise = daily["sunrise"][0].split("T")[-1] 
        sunset = daily["sunset"][0].split("T")[-1]

        # 这一次，Python 只负责提供纯粹的数据原料
        user_weather_data = f"""
- 当前运行时间段: {time_tag}
- 城市区域: 广东省河源市古竹镇
- 实时/当前温度: {cur_temp}°C
- 当前湿度: {cur_humidity}%
- 当前风速: {cur_wind} km/h
- 今日温差大局: 最低温 {temp_min}°C 到 最高温 {temp_max}°C
- 明细: 下一小时温度 {next_temp}°C / 降水概率 {next_pop}% / 云量 {next_cloud}% / 能见度 {next_vis / 1000:.1f} km
"""
    except Exception as e:
        print(f"气象数据抓取失败：{e}")
        return

    # ===== 4. AI 核心推演 (将整个排版全部交由 AI 自主渲染) =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""# Role
你是一个兼具顶级气象学家视角与贴心管家属性的智能体。请完全接管并自主渲染整份天气决策报告的全文。

# Task
根据传入的河源古竹镇原始数据，**严格按照指定格式**生成一整套完整的 Markdown 决策看板。

# Rules (硬性约束)
1. 【严格遵循一整套排版格式】：输出的内容必须完全匹配以下制式，连最上方的原始数据和 Emoji 都要由你亲自优雅地填入，严禁缺少任何模块：

   ☀️ 今日天气决策情报
   【出门1小时预报】温度：(填入下一小时温度) °C / 降水概率：(填入下一小时降水概率) % / 风速：(填入当前风速) km/h
   【全天宏观大局】最高温：(填入最高温) °C / 最低温：(填入最低温) °C

   🤖 豆包决策早报

   # 今日{{当前运行时间段}}决策早报
   ## 1. 未来1小时出门安排
   (大白话内容：必须包含结合温湿度算出的【实际体感温度】和黏糊/清爽描述；【未来一小时短时状况】如是否有突发降水狂风、骑行/步行提醒)
   
   ## 2. 全天穿搭与防雨防晒规划
   (大白话内容：必须包含明确具体的【穿衣建议】；针对温差和紫外线的生活指南；具体的【随身物品建议】)
   
   ## 3. 今日大自然追光预测
   (大白话内容：结合云量和能见度自主推演今天是否有几率触发特殊自然现象。不管有没有，都必须在这里给出一个明确的分析交代。无奇观时可以写“由于云量过厚，今日各大奇观概率均低于20%...”；有奇观且几率大于70%时，直接升级为【高能奇观预警】并描述视觉画面)

2. 【字数与语气】：用充满生活温度、专业且接地气的大白话撰写。除格式要求的标志外，拒绝任何多余的废话前缀（如“好的”、“这是为您生成的报告”）。

# 今日原始气象数据流：
[DATA_START]
{user_weather_data}
[DATA_END]"""

    try:
        completion = client.chat.completions.create(
            model="ep-20260628222322-mstpq",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        final_body = completion.choices[0].message.content
    except Exception as e:
        final_body = f"AI调用失败：{e}"

    # ===== 5. 拼装与发送 =====
    print(final_body) # 此时打印出来的就是 100% 由大模型生成的完整纯净文本了
    
    try:
        msg = MIMEText(final_body, "plain", "utf-8")
        msg["Subject"] = f"⏰ 您的{time_tag}天气决策早报"
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
