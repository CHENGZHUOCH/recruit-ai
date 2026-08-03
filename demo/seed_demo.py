# -*- coding: utf-8 -*-
"""生成一批演示数据,让看板首次打开即有内容。可重复执行(每次追加)。"""
import random
from datetime import datetime, timedelta

import storage

NAMES = ["陈晓", "刘洋", "林静", "吴刚", "周雨", "郑爽", "孙倩", "朱伟", "胡悦", "何军",
         "郭婷", "罗鹏", "梁芳", "宋杰", "唐雪", "许强", "韩梅", "冯超", "曹娜", "邓飞"]
POSITIONS = ["后端工程师", "前端工程师", "测试工程师", "产品经理", "数据分析师",
             "算法工程师", "UI设计师", "运维工程师"]
STAGES = ["简历", "初筛", "面试", "Offer", "入职", "淘汰"]


def build_demo_records(n=30):
    now = datetime.now()
    recs = []
    for i in range(n):
        # 生成 1~25 天前的随机时间,营造"持续招聘"的趋势感
        day = now - timedelta(days=random.randint(1, 25), hours=random.randint(0, 8))
        stage = random.choice(STAGES)
        status = {"简历": "进行中", "初筛": "进行中", "面试": random.choice(["通过", "待定", "不通过"]),
                  "Offer": "通过", "入职": "已入职", "淘汰": "不通过"}[stage]
        recs.append({
            "name": random.choice(NAMES),
            "position": random.choice(POSITIONS),
            "stage": stage,
            "status": status,
            "salary": random.choice([10000, 12000, 15000, 18000, 20000, 0, 0]),
            "note": random.choice(["", "复试约下周", "薪资待谈", "简历优秀", "已约技术面", ""]),
            "source": "演示数据",
            "create_time": day.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return recs


if __name__ == "__main__":
    storage.init_db()
    storage.insert_many(build_demo_records())
    print(f"已生成演示数据,当前共 {storage.count_total()} 条候选人记录")
