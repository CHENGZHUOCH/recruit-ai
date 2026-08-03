# -*- coding: utf-8 -*-
"""同步到腾讯在线文档(最低成本路径)。

方案 A(免费,推荐起步):导出 CSV,人工导入腾讯文档 / 企业微信文档,30 秒完成。
方案 B(进阶):调用腾讯文档开放平台 API 自动写入,需企业管理员在 https://docs.qq.com 申请应用凭证。

本脚本实现方案 A,并预留方案 B 的接入点说明。
"""
import urllib.request

import config
import storage


def export_csv_local():
    """方案 A:把数据库导出为 CSV(UTF-8 BOM,Excel 可直接打开)。"""
    rows = storage.all_candidates()
    with open(config.CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        f.write("姓名,岗位,阶段,状态,薪资(元/月),备注,来源,时间\n")
        for r in rows:
            cells = [r["name"], r["position"], r["stage"], r["status"], r["salary"],
                     r["note"].replace(",", "，"), r["source"], r["create_time"]]
            f.write(",".join(str(c) for c in cells) + "\n")
    return config.CSV_PATH


def fetch_from_server(host, port):
    """从运行中的服务拉取最新数据到 CSV,保证同步的是实时数据。"""
    with urllib.request.urlopen(f"http://{host}:{port}/api/export.csv", timeout=10) as resp:
        with open(config.CSV_PATH, "wb") as f:
            f.write(resp.read())
    return config.CSV_PATH


# ── 方案 B 接入点(腾讯文档开放平台,需企业凭证)──────────────────
# 1. 企业管理员在 docs.qq.com 开放平台创建应用,拿到 ClientId/ClientSecret
# 2. 换取 access_token 后,调用「创建表格/追加数据」接口,把候选人逐行写入
# 3. 每有新消息入库,可触发一次追加写入,实现真正"实时同步"
# 伪代码:
#   POST https://api.docs.qq.com/openapi/v1/doc/create_doc
#   POST https://api.docs.qq.com/openapi/v1/records  body=[{...候选人...}]


if __name__ == "__main__":
    path = export_csv_local()
    print("已导出(可直接上传腾讯在线文档):", path)
    print("共", storage.count_total(), "条记录")
    print("步骤:新建腾讯文档 → 导入 → 上传该 CSV → 选『替换』,即可作为团队共享的招聘台账。")
