# -*- coding: utf-8 -*-
"""企业微信智能机器人 · 长连接接收脚本。

HR 在企业微信群里 @机器人 发消息(如「张三 过了二面 后端 期望15k」),
脚本自动解析入库,并回复确认。与 app.py 共用 recruit.db,看板实时更新。

运行方式:
    双击「启动智能机器人.bat」,或命令行:
        pip install -i https://pypi.tuna.tsinghua.edu.cn/simple wecom-aibot-python-sdk
        python wecom_robot.py

依赖:wecom-aibot-python-sdk(官方 Python SDK,内置心跳保活/断线重连)
配置:config.py 的 WECOM_BOT_ID / WECOM_BOT_SECRET(企微后台智能机器人 → API模式 → 长连接)
"""
import re
import sys

import config
import llm_parser
import storage

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from aibot import WSClient, WSClientOptions
except ImportError:
    print("缺少依赖,请先执行:")
    print("    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple wecom-aibot-python-sdk")
    sys.exit(1)


def _clean_mention(content):
    """去掉群聊里的 @机器人 前缀(如 '@招聘数据助手 张三 过了二面')。

    单聊时通常没有 @ 前缀,原样返回。
    """
    return re.sub(r"^\s*@[^\s@]+", "", content).strip()


async def on_text(client, frame):
    try:
        body = frame.get("body", {})
        content = ((body.get("text") or {}).get("content") or "").strip()
        if not content:
            return
        text = _clean_mention(content)
        if not text:
            return

        records = llm_parser.parse_records(text, source="企业微信智能机器人")
        storage.insert_many(records)

        if records:
            names = "、".join(r["name"] for r in records if r.get("name"))
            reply = f"✅ 已记录 **{names}** 共 {len(records)} 条,看板已更新"
        else:
            reply = "❌ 未能识别出候选人信息,试试格式:**姓名 阶段 岗位 期望薪资**"
        await client.reply(frame, {"msgtype": "markdown", "markdown": {"content": reply}})
        print(f"[robot] 收到: {text}")
        print(f"[robot] 回复: {reply}")
    except Exception as e:
        print("[robot] 处理异常:", e)
        try:
            await client.reply(frame, {
                "msgtype": "markdown",
                "markdown": {"content": f"❌ 解析失败:{e}"},
            })
        except Exception:
            pass


def main():
    storage.init_db()

    bot_id = config.WECOM_BOT_ID
    secret = config.WECOM_BOT_SECRET
    if not bot_id or not secret:
        print("请先在 config.py 填写 WECOM_BOT_ID 和 WECOM_BOT_SECRET")
        print("获取位置:企微后台 → 应用管理 → 智能机器人 → API模式 → 长连接")
        sys.exit(1)

    client = WSClient(WSClientOptions(bot_id=bot_id, secret=secret))
    client.on("message.text", lambda frame: on_text(client, frame))
    print("智能机器人长连接已启动,等待 HR 消息...")
    print("(Ctrl+C 停止)")
    try:
        client.run()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
