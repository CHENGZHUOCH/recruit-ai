# -*- coding: utf-8 -*-
"""全局配置:API Key、服务端口、数据文件路径。"""
import os

# ── 大模型配置 ──────────────────────────────────────────────
# 填入 DEEPSEEK_API_KEY 后启用 DeepSeek 语义解析;
# 留空则使用内置规则引擎解析(零依赖,同样可运行 Demo)。
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ── 服务配置 ──────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8080

# ── 企业微信智能机器人(长连接)配置───────────────────────────
# 对应企微后台 → 应用管理 → 智能机器人 → API模式 → 长连接 里的 BotID 和 Secret。
# 长连接方案无需公网 URL / 备案域名,HR 在群里 @机器人 发消息即自动入库。
WECOM_BOT_ID = os.environ.get("WECOM_BOT_ID", "")
WECOM_BOT_SECRET = os.environ.get("WECOM_BOT_SECRET", "")

# ── 数据文件 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "recruit.db")
DASHBOARD_PATH = os.path.join(BASE_DIR, "dashboard.html")
CSV_PATH = os.path.join(BASE_DIR, "招聘数据_同步腾讯文档.csv")

# ── 本机私有配置(可选)──────────────────────────────────────
# 若存在 config_local.py(已被 .gitignore 排除,不进入代码仓库),
# 则用其中的真实 Key/凭据覆盖上面留空的值,方便本机直接运行。
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
