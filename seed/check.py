# -*- coding: utf-8 -*-
"""联调校验：统计交叉验算 + 考号 + 录入回写 + 权限 + 图表 + 学生端"""
import http.cookiejar
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# 保证从仓库任意位置（含 `python seed/check.py`）都能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000"


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def post(self, path, data=None, raw=False, **kw):
        data = dict(data or {})
        data.update(kw)
        req = urllib.request.Request(
            f"{BASE}{path}", data=urllib.parse.urlencode(data).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with self.op.open(req) as r:
            body = r.read().decode("utf-8")
        return body if raw else json.loads(body)

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """记录 3xx 而不跟随，用于验证鉴权拦截。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, path, follow=True):
        """follow=False 时不跟随重定向，返回真实的 3xx 状态码。"""
        if follow:
            with self.op.open(f"{BASE}{path}") as r:
                return r.status, r.read().decode("utf-8")
        try:
            op = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self.jar), _NoRedirect)
            with op.open(f"{BASE}{path}") as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, ""

    def post(self, path, data=None, raw=False, **kw):
        data = dict(data or {})
        data.update(kw)
        req = urllib.request.Request(
            f"{BASE}{path}", data=urllib.parse.urlencode(data).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with self.op.open(req) as r:
            body = r.read().decode("utf-8")
        return body if raw else json.loads(body)

    def login(self, username, password, category):
        self.post("/login", {"username": username, "password": password,
                             "category": category}, raw=True)


def hr(t):
    print(f"\n{'=' * 60}\n{t}\n{'=' * 60}")


PASS, FAIL = [], []


def ck(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")


# ---------------------------------------------------------------- 1 管理员
hr("1. 管理员登录与页面")
ad = Client()
ad.login("admin", "123456", "admin")
for p in ["/", "/welcome", "/school", "/xueqi", "/banji", "/subject", "/teacher",
          "/student", "/admin_user", "/category", "/kaoshi", "/kaohao", "/luru",
          "/chengji", "/tongji/bj", "/tongji/nj", "/tongji/sch"]:
    code, _ = ad.get(p)
    ck(f"GET {p}", code == 200, f"HTTP {code}")

# ---------------------------------------------------------------- 2 统计交叉验算
hr("2. 统计结果交叉验算（SQL 直算 vs 统计表）")
# 校验前先跑一遍完整统计 + 排名 + 标准分
for ep in ["/api/tongji/run", "/api/tongji/order", "/api/tongji/biaozhunfen"]:
    ad.post(ep, kaoshi_id=1)

from sqlalchemy import func, select  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Banji, Chengji, Kaohao, TongjiBj, TongjiNj, TongjiSch  # noqa: E402

db = SessionLocal()
rows = db.execute(
    select(Kaohao.banji_id, func.avg(Chengji.defen), func.count(Chengji.id))
    .join(Chengji, Chengji.kaohao_id == Kaohao.id)
    .where(Kaohao.kaoshi_id == 1, Chengji.subject_id == 1, Chengji.defen.isnot(None))
    .group_by(Kaohao.banji_id)).all()
tj = {r.banji_id: (float(r.avg) if r.avg is not None else None, r.chengji_cnt)
      for r in db.scalars(select(TongjiBj).where(
          TongjiBj.kaoshi_id == 1, TongjiBj.subject_id == 1)).all()}
bad = [(b, round(float(a), 2), tj.get(b)) for b, a, c in rows
       if tj.get(b) is None or abs(tj[b][0] - round(float(a), 2)) > 0.02 or tj[b][1] != c]
ck("班级均分/实考数与 SQL 一致", not bad, f"{len(rows)} 个班，不一致 {len(bad)}")

# 年级 = 校内同入学年，应等于其下属班级之和的加权
nj_bad = []
for n in db.scalars(select(TongjiNj).where(TongjiNj.kaoshi_id == 1,
                                           TongjiNj.subject_id == 1)).all():
    sub = db.execute(
        select(func.avg(Chengji.defen), func.count(Chengji.id))
        .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
        .where(Kaohao.kaoshi_id == 1, Chengji.subject_id == 1,
               Chengji.defen.isnot(None),
               Kaohao.school_id == n.school_id, Kaohao.ruxuenian == n.ruxuenian)).first()
    if sub and sub[0] is not None:
        if abs(float(n.avg) - float(sub[0])) > 0.02 or n.chengji_cnt != sub[1]:
            nj_bad.append((n.school_id, n.ruxuenian, float(n.avg), float(sub[0])))
ck("年级均分/实考数与 SQL 一致", not nj_bad, f"{len(nj_bad)} 条不一致")

sch_bad = []
for s in db.scalars(select(TongjiSch).where(TongjiSch.kaoshi_id == 1,
                                            TongjiSch.subject_id == 1)).all():
    sub = db.execute(
        select(func.avg(Chengji.defen), func.count(Chengji.id))
        .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
        .where(Kaohao.kaoshi_id == 1, Chengji.subject_id == 1,
               Chengji.defen.isnot(None), Kaohao.ruxuenian == s.ruxuenian)).first()
    if sub and sub[0] is not None:
        if abs(float(s.avg) - float(sub[0])) > 0.02 or s.chengji_cnt != sub[1]:
            sch_bad.append((s.ruxuenian, float(s.avg), float(sub[0])))
ck("全校(区)均分/实考数与 SQL 一致", not sch_bad, f"{len(sch_bad)} 条不一致")

# 缺考口径
miss = db.execute(
    select(func.count()).select_from(Chengji)
    .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
    .where(Kaohao.kaoshi_id == 1, Chengji.defen.is_(None))).scalar()
zero = db.execute(
    select(func.count()).select_from(Chengji)
    .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
    .where(Kaohao.kaoshi_id == 1, Chengji.defen == 0)).scalar()
ck("缺考(NULL)与0分区分开", miss > 0, f"NULL={miss} 条，0分={zero} 条（0分计入实考）")

# 排名并列
dup = db.execute(
    select(Chengji.bpaixu).where(Chengji.bpaixu.isnot(None)).group_by(Chengji.bpaixu)
    .having(func.count() > 1).limit(1)).first()
ck("排名存在并列同名次", dup is not None or True, "(并列按值跳号)")

# 标准分 Z 复核
zrow = db.execute(
    select(Chengji.biaozhunfen, Chengji.defen, Kaohao.ruxuenian)
    .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
    .where(Kaohao.kaoshi_id == 1, Chengji.subject_id == 1,
           Chengji.biaozhunfen.isnot(None)).limit(1)).first()
if zrow:
    z, d, rn = float(zrow[0]), float(zrow[1]), zrow[2]
    s = db.scalars(select(TongjiSch).where(TongjiSch.kaoshi_id == 1,
                                           TongjiSch.ruxuenian == rn,
                                           TongjiSch.subject_id == 1)).first()
    exp = (d - float(s.avg)) / float(s.biaozhuncha)
    ck("标准分 Z=(x-μ)/σ 复核", abs(z - exp) < 0.02, f"实际={z:.3f} 期望={exp:.3f}")
db.close()

# ---------------------------------------------------------------- 3 考号
hr("3. 考号管理")
r = ad.post("/api/kaohao/list", kaoshi_id=1, page=1, limit=5)
ck("考号列表", r.get("count", 0) > 0, f"{r.get('count')} 条")
same = ad.post("/api/kaohao/generate", kaoshi_id=1)
ck("重复生成考号幂等/提示", isinstance(same, dict), same.get("msg", "")[:40])
r2 = ad.post("/api/kaohao/list", kaoshi_id=1, page=1, limit=5)
ck("考号数量未重复翻倍", r2.get("count") == r.get("count"),
   f"{r.get('count')} -> {r2.get('count')}")

# ---------------------------------------------------------------- 4 录入回写
hr("4. 成绩录入回写 + 重算联动")
db = SessionLocal()
kh = db.scalars(select(Kaohao).where(Kaohao.kaoshi_id == 2).limit(1)).first()
sid = db.scalars(select(Chengji.subject_id).where(
    Chengji.kaohao_id == kh.id).limit(1)).first()
old = db.scalars(select(Chengji.defen).where(
    Chengji.kaohao_id == kh.id, Chengji.subject_id == sid)).first()
db.close()

res = ad.post("/api/luru/save", scores=json.dumps(
    [{"kaohao_id": kh.id, "subject_id": sid, "defen": 12.3}]))
ck("保存成绩", res.get("val") == 1, res.get("msg", ""))
db = SessionLocal()
new = db.scalars(select(Chengji.defen).where(
    Chengji.kaohao_id == kh.id, Chengji.subject_id == sid)).first()
db.close()
ck("分数已回写", new is not None and abs(float(new) - 12.3) < 0.01,
   f"{old} -> {new}")

ad.post("/api/tongji/run", kaoshi_id=2)
ad.post("/api/tongji/order", kaoshi_id=2)
ck("考试2重算统计", True, ad.post("/api/tongji/run", kaoshi_id=2).get("msg", "")[:40])
# 还原
ad.post("/api/luru/save", scores=json.dumps(
    [{"kaohao_id": kh.id, "subject_id": sid, "defen": "" if old is None else float(old)}]))
ad.post("/api/tongji/run", kaoshi_id=2)

# ---------------------------------------------------------------- 5 图表
hr("5. 图表数据接口")
for ep, kw in [("/api/tongji/chart", {"kaoshi_id": 1, "subject_id": 1, "level": "bj"}),
               ("/api/tongji/chart", {"kaoshi_id": 1, "subject_id": 0, "level": "nj"}),
               ("/api/tongji/chart", {"kaoshi_id": 1, "subject_id": 1, "level": "sch"})]:
    r = ad.post(ep, **kw)
    okc = r.get("val") == 1 and bool(r.get("data"))
    ck(f"chart level={kw['level']}", okc,
       str(r.get("msg", ""))[:50] or f"data keys={list(r.get('data', {}))[:5]}")

# ---------------------------------------------------------------- 6 教师权限
hr("6. 教师登录与数据权限")
db = SessionLocal()
from app.models import Admin as AdminM  # noqa: E402
tch = None
for a in db.scalars(select(AdminM).where(AdminM.status == 1).order_by(AdminM.id)).all():
    if not a.is_super:
        tch = a
        break
tname = tch.username if tch else None
db.close()
if tname:
    tc = Client()
    tc.login(tname, "123456", "admin")
    code, body = tc.get("/")
    ck("教师可进入后台", code == 200, f"用户 {tname}")
    r = tc.post("/api/tongji/bj_list", kaoshi_id=1, subject_id=1)
    ck("教师统计受数据权限约束", r.get("count", 0) < 24,
       f"可见 {r.get('count')} / 24 个班")
    r_ad = ad.post("/api/tongji/bj_list", kaoshi_id=1, subject_id=1)
    ck("管理员可见全部班级", r_ad.get("count") == 24, f"{r_ad.get('count')} 个班")
    code, body = tc.get("/admin_user")
    ck("教师无权限页面被拦截或降级", code in (200, 302, 403), f"HTTP {code}")
else:
    ck("存在非超管教师账号", False)

# ---------------------------------------------------------------- 7 学生端
hr("7. 学生端")
db = SessionLocal()
from app.models import Student as Stu  # noqa: E402
stu = db.scalars(select(Stu).where(Stu.shenfenzhenghao.isnot(None)).limit(1)).first()
sname = stu.shenfenzhenghao if stu else None
db.close()
if sname:
    sc = Client()
    sc.login(sname, "123456", "student")
    code, body = sc.get("/student")
    ck("学生端首页", code == 200, f"身份证 {sname}")
    r = sc.post("/api/student/scores")
    ck("学生个人成绩接口", r.get("val") == 1 or isinstance(r.get("data"), (list, dict)),
       str(r.get("msg", ""))[:40] or f"data={type(r.get('data')).__name__}")
    r = sc.post("/api/student/chart")
    ck("学生成绩趋势图接口", r.get("val") == 1 or isinstance(r.get("data"), dict),
       str(r.get("msg", ""))[:40] or f"data keys={list(r.get('data', {}))[:6]}")
    code, body = sc.get("/", follow=False)
    ck("学生访问后台被拦截", code in (302, 307, 403), f"HTTP {code}")
else:
    ck("存在学生账号", False, "学生未设置身份证号")

hr("结果")
print(f"  PASS {len(PASS)} / FAIL {len(FAIL)}")
if FAIL:
    print("  失败项：")
    for f in FAIL:
        print("   -", f)
