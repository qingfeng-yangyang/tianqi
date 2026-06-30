import os
import requests
import smtplib
from email.mime.text import MIMEText
from openai import OpenAI


def run_agent():

    # ===== Secrets =====
    email = os.environ["EMAIL"]
    app_password = os.environ["APP_PASSWORD"]
    ark_key = os.environ["ARK_API_KEY"]

    # ===== 天气（修改为获取逐小时和每日预报） =====
    weather = requests.get(
        "https://api.open-meteo.com/v1/forecast?latitude=22.35&longitude=113.30&hourly=temperature_2m,precipitation_probability,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FShanghai"
    ).json()

    # 提取未来1小时（以早上7点第7个数据点为例）
    temp_next = weather["hourly"]["temperature_2m"][7]
    pop_next = weather["hourly"]["precipitation_probability"][7]
    wind_next = weather["hourly"]["wind_speed_10m"][7]

    # 提取全天大局
    temp_max = weather["daily"]["temperature_2m_max"][0]
    temp_min = weather["daily"]["temperature_2m_min"][0]

    # ===== AI =====
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=ark_key,
    )

    prompt = f"""
你是一个生活助手。请根据以下天气数据，重点从两个维度给出今天7点的决策早报：
1. 安排出门事宜（针对未来1小时的实时精准天气情况）
2. 全天整体的穿搭与防雨防晒规划（针对全天天气状态）

天气情报：
【未来1小时内】温度：{temp_next}℃，降水概率：{pop_next}%，风速：{wind_next} m/s
【今天一整天】最高温度：{temp_max}℃，最低温度：{temp_min}℃

回答尽量精简、字字句句。
"""

    try:
        # 原样复制回你的专属 ep，直接调用
        response = client.responses.create(
            model="ep-20260628222322-mstpq",
            input=prompt
        )

        advice = response.output[1].content[0].text

    except Exception as e:
        advice = f"AI调用失败：{e}"

    # ===== 邮件内容 =====
    body = f"""
🌤 今日天气决策情报

【出门1小时预报】温度：{temp_next} ℃ / 降水概率：{pop_next} % / 风速：{wind_next} m/s
【全天宏观大局】最高温：{temp_max} ℃ / 最低温：{temp_min} ℃


🤖 豆包决策早报

{advice}
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "⏰ 您的7点天气决策早报"
    msg["From"] = email
    msg["To"] = email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(email, app_password)
    server.send_message(msg)
    server.quit()

    print("AGENT RUN SUCCESS")


if __name__ == "__main__":
    run_agent()
