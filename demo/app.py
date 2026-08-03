# -*- coding: utf-8 -*-
"""招聘数据管家 · Demo 服务端。

零第三方依赖,运行方式:
    python app.py
然后浏览器打开 http://127.0.0.1:8080

接口:
    GET  /                招聘可视化看板(dashboard.html)
    GET  /api/dashboard   看板统计 JSON
    GET  /api/candidates  候选人明细 JSON
    POST /api/msg         接收企业微信风格的自然语言消息(核心入口)
    GET  /api/export.csv  导出 CSV(用于同步腾讯在线文档)
企业微信接收见 wecom_robot.py(智能机器人长连接)。
"""
import csv
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
import llm_parser
import storage


def _handle_msg(raw_text, source="企业微信"):
    """核心业务:自然语言 → AI 解析 → 入库 → 返回结果。"""
    records = llm_parser.parse_records(raw_text, source=source)
    storage.insert_many(records)
    return records


def _text_message(body):
    """提取消息文本:兼容 JSON 消息体(Content/content/text 字段)与纯文本。"""
    try:
        data = json.loads(body)
    except Exception:
        return body.decode("utf-8", "ignore")
    if isinstance(data, dict):
        for key in ("Content", "content", "text"):
            if key in data:
                val = data[key]
                if isinstance(val, dict):
                    val = val.get("Content") or val.get("content") or val.get("text")
                if val:
                    return str(val)
    return json.dumps(data, ensure_ascii=False)


class Handler(BaseHTTPRequestHandler):
    def _query_params(self):
        q = parse_qs(urlparse(self.path).query)
        return {k: v[0] for k, v in q.items()}

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(config.DASHBOARD_PATH, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/dashboard":
            return self._send(200, json.dumps(storage.dashboard_stats(), ensure_ascii=False))
        if path == "/api/candidates":
            return self._send(200, json.dumps(storage.all_candidates(), ensure_ascii=False))
        if path == "/api/export.csv":
            return self._export_csv()
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/msg":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            text = _text_message(body)
            records = _handle_msg(text)
            return self._send(200, json.dumps({
                "ok": True,
                "message": f"已识别 {len(records)} 条候选人记录",
                "records": records,
            }))
        return self._send(404, json.dumps({"error": "not found"}))

    def _export_csv(self):
        rows = storage.all_candidates()
        with open(config.CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["姓名", "岗位", "阶段", "状态", "薪资(元/月)", "备注", "来源", "时间"])
            writer.writeheader()
            for r in rows:
                writer.writerow({
                    "姓名": r["name"], "岗位": r["position"], "阶段": r["stage"],
                    "状态": r["status"], "薪资(元/月)": r["salary"], "备注": r["note"],
                    "来源": r["source"], "时间": r["create_time"],
                })
        return self._send(200, open(config.CSV_PATH, "rb").read(), "text/csv; charset=utf-8")

    def log_message(self, *args):
        pass  # 精简控制台输出


def main():
    storage.init_db()
    server = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    print(f"招聘数据管家已启动: http://{config.HOST}:{config.PORT}")
    print("当前共", storage.count_total(), "条候选人记录")
    print("AI 模式:", "DeepSeek(已配置 API Key)" if config.DEEPSEEK_API_KEY else "规则引擎(内置,未配置 Key)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
