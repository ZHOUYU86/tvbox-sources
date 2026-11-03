# -*- coding: utf-8 -*-
"""
坏源告警邮件发送脚本
"""
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

with open("monitor/result.json", "r", encoding="utf-8") as f:
    result = json.load(f)

failed = result["failed"]
success = result["success"]

now = datetime.now().strftime("%Y-%m-%d %H:%M")
body = "检测时间: " + now + "\n"
body += "正常: " + str(len(success)) + "个, 异常: " + str(len(failed)) + "个\n\n"
body += "异常源列表:\n"
for s in failed:
    body += "- " + s["name"] + " (" + s.get("from_file", "") + "): " + s.get("error", "") + "\n"

msg = MIMEMultipart()
msg["From"] = "863904696@qq.com"
msg["To"] = "863904696@qq.com"
msg["Subject"] = "[影视源告警] " + str(len(failed)) + "个源异常 - " + datetime.now().strftime("%m-%d %H:%M")
msg.attach(MIMEText(body, "plain", "utf-8"))

server = smtplib.SMTP_SSL("smtp.qq.com", 465)
server.login("863904696@qq.com", os.environ["QQ_SMTP_AUTH_CODE"])
server.sendmail("863904696@qq.com", "863904696@qq.com", msg.as_string())
server.quit()
print("告警邮件已发送")
