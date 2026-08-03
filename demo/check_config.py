# -*- coding: utf-8 -*-
"""供「安装依赖.bat」调用:检查机器人配置是否已填写。"""
import sys

import config

if config.WECOM_BOT_ID and config.WECOM_BOT_SECRET:
    sys.exit(0)
sys.exit(1)
