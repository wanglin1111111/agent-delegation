#!/usr/bin/env python3
"""validate.py — agent-delegation Agent 委派计划七维校验器

输入: Agent 委派/自动化计划 JSON（schema 见 tests/sample_good.json）
  {
    "task_tiering": {                        // 第 1 步：任务分层
      "done": true,                          // 已做一周重复工作盘点
      "tiers": [
        {"name": "行业日报汇总", "frequency_per_week": 5, "tier": "A",
         "reversible": true, "trust_or_money": false, "decide_30s": true},
        {"name": "客户邮件回复", "frequency_per_week": 15, "tier": "B",
         "reversible": true, "trust_or_money": false, "decide_30s": true},
        {"name": "客户投诉安抚", "frequency_per_week": 2, "tier": "C",
         "reversible": false, "trust_or_money": true, "decide_30s": false}
      ]
    },
    "pilot": {                               // 第 2 步：单点试点
      "single_task": true,                   // 试点期只切一个任务
      "task": "每日行业简报",
      "four_conditions": {                   // 可交接四条件（全 true）
        "input_structurable": true,
        "result_verifiable": true,
        "error_rollbackable": true,
        "frequency_ge_3_per_week": true
      },
      "weeks_run": 2,                        // 试点周数（≥2）
      "success_rate": 0.9,                   // 成功率（≥0.80）
      "minutes_saved_ratio": 0.6             // 省分钟比（≥0.50）
    },
    "zero_friction_onboarding": {            // 第 3 步：零门槛接入
      "trigger_is_existing_action": true,    // 触发=本来就要做的动作
      "no_new_entry": true,                  // 没为 Agent 新建入口/流程
      "onboarding_week_missed_triggers": 0   // 接入一周"想起来才用"漏掉次数（=0）
    },
    "trust_ladder": {                        // 第 4 步：信任阶梯
      "current_level": "L2",                 // L1 只读 / L2 可写 / L3 可代发
      "level_evidence_weeks": 4,             // 当前级别达标证据周数
                                             // （L1→L2 需 ≥2；L2→L3 需 ≥4）
      "rollback_tested": true,               // 回滚流程实测过（L2 及以上必须）
      "human_review_point_set": true,        // 人工复核点已配置
      "l3_safety_set": ["草稿可见", "延迟发送", "白名单渠道", "频次上限"],
                                             // L3 必须四件套齐全
      "c_tier_automated": false,             // C 禁区任务被自动化（必须 false）
      "incident_this_period": 0              // 本周期事故数（>0 须已降级——
                                             // 由 level 与 evidence 一致性间接校验）
    },
    "asset_sediment": {                      // 第 5 步：沉淀资产
      "template_triad": true,                // 三件套齐（输入模板+提示词+验收清单）
      "sop_written": true,                   // SOP 一页纸写完
      "other_person_ran": true,              // 没跑过的人照 SOP 跑通 ≥3 次
      "sop_reuse_count": 1                   // 团队复用人数（≥1）
    },
    "risk_threshold": {                      // 第 6 步：风险硬阈值
      "money_tasks_exist": true,             // 有涉金额/额度的自动化
      "cost_per_error_calculated": true,     // 已算"错一次赔多少"
      "redline_in_config": true,             // 红线写进配置（非"我记得"）
      "redline_value": 10000,                // 红线金额（>0）
      "redline_recomputed_on_level_up": true,// 升级时重算过红线
      "incentive_aligned": true              // 激励与"做对"对齐（非纯"做成"）
    }
  }

七维校验（任一 FAIL → exit 1）：
  D1 任务分层: done=true 且 tiers 非空；每项 tier ∈ {A,B,C}；
     归层一致性：tier=C 须 trust_or_money=true 或 reversible=false（禁区理由成立）；
     tier=A/B 须 reversible=true 且 trust_or_money=false 且 decide_30s=true
     （A/B 出现涉信任资金或不可逆 = 错层，validate.py 拦截）
  D2 单点试点: single_task=true 且 four_conditions 四项全 true
     且 weeks_run ≥2 且 success_rate ≥0.80 且 minutes_saved_ratio ≥0.50
     （"感觉好用"不是验收；四条件缺一条先补条件）
  D3 零门槛接入: trigger_is_existing_action=true 且 no_new_entry=true
     且 onboarding_week_missed_triggers=0（漏>0=触发还不够零门槛，再降一档）
  D4 信任阶梯: current_level ∈ {L1,L2,L3}；
     L2 须 level_evidence_weeks ≥2 且 rollback_tested=true；
     L3 须 level_evidence_weeks ≥4 且 rollback_tested=true
     且 l3_safety_set 四件套齐全（草稿可见/延迟发送/白名单渠道/频次上限）；
     c_tier_automated 必须 false（C 禁区任何级别不碰）
  D5 沉淀资产: template_triad=true 且 sop_written=true
     且 other_person_ran=true（别人跑通才是真资产，只有你能跑=个人习惯）
     且 sop_reuse_count ≥1
  D6 风险硬阈值: money_tasks_exist=true 时——cost_per_error_calculated=true
     且 redline_in_config=true 且 redline_value>0 且 redline_recomputed_on_level_up=true
     且 incentive_aligned=true（别让佣金逻辑反过来收割你）；
     money_tasks_exist=false 时——本维直接 OK（无涉金额自动化）
  D7 一致性: trust_ladder.current_level 与 pilot 关系——
     current_level ≥L2 须 pilot 两个数达标（试点没过不能放权）；
     current_level = L3 须 pilot 达标 且 onboarding 三条件全过
     （L3 是对外，前置没齐 = 跳级）；
     且 task_tiering 里至少存在一个 tier ∈ {A,B} 的任务
     （分层表里全是 C = 没有可委派对象，试点无从谈起）

退出码：0=通过 / 1=有缺陷 / 2=文件/格式错误
"""
import json
import sys

TIERS = {"A", "B", "C"}
LEVELS = {"L1", "L2", "L3"}
L3_SAFETY = ("草稿可见", "延迟发送", "白名单渠道", "频次上限")


def fail(checks, code, msg):
    checks.append(("FAIL", code, msg))


def ok(checks, code, msg):
    checks.append(("OK", code, msg))


def validate(plan):
    checks = []

    tt = plan.get("task_tiering") or {}
    pl = plan.get("pilot") or {}
    zf = plan.get("zero_friction_onboarding") or {}
    tl = plan.get("trust_ladder") or {}
    asd = plan.get("asset_sediment") or {}
    rt = plan.get("risk_threshold") or {}

    # D1 任务分层
    tiers = tt.get("tiers") or []
    if tt.get("done") is not True:
        fail(checks, "D1", "done=false——没做一周重复工作盘点就谈 Agent=把权限决策留给事故")
    elif not tiers:
        fail(checks, "D1", "tiers 为空——盘点没产出分层结果")
    else:
        bad_tiers = []
        for t in tiers:
            nm = str(t.get("name", "?"))
            tier = t.get("tier")
            if tier not in TIERS:
                bad_tiers.append(f"{nm}(tier 非法)")
                continue
            rev = t.get("reversible") is True
            tm = t.get("trust_or_money") is True
            d30 = t.get("decide_30s") is True
            if tier == "C":
                if not (tm or rev is False):
                    bad_tiers.append(f"{nm}(归 C 但理由不成立：未涉信任/资金且可逆)")
            else:
                if tm:
                    bad_tiers.append(f"{nm}(涉对外信任/资金合规，必须 C 禁区，错归 {tier})")
                elif not rev:
                    bad_tiers.append(f"{nm}(不可逆，最高 B 层且须人工发出，错归 {tier})")
                elif not d30:
                    bad_tiers.append(f"{nm}(30 秒拍不了板，先拆任务，不能直接进 {tier})")
        if bad_tiers:
            fail(checks, "D1", "分层错误: " + "；".join(bad_tiers))
        else:
            n = len(tiers)
            ok(checks, "D1", f"任务分层合规（{n} 项任务，A/B/C 归层判据全过）")

    # D2 单点试点
    fc = pl.get("four_conditions") or {}
    sr = pl.get("success_rate")
    msr = pl.get("minutes_saved_ratio")
    wk = pl.get("weeks_run")
    if pl.get("single_task") is not True:
        fail(checks, "D2", "single_task=false——试点期同时切多个任务=出问题无法归因")
    elif not all(fc.get(k) is True for k in
                 ("input_structurable", "result_verifiable", "error_rollbackable",
                  "frequency_ge_3_per_week")):
        missing = [k for k in ("input_structurable", "result_verifiable",
                               "error_rollbackable", "frequency_ge_3_per_week")
                   if fc.get(k) is not True]
        fail(checks, "D2", f"可交接四条件缺: {missing}——缺一条先补条件再试点，不硬上")
    elif not isinstance(wk, int) or wk < 2:
        fail(checks, "D2", f"weeks_run={wk!r}——试点须 ≥2 周（两周才有稳定数字）")
    elif not isinstance(sr, (int, float)) or sr < 0.80:
        fail(checks, "D2", f"success_rate={sr!r}——成功率 <80%，'感觉好用'不是验收")
    elif not isinstance(msr, (int, float)) or msr < 0.50:
        fail(checks, "D2", f"minutes_saved_ratio={msr!r}——省分钟 <50%（工具成本>节省）")
    else:
        ok(checks, "D2", f"试点验收过（{wk} 周，成功率 {sr:.0%}，省分钟 {msr:.0%}）")

    # D3 零门槛接入
    missed = zf.get("onboarding_week_missed_triggers")
    if zf.get("trigger_is_existing_action") is not True:
        fail(checks, "D3", "trigger_is_existing_action=false——触发不是本来就要做的动作=新门槛")
    elif zf.get("no_new_entry") is not True:
        fail(checks, "D3", "no_new_entry=false——为 Agent 新建了入口/流程：多一道流程=必然用不起来")
    elif missed != 0:
        fail(checks, "D3", f"onboarding_week_missed_triggers={missed}——'想起来才用'漏了=触发还不够零门槛，再降一档")
    else:
        ok(checks, "D3", "零门槛接入合规（触发=已有动作，无新入口，一周零漏）")

    # D4 信任阶梯
    lv = tl.get("current_level")
    ew = tl.get("level_evidence_weeks")
    if lv not in LEVELS:
        fail(checks, "D4", f"current_level={lv!r}——级别非法（L1 只读/L2 可写/L3 可代发）")
    elif tl.get("c_tier_automated") is not False:
        fail(checks, "D4", "c_tier_automated=true——C 禁区（情感/对外承诺/资金合规）被自动化，任何级别都不碰")
    elif lv == "L1":
        if not isinstance(ew, int) or ew < 1:
            fail(checks, "D4", f"L1 达标证据 {ew!r} 周——L1 至少 1 周稳定运行")
        else:
            ok(checks, "D4", f"信任阶梯 L1 合规（{ew} 周证据，C 区零自动化）")
    else:
        need = 2 if lv == "L2" else 4
        if not isinstance(ew, int) or ew < need:
            fail(checks, "D4", f"{lv} 达标证据 {ew!r} 周——须 ≥{need} 周（L3 要 4 周，急=风险溢价不是信任）")
        elif tl.get("rollback_tested") is not True:
            fail(checks, "D4", "rollback_tested=false——{lv} 回滚流程没实测过（没实测的回滚=想象中的回滚）".format(lv=lv))
        elif tl.get("human_review_point_set") is not True:
            fail(checks, "D4", "human_review_point_set=false——人工复核点没配置，放权没有刹车")
        elif lv == "L3":
            safety = tl.get("l3_safety_set") or []
            missing = [s for s in L3_SAFETY if s not in safety]
            if missing:
                fail(checks, "D4", f"L3 安全四件套缺: {missing}——缺一不升 L3（对外发送没有反悔窗口=裸奔）")
            else:
                ok(checks, "D4", f"信任阶梯 L3 合规（{ew} 周证据 + 回滚实测 + 四件套齐全 + C 区零自动化）")
        else:
            ok(checks, "D4", f"信任阶梯 L2 合规（{ew} 周证据 + 回滚实测 + 复核点已配 + C 区零自动化）")

    # D5 沉淀资产
    if asd.get("template_triad") is not True:
        fail(checks, "D5", "template_triad=false——三件套缺（输入模板+提示词+验收清单缺一会漂移）")
    elif asd.get("sop_written") is not True:
        fail(checks, "D5", "sop_written=false——SOP 没写（跑通不固化，拖一周就丢了）")
    elif asd.get("other_person_ran") is not True:
        fail(checks, "D5", "other_person_ran=false——没跑过的人没照 SOP 跑通=个人习惯不是资产")
    elif not isinstance(asd.get("sop_reuse_count"), int) or asd.get("sop_reuse_count") < 1:
        fail(checks, "D5", f"sop_reuse_count={asd.get('sop_reuse_count')!r}——复用人数 <1，SOP 没进团队")
    else:
        ok(checks, "D5", f"沉淀合规（三件套 + SOP + 他人跑通，复用 {asd['sop_reuse_count']} 人）")

    # D6 风险硬阈值
    if rt.get("money_tasks_exist") is not True:
        ok(checks, "D6", "无涉金额/额度自动化（红线维度不适用）")
    else:
        rv = rt.get("redline_value")
        if rt.get("cost_per_error_calculated") is not True:
            fail(checks, "D6", "cost_per_error_calculated=false——没算'错一次赔多少'就放自动化=红线没有数学基础")
        elif rt.get("redline_in_config") is not True:
            fail(checks, "D6", "redline_in_config=false——红线没写进配置（'我记得'不是红线，配置才是）")
        elif not isinstance(rv, (int, float)) or rv <= 0:
            fail(checks, "D6", f"redline_value={rv!r}——红线金额非法（须 >0）")
        elif rt.get("redline_recomputed_on_level_up") is not True:
            fail(checks, "D6", "redline_recomputed_on_level_up=false——升级时没重算红线（L2/L3 覆盖动作范围变大，阈值要随级别明确）")
        elif rt.get("incentive_aligned") is not True:
            fail(checks, "D6", "incentive_aligned=false——激励与'做成'而非'做对'对齐=佣金逻辑反过来收割你")
        else:
            ok(checks, "D6", f"风险硬阈值合规（错一次赔已算 + 红线 {rv} 写进配置 + 升级重算 + 激励对齐）")

    # D7 一致性
    pilot_ok = (pl.get("single_task") is True
                and all(fc.get(k) is True for k in
                        ("input_structurable", "result_verifiable", "error_rollbackable",
                         "frequency_ge_3_per_week"))
                and isinstance(wk, int) and wk >= 2
                and isinstance(sr, (int, float)) and sr >= 0.80
                and isinstance(msr, (int, float)) and msr >= 0.50)
    onboarding_ok = (zf.get("trigger_is_existing_action") is True
                     and zf.get("no_new_entry") is True and missed == 0)
    has_ab = any(t.get("tier") in ("A", "B") for t in tiers)
    issues = []
    if lv in ("L2", "L3") and not pilot_ok:
        issues.append(f"信任级别 {lv} 但试点两数未达标（试点没过不能放权）")
    if lv == "L3" and not onboarding_ok:
        issues.append("L3 对外但零门槛接入未全过（前置没齐=跳级）")
    if tiers and not has_ab:
        issues.append("分层表里全是 C 禁区（没有可委派对象，试点无从谈起）")
    if issues:
        fail(checks, "D7", "一致性: " + "；".join(issues))
    else:
        ok(checks, "D7", f"一致性合规（级别 {lv} 与试点/接入/分层前置匹配）")

    return checks


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py plan.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: 无法读取/解析: {e}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict):
        print("ERROR: 顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    checks = validate(plan)
    fails = [c for c in checks if c[0] == "FAIL"]
    for status, code, msg in checks:
        if status == "FAIL":
            print(f"[{code}] FAIL {msg}")
    print(f"== {len(checks) - len(fails)} OK / {len(fails)} FAIL ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
