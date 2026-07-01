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

        # 头部原始数据卡片
        raw_info = f"""☀️ 今日天气决策情报

【出门1小时预报】温度：{cur_temp} °C / 降水概率：{next_pop} % / 风速：{cur_wind} km/h
【全天宏观大局】最高温：{temp_max} °C / 最低温：{temp_min} °C
"""

        user_weather_data = f"""
- 当前运行时间段: {time_tag}
- 城市区域: 广东省河源市古竹镇
- 实时天气: 温度 {cur_temp}°C / 湿度 {cur_humidity}% / 风速 {cur_wind} km/h
- 今日温差: {temp_min}°C ~ {temp_max}°C
- 日出日落: {sunrise} / {sunset}
- 未来一小时精细预报: 温度 {next_temp}°C / 降水概率 {next_pop}% / 云量 {next_cloud}% / 能见度 {next_vis / 1000:.1f} km
"""
    except Exception as e:
        print(f"气象数据抓取失败：{e}")
        return

    # ===== 4. AI 核心推演 (修改第三板块为必出分析) =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""# Role
你是一个兼具顶级气象学家视角与风光摄影师灵魂的智能体。请严格按照用户指定的 Markdown 格式输出。

# Task
根据传入的河源古竹镇气象数据，生成一份天气决策报告。

# Rules (硬性约束)
1. 【严格遵循排版格式】：输出的内容必须完全匹配以下制式，结构分明：
   # 今日{{当前运行时间段}}决策早报
   ## 1. 未来1小时出门安排
   (大白话内容：必须包含结合温湿度算出的【实际体感温度】和黏糊/清爽描述；【未来一小时短时状况】如是否有突发降水狂风、骑行/步行提醒)
   ## 2. 全天穿搭与防雨防晒规划
   (大白话内容：必须包含明确具体的【穿衣建议】；针对温差和紫外线的生活指南；具体的【随身物品建议】)
   ## 3. 今日大自然追光预测
   (大白话内容：AI自主推演今天是否有几率触发特殊自然现象。不管有没有，都必须在这里给出一个明确的结论。你可以写“今日各大罕见奇观触发概率均低于30%，主要是因为云量/能见度不达标”；或者当某项奇观几率大于70%时，直接升级为【高能奇观预警】，指出精准时刻与视觉画面描述)
2. 【字数与语气】：用充满生活温度、专业且接地气的大白话撰写。总字数控制在 260 字以内，拒绝任何废话前缀。

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
        ai_advice = completion.choices[0].message.content
    except Exception as e:
        ai_advice = f"AI调用失败：{e}"

    # ===== 5. 拼装与发送 =====
    final_body = f"{raw_info}\n\n🤖 豆包决策早报\n\n{ai_advice}"
    print(final_body)
    
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
