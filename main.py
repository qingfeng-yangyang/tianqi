import os
import requests
import smtplib
from email.mime.text import MIMEText

def run_agent():

    # ===== Secrets =====
    email = os.environ["EMAIL"]
    app_password = os.environ["APP_PASSWORD"]
    ark_key = os.environ["ARK_API_KEY"]

    # ===== 天气 =====
    weather = requests.get(
        "https://api.open-meteo.com/v1/forecast?latitude=23.12&longitude=114.41&current=temperature_2m,wind_speed_10m,precipitation"
    ).json()

    temp = weather["current"]["temperature_2m"]
    wind = weather["current"]["wind_speed_10m"]
    rain = weather["current"]["precipitation"]

    prompt = f"""
你是生活助手，根据天气给出出行建议：

温度：{temp}
风速：{wind}
降雨：{rain}

请回答：
1. 是否适合出门
2. 是否需要带伞
3. 一句话总结
"""

    # ===== AI（Base API，无EP）=====
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {ark_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "Doubao-Seed-2.0-lite",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        timeout=20
    )

    print("STATUS:", response.status_code)
    print("TEXT:", response.text)

    # ===== 安全解析（永不崩）=====
    try:
        data = response.json()
        advice = data["choices"][0]["message"]["content"]
    except:
        advice = "AI返回失败：" + response.text

    # ===== 发邮件 =====
    msg = MIMEText(advice, "plain", "utf-8")
    msg["Subject"] = "今日AI天气建议"
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
