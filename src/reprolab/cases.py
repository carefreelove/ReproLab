"""Version-paired fixtures. Oracle material is only consumed by the host evaluator."""

import io
import json
import re
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from reprolab.core import LabError, atomic_write, bounded_path, digest

SYNTHETIC = {
    "empty-mean": {
        "issue": "source.mean([]) 应返回 0，非空输入返回算术平均值。当前空列表会失败，请生成测试。",
        "bug": "def mean(values):\n    return sum(values) / len(values)\n",
        "fix": "def mean(values):\n    return sum(values) / len(values) if values else 0\n",
        "test": "from source import mean\n\ndef test_empty():\n    assert mean([]) == 0\n    assert mean([2, 4]) == 3\n",
    },
    "inclusive-window": {
        "issue": "source.in_window(value, start, end) 的时间窗口应包含两个端点，结束时刻的记录被遗漏。参数为整数时间戳。",
        "bug": "def in_window(value, start, end):\n    return start <= value < end\n",
        "fix": "def in_window(value, start, end):\n    return start <= value <= end\n",
        "test": "from source import in_window\n\ndef test_end():\n    assert in_window(20, 10, 20) is True\n    assert in_window(21, 10, 20) is False\n",
    },
    "shared-state": {
        "issue": "source.Bucket 的不同实例应拥有独立的 items 列表。调用 add(value) 后另一个实例也出现了数据。",
        "bug": "class Bucket:\n    items = []\n    def add(self, value):\n        self.items.append(value)\n",
        "fix": "class Bucket:\n    def __init__(self):\n        self.items = []\n    def add(self, value):\n        self.items.append(value)\n",
        "test": 'from source import Bucket\n\ndef test_independent():\n    first, second = Bucket(), Bucket()\n    first.add("a")\n    assert second.items == []\n',
    },
    "negative-offset": {
        "issue": "source.paginate(items, offset, limit) 应拒绝负 offset，抛出 ValueError。当前负数会按 Python 切片规则处理。",
        "bug": "def paginate(items, offset, limit):\n    return items[offset:offset + limit]\n",
        "fix": 'def paginate(items, offset, limit):\n    if offset < 0:\n        raise ValueError("negative offset")\n    return items[offset:offset + limit]\n',
        "test": "import pytest\nfrom source import paginate\n\ndef test_negative():\n    with pytest.raises(ValueError):\n        paginate([1, 2, 3], -1, 2)\n",
    },
    "zero-capacity": {
        "issue": "source.chunks(items, n) 返回分块列表。约定 n=0 返回空列表，n<0 抛出 ValueError。当前零容量失败。",
        "bug": "def chunks(items, n):\n    return [items[i:i+n] for i in range(0, len(items), n)]\n",
        "fix": 'def chunks(items, n):\n    if n < 0:\n        raise ValueError("negative size")\n    if n == 0:\n        return []\n    return [items[i:i+n] for i in range(0, len(items), n)]\n',
        "test": "from source import chunks\n\ndef test_zero():\n    assert chunks([1, 2], 0) == []\n",
    },
    "decimal-money": {
        "issue": 'source.money(amount) 接收十进制字符串，按 ROUND_HALF_UP 保留两位返回 Decimal。输入 2.675 的结果应为 Decimal("2.68")。',
        "bug": "from decimal import Decimal\n\ndef money(amount):\n    return Decimal(str(round(float(amount), 2)))\n",
        "fix": 'from decimal import Decimal, ROUND_HALF_UP\n\ndef money(amount):\n    return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)\n',
        "test": 'from decimal import Decimal\nfrom source import money\n\ndef test_rounding():\n    assert money("2.675") == Decimal("2.68")\n',
    },
}
REAL = {
    "chunked-even": {
        "repository": "more-itertools/more-itertools",
        "buggy": "20c4ee5c63f8f8c35a37aee3b69d95cd2450c09a",
        "fixed": "08dca284ba5446a026afdc34067b658f9da989eb",
        "issue": "more_itertools.chunked_even(iterable, n) 在 n=0 时应得到空结果且不消耗输入迭代器；n<0 时应抛出 ValueError 且不消耗输入。请验证边界及迭代器状态。",
        "source": "https://github.com/more-itertools/more-itertools/pull/1342",
        "test": 'import more_itertools as mi\n\ndef test_zero():\n    source = iter("ABC")\n    assert list(mi.chunked_even(source, 0)) == []\n    assert list(source) == list("ABC")\n',
    },
    "numeric-range": {
        "repository": "more-itertools/more-itertools",
        "buggy": "08dca284ba5446a026afdc34067b658f9da989eb",
        "fixed": "f42daddf205f335fea6e200dad46049f33e71221",
        "issue": "more_itertools.numeric_range 的等值比较和 hash 应支持元素数量超过 sys.maxsize 的有效范围，与内置 range 行为一致。numeric_range(10**30) 的比较和哈希当前抛出 OverflowError；显式 len() 仍可抛出 OverflowError。",
        "source": "https://github.com/more-itertools/more-itertools/pull/1345",
        "test": "import more_itertools as mi\n\ndef test_large_range():\n    first = mi.numeric_range(10**30)\n    second = mi.numeric_range(10**30)\n    assert first == second\n    assert hash(first) == hash(range(10**30))\n",
    },
}


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ReproLab/0.1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(30_000_001)
    except (OSError, urllib.error.URLError) as exc:
        raise LabError("download", "公开仓库下载失败，请检查网络后重试") from exc
    if len(data) > 30_000_000:
        raise LabError("repository_limit", "仓库快照超过 30 MB 下载上限")
    return data


def fetch_snapshot(home: Path, repository: str, commit: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(
        r"[a-f0-9]{40}", commit
    ):
        raise LabError("repository", "请提供 owner/name 和完整 commit SHA")
    destination = home / "sources" / digest(repository)[:12] / commit
    if (destination / ".snapshot-complete").exists():
        return destination
    metadata = json.loads(download(f"https://api.github.com/repos/{repository}"))
    if metadata.get("private", True):
        raise LabError("repository", "目标应为公开仓库")
    archive = download(f"https://api.github.com/repos/{repository}/tarball/{commit}")
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        for item in bundle:
            parts = Path(item.name).parts[1:]
            if not parts or any(
                part in {".git", ".env", "__pycache__"} or part.startswith(".env.") for part in parts
            ):
                continue
            if item.issym() or item.islnk():
                raise LabError("repository", "快照包含符号链接，请使用受控的纯 Python 项目")
            if not item.isfile():
                continue
            total += item.size
            if total > 60_000_000 or item.size > 2_000_000:
                raise LabError("repository_limit", "仓库展开体积或单文件大小达到上限")
            path = bounded_path(destination, "/".join(parts))
            atomic_write(path, bundle.extractfile(item).read())
    atomic_write(destination / ".snapshot-complete", commit)
    return destination


def prepare_case(home: Path, name: str) -> dict:
    if name in REAL:
        case = REAL[name]
        for commit in (case["buggy"], case["fixed"]):
            fetch_snapshot(home, case["repository"], commit)
        return {key: value for key, value in case.items() if key != "test"} | {"case": name}
    if name not in SYNTHETIC:
        raise LabError("case", "未知案例")
    case = SYNTHETIC[name]
    commits = {}
    for variant in ("bug", "fix"):
        commit = digest(case[variant])[:40]
        destination = home / "sources" / digest("fixture/" + name)[:12] / commit
        atomic_write(destination / "source.py", case[variant])
        atomic_write(destination / ".snapshot-complete", commit)
        commits[variant] = commit
    return {
        "case": name,
        "repository": "fixture/" + name,
        "buggy": commits["bug"],
        "fixed": commits["fix"],
        "issue": case["issue"],
        "source": "self_authored_fixture",
    }


def source_path(home: Path, spec: dict, variant: str = "buggy") -> Path:
    return home / "sources" / digest(spec["repository"])[:12] / spec[variant]


def oracle_test(name: str) -> str:
    return (SYNTHETIC | REAL)[name]["test"]
