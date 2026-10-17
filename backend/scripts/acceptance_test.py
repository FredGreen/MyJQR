# -*- coding: utf-8 -*-
"""本机验收测试：按 docs/测试用例-本机验收.md 逐条执行。

用法（backend/ 目录下，需 API+worker 已启动、.env 已填 DEEPSEEK_API_KEY）：
    python -X utf8 -m scripts.acceptance_test
可配：环境变量 MYJQR_BASE（默认 http://127.0.0.1:9000）
"""
import json
import os
import sys
import time

import httpx

BASE = os.environ.get("MYJQR_BASE", "http://127.0.0.1:9000")
CLIENT = httpx.Client(base_url=BASE, timeout=30)

RESULTS: list[tuple[str, bool, str]] = []


def run_tc(tc: str, name: str, fn):
    try:
        detail = fn()
        RESULTS.append((tc, True, detail or "ok"))
        print(f"[PASS] {tc} {name}" + (f" — {detail}" if detail else ""))
    except Exception as e:
        RESULTS.append((tc, False, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {tc} {name} — {type(e).__name__}: {e}")


def ok(resp, status=200):
    assert resp.status_code == status, f"HTTP {resp.status_code}: {resp.text[:200]}"
    return resp.json()


def api(method, path, token=None, expect=200, **kw):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return ok(CLIENT.request(method, path, headers=headers, **kw), expect)


# ---------- 全局状态（用例间传递） ----------
S = {}


def tc01_health():
    d = api("GET", "/health")
    assert d["code"] == 0
    return d["msg"]


def tc02_register():
    email = f"accept{int(time.time())}@test.com"
    d = api("POST", "/api/v1/auth/register",
            json={"email": email, "password": "test12345", "nickname": "验收测试"})
    S["email"], S["password"] = email, "test12345"
    S["token"] = d["data"]["tokens"]["access_token"]
    return f"user_id={d['data']['id']}, email={email}"


def tc03_login():
    d = api("POST", "/api/v1/auth/login",
            json={"email": S["email"], "password": S["password"]})
    assert d["data"]["tokens"]["access_token"]
    return "tokens issued"


def tc04_categories():
    d = api("GET", "/api/v1/template/category/list", S["token"])
    lst = d["data"]["list"]
    assert len(lst) == 15, f"分类数 {len(lst)} != 15"
    S["category_id"] = lst[0]["category_id"]
    return f"{len(lst)} categories"


def tc05_recommend_pagination():
    p1 = api("GET", "/api/v1/template/recommend/list",
             S["token"], params={"page_size": 20})["data"]
    assert len(p1["list"]) == 20 and p1["has_more"] and p1["cursor"] > 0
    p2 = api("GET", "/api/v1/template/recommend/list", S["token"],
             params={"page_size": 20, "cursor": p1["cursor"]})["data"]
    ids1 = {t["template_id"] for t in p1["list"]}
    ids2 = {t["template_id"] for t in p2["list"]}
    assert not (ids1 & ids2), "两页出现重复模板"
    # 翻完所有页，供 TC06 按名字找模板（种子模板 id 小，排在推荐列表末尾）
    all_tpls, cursor = list(p1["list"]), p1["cursor"]
    while cursor:
        page = api("GET", "/api/v1/template/recommend/list", S["token"],
                   params={"page_size": 20, "cursor": cursor})["data"]
        all_tpls += page["list"]
        cursor = page["cursor"]
    S["templates"] = all_tpls
    return f"page1=20, page2={len(p2['list'])}, cursor={p1['cursor']}, total={len(all_tpls)}"


def tc06_detail_no_prompt_leak():
    tpl = next(t for t in S["templates"] if t["name"] == "今日选题")
    S["gen_template_id"], S["gen_price"] = tpl["template_id"], tpl["joule_price"]
    d = api("GET", "/api/v1/template/detail", S["token"],
            params={"template_id": tpl["template_id"]})
    detail = d["data"]
    assert "system_prompt" not in json.dumps(detail), "提示词泄露到 detail"
    assert "user_prompt" not in json.dumps(detail), "提示词泄露到 detail"
    assert detail.get("usage_example"), "缺少 usage_example"
    return f"tpl={tpl['template_id']}({tpl['joule_price']}J), 无提示词泄露"


def tc07_category_templates():
    d = api("GET", "/api/v1/template/list", S["token"],
            params={"category_id": S["category_id"], "page_size": 100})
    items = d["data"]["list"]
    assert items and "rank" in items[0]
    return f"category {S['category_id']}: {len(items)} items"


def _find_tpl(tid: int) -> dict:
    """推荐列表按 id 倒序，种子模板在末尾——翻页找到目标模板。"""
    cursor, seen = 0, {}
    for _ in range(10):
        page = api("GET", "/api/v1/template/recommend/list", S["token"],
                   params={"page_size": 20, "cursor": cursor})["data"]
        for t in page["list"]:
            seen[t["template_id"]] = t
        if tid in seen or not page["cursor"]:
            break
        cursor = page["cursor"]
    assert tid in seen, f"翻完推荐列表未找到模板 {tid}"
    return seen[tid]


def tc08_bookmark():
    tid = S["gen_template_id"]
    api("POST", f"/api/v1/template/{tid}/bookmark", S["token"])
    assert _find_tpl(tid)["is_bookmarked"] is True, "收藏后 is_bookmarked 未变 true"
    api("DELETE", f"/api/v1/template/{tid}/bookmark", S["token"])
    assert _find_tpl(tid)["is_bookmarked"] is False, "取消收藏后 is_bookmarked 未变 false"
    return "收藏/取消收藏状态正确"


def tc09_initial_balance():
    d = api("GET", "/api/v1/joule/me", S["token"])
    bal = d["data"]["balance"]
    assert bal == 100, f"初始余额 {bal} != 100"
    return "balance=100"


def _read_stream(work_id: int, seq: int = 0, timeout: float = 300):
    """读取 SSE 流直到 done/error，返回 (事件类型列表, delta 数, report, 结束事件data)。"""
    events, deltas, report, end_data = [], 0, None, None
    url = f"/api/v1/works/{work_id}/stream"
    headers = {"Authorization": f"Bearer {S['token']}"}
    deadline = time.time() + timeout
    cur_event = None
    with CLIENT.stream("GET", url, params={"seq": seq}, headers=headers,
                       timeout=httpx.Timeout(10, read=30)) as r:
        assert r.status_code == 200, f"stream HTTP {r.status_code}"
        for line in r.iter_lines():
            if time.time() > deadline:
                raise TimeoutError("SSE 读取超时")
            if line.startswith("event:"):
                cur_event = line[6:].strip()
                if cur_event not in events:
                    events.append(cur_event)
            elif line.startswith("data:") and cur_event:
                data = json.loads(line[5:].strip())
                if cur_event == "delta":
                    deltas += 1
                elif cur_event == "report":
                    report = data
                elif cur_event in ("done", "error"):
                    end_data = data
                    return events, deltas, report, end_data
    raise AssertionError(f"SSE 未收到终止事件，events={events}")


def tc10_generate_full_chain():
    d = api("POST", "/api/v1/works/generate", S["token"],
            json={"template_id": S["gen_template_id"],
                  "input": "写一篇关于坚持的短文",
                  "response_length": 1, "enable_think": False,
                  "show_references": True})
    work_id = d["data"]["work_id"]
    S["work_id"] = work_id
    assert d["data"]["joule_cost"] == S["gen_price"]
    events, deltas, report, end = _read_stream(work_id)
    assert "stage" in events, f"缺少 stage 事件: {events}"
    assert deltas > 0, f"无 delta 输出: {events}"
    assert "report" in events and report, f"缺少 AI 率报告: {events}"
    assert "done" in events, f"未正常结束: {events}, end={end}"
    # 扣费核验：100 - price
    bal = api("GET", "/api/v1/joule/me", S["token"])["data"]["balance"]
    assert bal == 100 - S["gen_price"], f"余额 {bal} != {100 - S['gen_price']}"
    w = api("GET", f"/api/v1/works/{work_id}", S["token"])["data"]
    assert w["status"] == "done", f"作品状态 {w['status']}"
    assert w.get("word_cnt", 0) > 0, "作品无字数"
    S["report"] = report
    return (f"work={work_id}, events={events}, deltas={deltas}, "
            f"word_cnt={w['word_cnt']}, balance={bal}")


def tc11_stream_replay():
    events, deltas, _, _ = _read_stream(S["work_id"], seq=0, timeout=30)
    assert "delta" in events and "done" in events, f"重放不完整: {events}"
    return f"replay ok, {deltas} deltas"


def tc12_insufficient_balance():
    # 余额已 0，再生成应 402
    assert api("GET", "/api/v1/joule/me", S["token"])["data"]["balance"] == 0
    resp = CLIENT.post("/api/v1/works/generate",
                       headers={"Authorization": f"Bearer {S['token']}"},
                       json={"template_id": S["gen_template_id"],
                             "input": "再写一篇关于勇气的短文",
                             "response_length": 1, "enable_think": False})
    assert resp.status_code == 402, f"HTTP {resp.status_code}: {resp.text[:150]}"
    return resp.json()["detail"]


def tc13_admin_login():
    d = api("POST", "/api/v1/admin/login",
            json={"username": "admin", "password": "admin123456"})
    # admin 登录的 data 即 issue_tokens() 返回值（无 tokens 包一层）
    S["admin_token"] = d["data"]["access_token"]
    return "admin token issued"


def tc14_dashboard():
    d = api("GET", "/api/v1/admin/dashboard/overview", S["admin_token"])
    assert d["code"] == 0 and d["data"]
    return json.dumps(d["data"], ensure_ascii=False)[:80] + "..."


def tc15_gen_redeem_codes():
    d = api("POST", "/api/v1/admin/redeem-codes/batch", S["admin_token"],
            json={"amount": 1000, "count": 1})
    S["code"] = d["data"]["codes"][0]
    return f"batch={d['data']['batch_no']}, code={S['code']}"


def tc16_redeem():
    d = api("POST", "/api/v1/joule/redeem", S["token"], json={"code": S["code"]})
    assert d["data"]["amount"] == 1000
    bal = api("GET", "/api/v1/joule/me", S["token"])["data"]["balance"]
    assert bal == 1000, f"充值后余额 {bal} != 1000"
    resp = CLIENT.post("/api/v1/joule/redeem",
                       headers={"Authorization": f"Bearer {S['token']}"},
                       json={"code": S["code"]})
    assert resp.status_code == 409, f"重复兑换应 409，实际 {resp.status_code}"
    return "充值 +1000，重复兑换被拒(409)"


def tc17_transactions():
    d = api("GET", "/api/v1/joule/transactions", S["token"])
    types = {t["biz_type"] for t in d["data"]["list"]}
    # freeze 不写流水（只记冻结核），结算记 generate，充值记 redeem
    assert {"gift", "generate", "redeem"} <= types, f"流水类型不全: {types}"
    return f"types={sorted(types)}"


def tc18_works_list():
    d = api("GET", "/api/v1/works", S["token"])
    ids = [w["work_id"] for w in d["data"]["list"]]
    assert S["work_id"] in ids, "作品列表缺刚生成的作品"
    w = api("GET", f"/api/v1/works/{S['work_id']}", S["token"])["data"]
    assert w.get("content") or w.get("content_rich") or w.get("title"), "作品详情无正文"
    return f"works={len(ids)}, title={w.get('title', '')[:30]}"


def main():
    print(f"== MyJQR 验收测试 @ {BASE} ==")
    tcs = [(k[2:].split("_", 1)[0], k[2:].split("_", 1)[1], fn)
           for k, fn in sorted(globals().items())
           if k.startswith("tc") and callable(fn) and k[2:4].isdigit()]
    for tc, name, fn in tcs:
        run_tc(tc, name, fn)
    passed = sum(1 for _, ok_, _ in RESULTS if ok_)
    print(f"\n== 结果：{passed}/{len(RESULTS)} 通过 ==")
    for tc, ok_, detail in RESULTS:
        if not ok_:
            print(f"  FAIL {tc}: {detail}")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
