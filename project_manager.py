import asyncio
import glob
import html
import json
import logging
import os
import shutil
import signal
import subprocess

import config

logger = logging.getLogger(__name__)


def _is_tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def get_directory_projects() -> list[dict]:
    """
    Projects papkasidagi (masalan /home/server/Projects/) mustaqil loyihalar (frontend, backend, botlar).
    Har bir loyihada manage.sh, systemd, docker yoki alohida jarayon bor-yo'qligi tekshiriladi.
    """
    projects_dir = getattr(config, "PROJECTS_DIR", "/home/server/Projects")
    if not os.path.exists(projects_dir):
        return []

    local_apps = []
    try:
        entries = sorted(os.listdir(projects_dir))
        for item in entries:
            proj_path = os.path.join(projects_dir, item)
            if not os.path.isdir(proj_path) or item.startswith("."):
                continue

            manage_sh = os.path.join(proj_path, "manage.sh")
            has_manage = os.path.isfile(manage_sh) and os.access(manage_sh, os.X_OK)
            service_file = f"{item}.service"
            has_systemd = os.path.isfile(f"/etc/systemd/system/{service_file}") or os.path.isfile(os.path.join(proj_path, service_file))
            has_package_json = os.path.isfile(os.path.join(proj_path, "package.json"))

            # Loyihaning joriy holatini aniqlash
            status = "inactive"
            active_pids = []

            # 1. Systemctl orqali holatni tekshirish
            if has_systemd or has_manage:
                try:
                    res = subprocess.run(
                        ["systemctl", "is-active", item],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    svc_status = res.stdout.strip()
                    if svc_status in ("active", "activating"):
                        status = "active"
                    elif svc_status in ("failed", "deactivating"):
                        status = "failed"
                except Exception:
                    pass

            # 2. Agar systemd inactive bo'lsa, processlar orasidan qidiramiz
            if status != "active":
                try:
                    # Ushbu loyiha papkasidan ishlayotgan jarayonlarni qidirish
                    pgrep = subprocess.run(
                        ["pgrep", "-f", proj_path],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if pgrep.returncode == 0 and pgrep.stdout.strip():
                        pids = pgrep.stdout.strip().split()
                        active_pids = [p for p in pids if int(p) != os.getpid()]
                        if active_pids:
                            status = f"running (PID: {','.join(active_pids[:2])})"
                except Exception:
                    pass

            # Turi va tafsiloti
            if has_manage:
                proj_type = "manage"
                details = f"Script: manage.sh | Path: {proj_path}"
            elif has_systemd:
                proj_type = "systemd"
                details = f"Systemd: {service_file} | Path: {proj_path}"
            elif has_package_json:
                proj_type = "node"
                details = f"Node/Frontend App | Path: {proj_path}"
            else:
                proj_type = "app"
                details = f"Loyiha papkasi: {proj_path}"

            local_apps.append({
                "id": item,
                "name": item,
                "type": proj_type,
                "status": status,
                "path": proj_path,
                "has_manage": has_manage,
                "has_systemd": has_systemd,
                "details": details,
            })
    except Exception as e:
        logger.warning(f"Projects papkasini skanerlashda xatolik: {e}")

    return local_apps


def get_systemd_custom_services() -> list[dict]:
    """/etc/systemd/system/ papkasidagi maxsus loyiha servislari."""
    services = []
    service_dir = "/etc/systemd/system"
    if not os.path.exists(service_dir):
        return services

    # Ignored system services that shouldn't clutter the project list
    ignored_prefixes = ("multi-user.target", "getty", "systemd", "snap", "cloud", "ssh", "network")

    try:
        for fname in os.listdir(service_dir):
            if fname.endswith(".service") and not fname.startswith("."):
                if any(fname.startswith(p) for p in ignored_prefixes):
                    continue

                svc_name = fname.replace(".service", "")
                try:
                    res = subprocess.run(
                        ["systemctl", "is-active", fname],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    status = res.stdout.strip() or "inactive"
                except Exception:
                    status = "unknown"

                services.append({
                    "id": fname,
                    "name": svc_name,
                    "type": "systemd",
                    "status": status,
                    "details": f"Systemd Service ({fname})",
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
                    if "server-master-bot" in args_lower or ("main.py" in args_lower and "server-logs-bot" in args_lower):
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
                            "details": f"CPU: {cpu}% | RAM: {mem}% | CMD: {args[:55]}",
                        })
    except Exception as e:
        logger.warning(f"Alohida jarayonlarni o'qishda xato: {e}")

    return processes[:12]


def scan_all_projects() -> dict[str, list[dict]]:
    """Serverdagi barcha loyihalar va jarayonlarni toifalarga bo'lib aniqlash."""
    return {
        "apps": get_directory_projects(),
        "systemd": get_systemd_custom_services(),
        "pm2": get_pm2_projects(),
        "docker": get_docker_containers(),
        "processes": get_standalone_processes(),
    }


async def control_project(proj_type: str, proj_id: str, action: str) -> tuple[bool, str]:
    """
    Loyihani boshqarish (start, stop, restart, status).
    manage.sh, systemd, pm2, docker yoki processlar bilan ishlaydi.
    """
    allowed_actions = ("start", "stop", "restart", "status")
    if action not in allowed_actions:
        return False, f"⚠️ Noto'g'ri amal: «{action}». Ruxsat etilgan: {', '.join(allowed_actions)}"

    projects_dir = getattr(config, "PROJECTS_DIR", "/home/server/Projects")
    proj_path = os.path.join(projects_dir, proj_id)
    manage_sh = os.path.join(proj_path, "manage.sh")

    # 1. Agar loyihada manage.sh bo'lsa
    if proj_type in ("manage", "apps", "app") and os.path.isfile(manage_sh):
        cmd = ["bash", manage_sh, action]
        cwd = proj_path
    # 2. Agar systemd bo'lsa
    elif proj_type == "systemd" or os.path.isfile(f"/etc/systemd/system/{proj_id}.service") or os.path.isfile(f"/etc/systemd/system/{proj_id}"):
        svc_name = proj_id if proj_id.endswith(".service") else f"{proj_id}.service"
        cmd = ["sudo", "systemctl", action, svc_name]
        cwd = None
    # 3. PM2
    elif proj_type == "pm2":
        cmd = ["pm2", action, proj_id]
        cwd = None
    # 4. Docker
    elif proj_type == "docker":
        cmd = ["docker", action, proj_id]
        cwd = None
    # 5. Process (PID)
    elif proj_type == "process":
        try:
            pid = int(proj_id)
            if action in ("stop", "kill"):
                return await kill_process_by_pid(pid)
            elif action == "status":
                res = subprocess.run(["ps", "-p", str(pid), "-o", "pid,user,%cpu,%mem,stat,time,args"], capture_output=True, text=True)
                return True, f"📊 <b>PID {pid} holati:</b>\n<pre>{html.escape(res.stdout)}</pre>"
            else:
                return False, f"ℹ️ Oddiy jarayon (PID {pid}) uchun faqat «Stop» va «Status» qo'llab-quvvatlanadi."
        except ValueError:
            return False, "❌ Noto'g'ri PID raqami."
    else:
        # Oxirgi urinish: systemctl
        cmd = ["sudo", "systemctl", action, proj_id]
        cwd = None

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=12.0)
        except asyncio.TimeoutError:
            proc.kill()
            return True, f"⏳ <code>{' '.join(cmd)}</code> buyrug'i fonda bajarilmoqda..."

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        combined_output = out or err or f"Amal yakunlandi (Exit code: {proc.returncode})"
        if len(combined_output) > 1500:
            combined_output = combined_output[:1500] + "... [qisqartirildi]"

        if proc.returncode == 0:
            return True, f"✅ <b>{proj_id}</b> muvaffaqiyatli <code>{action}</code> qilindi!\n\n📋 <b>Natija:</b>\n<pre>{html.escape(combined_output)}</pre>"
        else:
            return False, f"⚠️ <b>{proj_id}</b> uchun <code>{action}</code> bajarildi, lekin chiqish kodi {proc.returncode}:\n<pre>{html.escape(combined_output)}</pre>"
    except Exception as e:
        return False, f"❌ Xatolik yuz berdi: {str(e)}"


async def get_project_logs(proj_type: str, proj_id: str, lines: int = 35) -> str:
    """Loyihaning so'nggi loglarini olish."""
    projects_dir = getattr(config, "PROJECTS_DIR", "/home/server/Projects")
    proj_path = os.path.join(projects_dir, proj_id)

    # 1. Agar Projects ichidagi loyiha bo'lsa
    if proj_type in ("manage", "apps", "app") or os.path.isdir(proj_path):
        # A) Systemd orqali tekshirish
        svc_name = proj_id.replace(".service", "")
        if os.path.isfile(f"/etc/systemd/system/{svc_name}.service"):
            cmd = ["journalctl", "-u", f"{svc_name}.service", "-n", str(lines), "--no-pager"]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass

        # B) Papkadagi *.log fayllarni qidirish
        log_files = glob.glob(os.path.join(proj_path, "*.log"))
        if log_files:
            latest_log = max(log_files, key=os.path.getmtime)
            try:
                res = subprocess.run(["tail", f"-n{lines}", latest_log], capture_output=True, text=True, timeout=3)
                if res.returncode == 0 and res.stdout.strip():
                    return f"Manba: {os.path.basename(latest_log)}\n" + res.stdout.strip()
            except Exception:
                pass

    # 2. Systemd
    if proj_type == "systemd" or proj_id.endswith(".service"):
        cmd = ["journalctl", "-u", proj_id, "-n", str(lines), "--no-pager"]
    # 3. PM2
    elif proj_type == "pm2":
        cmd = ["pm2", "logs", proj_id, "--lines", str(lines), "--nostream"]
    # 4. Docker
    elif proj_type == "docker":
        cmd = ["docker", "logs", "--tail", str(lines), proj_id]
    # 5. Process
    elif proj_type == "process":
        try:
            pid = int(proj_id)
            cwd_link = f"/proc/{pid}/cwd"
            if os.path.exists(cwd_link):
                real_cwd = os.path.realpath(cwd_link)
                logs = glob.glob(os.path.join(real_cwd, "*.log"))
                if logs:
                    res = subprocess.run(["tail", f"-n{lines}", logs[0]], capture_output=True, text=True, timeout=3)
                    return f"Manba: {logs[0]}\n" + res.stdout.strip()
            return f"ℹ️ PID {pid} jarayoni uchun log fayli topilmadi."
        except Exception as e:
            return f"❌ Loglarni topishda xatolik: {e}"
    else:
        cmd = ["journalctl", "-u", proj_id, "-n", str(lines), "--no-pager"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=6.0)
        except asyncio.TimeoutError:
            proc.kill()
            return "⏳ Loglarni olish vaqti tugadi (Timeout)."

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
        return False, "⛔️ Tizim asosiy jarayonini (PID 1) to'xtatish taqiqlangan!"

    if pid == own_pid:
        return False, "⛔️ Botning o'z jarayonini to'xtatishga ruxsat berilmaydi!"

    try:
        os.kill(pid, sig)
        await asyncio.sleep(0.5)
        try:
            os.kill(pid, 0)
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
