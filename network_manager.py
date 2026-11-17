import html
import logging
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)


def get_listening_ports() -> list[dict]:
    """
    Serverda hozirda eshitilayotgan (LISTEN) barcha portlar ro'yxatini olish.
    """
    ports = []
    out = ""

    # 1. ss orqali sinab ko'ramiz
    if shutil.which("ss"):
        try:
            res = subprocess.run(
                ["ss", "-tulpn", "-H"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            out = res.stdout
        except Exception as e:
            logger.warning(f"ss buyrug'ini bajarishda xato: {e}")

    # 2. netstat orqali fallback
    if not out and shutil.which("netstat"):
        try:
            res = subprocess.run(
                ["netstat", "-tulpn"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            out = res.stdout
        except Exception:
            pass

    if not out:
        return ports

    for line in out.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 5:
            continue

        proto = parts[0].lower()
        local_addr = parts[4] if len(parts) >= 5 else ""

        # Port va IP ni ajratamiz
        port_num = 0
        ip_addr = "*"
        if ":" in local_addr:
            ip_addr, _, port_str = local_addr.rpartition(":")
            try:
                port_num = int(port_str)
            except ValueError:
                continue

        # Jarayon nomi va PID ni ajratamiz (masalan: users:(("nginx",pid=123,fd=6)))
        proc_name = "-"
        pid_str = "-"
        users_part = " ".join(parts[5:]) if len(parts) > 5 else ""
        if "users:" in users_part or 'pid=' in users_part:
            match = re.search(r'"([^"]+)",pid=(\d+)', users_part)
            if match:
                proc_name = match.group(1)
                pid_str = match.group(2)
            else:
                p_match = re.search(r'pid=(\d+)', users_part)
                if p_match:
                    pid_str = p_match.group(1)
        elif "/" in parts[-1]:
            # netstat formati: 1234/nginx
            p_parts = parts[-1].split("/", 1)
            pid_str = p_parts[0]
            proc_name = p_parts[1]

        ports.append({
            "proto": proto,
            "ip": ip_addr or "*",
            "port": port_num,
            "pid": pid_str,
            "proc": proc_name,
        })

    # Portlar bo'yicha saralaymiz va unikal qilamiz
    seen = set()
    unique_ports = []
    for p in sorted(ports, key=lambda x: x["port"]):
        key = (p["proto"], p["port"])
        if key not in seen:
            seen.add(key)
            unique_ports.append(p)

    return unique_ports


def format_listening_ports() -> str:
    """Ochiq portlarni chiroyli HTML jadval ko'rinishida formatlash."""
    ports = get_listening_ports()
    if not ports:
        return (
            "🌐 <b>TARMOQ VA OCHIQ PORTLAR:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ Hozirda eshitilayotgan faol ochiq portlar topilmadi yoki huquq yetarli emas."
        )

    lines = [
        "🌐 <b>SERVERDA ESHITILAYOTGAN FAOL PORTLAR:</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "<code>PORT    PROTO  JARAYON (PID)</code>",
        "<code>-------------------------------</code>",
    ]

    for p in ports:
        port_s = f"{p['port']:<7}"
        proto_s = f"{p['proto'].upper():<6}"
        proc_info = f"{p['proc']} ({p['pid']})" if p['pid'] != "-" else p['proc']
        lines.append(f"<code>{port_s} {proto_s} {proc_info[:16]}</code>")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Jami ochiq portlar: <b>{len(ports)}</b> ta")
    return "\n".join(lines)
