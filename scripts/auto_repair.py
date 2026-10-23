#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TVBox 全自动精准修复 v2 —— 读 health_check.py 的 JSON 报告，对症下药
=================================================
Level 1  字段残留 (fix=strip)   -> 本地剥字段 + 并发安全提交推送（不重跑上游，避免字段拉回）
Level 2  健康故障/同步断裂/任务失败 (fix=resync)
            -> dispatch 对应同步 workflow 自动重跑（自带重下jar+动态md5+剥字段）
Level 3  无法自动修 -> 记录，由 workflow 复检失败时发邮件通知
"""
import argparse
import json
import subprocess
import sys

# workflow 数字ID（dispatch 必须用数字ID，文件名会404）
WORKFLOW_IDS = {
    "wmz-sync": 393745971,
    "pg-aowu-sync": 393745969,
    "zhenxin-sync": 393745972,
    "sync-legacy-sources": 393893372,
    "update-live-tv": 386732722,
}


def git_push_all(message):
    """并发安全提交推送（pull --rebase + push 重试 3 次）"""
    subprocess.run(["git", "config", "user.name", "zhouyu86-bot"], check=False)
    subprocess.run(["git", "config", "user.email", "863904696@qq.com"], check=False)
    subprocess.run(["git", "add", "-A"], check=False)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], check=False)
    if r.returncode == 0:
        print("[repair] 无变化，无需提交")
        return True
    subprocess.run(["git", "commit", "-m", message], check=False)
    for i in range(1, 4):
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
        p = subprocess.run(["git", "push"], check=False)
        if p.returncode == 0:
            print(f"[repair] push 成功 (attempt {i})")
            return True
        print(f"[repair] push 冲突重试 (attempt {i})")
        subprocess.run(["sleep", "10"], check=False)
    return False


def strip_fongmi(files):
    """Level 1: 剥离 FongMi 扩展字段（文本级，不重排 JSON）"""
    fixed = []
    for f in files:
        r = subprocess.run([sys.executable, "scripts/strip_fongmi_extra.py", f])
        if r.returncode == 0:
            fixed.append(f)
            print(f"[repair] 剥离字段: {f}")
        else:
            print(f"[repair] 剥离跳过(可能已干净): {f}")
    if fixed:
        git_push_all(f"auto-repair: strip fongmi extra from {','.join(fixed)}")
    return fixed


def dispatch_workflows(names):
    """Level 2: dispatch 对应同步 workflow 自动重跑"""
    done = []
    for name in sorted(set(names)):
        wid = WORKFLOW_IDS.get(name)
        if not wid:
            print(f"[repair] 未知名 workflow: {name}，跳过")
            continue
        r = subprocess.run(
            ["gh", "api", "-X", "POST",
             f"repos/ZHOUYU86/tvbox-sources/actions/workflows/{wid}/dispatches",
             "-f", "ref=main", "--silent"],
            capture_output=True, text=True)
        if r.returncode == 0:
            done.append(name)
            print(f"[repair] 已触发自动重跑: {name} (wf#{wid})")
        else:
            print(f"[repair] 触发失败 {name}: {r.stderr.strip()[:120]}")
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True, help="health_check.py --json 输出的报告文件")
    args = ap.parse_args()

    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)

    if report.get("healthy"):
        print("[repair] 全部健康，无需修复")
        return

    # 先剥字段（Level1，本地修复），再重跑同步（Level2，自动更新）
    strip_fongmi(report.get("needs_strip", []))
    dispatch_workflows(report.get("needs_retry", []))

    print("[repair] 修复动作完成，等待复检...")


if __name__ == "__main__":
    main()
