from dataclasses import dataclass
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, socket
from uuid import uuid4

@dataclass(frozen=True)
class SessionContext:
    session_id: str
    container_name: str
    adb_port: int
    socks_port: int
    http_proxy_port: int
    runtime_dir: Path

def _is_tcp_port_free(port: int, host: str = "127.0.0.1") -> bool:
    sock = socket(AF_INET, SOCK_STREAM)
    sock.settimeout(0.2)
    result = sock.connect_ex((host, port))
    sock.close()
    return result != 0

def build_session_context(
    iteration: int,
    runtime_root: Path,
    container_prefix: str = "redroid",
    adb_port_base: int = 5555,
    socks_port_base: int = 1080,
    http_proxy_port_base: int = 1081,
    scan_limit: int = 500,
) -> SessionContext:
    runtime_root.mkdir(parents=True, exist_ok=True)
    for offset in range(scan_limit):
        adb_port = adb_port_base + offset
        socks_port = socks_port_base + offset
        http_proxy_port = http_proxy_port_base + offset
        if not all(_is_tcp_port_free(p) for p in (adb_port, socks_port, http_proxy_port)):
            continue
        session_id = f"i{iteration}_{uuid4().hex[:10]}"
        container_name = f"{container_prefix}_{session_id}"
        runtime_dir = runtime_root / session_id
        return SessionContext(
            session_id=session_id,
            container_name=container_name,
            adb_port=adb_port,
            socks_port=socks_port,
            http_proxy_port=http_proxy_port,
            runtime_dir=runtime_dir,
        )
    raise RuntimeError("Could not allocate free ports for a new session")
