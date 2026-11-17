import asyncio
import html
import json
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def is_docker_installed() -> bool:
    """Serverda Docker o'rnatilganmi tekshirish."""
    return shutil.which("docker") is not None


async def get_containers_summary() -> list[dict]:
    """Barcha Docker konteynerlari holatini olish."""
    if not is_docker_installed():
        return []

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a", "--format", "{{json .}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return []

        containers = []
        for line in stdout.decode("utf-8").strip().split("\n"):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                c_id = item.get("ID", "")
                c_name = item.get("Names", c_id)
                status_raw = item.get("Status", "")
                state = item.get("State", "unknown")
                image = item.get("Image", "")

                is_running = state.lower() == "running" or "up" in status_raw.lower()
                containers.append({
                    "id": c_id,
                    "name": c_name,
                    "image": image,
                    "state": state,
                    "status_str": status_raw,
                    "is_running": is_running,
                    "ports": item.get("Ports", ""),
                })
            except Exception:
                continue
        return containers
    except Exception as e:
        logger.debug(f"Docker konteynerlarini olishda xato: {e}")
        return []


async def get_container_logs(container_id: str, tail: int = 50) -> str:
    """Konteynerning oxirgi loglarini olish."""
    if not is_docker_installed():
        return "⚠️ Docker o'rnatilmagan."

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "logs", "--tail", str(tail), container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        res = out or err or "(Loglar bo'sh)"
        if len(res) > 3500:
            res = res[-3500:] + "\n... [qisqartirildi]"
        return res
    except Exception as e:
        return f"❌ Loglarni olishda xatolik: {e}"


async def control_container(container_id: str, action: str) -> tuple[bool, str]:
    """Docker konteynerini boshqarish (restart, stop, start)."""
    if not is_docker_installed():
        return False, "⚠️ Docker o'rnatilmagan."

    if action not in ("restart", "stop", "start"):
        return False, f"⚠️ Noto'g'ri amal: {action}"

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", action, container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return True, f"✅ Konteyner <code>{html.escape(container_id)}</code> muvaffaqiyatli <b>{action}</b> qilindi."
        else:
            err = stderr.decode().strip() or stdout.decode().strip()
            return False, f"❌ Xatolik ({action}):\n<code>{html.escape(err)}</code>"
    except Exception as e:
        return False, f"❌ Xatolik: {str(e)}"
