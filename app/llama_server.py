# -*- coding: utf-8 -*-
"""llama-server 进程管理：启动、健康检查、关闭。

参数针对「本机短文本翻译」调优（小 ctx、单 slot、可选 KV 量化），
host 固定读配置（默认 127.0.0.1，仅本机）。
"""

import subprocess
import threading
import time
from pathlib import Path

import requests

from .applog import get_logger
from .paths import resolve_path

_log = get_logger("llama")


# 仅允许本机回环，防止误配 0.0.0.0 把翻译服务暴露到局域网
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def sanitize_server_host(host: str | None) -> str:
    """配置/启动时强制本机 host。"""
    h = (host or "127.0.0.1").strip().lower()
    if h not in _LOCAL_HOSTS:
        _log.warning("server_host=%r 非本机，已强制 127.0.0.1", host)
        return "127.0.0.1"
    # 统一成 IPv4 回环，避免 [::1] 与 127.0.0.1 混用
    if h in ("localhost", "::1"):
        return "127.0.0.1"
    return h


class LlamaServer:
    def __init__(self, cfg: dict):
        self._cfg = cfg
        # 支持 config 里写 runtime/llama 这类相对项目根的路径
        self.llama_dir = resolve_path(cfg["llama_dir"])
        self.model_path = resolve_path(cfg["model_path"])
        self.host = sanitize_server_host(cfg.get("server_host"))
        cfg["server_host"] = self.host
        self.port = int(cfg["server_port"])
        self._proc: subprocess.Popen | None = None
        # 启动时预热与首次翻译可能并发调用 start，串行化避免重复拉起进程
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_healthy(self, timeout: float = 2.0) -> bool:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def _build_cmd(self, exe: Path) -> list[str]:
        """按配置拼 llama-server 参数（翻译场景默认偏快、省显存）。"""
        cfg = self._cfg
        ngl = int(cfg.get("n_gpu_layers", 99))
        threads = int(cfg.get("threads", 8))
        ctx = int(cfg.get("ctx_size", 2048))
        batch = int(cfg.get("batch_size", 512))
        ubatch = int(cfg.get("ubatch_size", 256))
        slots = int(cfg.get("parallel_slots", 1))
        flash = bool(cfg.get("flash_attn", True))
        mlock = bool(cfg.get("mlock", False))
        ctk = str(cfg.get("cache_type_k") or "").strip()
        ctv = str(cfg.get("cache_type_v") or "").strip()

        # 合理夹紧，避免配错把服务拉挂
        ctx = max(512, min(ctx, 8192))
        batch = max(64, min(batch, 4096))
        ubatch = max(32, min(ubatch, batch))
        slots = max(1, min(slots, 4))
        threads = max(1, min(threads, 64))

        cmd = [
            str(exe),
            "-m", str(self.model_path),
            "-ngl", str(ngl),
            "-t", str(threads),
            "-c", str(ctx),
            "-b", str(batch),
            "-ub", str(ubatch),
            "-np", str(slots),
            "--flash-attn", "on" if flash else "auto",
            "--port", str(self.port),
            "--host", self.host,
        ]
        if mlock:
            cmd.append("--mlock")
        if ctk:
            cmd.extend(["-ctk", ctk])
        if ctv:
            cmd.extend(["-ctv", ctv])
        return cmd

    def start(self, wait_seconds: int = 180) -> None:
        """启动 llama-server 并等待就绪。已有健康实例则直接复用。

        线程安全：并发 start 会排队，后者等待前者完成后若已健康则直接返回。
        冷启动加载模型可能较久，默认最多等 180 秒。
        """
        with self._lock:
            if self.is_healthy():
                _log.info("复用已有健康实例 %s", self.base_url)
                return
            exe = self.llama_dir / "llama-server.exe"
            if not exe.exists():
                raise FileNotFoundError(f"未找到 llama-server：{exe}")
            if not self.model_path.exists():
                raise FileNotFoundError(f"未找到模型文件：{self.model_path}")

            # 上一轮本程序拉起的进程若已僵死，先清掉再启
            if self._proc is not None and self._proc.poll() is not None:
                self._proc = None

            cmd = self._build_cmd(exe)
            _log.info(
                "启动 llama-server port=%s ngl=%s ctx=%s batch=%s/%s np=%s mlock=%s ctk=%s model=%s",
                self.port,
                self._cfg.get("n_gpu_layers"),
                self._cfg.get("ctx_size"),
                self._cfg.get("batch_size"),
                self._cfg.get("ubatch_size"),
                self._cfg.get("parallel_slots"),
                self._cfg.get("mlock"),
                self._cfg.get("cache_type_k") or "-",
                self.model_path,
            )
            _log.info("cmdline: %s", " ".join(cmd))
            # CREATE_NO_WINDOW：后台运行不弹黑框
            self._proc = subprocess.Popen(
                cmd,
                cwd=str(self.llama_dir),
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.time() + wait_seconds
            while time.time() < deadline:
                if self.is_healthy():
                    _log.info(
                        "llama-server 就绪 pid=%s base=%s",
                        self._proc.pid if self._proc else "?",
                        self.base_url,
                    )
                    return
                if self._proc.poll() is not None:
                    code = self._proc.returncode
                    self._proc = None
                    _log.error("llama-server 启动后立即退出 code=%s", code)
                    raise RuntimeError(
                        f"llama-server 启动后立即退出（返回码 {code}），"
                        "请检查显卡驱动、模型文件与启动参数"
                        "（可把 cache_type_k/v 置空或 flash_attn=false 重试）"
                    )
                time.sleep(0.5)
            _log.error("llama-server %s 秒内未就绪", wait_seconds)
            raise TimeoutError(f"llama-server 在 {wait_seconds} 秒内未就绪")

    def stop(self) -> None:
        """仅关闭本程序拉起的进程，不影响用户自己启动的实例。"""
        with self._lock:
            if self._proc and self._proc.poll() is None:
                _log.info("停止本程序拉起的 llama-server pid=%s", self._proc.pid)
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None
