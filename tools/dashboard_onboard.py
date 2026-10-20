#!/usr/bin/env python3
"""Interactive dashboard project intake and GitHub spec publisher. Python stdlib only."""
import argparse, base64, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
REF_DEFAULT = "mtaghipourpars-dotcom/MDASHBOARD"

def api(method, url, token=None, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Accept":"application/vnd.github+json", "X-GitHub-Api-Version":"2022-11-28", "User-Agent":"MDASHBOARD-onboarding-tool"}
    if token: headers["Authorization"] = "Bearer " + token
    if data is not None: headers["Content-Type"]="application/json"
    req=urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw=res.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail=e.read().decode("utf-8","replace")
        raise RuntimeError(f"GitHub API {e.code} for {url}: {detail[:500]}") from e

def parse_repo(value):
    value=value.strip().rstrip("/")
    m=re.search(r"github\.com/([^/]+/[^/]+)", value)
    if m: value=m.group(1)
    value=value.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("REPO must be OWNER/REPO or a GitHub URL")
    return value

def repo_info(repo, token):
    return api("GET", f"{API}/repos/{repo}", token)

def tree(repo, branch, token):
    try:
        data=api("GET", f"{API}/repos/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1", token)
        return {x["path"]:x for x in data.get("tree",[])}, data.get("truncated",False)
    except RuntimeError as e:
        # A newly created repository can have no initial commit yet.
        if "Git Repository is empty" in str(e) or "API 409" in str(e):
            return {}, False
        raise

def read_file(repo, path, branch, token):
    u=f"{API}/repos/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(branch)}"
    obj=api("GET",u,token)
    if obj.get("encoding")=="base64":
        return base64.b64decode(obj["content"]).decode("utf-8","replace")
    return ""

def prompt(label, default=None):
    suffix=f" [{default}]" if default else ""
    answer=input(f"{label}{suffix}: ").strip()
    return answer or (default or "")

def ask_yes_no(label, default=False):
    answer=input(f"{label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not answer else answer in ("y","yes","بله","آره")

def json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"

def make_specs(repo, answers, target_paths):
    stamp=datetime.now(timezone.utc).isoformat()
    application={"schema_version":"1.0","project_id":repo.lower().replace("/","-"),"name":{"fa":answers["نام محصول"],"en":answers["Product name"]},"purpose":answers["هدف محصول"],"target_repository":repo,"status":"DRAFT","deployment":{"mode":answers["محیط استقرار"] or "UNKNOWN"},"languages": [x.strip() for x in answers["زبان‌ها"].split(",") if x.strip()] or ["UNKNOWN"],"constraints":[answers["محدودیت‌ها"]],"non_goals":[],"created_at":stamp,"evidence_refs":["OWNER_PROVIDED"],"open_questions":["تکمیل پوسته، صفحات، ویجت‌ها و قراردادهای داده در دورهای بعدی"]}
    shell={"schema_version":"1.0","status":"PROPOSED","header":{"title":answers["عنوان هدر"],"logo_asset_ref":answers["مسیر لوگو"] or None,"items":[]},"footer":{"description":answers["فوتر"]},"sidebar":{"fixed":answers["منوها و چیدمان ثابت هستند؟"].lower() not in ("خیر","no","n")},"languages":application["languages"],"direction_by_locale":{},"responsive_rules":[],"open_questions":["زبان و جهت نوشتار هر locale باید تأیید شود"]}
    pages={"schema_version":"1.0","pages":[]}
    widgets={"schema_version":"1.0","widgets":[]}
    data={"schema_version":"1.0","contracts":[]}
    metrics={"schema_version":"1.0","metrics":[]}
    interactions={"schema_version":"1.0","default_mode":"READ_ONLY","widgets":[],"alerting":{"rules":[]},"execution":{"enabled":False,"authorization":"UNKNOWN","audit":"UNKNOWN","rollback":"UNKNOWN"}}
    localization={"schema_version":"1.0","locales":application["languages"],"default_locale":application["languages"][0],"direction_by_locale":{},"required_localized_surfaces":["titles","labels","legends","tooltips","empty/loading/error states"]}
    assets={"schema_version":"1.0","assets":[]}
    assessment=f"""# ارزیابی REPO مقصد\n\n- REPO: {repo}\n- تاریخ بررسی: {stamp}\n- وضعیت: بررسی اولیه انجام شد؛ جزئیات در خروجی ابزار/گزارش این اجرا ثبت می‌شود.\n- ساختار موجود پیش از نوشتن: {len(target_paths)} مسیر\n- نام محصول: {answers['نام محصول']}\n- هدف: {answers['هدف محصول']}\n- نکته: محتوای فایل‌های موجود بدون تأیید بازنویسی نمی‌شود.\n"""
    questions=f"""# پرسش‌های باز\n\nاطلاعات زیر فقط شروع مصاحبه است؛ جزئیات صفحات و ویجت‌ها باید در گام‌های بعدی پرسیده و تأیید شوند.\n\n- [ ] عنوان/مسیر لوگو و دارایی‌های نهایی\n- [ ] فهرست دقیق صفحات و ترتیب سایدبار\n- [ ] ردیف/ستون و چیدمان هر صفحه\n- [ ] تعریف هر ویجت و جایگاه آن\n- [ ] منبع و قرارداد داده هر ویجت\n- [ ] تعریف و آستانه KPIها\n- [ ] زبان‌ها، RTL/LTR و معیارهای پذیرش\n"""
    work=f"""# دستور کار ماشین برای پروژه {repo}\n\nوضعیت: DRAFT؛ مجوز پیاده‌سازی رفتار تأییدنشده نیست.\n\n1. ابتدا این مشخصات و فایل‌های موجود REPO را بخوان.\n2. هیچ تصمیمی را از روی حدس قطعی نکن.\n3. پرسش‌های باز را مرحله‌ای از مالک بپرس.\n4. پیش از تغییر فایل موجود، تفاوت را نشان بده و اجازه بگیر.\n5. برای هر ویجت شناسه، صفحه، نوع، جایگاه، منبع، فیلدها، حالت‌ها و معیار پذیرش تعریف کن.\n6. حالت پیش‌فرض READ_ONLY است؛ اجرای عملیات فقط با تأیید صریح مجاز است.\n7. تست اجرا‌نشده را PASSED اعلام نکن.\n"""
    cross_page_validation = """# Cross-Page Data Integrity & Consistency Validation
وضعیت: REQUIRED GATE — معیار الزامی پیش از تأیید مشخصات و انتشار

## هدف
تضمین قابل‌ممیزی سازگاری ویجت‌های خلاصه/هشدار با صفحات جزئیات. برابر بودن عدد به‌تنهایی کافی نیست؛ تعریف KPI، مجموعه رکوردها، فیلترها، زمان/نسخه داده، واحد و دسترسی نیز بررسی می‌شود.

## اصول
1. هر KPI دارای ID پایدار، فرمول و نسخه مرجع در KPI Registry باشد.
2. هر ویجت به Data Contract نسخه‌دار ارجاع دهد؛ مورد ناشناخته UNKNOWN/BLOCKED می‌ماند.
3. هر drill-down مقصد، نگاشت فیلتر، محدوده زمانی و رفتار دسترسی مشخص داشته باشد.
4. null، empty، stale، partial، unavailable و error بی‌صدا به صفر یا وضعیت سالم تبدیل نشوند.
5. رابطه خلاصه و جزئیات فقط با محدوده، تعریف، واحد، زمان/نسخه و دامنه دسترسی سازگار مقایسه شود.
6. ابهام در فرمول KPI، شرط واجد شرایط بودن، آستانه هشدار یا رفتار کاربری نیازمند تأیید مالک است.

## ردیابی اجباری
برای هر رابطه یک شناسه مانند LINK-001 ثبت شود: source_widget_id، target_page_id، kpi_id/version، data_contract_id/version، filter_mapping، time_scope، identity_key، SNAPSHOT/LIVE policy، acceptance_test_ids، status و evidence_refs.

## کنترل‌های اجباری
- ارجاع تمام page/widget/KPI/data-contractها معتبر و یکتا باشد.
- فرمول، دامنه، شروط ورود/خروج، بازه، تجمیع و distinct-count یکسان باشد.
- فیلترهای مؤثر و پارامترهای drill-down به مقصد منتقل شوند.
- شمارش و مجموعه کلیدهای یکتا با داده مرجع تطبیق داشته باشد؛ pagination و duplicate handling آزموده شوند.
- واحد، timezone، rounding و semantics وضعیت یکسان باشد.
- calculated_at و source_updated_at ثبت شوند؛ snapshot_id/data_version در صورت پشتیبانی استفاده شود.
- محدودیت دسترسی، localization، RTL/LTR و قالب اعداد بررسی شوند.
- هر اختلاف باید با قاعده مصوب توضیح داده شود؛ اختلاف توضیح‌نداده‌شده FAIL است.

## سیاست تازگی
SNAPSHOT: خلاصه و جزئیات از یک نسخه داده استفاده کنند؛ برای تطبیق دقیق ترجیح دارد.
LIVE: مقصد داده تازه می‌خواند؛ تغییر عدد فقط با زمان‌های قابل‌مشاهده و امکان تفکیک تغییر واقعی از خطای فیلتر قابل قبول است.
سیاست نامشخص = BLOCKED.

## تست‌های پایه
CP-001 ReferentialIntegrity؛ CP-002 MetricDefinitionParity؛ CP-003 FilterParity؛ CP-004 CountReconciliation؛ CP-005 RecordSetReconciliation؛ CP-006 UnitAndTimeParity؛ CP-007 FreshnessAndSnapshot؛ CP-008 FailureStateSemantics؛ CP-009 DrillDownNavigation؛ CP-010 AuthorizationConsistency؛ CP-011 LocalizationParity؛ CP-012 Regression.
هر نتیجه باید test_id، زمان/محیط، نسخه مشخصات، ورودی و شواهد، انتظار، نتیجه واقعی، PASS/FAIL/BLOCKED/NOT_RUN، اختلاف و مسئول پیگیری را ثبت کند.

## معیار عبور
تمام روابط خلاصه→جزئیات قرارداد و آزمون داشته باشند؛ تمام آزمون‌های بحرانی PASS باشند؛ اختلاف بحرانی یا ابهام مسدودکننده باقی نماند؛ شواهد و تأیید مالک ثبت شود. NOT_RUN برابر PASS نیست.

## چرخه
پس از تعریف صفحات، ویجت‌ها، KPIها و قراردادها ماتریس ردیابی بساز؛ قبل از تأیید مشخصات کنترل ساختاری و پوشش روابط را اجرا کن؛ پس از پیاده‌سازی تست fixtureها، پیش از release regression و در runtime تازگی/خطاها را پایش کن. تغییر قرارداد یا KPI آزمون‌های وابسته را برای اجرای مجدد نامعتبر می‌کند.

## محدوده تضمین
این Gate شواهد قابل ممیزی از سازگاری تعریف‌شده ارائه می‌کند، نه تضمین مطلق صحت ذاتی منبع داده یا نبود تمام خطاهای ممکن.
"""
    return {
      "specs/application.json":json_bytes(application),
      "specs/shell.json":json_bytes(shell),
      "specs/navigation.json":json_bytes({"schema_version":"1.0","status":"DRAFT","sidebar":{"fixed":shell["sidebar"]["fixed"],"items":[]},"routes":[]}),
      "specs/pages.json":json_bytes(pages),
      "specs/widgets.json":json_bytes(widgets),
      "specs/data-contracts.json":json_bytes(data),
      "specs/metrics.json":json_bytes(metrics),
      "specs/interactions.json":json_bytes(interactions),
      "specs/localization.json":json_bytes(localization),
      "specs/assets.json":json_bytes(assets),
      "docs/REPOSITORY_ASSESSMENT.md":assessment,
      "docs/OPEN_QUESTIONS.md":questions,
      "docs/IMPLEMENTATION_WORK_ORDER.md":work,
      "docs/CROSS_PAGE_DATA_INTEGRITY.md":cross_page_validation,
      "docs/DECISIONS.md":"# Decision log\n\n| ID | Decision | Provenance | Status | Date |\n|---|---|---|---|---|\n| D-001 | Initial project intake recorded | OWNER_PROVIDED | PROPOSED | "+stamp+" |\n",
      "docs/CHANGELOG.md":"# Changelog\n\n- "+stamp+": Initial dashboard project specification draft generated.\n"
    }

def main():
    p=argparse.ArgumentParser(description="Compare a dashboard target repository with MDASHBOARD methodology, collect intake and push draft specs.")
    p.add_argument("--repo", required=True, help="GitHub OWNER/REPO or URL")
    p.add_argument("--reference", default=REF_DEFAULT, help="Reference repository OWNER/REPO")
    p.add_argument("--branch", help="Target branch; defaults to repository default branch")
    p.add_argument("--dry-run", action="store_true", help="Do not push; write generated files locally")
    p.add_argument("--output", default="dashboard-spec-output", help="Local output folder for --dry-run")
    args=p.parse_args()
    try:
        target=parse_repo(args.repo); reference=parse_repo(args.reference)
        token=os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        print(f"Target: {target} | Reference: {reference}")
        ref_info=repo_info(reference, token)
        tgt_info=repo_info(target, token)
        ref_tree, ref_truncated=tree(reference, ref_info["default_branch"], token)
        tgt_branch=args.branch or tgt_info["default_branch"]
        tgt_tree, tgt_truncated=tree(target, tgt_branch, token)
        print(f"Reference files: {len(ref_tree)}; target files: {len(tgt_tree)}; target branch: {tgt_branch}")
        if ref_truncated or tgt_truncated:
            print("WARNING: GitHub marked a tree as truncated; comparison may be incomplete.")
        ref_paths=set(ref_tree); tgt_paths=set(tgt_tree)
        print("\nReference files absent in target (first 50):")
        for path in sorted(ref_paths-tgt_paths)[:50]: print("  +",path)
        print("\nTarget files absent in reference (first 50):")
        for path in sorted(tgt_paths-ref_paths)[:50]: print("  -",path)
        print("\nRepository files will not be overwritten unless explicitly approved.")
        answers={}
        questions=[
          ("نام محصول","Product name",""),
          ("Product name","Product name",""),
          ("هدف محصول","Purpose / decisions supported",""),
          ("محیط استقرار","Deployment (on-prem / cloud / hybrid / unknown)","UNKNOWN"),
          ("زبان‌ها","Languages, comma-separated (e.g. fa,en)","fa,en"),
          ("عنوان هدر","Header title",""),
          ("مسیر لوگو","Logo asset path (exact path or blank if unknown)",""),
          ("فوتر","Footer content or unknown","UNKNOWN"),
          ("منوها و چیدمان ثابت هستند؟","Are navigation/layout/widgets fixed? (yes/no/unknown)","yes"),
          ("محدودیت‌ها","Important constraints / non-goals","UNKNOWN")
        ]
        for key,label,default in questions: answers[key]=prompt(label,default)
        specs=make_specs(target,answers,tgt_paths)
        if args.dry_run:
            from pathlib import Path
            out=Path(args.output)
            for path,content in specs.items():
                dest=out/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(content,encoding="utf-8")
            print(f"\nDry-run complete: {len(specs)} files written under {out.resolve()}; nothing pushed.")
            return
        if not token:
            raise RuntimeError("No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN, or use --dry-run.")
        if not tgt_info.get("permissions",{}).get("push",False):
            raise RuntimeError("Connected GitHub identity does not have push permission for target repository.")
        if not ask_yes_no(f"Push up to {len(specs)} draft specification files to {target}@{tgt_branch}? Existing files will be skipped unless overwrite is separately confirmed",False):
            print("Cancelled; nothing pushed."); return
        pushed=[]; skipped=[]; failed=[]
        for path,content in specs.items():
            if path in tgt_paths:
                if not ask_yes_no(f"File exists: {path}. Overwrite it?",False):
                    skipped.append(path); continue
                try:
                    current=api("GET",f"{API}/repos/{target}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(tgt_branch)}",token)
                    result=api("PUT",f"{API}/repos/{target}/contents/{urllib.parse.quote(path,safe='/')}",token,{"message":f"docs: update dashboard specification {path}","content":base64.b64encode(content.encode()).decode(),"sha":current["sha"],"branch":tgt_branch})
                except Exception as e: failed.append((path,str(e))); continue
            else:
                try:
                    result=api("PUT",f"{API}/repos/{target}/contents/{urllib.parse.quote(path,safe='/')}",token,{"message":f"docs: add dashboard specification {path}","content":base64.b64encode(content.encode()).decode(), **({} if target_was_empty else {"branch":tgt_branch})})
                except Exception as e: failed.append((path,str(e))); continue
            pushed.append((path,result.get("commit",{}).get("sha","unknown")))
        print(f"\nPushed: {len(pushed)}; skipped: {len(skipped)}; failed: {len(failed)}")
        for path,sha in pushed: print("PUSHED",path,sha)
        for path in skipped: print("SKIPPED",path)
        for path,error in failed: print("FAILED",path,error)
        if failed: sys.exit(2)
    except (ValueError, RuntimeError, urllib.error.URLError) as e:
        print("ERROR:",e,file=sys.stderr); sys.exit(1)

if __name__=="__main__": main()
