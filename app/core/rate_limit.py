"""简单的内存登录频率限制器

按 IP 地址限制登录尝试频率：5 次失败后锁定 15 分钟。
使用内存字典存储，进程重启后清空（适合单实例部署）。
"""

import time
from collections import defaultdict

MAX_ATTEMPTS = 5
LOCK_DURATION = 900  # 15 分钟


_attempts: dict[str, list[float]] = defaultdict(list)


def _cleanup_old_attempts(ip: str, now: float) -> None:
    cutoff = now - LOCK_DURATION
    _attempts[ip] = [t for t in _attempts[ip] if t > cutoff]


def is_locked(ip: str) -> bool:
    now = time.time()
    _cleanup_old_attempts(ip, now)
    return len(_attempts[ip]) >= MAX_ATTEMPTS


def record_failure(ip: str) -> None:
    now = time.time()
    _cleanup_old_attempts(ip, now)
    _attempts[ip].append(now)


def reset(ip: str) -> None:
    _attempts.pop(ip, None)
