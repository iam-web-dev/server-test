import asyncio
import html
import logging
import os
import re
import shlex

logger = logging.getLogger(__name__)

# Adminlar bo'yicha joriy ishchi papka (Current Working Directory)
_user_cwds: dict[int, str] = {}
DEFAULT_TIMEOUT = 60
OUTPUT_LIMIT_CHARS = 3800


def get_user_cwd(user_id: int | None = None) -> str:
    """Foydalanuvchining joriy papkasini olish."""
    if user_id and user_id in _user_cwds:
        cwd = _user_cwds[user_id]
        if os.path.exists(cwd) and os.path.isdir(cwd):
            return cwd
    return os.getcwd()


def reset_user_cwd(user_id: int):
    """Foydalanuvchi papkasini boshlang'ichga qaytarish."""
    if user_id in _user_cwds:
        del _user_cwds[user_id]


async def execute_command(
    command: str,
    user_id: int | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str, bytes | None, str]:
    """
    Linux buyrug'ini root huquqi bilan asinxron bajarish.
    
    Qaytaradi:
        (formatted_text, file_bytes_if_large, current_cwd)
    """
    clean_cmd = command.strip()
    cwd = get_user_cwd(user_id)

    if not clean_cmd:
        return ("⚠️ Bo'sh buyruq kiritildi.", None, cwd)

    # cd buyrug'ini tekshirish va kuzatish uchun bash skript wrap qilamiz
    # Marker yordamida buyruq yakunlanganidan keyingi joriy papkani aniqlaymiz
    cwd_marker = "__MASTER_BOT_CWD_MARKER__"
    wrapped_cmd = f"{clean_cmd}\n__RET=$?\necho '{cwd_marker}'\npwd\nexit $__RET"

    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    env["PATH"] = env.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")

    proc = None
    try:
        proc = await asyncio.create_subprocess_shell(
            wrapped_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            cwd=cwd,
            env=env,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        if proc:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
        return (
            f"⏱ <b>Xatolik: Buyruq vaqti tugadi (Timeout: {timeout}s)!</b>\n"
            f"Buyruq fonga o'tkazilmagan yoki qotib qolgan.",
            None,
            cwd,
        )
    except Exception as e:
        return (f"❌ <b>Buyruqni bajarishda xatolik:</b>\n<code>{html.escape(str(e))}</code>", None, cwd)

    raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
    raw_stderr = stderr_bytes.decode("utf-8", errors="replace")
    return_code = proc.returncode if proc else 0

    # CWD markerini tekshirib yangi papkani olamiz
    new_cwd = cwd
    actual_stdout = raw_stdout
    if cwd_marker in raw_stdout:
        parts = raw_stdout.split(cwd_marker)
        actual_stdout = parts[0].rstrip("\r\n")
        after_marker = parts[1].strip().split("\n")
        if after_marker and os.path.exists(after_marker[0].strip()):
            new_cwd = after_marker[0].strip()
            if user_id:
                _user_cwds[user_id] = new_cwd

    full_output = ""
    if actual_stdout:
        full_output += actual_stdout
    if raw_stderr:
        if full_output:
            full_output += "\n"
        full_output += f"[STDERR]\n{raw_stderr}"

    status_icon = "✅" if return_code == 0 else f"❌ (Exit code: {return_code})"

    # Katta hajmdagi chiqishni tekshirish
    if len(full_output) > OUTPUT_LIMIT_CHARS:
        file_bytes = full_output.encode("utf-8")
        preview = full_output[:1200]
        text = (
            f"💻 <b>BUYRUQ NATIJASI ({status_icon})</b>\n"
            f"📁 <b>Papka:</b> <code>{new_cwd}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<pre>{html.escape(preview)}\n... [Chiqish juda katta ({len(full_output)} belgi)]</pre>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 <i>To'liq natija .txt fayl sifatida biriktirildi.</i>"
        )
        return (text, file_bytes, new_cwd)
    else:
        content = full_output if full_output.strip() else "(Natija bo'sh / No output)"
        text = (
            f"💻 <b>BUYRUQ NATIJASI ({status_icon})</b>\n"
            f"📁 <b>Papka:</b> <code>{new_cwd}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<pre>{html.escape(content)}</pre>"
        )
        return (text, None, new_cwd)
