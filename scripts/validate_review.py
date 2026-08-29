#!/usr/bin/env python3
"""validate_review.py — 需求评审产物的确定性校验器（v2 加固版）。

只检查格式与硬约束（证据结构存在性），不判断证据真实性/相关性/充分性（语义评审与人工抽检职责）。
用法: python3 validate_review.py <评审工作目录>
退出码: 0=零违规, 1=存在违规。输出 JSON: {"violations": [...], "findings": [...], "stats": {...}}
"""
import json, os, re, sys

VALID_IMPACT = {"P0", "P1", "P2", "P3"}
VALID_EVIDENCE = {"已确认", "较高可信", "条件成立", "待核验"}
VALID_RELEASE = {"阻断", "条件放行", "待澄清", "不影响放行"}
NON_BLOCKING_EVIDENCE = {"待核验", "条件成立", "较高可信"}  # 阻断必须已确认（fail-closed）
VALID_DIMENSIONS = {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "G"}
VALID_STATUS = {"打开", "已销号", "不适用"}
REQUIRED_COLUMNS = ["F-ID", "维度", "impact_level", "evidence_status", "release_effect",
                    "定位", "原文摘录", "问题描述与后果", "证据来源", "修改建议",
                    "关闭条件", "澄清问题", "状态"]
REQUIRED_ARTIFACTS = ["issues-ledger.md", "req-items.md", "research-log.md", "报告.md"]
VERDICT_WORDS = ("通过", "不通过")
URL_PAT = re.compile(r"https?://")
ID_REF_PAT = re.compile(r"\b(REQ|BIZ|F)-(\d{3,})\b")
FID_PAT = re.compile(r"^F-(\d{3,})$")

def split_row(line):
    protected = line.replace("\\|", "\x00")
    return [p.strip().replace("\x00", "\\|") for p in protected.strip().strip("|").split("|")]

def parse_ledger(path):
    cols, rows, malformed = [], [], []
    lines = open(path, encoding="utf-8").read().split("\n")
    header_idx = None
    for i, ln in enumerate(lines):
        if "F-ID" in ln and ln.strip().startswith("|"):
            cols = split_row(ln)
            if i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
                header_idx = i
                break
    if header_idx is None:
        return None, rows, malformed  # 表头缺失
    for ln in lines[header_idx + 2:]:
        s = ln.strip()
        if not s.startswith("|"):
            if rows:
                break
            continue
        if re.match(r"^\|[\s:|-]+\|$", s):
            continue
        parts = split_row(ln)
        if len(parts) == len(cols):
            rows.append(dict(zip(cols, parts)))
        else:
            malformed.append(f"台账第 {lines.index(ln)+1} 行列数 {len(parts)}≠{len(cols)}（fail-closed：不得静默跳过）")
    return cols, rows, malformed

def load_ids(path, id_prefix):
    if not os.path.exists(path):
        return None
    text = open(path, encoding="utf-8").read()
    return set(f"{id_prefix}-{m}" for m in re.findall(rf"\b{id_prefix}-(\d{{3,}})\b", text))

def validate(workdir):
    v = []
    # 0. 必需产物存在性 + 非空合法性（fail-closed）
    for art in REQUIRED_ARTIFACTS:
        p = os.path.join(workdir, art)
        if not os.path.exists(p):
            v.append(f"必需产物缺失：{art}")
        elif art == "research-log.md":
            txt = open(p, encoding="utf-8").read()
            raw = [l.rstrip() for l in txt.split("\n")]
            nonempty = [i for i, l in enumerate(raw) if l.strip()]
            LOG_COLS = ["时间", "层级", "去标识化查询", "脱敏检查", "来源", "结论摘要", "应用到 Finding"]
            # 哨兵：整行以"未调研：/不适用："开头（blockquote 前缀可选）——嵌在长句中不算
            # 哨兵：整行以"未调研：/不适用："开头且说明非空；哨兵模式下文件不得再含任何表格行
            sentinel_lines = [i for i in nonempty
                              if re.match(r"^>?\s*(未调研|不适用)[：:]", raw[i].strip())]
            has_table = any(raw[i].strip().startswith("|") for i in nonempty)
            valid_sentinel = any(re.match(r"^>?\s*(未调研|不适用)[：:]\s*\S", raw[i].strip()) for i in sentinel_lines)
            if not nonempty:
                v.append("research-log.md 为空（须有合法表头记录或整行哨兵'未调研：<非空说明>'）")
            elif sentinel_lines and not valid_sentinel:
                v.append("research-log.md 哨兵行说明为空（'未调研/不适用：'后必须有非空说明）")
            elif valid_sentinel and has_table:
                v.append("research-log.md 哨兵与调研表格并存（有调研表格时走表头解析，不得用哨兵跳过检查）")
            elif valid_sentinel:
                pass  # 纯哨兵模式（无任何表格行）：规范豁免
            else:
                # 严格表头解析：存在某行精确等于七列；表头下一行须为分隔行；数据行严格七列
                hidx = next((i for i in nonempty if raw[i].strip().startswith("|")
                             and split_row(raw[i]) == LOG_COLS), None)
                if hidx is None:
                    v.append("research-log.md 表头非法（须存在精确七列表头行 | 时间 | 层级 | 去标识化查询 | 脱敏检查 | 来源 | 结论摘要 | 应用到 Finding |，或整行哨兵'未调研：<说明>'；字段名散落文本不构成表头）")
                else:
                    after = [i for i in nonempty if i > hidx]
                    if not after or not re.match(r"^\|[\s:|-]+\|$", raw[after[0]].strip()):
                        v.append("research-log.md 表头后缺少分隔行（|---|…|）")
                    for i in after[1:]:
                        s = raw[i].strip()
                        if not s.startswith("|"):
                            break  # 表格结束，其后为普通文本
                        if re.match(r"^\|[\s:|-]+\|$", s):
                            continue
                        cells = split_row(s)
                        if len(cells) != len(LOG_COLS):
                            v.append(f"research-log.md 数据行列数 {len(cells)}≠{len(LOG_COLS)}（第 {i+1} 行，fail-closed）")
                            continue
                        if "L3" in cells[1]:
                            if not cells[3].strip():
                                v.append(f"research-log.md L3 行（第 {i+1} 行）'脱敏检查'列为空（L3 外发必须留痕脱敏确认）")
                            if not cells[4].strip():
                                v.append(f"research-log.md L3 行（第 {i+1} 行）'来源'列为空（外部结论必须可溯源）")
        elif os.path.getsize(p) < 10:
            v.append(f"必需产物疑似为空：{art}")

    ledger = os.path.join(workdir, "issues-ledger.md")
    if not os.path.exists(ledger):
        return {"violations": v + ["issues-ledger.md 不存在"], "findings": [], "stats": {}}

    cols, rows, malformed = parse_ledger(ledger)
    v.extend(malformed)
    # 1. 固定 schema 列完整性
    if cols is None:
        v.append("issues-ledger.md 表头缺失（需含 F-ID 的 13 列固定表头）")
        rows = []
    elif cols != REQUIRED_COLUMNS:
        missing = [c for c in REQUIRED_COLUMNS if c not in cols]
        extra = [c for c in cols if c not in REQUIRED_COLUMNS]
        if missing:
            v.append(f"表头缺列：{missing}（固定 schema 见 report-template.md）")
        if extra:
            v.append(f"表头多列：{extra}（列名/顺序须与固定 schema 一致）")
    # 零数据行是合法结果（零发现=正面确认），不作为违规

    findings = [r for r in rows if r.get("F-ID", "") and not r.get("F-ID", "").startswith("_")]

    def rel_of(r):
        m = re.match(r"^(阻断|条件放行|待澄清|不影响放行)", r.get("release_effect", ""))
        return m.group(1) if m else r.get("release_effect", "")

    # 2. F-ID 格式与连续性
    nums = []
    for r in findings:
        fid = r.get("F-ID", "")
        m = FID_PAT.match(fid)
        if not m:
            v.append(f"F-ID 格式非法：'{fid}'（须为 F-NNN 三位起编号）")
        else:
            nums.append(int(m.group(1)))
    if nums and sorted(nums) != list(range(1, len(nums) + 1)):
        v.append(f"F-ID 连续性违规：应为 F-001 起连续编号，实际 {sorted(nums)}")

    # 3. F-ID 唯一
    seen = set()
    for r in findings:
        fid = r.get("F-ID", "")
        if fid in seen:
            v.append(f"F-ID 重复：{fid}（F-ID 必须唯一）")
        seen.add(fid)

    req_ids = load_ids(os.path.join(workdir, "req-items.md"), "REQ")
    biz_ids = load_ids(os.path.join(workdir, "biz-items.md"), "BIZ")

    for r in findings:
        fid = r.get("F-ID", "?")
        imp = r.get("impact_level", "")
        ev = r.get("evidence_status", "")
        rel = r.get("release_effect", "")
        src = r.get("证据来源", "")

        # 4. 枚举合法性（空值即非法；release_effect 允许枚举值后附条件文本如"条件放行（条件：…）"）
        def enum_base(val):
            m = re.match(r"^(阻断|条件放行|待澄清|不影响放行)", val)
            return m.group(1) if m else val
        if imp not in VALID_IMPACT:
            v.append(f"{fid}: impact_level 非法值 '{imp or '(空)'}'（允许 {sorted(VALID_IMPACT)}）")
        if ev not in VALID_EVIDENCE:
            v.append(f"{fid}: evidence_status 非法值 '{ev or '(空)'}'（允许 {sorted(VALID_EVIDENCE)}）")
        if enum_base(rel) not in VALID_RELEASE:
            v.append(f"{fid}: release_effect 非法值 '{rel or '(空)'}'（允许 {sorted(VALID_RELEASE)}）")

        # 5b. 维度与状态枚举 + 所有级 Finding 必有原文摘录（fail-closed）
        # 维度允许基值后附子项标注（D3-11 / D3（D3-4 术语漂移）），基值必须是 D1-D8/G
        dim_val = r.get("维度", "")
        if not re.match(r"^(D[1-8]|G)(?!\d)", dim_val):
            v.append(f"{fid}: 维度非法值 '{dim_val}'（基值允许 D1-D8/G，可附子项标注）")
        if r.get("状态", "") not in VALID_STATUS:
            v.append(f"{fid}: 状态非法值 '{r.get('状态','')}'（允许 打开/已销号/不适用）")
        if not r.get("原文摘录", "").strip():
            v.append(f"{fid}: 缺少 '原文摘录'（任何级别 Finding 都必须有防幻觉锚点）")

        # 5. P0/P1 证据结构五要素
        if imp in ("P0", "P1"):
            for field, val in (("原文摘录", r.get("原文摘录", "")), ("证据来源", src),
                               ("证据状态", ev), ("修改建议", r.get("修改建议", "")),
                               ("关闭条件", r.get("关闭条件", ""))):
                if not str(val).strip():
                    v.append(f"{fid}: P0/P1 Finding 缺少 '{field}'（五要素必须齐备）")

        # 6. 证据不足不得阻断（待核验/条件成立）
        if ev in NON_BLOCKING_EVIDENCE and rel_of(r) == "阻断":
            v.append(f"{fid}: evidence_status={ev} 不得 release_effect=阻断（证据不足只能进待澄清/条件放行）")

        # 7. 外部事实三字段
        if URL_PAT.search(src):
            if "来源类型" not in src:
                v.append(f"{fid}: 外部证据来源含 URL 但缺少 '来源类型'")
            if "核验日期" not in src:
                v.append(f"{fid}: 外部证据来源含 URL 但缺少 '核验日期'")

        # 8. 跨产物 ID 引用（引用必须可核对）
        for field in ("问题描述与后果", "修改建议", "定位"):
            for m in ID_REF_PAT.finditer(r.get(field, "")):
                ref, pfx = m.group(0), m.group(1)
                if pfx == "REQ":
                    if req_ids is None:
                        v.append(f"{fid}: 引用 {ref} 但 req-items.md 缺失，引用无法核对")
                    elif ref not in req_ids:
                        v.append(f"{fid}: 引用了未定义的 {ref}（req-items.md 中不存在）")
                if pfx == "BIZ":
                    if biz_ids is None:
                        v.append(f"{fid}: 引用 {ref} 但 biz-items.md 缺失（无业务方案时不应出现 BIZ 引用）")
                    elif ref not in biz_ids:
                        v.append(f"{fid}: 引用了未定义的 {ref}（biz-items.md 中不存在）")

    # 9. coverage-matrix 双向指向
    matrix = os.path.join(workdir, "coverage-matrix.md")
    if os.path.exists(matrix):
        mtext = open(matrix, encoding="utf-8").read()
        for m in re.finditer(r"\bREQ-(\d{3,})\b", mtext):
            ref = m.group(0)
            if req_ids is None:
                v.append(f"coverage-matrix 引用 {ref} 但 req-items.md 缺失，引用无法核对")
            elif ref not in req_ids:
                v.append(f"coverage-matrix 引用未定义的 {ref}")
        for m in re.finditer(r"\bBIZ-(\d{3,})\b", mtext):
            ref = m.group(0)
            if biz_ids is None:
                v.append(f"coverage-matrix 引用 {ref} 但 biz-items.md 缺失，引用无法核对")
            elif ref not in biz_ids:
                v.append(f"coverage-matrix 引用未定义的 {ref}")

    # 10. 报告 review_status 取值与三档结论约束
    report = os.path.join(workdir, "报告.md")
    if os.path.exists(report):
        rtext = open(report, encoding="utf-8").read()
        # 容忍 markdown 粗体等包裹（**review_status**:）
        m = re.search(r"\**review_status\**\s*[：:]\s*(已完成|待补充)", rtext)
        if not m:
            v.append("报告.md 缺少合法的 review_status 字段（已完成｜待补充 必须显式声明）")
        elif m.group(1) == "待补充":
            for w in VERDICT_WORDS:
                if re.search(r"(总体)?结论[：:]?\s*.{0,6}" + w, rtext):
                    v.append(f"review_status=待补充 时不得给出三档结论（发现 '{w}'——应输出'待补充后重评'）")
                    break
        else:
            # 已完成：三档结论必须存在且与台账阻断/条件项一致（fail-closed）
            blk = sum(1 for r in findings if rel_of(r) == "阻断")
            cond = sum(1 for r in findings if rel_of(r) == "条件放行")
            mv = re.search(r"(总体)?结论[：:]?\s*.{0,6}(通过|不通过)", rtext)
            if not mv:
                v.append("review_status=已完成 但报告缺少三档结论（通过｜有条件通过｜不通过 必须显式给出）")
            else:
                verdict = "不通过" if "不通过" in mv.group(0) else ("通过" if "有条件通过" not in mv.group(0) else "有条件通过")
                if verdict in ("通过", "有条件通过") and blk > 0:
                    v.append(f"报告结论'{verdict}'与台账矛盾：台账存在 {blk} 项已确认阻断（阻断语义绝对化——存在阻断必须'不通过'；可带条件关闭的应标'条件放行'而非'阻断'）")
                elif verdict == "通过" and cond > 0:
                    v.append(f"报告结论'通过'与台账矛盾：台账存在 {cond} 项条件放行（至少'有条件通过'）")
                elif verdict == "有条件通过" and blk == 0 and cond == 0:
                    v.append("报告'有条件通过'但台账无条件放行项（结论无依据）")
                elif verdict == "不通过" and blk == 0:
                    v.append("报告'不通过'但台账零阻断项（须说明非阻断性不通过理由）")

        # 建议节三分类校验（fail-closed：存在"同业实践与优化建议"节时每条 SUG 行必须带合法三类标签）
        msug = re.search(r"同业实践与优化建议", rtext)
        if msug:
            # 截取建议节到下一个 ###/## 标题（待核验线索节之后的内容不再按正式建议约束）
            seg = rtext[msug.start():]
            m_end = re.search(r"\n##+\s*(?!#).*?(待核验线索|亮点|风险与影响)", seg)
            sug_zone = seg[:m_end.start()] if m_end else seg
            formal_zone = sug_zone.split("待核验线索")[0]  # 正式建议区
            VALID_SUG_TAGS = ("法规事实", "具名同业事实", "设计推断")
            for ln in formal_zone.split("\n"):
                s = ln.strip()
                if not (s.startswith(("- **SUG", "* **SUG")) or re.match(r"^\d+\.\s*\*\*SUG", s)):
                    continue
                mtag = re.search(r"\[(法规事实|具名同业事实|设计推断|[^\]]+)\]", s)
                if not mtag:
                    v.append(f"建议行缺三类标签（[法规事实]/[具名同业事实]/[设计推断] 之一）：{s[:50]}…")
                elif mtag.group(1) not in VALID_SUG_TAGS:
                    v.append(f"建议行使用非法标签 '[{mtag.group(1)}]'（待核验内容应移入'待核验线索'小节，不作为正式建议）：{s[:50]}…")
                else:
                    if "待核验" in s:
                        v.append(f"正式建议含'待核验'内容（应移入待核验线索节）：{s[:50]}…")
                    if mtag.group(1) == "具名同业事实" and not re.search(r"(https?://|第\S+页|§|章节|〔\d{4}〕)", s):
                        v.append(f"[具名同业事实] 缺一手来源锚点（URL/页码/章节）：{s[:50]}…")

        # 报告统计与台账核对（fail-closed：写了统计就必须与台账一致；未写的项不核对）
        ms = re.search(r"统计[：:]", rtext)
        if ms:
            seg = rtext[ms.start():ms.start() + 300]
            ledger_counts = {k: sum(1 for r in findings if r.get("impact_level") == k)
                             for k in ("P0", "P1", "P2", "P3")}
            ledger_counts.update({
                "阻断": sum(1 for r in findings if rel_of(r) == "阻断"),
                "条件放行": sum(1 for r in findings if rel_of(r) == "条件放行"),
                "待澄清": sum(1 for r in findings if rel_of(r) == "待澄清"),
            })
            for key, actual in ledger_counts.items():
                pat = re.compile(key + r"(?![\d/P])\s*[x×:：]?\s*(\d+)")
                mc = pat.search(seg)
                if mc and int(mc.group(1)) != actual:
                    v.append(f"报告统计与台账不符：{key} 报告={mc.group(1)} 台账={actual}")

    stats = {
        "findings": len(findings),
        "by_impact": {k: sum(1 for r in findings if r.get("impact_level") == k) for k in VALID_IMPACT},
        "blocking": sum(1 for r in findings if rel_of(r) == "阻断"),
    }
    return {"violations": v, "findings": findings, "stats": stats}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python3 validate_review.py <评审工作目录>", file=sys.stderr); sys.exit(2)
    result = validate(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result["violations"] else 0)
