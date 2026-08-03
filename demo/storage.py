# -*- coding: utf-8 -*-
"""SQLite 数据层:候选人表、写入、查询、统计。标准库实现,零依赖。"""
import json
import sqlite3
from datetime import datetime

import config

# 阶段统一枚举(前端看板与解析共用)
STAGES = ["简历", "初筛", "面试", "Offer", "入职", "淘汰"]
STAGE_ORDER = {s: i for i, s in enumerate(STAGES)}

# 状态统一枚举
STATUSES = ["进行中", "通过", "不通过", "待定", "已入职"]


def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT DEFAULT '',
            stage TEXT DEFAULT '简历',
            status TEXT DEFAULT '进行中',
            salary INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            source TEXT DEFAULT '企业微信',
            create_time TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def insert_candidate(rec):
    """插入一条候选人记录,rec 为 dict,缺失字段自动补默认值。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _conn()
    conn.execute(
        """INSERT INTO candidates(name, position, stage, status, salary, note, source, create_time)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            rec.get("name", "未命名"),
            rec.get("position", ""),
            rec.get("stage", "简历"),
            rec.get("status", "进行中"),
            int(rec.get("salary", 0) or 0),
            rec.get("note", ""),
            rec.get("source", "企业微信"),
            rec.get("create_time", now),
        ),
    )
    conn.commit()
    conn.close()


def insert_many(records):
    for r in records:
        insert_candidate(r)


def all_candidates(limit=500):
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM candidates ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_total():
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    conn.close()
    return n


def dashboard_stats():
    """聚合看板所需统计:漏斗、阶段分布、状态分布、近14天趋势、最新明细。"""
    conn = _conn()

    # 各阶段人数(用于漏斗与饼图)
    stage_rows = conn.execute(
        "SELECT stage, COUNT(*) AS c FROM candidates GROUP BY stage"
    ).fetchall()
    stage_count = {r["stage"]: r["c"] for r in stage_rows}

    # 各状态人数
    status_rows = conn.execute(
        "SELECT status, COUNT(*) AS c FROM candidates GROUP BY status"
    ).fetchall()
    status_count = {r["status"]: r["c"] for r in status_rows}

    # 近 14 天新增趋势
    trend_rows = conn.execute(
        """SELECT substr(create_time, 1, 10) AS day, COUNT(*) AS c
           FROM candidates
           GROUP BY day ORDER BY day DESC LIMIT 14"""
    ).fetchall()
    trend = [{"date": r["day"], "count": r["c"]} for r in trend_rows][::-1]

    conn.close()

    # 漏斗按固定阶段顺序输出
    funnel = [
        {"stage": s, "count": stage_count.get(s, 0)} for s in STAGES
    ]
    return {
        "total": sum(stage_count.values()),
        "funnel": funnel,
        "stage_count": stage_count,
        "status_count": status_count,
        "trend": trend,
        "candidates": all_candidates(50),
    }


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成:", config.DB_PATH)
