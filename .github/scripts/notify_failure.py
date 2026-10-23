#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Actions 同步失败时发送邮件通知到指定邮箱（QQ 邮箱 SMTP）。
用法：由 workflow 在 if: failure() 步骤调用。
凭据从环境变量读取（GitHub Secrets）：
  SMTP_USER   QQ 邮箱地址（发件人）
  SMTP_PASS   QQ 邮箱 SMTP 授权码（16位，在 QQ 邮箱设置→账户→开启SMTP服务获取）
  MAIL_TO     收件邮箱，缺省 863904696@qq.com
未配置凭据时只打印提示并正常退出（不因通知失败而让 run 变得更糟）。"""
import os
import smtplib
import ssl
import time

smtp_user = os.environ.get("SMTP_USER", "").strip()
smtp_pass = os.environ.get("SMTP_PASS", "").strip()
mail_to = os.environ.get("MAIL_TO", "863904696@qq.com").strip()

if not smtp_user or not smtp_pass:
    print("[notify] 未配置 SMTP_USER/SMTP_PASS secrets，跳过邮件通知。")
    print("[notify] 配置方法：仓库 Settings -> Secrets and variables -> Actions -> New repository secret")
    print("[notify]   SMTP_USER = QQ邮箱地址")
    print("[notify]   SMTP_PASS = QQ邮箱SMTP授权码")
    raise SystemExit(0)

repo = os.environ.get("GITHUB_REPOSITORY", "unknown/repo")
run_id = os.environ.get("GITHUB_RUN_ID", "?")
wf = os.environ.get("GITHUB_WORKFLOW", "unknown-workflow")
server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
run_url = f"{server}/{repo}/actions/runs/{run_id}"

subject = f"[TVBox自动同步失败] {wf} - {repo} #{run_id}"
body = (
    "TVBox 源自动同步任务运行失败，请尽快检查。\n\n"
    f"仓库: {repo}\n"
    f"工作流: {wf}\n"
    f"运行编号: #{run_id}\n"
    f"运行链接: {run_url}\n\n"
    "可能原因：上游接口/仓库失效、网络超时、文件拉取失败。\n"
    "可到运行链接查看详细日志。\n"
)

msg = (
    f"From: {smtp_user}\r\n"
    f"To: {mail_to}\r\n"
    f"Subject: {subject}\r\n"
    "Content-Type: text/plain; charset=utf-8\r\n"
    "\r\n"
    f"{body}"
)

# QQ 邮箱 SMTP SSL: smtp.qq.com:465
last_err = None
for attempt in range(3):
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30, context=ctx) as s:
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, [mail_to], msg.encode("utf-8"))
        print(f"[notify] 邮件已发送到 {mail_to} (attempt {attempt + 1})")
        raise SystemExit(0)
    except Exception as e:
        last_err = e
        print(f"[notify] 第 {attempt + 1} 次发送失败: {type(e).__name__}: {e}")
        time.sleep(5)

print(f"[notify] 邮件发送最终失败: {last_err}")
raise SystemExit(0)
