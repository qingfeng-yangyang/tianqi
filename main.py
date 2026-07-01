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

    # 配置经纬度（改变这里，城市和天气都会自动切换）
    lat = 23.54
    lon = 114.74

    # ===== 1.5 动态逆地理编码：通过经纬度获取城市名 =====
    city_name = "未知城市"
    try:
        # 使用 open-meteo 自带的 geocoding 或 openstreetmap 免费接口
        geo_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=zh"
        # 加上 User-Agent 规避合规检查
        headers = {"User-Agent": "WeatherAgent/1.0"}
        geo_res = requests.get(geo_url, headers=headers).json()
        
        address = geo_res.get("address", {})
        # 优先取镇/村/区，如果没有就取城市名
        city_name = address.get("town") or address.get("village") or address.get("suburb") or address.get("city") or "未知位置"
        # 去掉“镇”或“村”字让标题更精简（可选）
        city_name = city_name.replace("镇", "").replace("街道", "")
    except Exception as e:
        print(f"城市逆地理定位失败，使用默认名称。错误: {e}")
        city_name = "河源古竹"  # 降级备用名

    # ===== 2. 气象数据抓取 =====
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability,cloud_cover,visibility"
        "&daily=temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_speed_10m_min,precipitation_sum,sunrise,sunset"
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
        
        # 提取真实的全天宏观数据
        wind_max = daily["wind_speed_10m_max"][0]
        wind_min = daily["wind_speed_10m_min"][0]
        precip_sum = daily["precipitation_sum"][0]  # 全天降水总量 (mm)
        
        sunrise = daily["sunrise"][0].split("T")[-1] 
        sunset = daily["sunset"][0].split("T")[-1]

        # 头部原始数据卡片
        raw_info = f"""☀️ 今日天气决策情报

【出门1小时预报】温度：{cur_temp} °C / 降水概率：{next_pop} % / 风速：{cur_wind} km/h
【全天宏观大局】最高温：{temp_max} °C / 最低温：{temp_min} °C
最高风速：{wind_max} km/h / 最低风速：{wind_min} km/h
全天降水量：{precip_sum} mm
"""

        # 封装给 AI 的原料
        user_weather_data = f"""
- 城市区域: {city_name}
- 实时当前温度: {cur_temp}°C
- 当前相对湿度: {cur_humidity}%
- 当前实际风速: {cur_wind} km/h
- 全天最高气温: {temp_max}°C
- 全天最低气温: {temp_min}°C
- 全天最高风速: {wind_max} km/h
- 全天最低风速: {wind_min} km/h
- 全天预期总降水量: {precip_sum}mm
- 下一小时精细预报: 温度 {next_temp}°C / 降水概率 {next_pop}% / 云量 {next_cloud}% / 能见度 {next_vis / 1000:.1f} km
"""
    except Exception as e:
        print(f"气象数据抓取失败：{e}")
        return

    # ===== 3. AI 核心推演 (硬性规范体感数字与固定标题) =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""# Role
你是一个兼具顶级气象学家视角与贴心管家属性的智能体。请完全接管并自主渲染整份天气决策报告的全文。

# Task
根据传入的原始气象数据，**严格按照指定格式**生成一整套完整的 Markdown 决策看板。

# Rules (硬性约束)
1. 【标题动态输出】：大标题必须根据定位动态输出为：# {city_name}今日天气简报。严禁自作聪明生成带有时间段的标题。
2. 【体感温度必须包含实际数据】：在 `## 1` 的子集里，你必须结合当前的“实时温度、相对湿度和风速”进行综合推演，**给出一个具体的、带物理单位的预计体感温度数字（如“约 xx°C”）**，并紧跟一两个词形容体感。
3. 【严格遵循一整套排版格式】：输出的内容必须完全匹配以下制式，严禁合并或缺少模块。

   ☀️ 今日天气决策情报
   【出门1小时预报】温度：(填入下一小时温度) °C / 降水概率：(填入下一小时降水概率) % / 风速：(填入当前风速) km/h
   【全天宏观大局】最高温：(填入最高温) °C / 最低温：(填入最低温) °C /
   最高风速：{wind_max} km/h / 最低风速：{wind_min} km/h
   全天降水量：{precip_sum} mm

   🤖 豆包决策简报

   # {city_name}今日天气简报
   ## 1. 未来1小时出门安排
   - 实际体感温度：约 (填入计算出的体感温度数字)°C，(填入形容词，如“偏黏糊/干爽/闷热/凉爽”)
   (接下来另起一行输出大白话内容：结合体感进行【未来一小时短时状况】的具体描述，说明是否有突发降水狂风、给出骑行或步行提醒)
   
   ## 2. 全天穿搭与防雨防晒规划
   (大白话内容：必须结合全天降水量规范下雨提醒。包含明确具体的【穿衣建议】；针对全天温差和紫外线的生活指南；具体的【随身物品建议】)
   
   ## 3. 今日大自然追光预测
   (大白话内容：结合云量和能见度自主推演今天是否有几率触发特殊自然现象。无奇观时写“由于云量过厚，今日各大奇观概率均低于20%...”；有奇观且几率大于70%时，直接升级为【高能奇观预警】并描述视觉画面)

4. 【字数与语气】：用充满生活温度、专业且接地气的大白话撰写。除格式要求的标志外，拒绝任何多余的废话前缀。

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
