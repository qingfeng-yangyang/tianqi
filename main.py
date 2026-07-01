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

    # ===== 2. 气象数据抓取 (广东省河源市古竹镇) =====
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

        # 封装给 AI 的原料，重点强化温湿度、风速关联
        user_weather_data = f"""
- 城市区域: 广东省河源市古竹镇
- 实时当前温度: {cur_temp}°C
- 当前相对湿度: {cur_humidity}%
- 当前实际风速: {cur_wind} km/h
- 全天最高气温: {temp_max}°C
- 全天最低气温: {temp_min}°C
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
根据传入的河源古竹镇原始气象数据，**严格按照指定格式**生成一整套完整的 Markdown 决策看板。

# Rules (硬性约束)
1. 【标题必须写死】：严禁自作聪明生成带有时间段的标题。大标题必须雷打不动地输出为：# 今日天气简报
2. 【体感温度必须包含实际数据】：在 `## 1` 的子集里，你必须结合当前的“实时温度、相对湿度和风速”进行综合推演，**给出一个具体的、带物理单位的预计体感温度数字（如“约 xx°C”）**，并紧跟一两个词形容体感。
3. 【严格遵循一整套排版格式】：输出的内容必须完全匹配以下制式，严禁合并或缺少模块：

   ☀️ 今日天气决策情报
   【出门1小时预报】温度：(填入下一小时温度) °C / 降水概率：(填入下一小时降水概率) % / 风速：(填入当前风速) km/h
   【全天宏观大局】最高温：(填入最高温) °C / 最低温：(填入最低温) °C /
   最高风速：（填入全天最高风速）km/h / 最低风速：（填入全天最低风速）km/h
   降雨概率：（填入全天降雨概率）%

   🤖 豆包决策简报

   # 今日天气简报
   ## 1. 未来1小时出门安排
   - 实际体感温度：约 (填入计算出的体感温度数字)°C，(填入形容词，如“偏黏糊/干爽/闷热/凉爽”)
   (接下来另起一行输出大白话内容：结合体感进行【未来一小时短时状况】的具体描述，说明是否有突发降水狂风、给出骑行或步行提醒)
   
   ## 2. 全天穿搭与防雨防晒规划
   (大白话内容：必须包含明确具体的【穿衣建议】；针对全天温差和紫外线的生活指南；具体的【随身物品建议】)
   
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
        msg["Subject"] = "⏰ 今日天气简报" # 主题同步写死
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
