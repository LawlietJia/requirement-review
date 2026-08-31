#!/usr/bin/env python3
"""validate_review.py 的测试（TDD：先于实现编写）。运行: python3 test_validate_review.py"""
import json, os, sys, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("validate_review", os.path.join(HERE, "validate_review.py"))

def load():
    vr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vr)
    return vr

LEDGER_HEADER = ("| F-ID | 维度 | impact_level | evidence_status | release_effect | 定位 | 原文摘录 | "
                 "问题描述与后果 | 证据来源 | 修改建议 | 关闭条件 | 澄清问题 | 状态 |")
SEP = "|---|---|---|---|---|---|---|---|---|---|---|---|---|"

def row(fid="F-001", dim="D3", imp="P0", ev="已确认", rel="阻断", loc="§2.1",
        quote="有效期为1年", desc="与§3.2矛盾", src="GB/T 9385", sug="统一口径",
        close="修订后两处一致", cl="无", st="打开"):
    return f"| {fid} | {dim} | {imp} | {ev} | {rel} | {loc} | {quote} | {desc} | {src} | {sug} | {close} | {cl} | {st} |"

def make_dir(ledger_rows, matrix=None):
    d = tempfile.mkdtemp(prefix="vr-test-")
    with open(os.path.join(d, "issues-ledger.md"), "w") as f:
        f.write(LEDGER_HEADER + "\n" + SEP + "\n" + "\n".join(ledger_rows) + "\n")
    # 合法基线：补齐必需产物（个别用例按需覆盖）
    with open(os.path.join(d, "req-items.md"), "w") as f:
        f.write("REQ-001 示例条目\n")
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("| 时间 | 层级 | 去标识化查询 | 脱敏检查 | 来源 | 结论摘要 | 应用到 Finding |\n|---|---|---|---|---|---|---|\n")
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n不通过\n")
    if matrix is not None:
        with open(os.path.join(d, "coverage-matrix.md"), "w") as f:
            f.write(matrix)
    return d

CASES = []
def case(name):
    def deco(fn): CASES.append((name, fn)); return fn
    return deco

@case("合法ledger通过")
def t_ok():
    vr = load()
    r = vr.validate(make_dir([row()]))
    assert r["violations"] == [], r["violations"]

@case("重复F-ID违规")
def t_dup():
    vr = load()
    r = vr.validate(make_dir([row(fid="F-001"), row(fid="F-001", imp="P2", rel="不影响放行")]))
    assert any("F-ID" in v and ("重复" in v or "唯一" in v) for v in r["violations"]), r["violations"]

@case("P0缺原文摘录违规")
def t_p0_no_quote():
    vr = load()
    r = vr.validate(make_dir([row(quote="")]))
    assert any("原文摘录" in v for v in r["violations"]), r["violations"]

@case("P1缺关闭条件违规")
def t_p1_no_close():
    vr = load()
    r = vr.validate(make_dir([row(imp="P1", close="")]))
    assert any("关闭条件" in v for v in r["violations"]), r["violations"]

@case("非法impact_level违规")
def t_bad_level():
    vr = load()
    r = vr.validate(make_dir([row(imp="P5")]))
    assert any("impact_level" in v for v in r["violations"]), r["violations"]

@case("待核验不得定阻断")
def t_unverified_block():
    vr = load()
    r = vr.validate(make_dir([row(ev="待核验", rel="阻断")]))
    assert any("阻断" in v and "待核验" in v for v in r["violations"]), r["violations"]

@case("外部事实无核验日期违规")
def t_ext_no_date():
    vr = load()
    r = vr.validate(make_dir([row(src="http://example.gov.cn/law.htm（来源类型:法规）")]))
    assert any("核验日期" in v for v in r["violations"]), r["violations"]

@case("外部事实带核验日期通过")
def t_ext_with_date():
    vr = load()
    r = vr.validate(make_dir([row(src="http://example.gov.cn/law.htm（来源类型:法规；核验日期:2026-08-29）")]))
    assert r["violations"] == [], r["violations"]

@case("引用不存在的REQ违规")
def t_bad_ref():
    vr = load()
    d = make_dir([row(desc="与 REQ-999 矛盾")])
    r = vr.validate(d)
    assert any("REQ-999" in v for v in r["violations"]), r["violations"]

@case("表格竖线转义不破坏解析")
def t_pipe_escape():
    vr = load()
    r = vr.validate(make_dir([row(desc="字段\\|值的表格内容", quote="a\\|b")]))
    assert r["violations"] == [], r["violations"]
    assert r["findings"][0]["问题描述与后果"] == "字段\\|值的表格内容"

@case("覆盖矩阵单侧悬空违规")
def t_matrix_dangling():
    vr = load()
    matrix = ("| BIZ-ID | 覆盖状态 | REQ 引用 |\n|---|---|---|\n"
              "| BIZ-01 | 完全覆盖 | REQ-404 |\n")
    r = vr.validate(make_dir([row(imp="P2", rel="不影响放行")], matrix=matrix))
    assert any("REQ-404" in v for v in r["violations"]), r["violations"]

@case("review_status缺失违规")
def t_no_status():
    vr = load()
    d = make_dir([row()])
    # 报告缺失 review_status 字段
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("# 评审报告\n\n总体结论：不通过\n")
    r = vr.validate(d)
    assert any("review_status" in v for v in r["violations"]), r["violations"]

# ===== 加固轮失败测试（Codex 实测反例，2026-08-29）=====

@case("三枚举字段留空必违规")
def t_empty_enum():
    vr = load()
    r = vr.validate(make_dir([row(imp="", ev="", rel="")]))
    assert sum(1 for v in r["violations"] if "impact_level" in v or "evidence_status" in v or "release_effect" in v) >= 3, r["violations"]

@case("条件成立+阻断必违规")
def t_conditional_block():
    vr = load()
    r = vr.validate(make_dir([row(ev="条件成立", rel="阻断")]))
    assert any("条件成立" in v and "阻断" in v for v in r["violations"]), r["violations"]

@case("必需产物缺失必违规")
def t_missing_artifacts():
    vr = load()
    d = tempfile.mkdtemp(prefix="vr-test-")  # 手动建目录：只写 ledger，缺其余必需产物
    with open(os.path.join(d, "issues-ledger.md"), "w") as f:
        f.write(LEDGER_HEADER + "\n" + SEP + "\n" + row() + "\n")
    r = vr.validate(d)
    missing = " ".join(r["violations"])
    for need in ("req-items", "research-log", "报告"):
        assert need in missing, f"未提示缺失 {need}: {r['violations']}"

@case("固定表头缺列必违规")
def t_missing_column():
    vr = load()
    d = tempfile.mkdtemp(prefix="vr-test-")
    bad_header = LEDGER_HEADER.replace(" 关闭条件 |", " |")
    with open(os.path.join(d, "issues-ledger.md"), "w") as f:
        f.write(bad_header + "\n" + SEP.replace("|---|" * 0 + "|---|---|---|---|---|---|---|---|---|---|---|---|", "") + "\n")
    r = vr.validate(d)
    assert any("列" in v or "schema" in v or "表头" in v for v in r["violations"]), r["violations"]

@case("合法零Finding评审通过")
def t_zero_findings_ok():
    vr = load()
    d = tempfile.mkdtemp(prefix="vr-test-")
    with open(os.path.join(d, "issues-ledger.md"), "w") as f:
        f.write(LEDGER_HEADER + "\n" + SEP + "\n" + "| _无发现（正面确认）_ | — | — | — | — | — | — | — | — | — | — | — | — |\n")
    for aux, content in [("req-items.md", "REQ-001 示例\n"), ("research-log.md", "| 时间 | 层级 | 查询 | 脱敏检查 | 来源 | 结论 | 应用 |\n|---|---|---|---|---|---|---|\n"),
                         ("报告.md", "review_status: 已完成\n总体结论：通过（零发现）\n")]:
        with open(os.path.join(d, aux), "w") as f:
            f.write(content)
    r = vr.validate(d)
    assert not any("Finding" in v and "未解析" in v for v in r["violations"]), r["violations"]

@case("待补充时不得给三档结论")
def t_pending_with_verdict():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 待补充\n\n总体结论：不通过\n")
    r = vr.validate(d)
    assert any("待补充" in v and "三档" in v for v in r["violations"]), r["violations"]

@case("F-ID格式与连续性违规")
def t_fid_format():
    vr = load()
    r = vr.validate(make_dir([row(fid="F-1"), row(fid="F-003", imp="P2", rel="不影响放行")]))
    assert any("F-ID" in v and ("格式" in v or "连续" in v) for v in r["violations"]), r["violations"]

@case("release_effect枚举后附条件文本合法")
def t_rel_with_condition():
    vr = load()
    d = make_dir([row(imp="P1", rel="条件放行（条件：统一口径后复审）")])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("**review_status**: 已完成\n\n## 总体结论\n有条件通过\n")
    r = vr.validate(d)
    assert r["violations"] == [], r["violations"]

@case("粗体review_status可解析")
def t_bold_status():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("**review_status**: 已完成\n\n## 总体结论\n不通过\n")
    r = vr.validate(d)
    assert not any("review_status" in v for v in r["violations"]), r["violations"]

# ===== V1.4 fail-closed 反例（Codex 五轮实测，2026-08-29）=====

@case("畸形台账行列数不匹配必违规")
def t_malformed_row():
    vr = load()
    d = tempfile.mkdtemp(prefix="vr-test-")
    broken = row().rsplit("|", 3)[0] + "|"  # 少 2 列
    with open(os.path.join(d, "issues-ledger.md"), "w") as f:
        f.write(LEDGER_HEADER + "\n" + SEP + "\n" + broken + "\n")
    for aux, content in [("req-items.md", "REQ-001 x\n"), ("research-log.md", "| a |\n|---|\n| b |\n"),
                         ("报告.md", "review_status: 已完成\n")]:
        with open(os.path.join(d, aux), "w") as f:
            f.write(content)
    r = vr.validate(d)
    assert any("列数" in v for v in r["violations"]), r["violations"]

@case("报告结论与台账阻断矛盾必违规")
def t_verdict_ledger_conflict():
    vr = load()
    d = make_dir([row()])  # F-001 = P0 阻断
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n通过\n")
    r = vr.validate(d)
    assert any("结论" in v and ("阻断" in v or "通过" in v) for v in r["violations"]), r["violations"]

@case("较高可信不得定阻断")
def t_highconf_block():
    vr = load()
    r = vr.validate(make_dir([row(ev="较高可信", rel="阻断")]))
    assert any("较高可信" in v and "阻断" in v for v in r["violations"]), r["violations"]

@case("空research-log必违规")
def t_empty_log():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("\n")
    r = vr.validate(d)
    assert any("research-log" in v for v in r["violations"]), r["violations"]

@case("任何Finding缺原文摘录必违规")
def t_quote_all_levels():
    vr = load()
    r = vr.validate(make_dir([row(imp="P2", quote="")]))
    assert any("原文摘录" in v for v in r["violations"]), r["violations"]

@case("非法维度与非法状态必违规")
def t_bad_dim_status():
    vr = load()
    r = vr.validate(make_dir([row(dim="D9", st="玄学")]))
    assert any("维度" in v for v in r["violations"]) and any("状态" in v for v in r["violations"]), r["violations"]

@case("存在条件放行项时纯通过必违规")
def t_cond_pass_conflict():
    vr = load()
    d = make_dir([row(rel="条件放行（条件：补齐X）")])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n通过\n")
    r = vr.validate(d)
    assert any("条件放行" in v and "通过" in v for v in r["violations"]), r["violations"]

@case("已完成但报告无三档结论必违规")
def t_done_no_verdict():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 概述\n本文档整体质量尚可。\n")
    r = vr.validate(d)
    assert any("三档结论" in v or ("结论" in v and "已完成" in v) for v in r["violations"]), r["violations"]

@case("垃圾research-log（无固定表头）必违规")
def t_garbage_log():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("garbage | garbage\nxxx | yyy\n")
    r = vr.validate(d)
    assert any("research-log" in v and "表头" in v for v in r["violations"]), r["violations"]

@case("报告统计数与台账不符必违规")
def t_stats_mismatch():
    vr = load()
    d = make_dir([row()])  # 台账：P0×1 阻断×1
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n不通过\n\n统计：P0 99 / P1 0 / P2 0 / P3 0；阻断 99 / 条件放行 0 / 待澄清 0\n")
    r = vr.validate(d)
    assert any("统计" in v for v in r["violations"]), r["violations"]

@case("报告统计与台账一致时通过")
def t_stats_consistent_ok():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n不通过\n\n统计：P0 1 / P1 0 / P2 0 / P3 0；阻断 1 / 条件放行 0 / 待澄清 0\n")
    r = vr.validate(d)
    assert not any("统计" in v for v in r["violations"]), r["violations"]

@case("维度带子项标注合法（D3-11 / D3（说明））")
def t_dim_with_subtag():
    vr = load()
    d = make_dir([row(dim="D3-11"), row(fid="F-002", dim="D3（D3-4 术语漂移）", imp="P2", rel="不影响放行")])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n不通过\n")
    r = vr.validate(d)
    assert not any("维度非法" in v for v in r["violations"]), r["violations"]

@case("维度D9与D31仍非法")
def t_dim_still_strict():
    vr = load()
    r = vr.validate(make_dir([row(dim="D31")]))
    assert any("维度" in v for v in r["violations"]), r["violations"]

@case("列名散落文本的伪造research-log必违规")
def test_fake_log_scattered():
    vr = load()
    d = make_dir([row()])
    # 七个列名散落在普通文本里 + 一个竖线——文本共现但不构成合法表头
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("本次评审检索了时间和层级，去标识化查询与脱敏检查都做了，来源和结论摘要见上，应用到 Finding 无 | 完\n")
    r = vr.validate(d)
    assert any("research-log" in v for v in r["violations"]), r["violations"]

@case("表头列序错乱必违规")
def test_log_wrong_order():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("| 时间 | 脱敏检查 | 层级 | 去标识化查询 | 来源 | 结论摘要 | 应用到 Finding |\n|---|---|---|---|---|---|---|\n")
    r = vr.validate(d)
    assert any("research-log" in v and ("表头" in v or "列序" in v) for v in r["violations"]), r["violations"]

@case("数据行列数不等于七必违规")
def test_log_bad_row_cols():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("| 时间 | 层级 | 去标识化查询 | 脱敏检查 | 来源 | 结论摘要 | 应用到 Finding |\n|---|---|---|---|---|---|---|\n| 10:00 | L1 | 查术语 | ok | 文档 | 无 | F-001 | 多余列 |\n")
    r = vr.validate(d)
    assert any("research-log" in v and "列数" in v for v in r["violations"]), r["violations"]

@case("哨兵词嵌在长句中不豁免表头")
def test_log_sentinel_in_sentence():
    vr = load()
    d = make_dir([row()])
    # "未调研"出现在长句里而非规定的完整哨兵格式
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("本次评审过程中部分内容未调研，其余按计划执行，详见其他材料。\n")
    r = vr.validate(d)
    assert any("research-log" in v for v in r["violations"]), r["violations"]

@case("规范哨兵行合法")
def test_log_sentinel_ok():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("> 未调研：本次评审未触发任何调研（文档内证据充分）\n")
    r = vr.validate(d)
    assert not any("research-log" in v for v in r["violations"]), r["violations"]

@case("L3行缺来源字段必违规")
def test_log_l3_no_source():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("| 时间 | 层级 | 去标识化查询 | 脱敏检查 | 来源 | 结论摘要 | 应用到 Finding |\n|---|---|---|---|---|---|---|\n| 10:00 | L3 | 抽象问题A | 已确认无敏感内容 |  | 有结论 | F-001 |\n")
    r = vr.validate(d)
    assert any("research-log" in v and ("L3" in v or "来源" in v) for v in r["violations"]), r["violations"]

@case("哨兵行与非法表格并存不得绕过")
def test_log_sentinel_with_table_bypass():
    vr = load()
    d = make_dir([row()])
    # 哨兵行 + 一个缺来源的 L3 表格行——哨兵不得使整个文件免检
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("> 未调研：本次未触发调研\n\n| 时间 | 层级 | 去标识化查询 | 脱敏检查 | 来源 | 结论摘要 | 应用到 Finding |\n|---|---|---|---|---|---|---|\n| 10:00 | L3 | q | ok |  | 有 | F-001 |\n")
    r = vr.validate(d)
    assert any("research-log" in v and ("并存" in v or "L3" in v or "表" in v) for v in r["violations"]), r["violations"]

@case("空说明哨兵必违规")
def test_log_sentinel_empty_reason():
    vr = load()
    d = make_dir([row()])
    with open(os.path.join(d, "research-log.md"), "w") as f:
        f.write("> 未调研：\n")
    r = vr.validate(d)
    assert any("research-log" in v and "说明" in v for v in r["violations"]), r["violations"]

@case("存在阻断项时有条件通过必违规")
def t_block_with_conditional_pass():
    vr = load()
    d = make_dir([row()])  # F-001 = P1 已确认 阻断
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n有条件通过\n")
    r = vr.validate(d)
    assert any("阻断" in v and "不通过" in v for v in r["violations"]), r["violations"]

SUG_HEAD = "## 8. 同业实践与优化建议\n"

def make_sug_report(sug_lines):
    d = make_dir([row()])
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("review_status: 已完成\n\n## 总体结论\n不通过\n\n" + SUG_HEAD + "\n" + "\n".join(sug_lines) + "\n")
    return d

@case("建议行缺三类标签必违规")
def t_sug_no_tag():
    vr = load()
    d = make_sug_report(["- **SUG-01｜年审机制**：同业普遍实行年审，建议补充年度复审。"])
    r = vr.validate(d)
    assert any("建议" in v and ("标签" in v or "三类" in v) for v in r["violations"]), r["violations"]

@case("建议行使用非法标签必违规")
def t_sug_bad_tag():
    vr = load()
    d = make_sug_report(["- **SUG-01｜年审机制**：[待核验记载] 知识库记载办法要求年审，建议补充。"])
    r = vr.validate(d)
    assert any("非法" in v or ("标签" in v and "待核验" in v) for v in r["violations"]), r["violations"]

@case("待核验内容进入正式建议必违规")
def t_sug_pending_in_formal():
    vr = load()
    d = make_sug_report(["- **SUG-01｜监测机制**：[法规事实] 办法第 25 条要求季度报告（待核验），建议增加标识列。"])
    r = vr.validate(d)
    assert any("待核验" in v and "建议" in v for v in r["violations"]), r["violations"]

@case("具名同业事实无一手锚点必违规")
def t_sug_named_no_source():
    vr = load()
    d = make_sug_report(["- **SUG-01｜年审机制**：[具名同业事实] 工商银行实行评级限额年审，建议补充。"])
    r = vr.validate(d)
    assert any("具名同业" in v and ("来源" in v or "锚点" in v) for v in r["violations"]), r["violations"]

@case("三类合法标签建议通过")
def t_sug_valid_ok():
    vr = load()
    d = make_sug_report([
        "- **SUG-01｜年审机制**：[设计推断] 基于工程原则，建议补充年度复审。",
        "- **SUG-02｜监测联动**：[法规事实] 办法第 21 条（已核验）要求月度监测，建议增加预警。",
    ])
    r = vr.validate(d)
    assert not any("建议" in v and "标签" in v for v in r["violations"]), r["violations"]

# ---------------- section 11: docx 回写三件套（V1.7.0，TDD 先于实现） ----------------
import zipfile as _zip

WB_HEADER = "| F-ID | 片段数 | 已标注处数 | 状态 | 备注 |"
WB_SEP = "|---|---|---|---|---|"

def make_min_docx(path, rr=0, others=0):
    """手写最小 docx zip（纯 stdlib）：word/comments.xml 含 rr 条 requirement-review
    批注 + others 条他人批注。validator 只 zipfile 读 XML 计数，无需 python-docx。"""
    comments = "".join(
        f'<w:comment w:id="{i}" w:author="requirement-review"><w:p/></w:comment>'
        for i in range(rr)) + "".join(
        f'<w:comment w:id="{100 + i}" w:author="mayinyin"><w:p/></w:comment>'
        for i in range(others))
    with _zip.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        z.writestr("word/document.xml", '<?xml version="1.0"?><w:document/>')
        z.writestr("word/comments.xml",
                   '<?xml version="1.0"?><w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                   + comments + "</w:comments>")

def make_writeback(d, rows):
    """rows: [(fid, placed, status, note)]；未匹配行自动补未匹配明细。"""
    lines = ["# docx 回写状态", "", "- 原件: source.docx", "- 副本: source-评审批注-20260831.docx",
             "- 覆盖率: x/y", "", WB_HEADER, WB_SEP]
    lines += [f"| {fid} | 1 | {placed} | {st} | {note} |" for fid, placed, st, note in rows]
    un = [fid for fid, _p, st, _n in rows if st == "未匹配"]
    if un:
        lines += ["", "## 未匹配明细", ""]
        lines += [f"- {fid} 第1处摘录「xxx」：L1/L1.5/L2/L2.5/L3 均未命中（摘录非原文或属转换噪声）" for fid in un]
    with open(os.path.join(d, "docx-writeback.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

def add_docx_env(d, wb_rows, copy_rr):
    make_min_docx(os.path.join(d, "source.docx"))
    make_min_docx(os.path.join(d, "source-评审批注-20260831.docx"), rr=copy_rr, others=1)
    make_writeback(d, wb_rows)

@case("回写节不触发（无docx输入零违规）")
def t_wb_off():
    vr = load()
    r = vr.validate(make_dir([row()]))
    assert r["violations"] == [], r["violations"]

@case("有source无状态文件违规")
def t_wb_missing_status():
    vr = load()
    d = make_dir([row()])
    make_min_docx(os.path.join(d, "source.docx"))
    make_min_docx(os.path.join(d, "source-评审批注-20260831.docx"), rr=1)
    r = vr.validate(d)
    assert any("回写" in v and "docx-writeback" in v for v in r["violations"]), r["violations"]

@case("有状态文件无副本违规")
def t_wb_missing_copy():
    vr = load()
    d = make_dir([row()])
    make_min_docx(os.path.join(d, "source.docx"))
    make_writeback(d, [("F-001", 1, "已批注", "")])
    r = vr.validate(d)
    assert any("评审批注" in v and "副本" in v for v in r["violations"]), r["violations"]

@case("状态表缺打开态F-ID违规")
def t_wb_missing_fid():
    vr = load()
    d = make_dir([row(fid="F-001"), row(fid="F-002", imp="P2", rel="不影响放行")])
    add_docx_env(d, [("F-001", 1, "已批注", "")], copy_rr=1)
    r = vr.validate(d)
    assert any("F-002" in v and "缺" in v for v in r["violations"]), r["violations"]

@case("状态表多出台账外F-ID违规")
def t_wb_extra_fid():
    vr = load()
    d = make_dir([row()])
    add_docx_env(d, [("F-001", 1, "已批注", ""), ("F-999", 1, "已批注", "")], copy_rr=2)
    r = vr.validate(d)
    assert any("F-999" in v and "多出" in v for v in r["violations"]), r["violations"]

@case("已批注状态处数为0违规")
def t_wb_zero_placed():
    vr = load()
    d = make_dir([row()])
    add_docx_env(d, [("F-001", 0, "已批注", "")], copy_rr=0)
    r = vr.validate(d)
    assert any("已标注处数" in v for v in r["violations"]), r["violations"]

@case("副本批注数与状态不符违规")
def t_wb_count_mismatch():
    vr = load()
    d = make_dir([row()])
    add_docx_env(d, [("F-001", 1, "已批注", "")], copy_rr=2)
    r = vr.validate(d)
    assert any("批注数" in v and "≠" in v for v in r["violations"]), r["violations"]

@case("未匹配但报告无批注副本节违规")
def t_wb_unmatched_no_section():
    vr = load()
    d = make_dir([row()])
    add_docx_env(d, [("F-001", 0, "未匹配", "")], copy_rr=0)
    r = vr.validate(d)
    assert any("批注副本" in v for v in r["violations"]), r["violations"]

@case("三件套自洽零违规")
def t_wb_consistent():
    vr = load()
    d = make_dir([row()])
    add_docx_env(d, [("F-001", 1, "已批注", "")], copy_rr=1)
    r = vr.validate(d)
    assert r["violations"] == [], r["violations"]

if __name__ == "__main__":
    failed = 0
    for name, fn in CASES:
        try:
            fn(); print(f"  PASS  {name}")
        except AssertionError as e:
            failed += 1; print(f"  FAIL  {name}: {e}")
        except FileNotFoundError as e:
            failed += 1; print(f"  FAIL  {name}: 实现不存在 ({e})")
        except Exception as e:
            failed += 1; print(f"  ERROR {name}: {type(e).__name__} {e}")
    print(f"\n{len(CASES)-failed}/{len(CASES)} 通过")
    sys.exit(1 if failed else 0)
