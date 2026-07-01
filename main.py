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

    # ===== 2. 气象数据抓取 (已精准切换至：河源古竹镇) =====
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=23.54&longitude=114.74"  # 古竹镇坐标
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability,cloud_cover,visibility"
        "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&timezone=Asia%2FShanghai"
    )
    
    try:
        weather_res = requests.get(url).json()
        
        # 提取实时与全天大局
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

        # 封装给 AI 的原始数据
        user_weather_data = f"""
- 城市区域: 广东省河源市古竹镇
- 实时天气: 温度 {cur_temp}°C / 湿度 {cur_humidity}% / 风速 {cur_wind} km/h
- 今日极端温差: {temp_min}°C ~ {temp_max}°C
- 日出时刻: {sunrise} | 日落时刻: {sunset}
- 未来一小时精细预报: 温度 {next_temp}°C / 降水概率 {next_pop}% / 云量 {next_cloud}% / 能见度 {next_vis / 1000:.1f} km
"""
    except Exception as e:
        print(f"气象数据抓取失败：{e}")
        return

    # ===== 3. AI 核心推演 (换回大白话优美文风) =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""# Role
你是一个兼具顶级气象学家视角、风光摄影师灵魂、以及温和贴心管家属性的智能体。你说话语气亲切自然，拒绝死板的表格。

# Task
根据传入的河源古竹镇气象数据，用充满生活温度、画面感和人性化的【段落大白话】，为用户写一份早报。

# Rules (硬性约束)
1. 【文风要求】：模仿精美的人类文字。严禁输出类似“- 城市：xx \n - 实时天气：xx”这样的结构化表格。请将所有核心信息优雅地揉进段落里。
2. 【内容必须包含】：
   - 必须先点出“河源古竹镇”以及你根据温度、湿度和风速推演出的【实际体感温度】（如：黏糊闷热、清爽宜人等）。
   - 必须用一句话极其精准地提醒【未来一小时短时状况】（现在出门会不会撞上暴雨或狂风）。
   - 必须给出明确的穿衣方案、生活出行建议以及【随身物品建议】（如遮阳伞、防晒袖套、雨伞兜底等）。
3. 【大自然追光（按需留白）】：
   - 默默评估云量、能见度等指标。如果今天没有任何值得特意推开窗、抬头、或出门捕捉的自然奇观（彩虹、顶级火烧云、耶稣光、云海），关于奇观的部分【必须保持绝对空白】，严格节省 token。
   - 只有当某项奇观的触发几率大于 70% 时，才在文章最后空一行，单独写一段优美的【奇观预警】，指出精准时刻与视觉画面。
4. 【字数严控】：总字数严格控制在 220 字以内，拒绝任何废话前缀。

# 今日原始气象数据流：
[DATA_START]
{user_weather_data}
[DATA_END]"""

    try:
        completion = client.chat.completions.create(
            model="ep-20260628222322-mstpq",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4 
        )
        advice = completion.choices[0].message.content
    except Exception as e:
        advice = f"AI调用失败：{e}"

    # ===== 4. 邮件发送 =====
    print(advice)
    
    try:
        msg = MIMEText(advice, "plain", "utf-8")
        msg["Subject"] = "⏰ 古竹镇实时气象与追光决策早报"
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
