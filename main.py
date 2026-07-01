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

    # 配置经纬度（自动切换定位与天气）
    lat = 23.54
    lon = 114.74

    # ===== 1.5 动态逆地理编码：获取精简城市名 =====
    city_name = "未知城市"
    try:
        geo_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=zh"
        headers = {"User-Agent": "WeatherAgent/1.0"}
        geo_res = requests.get(geo_url, headers=headers).json()
        address = geo_res.get("address", {})
        
        raw_city = address.get("district") or address.get("city") or address.get("town") or "未知"
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
【出门1小时预报】
温度：{cur_temp} °C 
降水概率：{next_pop} % 
风速：{cur_wind} km/h
【全天宏观大局】
最高温：{temp_max} °C / 最低温：{temp_min} °C
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

    # ===== 3. AI 核心推演 (完全基于纯文本模板的高强度约束) =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""# Role
你是一个高审美、说话绝不拖泥带水的智能天气管家。你负责将天气数据提炼成精简的、没有废话的卡片式看板。

# Rules (必须严格遵守)
1. 你必须【100%严格复制】下方 [OUTPUT_TEMPLATE] 的格式，仅把括号 `[]` 里的提示换成基于数据的简短大白话。
2. 严禁自行删减、合并或修改任何带 `-` 的前置标签（如 `- 城市：`、`- 穿衣建议：`）。
3. 每一行标签后面的回答必须是【极简短句】，直接切入重点，严禁生成长篇大论。
4. 保持模板中行与行之间的【空行隔开】状态，以保证精工整的文本视觉。

# [OUTPUT_TEMPLATE]
{raw_info}

🤖 豆包决策简报

# {city_name}今日天气简报

- 城市：{city_name}

- 【实时天气】
温度：{cur_temp}°C 
湿度：{cur_humidity}% 
风速{cur_wind}km/h

- 实际体感温度：约 [计算出的体感温度数字]°C [一到两个词形容体感，例如：闷热/干爽/凉爽]

- 未来一小时状况：[简单描述短时天气状态，例如：持续多云，无突发降雨]

- 出行建议：[简单给出对应未来一小时的步行/骑行防护提醒]

- 穿衣建议：[具体实用的穿衣搭配短语，例如：透气短袖、短裤等夏装]

- 随身物品：[直接列出所需的随身物品，用逗号隔开，例如：遮阳伞、墨镜]

- 追光预测：[经过数据测算给出结论，例如：云量过厚，今日奇观概率均低于20%]
# [OUTPUT_TEMPLATE_END]

# 今日天气数据：
{user_weather_data}"""

    try:
        completion = client.chat.completions.create(
            model="ep-20260628222322-mstpq",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1  # 彻底锁死输出结构，让其不敢自由发挥
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
