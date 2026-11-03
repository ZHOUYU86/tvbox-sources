# -*- coding: utf-8 -*-
"""
同步失败告警邮件
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

now = datetime.now().strftime("%Y-%m-%d %H:%M")
body = "影视源自动同步失败\n"
body += "时间: " + now + "\n\n"
body += "请检查以下原因:\n"
body += "1. 上游仓库是否可访问\n"
body += "2. 网络是否正常\n"
body += "3. 是否有git冲突\n\n"
body += "请前往GitHub Actions查看详细日志。"

msg = MIMEMultipart()
msg["From"] = "863904696@qq.com"
msg["To"] = "863904696@qq.com"
msg["Subject"] = "[影视源同步告警] 自动同步失败 - " + datetime.now().strftime("%m-%d %H:%M")
msg.attach(MIMEText(body, "plain", "utf-8"))

server = smtplib.SMTP_SSL("smtp.qq.com", 465)
server.login("863904696@qq.com", os.environ["QQ_SMTP_AUTH_CODE"])
server.sendmail("863904696@qq.com", "863904696@qq.com", msg.as_string())
server.quit()
print("同步失败告警邮件已发送")
