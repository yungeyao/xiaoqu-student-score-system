"""全局配置：路径、数据库、站点信息、会话。

所有可调项集中在这里，避免散落在各处；敏感值支持用环境变量覆盖。
"""
import os
import secrets as _secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR = ROOT / "app" / "static"
UPLOAD_DIR = ROOT / "app" / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DB_URL = f"sqlite:///{DATA_DIR / 'cj.db'}"


class Site:
    """站点基础信息与功能开关。"""

    webtitle = "Student Management System"
    version = "1.0.0"
    danwei = "Sample Primary School"

    # 是否维护中
    weihu = False
    weihu_shijian = "2020-1-1 0:00"
    weihu_chixu = 10

    # 初始密码 N 天未修改则禁用帐号
    mimajinyong = 0  # 0 = 不启用，方便演示

    # 是否限制教师只能录入自己任课班级的成绩
    lurufanwei = False

    # 是否允许学生查看分数
    studefen = True


class Auth:
    """登录与权限策略。"""

    auth_on = True
    # 超级管理员 ID（不受数据权限与菜单裁剪限制）
    administrator = (1, 2)
    # 免校验的通用方法
    public_actions = {"upload", "ajaxdata", "saveall", "chaxun", "myinfo"}


# 学段年级名称
GRADELIST = ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]

# 会话签名密钥：优先取环境变量 CJ_SECRET_KEY；否则在 data/ 下持久化一份随机密钥，
# 首次启动生成、之后复用，既不在仓库里写死密钥，重启后也不会把所有人踢下线。
def _load_secret_key() -> str:
    env = os.getenv("CJ_SECRET_KEY")
    if env:
        return env
    keyfile = DATA_DIR / ".secret_key"
    if keyfile.exists():
        return keyfile.read_text(encoding="utf-8").strip()
    key = _secrets.token_hex(32)
    keyfile.write_text(key, encoding="utf-8")
    return key


SECRET_KEY = _load_secret_key()

SESSION_COOKIE = "cj_session"
# 会话有效期（秒）：1200 秒 × 6 = 2 小时
SESSION_EXPIRE = 1200 * 6
