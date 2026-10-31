"""配置、密钥和实验结果的统一读写；密钥不进入实验记录。"""

import hashlib
import json
import os
import re
import tempfile
import fcntl
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROTOCOL = "three-models-v1-rule-grading-unique-threshold"


def read_json(path):
    """按中文兼容的编码读取配置或结果。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json(path, value):
    """先写临时文件再替换，避免中断时损坏上一次检查点。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fingerprint(value):
    """为题目、配置和提示词建立稳定身份，避免恢复时混用不同实验。"""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_secrets(path=None):
    """读取本机密钥文件；已有环境变量优先，不执行文件中的任何代码。"""
    path = Path(path or ROOT / ".env.local")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            name, separator, value = line.partition("=")
            if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                raise ValueError("本机密钥文件格式错误，请重新运行配置向导。")
            os.environ.setdefault(name, json.loads(value))


def save_secrets(values, path=None):
    """以仅当前用户可读写的权限原子保存密钥。"""
    path = Path(path or ROOT / ".env.local")
    existing = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                name, value = line.split("=", 1)
                existing[name] = json.loads(value)
    existing.update({key: value for key, value in values.items() if value})
    fd, temporary = tempfile.mkstemp(prefix=".secret-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("# 本机密钥：不加入版本控制，不复制到实验结果。\n")
            for key, value in existing.items():
                handle.write(f"{key}={json.dumps(value, ensure_ascii=False)}\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_config(path=None):
    """加载模型的公开配置及独立保存的密钥。"""
    load_secrets()
    config = read_json(path or ROOT / "models.json")
    if config.get("schema_version") != 1 or not isinstance(config.get("models"), dict):
        raise ValueError("模型配置格式不正确。")
    return config


def safe_name(name):
    """限制运行目录名，防止覆盖工作区之外的文件。"""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise ValueError("运行名称只能包含字母、数字、下划线、短横线和点。")
    return name


def selected_models(config, names):
    """显式校验模型清单，避免拼写错误导致空实验。"""
    names = names or config.get("default_models") or list(config["models"])
    if len(set(names)) != len(names) or any(n not in config["models"] for n in names):
        raise ValueError("模型标识无效或重复；可用标识为 " + "、".join(config["models"]) + "。")
    return {name: config["models"][name] for name in names}


def open_run(directory, manifest):
    """已有运行必须与当前实验定义完全一致，才能恢复执行。"""
    directory = Path(directory)
    path = directory / "manifest.json"
    if path.exists():
        if read_json(path) != manifest:
            raise ValueError("已有运行的配置、题目或协议不同，请使用新的运行名称。")
    else:
        atomic_json(path, manifest)
    return directory


def result_path(directory, model, benchmark, prompt_id):
    """提示词用摘要命名，原始标识保存在文件内。"""
    return Path(directory) / safe_name(model) / safe_name(benchmark) / (fingerprint(prompt_id)[:16] + ".json")


def latest_run(results_root=None):
    """读取上一次运行位置。"""
    root = Path(results_root or ROOT / "results")
    pointer = root / "latest.json"
    if not pointer.exists():
        raise ValueError("尚无实验结果，请先执行小规模试跑。")
    return root / safe_name(read_json(pointer)["run_name"])


@contextmanager
def exclusive_run(directory):
    """同一实验只允许一个执行进程，避免重复调用和并发覆盖费用账本。"""
    with (Path(directory) / ".run.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("这个实验已有运行进程，请等待其完成，不要重复启动。") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
