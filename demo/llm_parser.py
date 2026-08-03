# -*- coding: utf-8 -*-
"""AI 语义解析层:把 HR 的自然语言汇报解析成结构化候选人记录。

主链路:DeepSeek 大模型(配置了 API Key 时)
兜底链路:内置规则引擎(无 Key / 无网络 / 解析异常时,保证 Demo 可跑)

规则引擎设计要点:
- 整句话优先解析为"一条候选人记录"(常见场景:一人一汇报)
- 姓名识别采用"锚点法":候选人姓名后 0~3 字内常紧跟业务动作词
  (通过/过了/挂了/面试/offer/入职/淘汰/期望 等),据此精准定位人名
- 一句话包含多人时才按标点切段逐条解析
"""
import json
import re
import sys
import urllib.request

import config
from storage import STAGES, STATUSES

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# DeepSeek 解析提示词:只让模型输出 JSON 数组,不做任何多余动作
SYSTEM_PROMPT = """你是招聘数据录入助手。HR 会用自然语言汇报招聘进展,请把其中每位候选人的信息解析为 JSON 对象,最后输出一个 JSON 数组(即使只有一个人也要用数组)。

每人的字段:
- name: 候选人姓名(字符串)
- position: 应聘岗位(字符串,如 后端工程师、前端、产品经理)
- stage: 当前阶段,必须从以下枚举取一个:["简历","初筛","面试","Offer","入职","淘汰"]
  映射参考:一面/二面/三面/技术面/HR面 都归为"面试";通过/拒绝/不合适 依据语境判断。
- status: 状态,必须从以下枚举取一个:["进行中","通过","不通过","待定","已入职"]
  (面试通过→通过,挂了/不合适/pass→不通过,口头offer已接受→已入职)
- salary: 薪资数字(元/月,如 15k→15000,1.5万→15000;未提及则填0)
- note: 其他关键信息(面试时间、待办、补充说明),没有则填空字符串

规则:不输出任何解释文字,只输出 JSON 数组。无法判断的字段用默认值。
特别注意:不要把"待定""还有""一个"等数量词/人称/引导语误当成候选人姓名;只有当明确是人名时才作为 name。"""


def parse_records(text, source="企业微信"):
    """解析一段 HR 汇报文本,返回候选人记录 dict 列表。"""
    text = (text or "").strip()
    if not text:
        return []

    records = _parse_by_llm(text)
    if not records:
        records = _parse_by_rules(text)

    for r in records:
        r["source"] = source
    return records


# ────────────────────────── 大模型链路 ──────────────────────────
def _parse_by_llm(text):
    if not config.DEEPSEEK_API_KEY:
        return []
    try:
        payload = json.dumps({
            "model": config.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
        }).encode("utf-8")
        req = urllib.request.Request(
            config.DEEPSEEK_BASE_URL + "/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + config.DEEPSEEK_API_KEY,
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        content = re.sub(r"^```(json)?|```$", "", content.strip())
        records = json.loads(content)
        if isinstance(records, dict):  # 兜底:模型可能只输出单个对象
            records = [records]
        return [_normalize(r) for r in records if isinstance(r, dict)]
    except Exception as e:  # 网络/解析失败时自动降级到规则引擎
        print("[llm] 解析失败,降级规则引擎:", e)
        return []


# ────────────────────────── 规则引擎兜底 ──────────────────────────
# 常见非人名词(避免把"候选人""产品经理"误当姓名)
_STOP_WORDS = {
    "今天", "昨天", "明天", "上周", "下周", "本周", "这周", "现在", "刚刚",
    "已经", "目前", "上午", "下午", "晚上", "早上", "这个", "那个", "一个",
    "候选人", "工程师", "产品经理", "产品", "后端", "前端", "测试", "算法",
    "设计", "运营", "数据分析", "数据", "开发", "运维", "专员", "经理",
    "主管", "总监", "顾问", "助理", "实习", "岗位", "简历", "薪资", "期望",
}
_POSITION_PREFIX = ("产品", "后端", "前端", "测试", "算法", "数据", "设计",
                    "运营", "开发", "运维", "实习生", "助理", "顾问", "专员")

_STAGE_PATTERN = re.compile(
    r"(简历|初筛|一面|二面|三面|复试|终面|技术面|HR面|面试|Offer|口头offer|入职|淘汰|pass|拒绝|不合适)"
)
_STATUS_PATTERN = re.compile(
    r"(通过|过了|挂了|没戏|不行|淘汰|拒绝|pass|待定|考虑|已入职|入职了|到岗)"
)
# 职位词:先匹配完整职位名,再匹配职位简称
_POSITION_FULL = re.compile(
    r"(后端工程师|前端工程师|测试工程师|算法工程师|数据分析师|数据工程师|"
    r"产品经理|运营专员|UI设计师|运维工程师|实施工程师|项目经理|开发工程师)"
)
_POSITION_SHORT = re.compile(r"(后端|前端|测试|产品|运营|算法|数据|设计|开发|运维|数分|HR|UI)")
_SALARY_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*([kKwW万])")

_STAGE_MAP = {
    "简历": "简历", "初筛": "初筛",
    "一面": "面试", "二面": "面试", "三面": "面试", "复试": "面试",
    "终面": "面试", "技术面": "面试", "HR面": "面试", "面试": "面试",
    "offer": "Offer", "口头offer": "Offer",
    "入职": "入职",
    "淘汰": "淘汰", "pass": "淘汰", "拒绝": "淘汰", "不合适": "淘汰",
}
_STATUS_MAP = {
    "通过": "通过", "过了": "通过",
    "挂了": "不通过", "没戏": "不通过", "不行": "不通过",
    "淘汰": "不通过", "拒绝": "不通过", "pass": "不通过", "不合适": "不通过",
    "待定": "待定", "考虑": "待定",
    "已入职": "已入职", "入职了": "已入职", "到岗": "已入职",
}
_TIME_WORDS = ("今天|昨天|明天|上周|下周|本周|这周|周[一二三四五六日天]|"
               "现在|刚刚|已经|目前|上午|下午|晚上|早上|这个|那个|一个")

# 姓名后 0~2 字内出现的业务动作/阶段词,用于锚定"这句话在讲一个候选人"
_ACTION_WORDS = re.compile(
    r"通过|过了|挂了|没戏|不行|待定|考虑|入职|面试|一面|二面|三面|复试|终面|"
    r"技术面|HR面|offer|淘汰|pass|简历|初筛|不合适|期望|约了|约"
)


def _is_name(cand):
    """候选词是否可作姓名:排除停止词、职位前缀、阶段/状态词。"""
    low = cand.lower()
    if cand in _STOP_WORDS or cand.startswith(_POSITION_PREFIX):
        return False
    if low in _STAGE_MAP or low in _STATUS_MAP:
        return False
    return True


def _plausible(cand):
    """疑似姓名的启发式:3 字名末字若是动词虚词,大概率是"张三过"这类误切。"""
    if len(cand) == 3 and cand[-1] in "过了着的一在是有进到约谈给被把和跟":
        return False
    return _is_name(cand)


def _has_business(rest):
    """片段里是否含岗位/阶段/状态等业务信息,用于区分"讲候选人"与"闲聊"。"""
    return bool(
        _STAGE_PATTERN.search(rest) or _STATUS_PATTERN.search(rest)
        or _POSITION_FULL.search(rest) or _POSITION_SHORT.search(rest)
    )


def _after_action(t, idx):
    """名字后 0~2 个汉字内是否紧跟业务动作词。"""
    for k in (0, 1, 2):
        if _ACTION_WORDS.match(t[idx + k:]):
            return True
    return False


def _find_name(seg):
    """三级找姓名:① 句首姓名(HR 汇报多以姓名开头)→ ② 锚点法 → ③ 首个非停止词。"""
    t = re.sub(_TIME_WORDS, " ", seg).strip()
    if not t:
        return None

    # ① 句首姓名:最常见,且需句中带业务信息才采信
    head = re.match(r"([\u4e00-\u9fa5]{2,3})", t)
    if head and _plausible(head.group(1)):
        if _has_business(t[len(head.group(1)):]):
            return head.group(1)

    # ② 锚点法:整句扫描"名字后紧跟业务动作"的候选(含 2/3 字重叠)
    for i in range(len(t)):
        for L in (3, 2):
            if i + L > len(t):
                continue
            cand = t[i:i + L]
            if _plausible(cand) and _after_action(t, i + L):
                return cand

    # ③ 首个非停止词
    for m in re.finditer(r"[\u4e00-\u9fa5]{2,3}", t):
        if _plausible(m.group(0)):
            return m.group(0)
    return None


def _extract_position(seg, name):
    """岗位提取:先剔除姓名/数字/时间/阶段/状态词,再匹配职位词。"""
    t = seg
    if name:
        t = t.replace(name, " ", 1)
    t = re.sub(r"[0-9a-zA-Z]+", " ", t)
    t = re.sub(_TIME_WORDS, " ", t)
    for w in sorted(_STAGE_MAP, key=len, reverse=True):
        t = t.replace(w, " ")
    for w in sorted(_STATUS_MAP, key=len, reverse=True):
        t = t.replace(w, " ")
    t = re.sub(r"[，。,.、;；\s]+", " ", t)
    m = _POSITION_FULL.search(t) or _POSITION_SHORT.search(t)
    return m.group(1) if m else ""


def _parse_by_rules(text):
    """整句优先(常见:一人一汇报);整句解不出再按标点切段(多人一条)。"""
    rec = _rule_one(text)
    if rec:
        return [rec]
    records = []
    for seg in re.split(r"[、，,;；]", text):
        r = _rule_one(seg.strip())
        if r:
            records.append(r)
    return records


def _rule_one(seg):
    seg = seg.strip()
    if len(seg) < 2:
        return None
    name = _find_name(seg)
    stage_m = _STAGE_PATTERN.search(seg)
    status_m = _STATUS_PATTERN.search(seg)
    salary_m = _SALARY_PATTERN.search(seg)

    if not name:
        return None
    # 既无岗位又无阶段/状态信息,大概率是闲聊,不强行入库
    position = _extract_position(seg, name)
    if not (position or stage_m or status_m):
        return None

    stage = _STAGE_MAP.get(stage_m.group(1).lower(), "简历") if stage_m else "简历"
    status = "进行中"
    if status_m:
        status = _STATUS_MAP.get(status_m.group(1).lower(), status)
    # 阶段与状态联动:已入职/已淘汰则补全对应状态
    if status == "进行中":
        if stage == "入职":
            status = "已入职"
        elif stage == "淘汰":
            status = "不通过"

    salary = 0
    if salary_m:
        num = float(salary_m.group(1))
        unit = salary_m.group(2).lower()
        salary = int(num * (10000 if unit in "万w" else 1000))

    # 备注 = 原句去掉姓名/薪资/时间词后的关键信息
    note = seg
    if name:
        note = note.replace(name, " ", 1)
    if salary_m:
        note = note.replace(salary_m.group(0), " ")
    note = re.sub(_TIME_WORDS, " ", note)
    note = re.sub(r"[，。,.、;；\s]+", " ", note).strip()

    return _normalize({
        "name": name,
        "position": position,
        "stage": stage,
        "status": status,
        "salary": salary,
        "note": note,
    })


def _normalize(r):
    """字段规范化:枚举校验、阶段与状态联动、薪资取整、默认值。"""
    stage = r.get("stage", "简历")
    status = r.get("status", "进行中")
    if stage not in STAGES:
        stage = "简历"
    if status not in STATUSES:
        status = "进行中"
    if status == "进行中":
        if stage == "入职":
            status = "已入职"
        elif stage == "淘汰":
            status = "不通过"
    return {
        "name": (r.get("name") or "").strip() or "未命名",
        "position": (r.get("position") or "").strip(),
        "stage": stage,
        "status": status,
        "salary": int(r.get("salary") or 0),
        "note": (r.get("note") or "").strip(),
    }


if __name__ == "__main__":
    demo_texts = [
        "今天张三过了一面,后端工程师,期望 15k,二面约周四",
        "李四 offer 了,前端,12k,周五入职",
        "王五那个产品经理简历不合适,pass 掉",
        "赵六 候选人 一面挂了 测试岗位",
        "孙倩 算法工程师 初筛通过,已约技术面",
        "周雨 UI设计师 已入职,薪资18k",
    ]
    for t in demo_texts:
        print("原文:", t)
        for r in parse_records(t):
            print("  →", json.dumps(r, ensure_ascii=False))
