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

    # 配置经纬度（这里以珠海附近为例，改变经纬度将自动切换定位与天气）
    lat = 22.27
    lon = 113.57

    # ===== 1.5 动态逆地理编码：获取精简城市名 =====
    city_name = "未知城市"
    try:
        geo_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=zh"
        headers = {"User-Agent": "WeatherAgent/1.0"}
        geo_res = requests.get(geo_url, headers=headers).json()
        address = geo_res.get("address", {})
        
        # 依次抓取最精准的区域级别名称
        raw_city = address.get("district") or address.get("city") or address.get("town") or "未知"
        # 过滤掉多余的后缀，保持像“珠海”、“古竹”一样干净
        city_name = raw_city.replace("市", "").replace("区", "").replace("镇", "").replace("街道", "")
    except Exception as e:
        print(f"城市定位失败：{e}")
        city_name = "本地"

    # ===== 2. 气象数据抓取 =====
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability,cloud_cover,visibility"
        "&daily=temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_speed_10m_min,precipitation_sum"
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
        wind_max = daily["wind_speed_10m_max"][0]
        wind_min = daily["wind_speed_10m_min"][0]
        precip_sum = daily["precipitation_sum"][0]  
        
        # 预先组装好顶部固定的数据看板
        raw_info = f"""☀️ 今日天气决策情报
【出门1小时预报】温度：{cur_temp} °C / 降水概率：{next_pop} % / 风速：{cur_wind} km/h
【全天宏观大局】最高温：{temp_max} °C / 最低温：{temp_min} °C
最高风速：{wind_max} km/h / 最低风速：{wind_min} km/h
全天降水量：{precip_sum} mm"""

        user_weather_data = f"""
- 城市: {city_name}
- 当前温度: {cur_temp}°C / 湿度: {cur_humidity}% / 风速: {cur_wind} km/h
- 全天温差: {temp_min}°C 到 {temp_max}°C
- 全天风速范围: {wind_min} 到 {wind_max} km/h
- 全天总降水量: {precip_sum}mm
- 下一小时精细预报: 温度 {next_temp}°C / 降水概率 {next_pop}% / 云量 {next_cloud}% / 能见度 {next_vis / 1000:.1f} km
"""
    except Exception as e:
        print(f"气象数据抓取失败：{e}")
        return

    # ===== 3. AI 核心推演 (重塑强约束，追求精致卡片感) =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""# Role
你是一个高审美、表达精炼的智能天气管家。请为用户定制一份视觉结构清晰、充满生活温度的卡片式看板。

# Task
严格基于给出的气象数据，直接渲染整份报告。禁止输出任何“好的”、“收到”或解释性的废话。

# Format Rules (硬性视觉样式，严禁脱离此结构)
你必须严格按照以下排版进行输出，通过空行和 Emoji 图标建立清晰的“图片卡片感”：

{raw_info}

🤖 豆包决策简报

# {city_name}今日天气简报

## 1. 未来1小时出门安排
- 实际体感温度：约 (计算出的体感温度数字)°C，(形容词，如“闷热/干爽/凉爽”)
(另起一行输出大白话叙述：一句话描述短时天气状态，并给出具体的出行方式步行/骑行建议，做到精炼简洁)

## 2. 全天穿搭与防雨防晒规划
(大白话叙述：包含明确具体的【穿衣建议】；针对全天温差和降水的生活指南；列出具体的【随身物品】如遮阳伞、墨镜等。字数要紧凑精炼)

## 3. 今日大自然追光预测
(大白话叙述：根据云量和能见度一句话判定。如“云量过厚，今日奇观概率较低...”或“视野极佳，傍晚触发晚霞概率高...”)

# 原始气象数据：
{user_weather_data}"""

    try:
        completion = client.chat.completions.create(
            model="ep-20260628222322-mstpq",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2  # 降低随机性，严格按格式输出
        )
        final_body = completion.choices[0].message.content
    except Exception as e:
        final_body = f"AI调用失败：{e}"

    # ===== 4. 发送邮件 =====
    print(final_body)
    
    try:
        msg = MIMEText(final_body, "plain", "utf-8")
        msg["Subject"] = f"⏰ {city_name}今日天气简报"
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
