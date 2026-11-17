import asyncio
import html
import json
import logging
import os
import shutil
import signal
import subprocess

logger = logging.getLogger(__name__)


def _is_tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def get_systemd_custom_services() -> list[dict]:
    """/etc/systemd/system/ papkasidagi maxsus loyiha servislari."""
    services = []
    service_dir = "/etc/systemd/system"
    if not os.path.exists(service_dir):
        return services

    try:
        for fname in os.listdir(service_dir):
            if fname.endswith(".service") and not fname.startswith("."):
                svc_name = fname
                # Holatini tekshiramiz
                try:
                    res = subprocess.run(
                        ["systemctl", "is-active", svc_name],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    status = res.stdout.strip() or "inactive"
                except Exception:
                    status = "unknown"

                services.append({
                    "id": svc_name,
                    "name": svc_name.replace(".service", ""),
                    "type": "systemd",
                    "status": status,
                    "details": f"Systemd Service ({svc_name})",
                })
    except Exception as e:
        logger.warning(f"Systemd servislarini o'qishda xatolik: {e}")

    return services


def get_pm2_projects() -> list[dict]:
    """PM2 orqali boshqarilayotgan Node/Python loyihalar."""
    if not _is_tool_available("pm2"):
        return []

    try:
        res = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            apps = []
            for item in data:
                status = item.get("pm2_env", {}).get("status", "unknown")
                pid = item.get("pid", 0)
                mem = item.get("monit", {}).get("memory", 0) / (1024 * 1024)
                cpu = item.get("monit", {}).get("cpu", 0)
                apps.append({
                    "id": item.get("name", str(item.get("pm_id"))),
                    "name": item.get("name", "pm2_app"),
                    "type": "pm2",
                    "status": status,
                    "pid": pid,
                    "details": f"CPU: {cpu}% | RAM: {round(mem, 1)} MB",
                })
            return apps
    except Exception as e:
        logger.debug(f"PM2 ma'lumotlarini olishda xato: {e}")
    return []


def get_docker_containers() -> list[dict]:
    """Docker konteynerlari ro'yxati."""
    if not _is_tool_available("docker"):
        return []

    try:
        cmd = ["docker", "ps", "-a", "--format", "{{json .}}"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            containers = []
            for line in res.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    c_id = obj.get("ID", "")
                    c_name = obj.get("Names", c_id)
                    state = obj.get("State", "unknown")
                    image = obj.get("Image", "")
                    containers.append({
                        "id": c_name or c_id,
                        "name": c_name or c_id,
                        "type": "docker",
                        "status": state,
                        "details": f"Image: {image[:20]} | Status: {obj.get('Status', '')}",
                    })
                except Exception:
                    continue
            return containers
    except Exception as e:
        logger.debug(f"Docker konteynerlarini olishda xato: {e}")
    return []


def get_standalone_processes() -> list[dict]:
    """
    Fonda erkin yurgan backend/frontend/bot jarayonlari
    (python, node, uvicorn, gunicorn, va h.k.)
    """
    processes = []
    own_pid = os.getpid()

    try:
        res = subprocess.run(
            ["ps", "-eo", "pid,user,%cpu,%mem,comm,args", "--sort=-%mem"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().split("\n")[1:]
            for line in lines:
                parts = line.split(maxsplit=5)
                if len(parts) >= 6:
                    pid_str, user, cpu, mem, comm, args = parts
                    try:
                        pid = int(pid_str)
                    except ValueError:
                        continue

                    if pid in (1, own_pid):
                        continue

                    args_lower = args.lower()
                    comm_lower = comm.lower()

                    # Qiziqarli app kalit so'zlari
                    is_app = any(kw in args_lower or kw in comm_lower for kw in [
                        "python", "node", "uvicorn", "gunicorn", "celery",
                        "fastapi", "django", "flask", "bot", "npm", "yarn", "vite", "next"
                    ])

                    # Botning o'zini filtrlaymiz
                    if "server-master-bot" in args_lower or ("main.py" in args_lower and "Bots" in args):
                        continue

                    if is_app:
                        processes.append({
                            "id": str(pid),
                            "name": f"{comm} ({pid})",
                            "type": "process",
                            "status": "running",
                            "pid": pid,
                            "user": user,
                            "cpu": cpu,
                            "mem": mem,
                            "details": f"User: {user} | CPU: {cpu}% | RAM: {mem}% | CMD: {args[:50]}",
                        })
    except Exception as e:
        logger.warning(f"Alohida jarayonlarni o'qishda xato: {e}")

    return processes[:15]


def scan_all_projects() -> dict[str, list[dict]]:
    """Serverdagi barcha loyihalar va jarayonlarni toifalarga bo'lib aniqlash."""
    return {
        "systemd": get_systemd_custom_services(),
        "pm2": get_pm2_projects(),
        "docker": get_docker_containers(),
        "processes": get_standalone_processes(),
    }


async def control_project(proj_type: str, proj_id: str, action: str) -> tuple[bool, str]:
    """
    Loyihani boshqarish (start, stop, restart, reload).
    """
    allowed_actions = ("start", "stop", "restart", "reload")
    if action not in allowed_actions:
        return False, f"⚠️ Noto'g'ri amal: «{action}». Ruxsat etilgan: {', '.join(allowed_actions)}"

    cmd = None
    if proj_type == "systemd":
        cmd = ["systemctl", action, proj_id]
    elif proj_type == "pm2":
        cmd = ["pm2", action, proj_id]
    elif proj_type == "docker":
        cmd = ["docker", action, proj_id]
    else:
        return False, f"⚠️ Ushbu turdagi loyihani ({proj_type}) {action} qilib bo'lmaydi."

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return True, f"✅ <b>{proj_id}</b> loyihasi muvaffaqiyatli <code>{action}</code> qilindi!"
        else:
            err_msg = stderr.decode().strip() or stdout.decode().strip() or "Noma'lum xatolik"
            return False, f"❌ <b>{action.upper()} xatosi:</b>\n<code>{html.escape(err_msg)}</code>"
    except Exception as e:
        return False, f"❌ Xatolik yuz berdi: {str(e)}"


async def get_project_logs(proj_type: str, proj_id: str, lines: int = 40) -> str:
    """Loyihaning so'nggi loglarini olish."""
    cmd = None
    if proj_type == "systemd":
        cmd = ["journalctl", "-u", proj_id, "-n", str(lines), "--no-pager"]
    elif proj_type == "pm2":
        cmd = ["pm2", "logs", proj_id, "--lines", str(lines), "--nostream"]
    elif proj_type == "docker":
        cmd = ["docker", "logs", "--tail", str(lines), proj_id]
    else:
        return f"ℹ️ «{proj_type}» turidagi jarayon uchun log manbasi avtomatik aniqlanmadi."

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        result = out or err or "(Loglar bo'sh)"
        if len(result) > 3500:
            result = result[-3500:] + "\n... [qisqartirildi]"
        return result
    except Exception as e:
        return f"❌ Loglarni olishda xatolik: {e}"


async def kill_process_by_pid(pid: int, sig: int = signal.SIGTERM) -> tuple[bool, str]:
    """Xavfli yoki katta resurs sarflayotgan jarayonni to'xtatish (Kill)."""
    own_pid = os.getpid()

    if pid <= 1:
        return False, "⛔️ Tizim asosiy jarayonini (PID 1) to'xtatish xavfli va taqiqlangan!"

    if pid == own_pid:
        return False, "⛔️ Botning o'z jarayonini o'ldirishga ruxsat berilmaydi!"

    try:
        os.kill(pid, sig)
        # 1 soniya kutib ko'ramiz
        await asyncio.sleep(0.5)
        try:
            # Jarayon tirikmi tekshirish
            os.kill(pid, 0)
            # Agar hali tirik bo'lsa SIGKILL yuboramiz
            if sig != signal.SIGKILL:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        return True, f"✅ Jarayon (PID: <code>{pid}</code>) to'xtatildi."
    except ProcessLookupError:
        return True, f"ℹ️ Jarayon (PID: <code>{pid}</code>) allaqachon mavjud emas."
    except PermissionError:
        return False, f"⛔️ Jarayonni (PID: <code>{pid}</code>) to'xtatish uchun yetarli huquq yo'q."
    except Exception as e:
        return False, f"❌ Xatolik: {str(e)}"
