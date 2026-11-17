# SysAdmin & DevOps Master Tool Telegram Boti Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the server monitoring bot into a full-featured SysAdmin & DevOps Master Tool on Debian 13 minimal with root-level terminal execution, project/process supervision, autostart on boot with Telegram boot alerts, network inspection, and system management.

**Architecture:** A modular asynchronous architecture in Python using `aiogram 3` and `asyncio.subprocess`. Subsystems include: `terminal_manager` for non-blocking root shell execution and output pagination, `project_manager` for detecting and controlling PM2/Docker/Systemd/Python apps, `docker_manager` for container operations, `network_manager` for listening port discovery, `file_manager` for remote log tailing and cache cleanup, and `boot_notifier` tied into Debian 13 `systemd` autostart.

**Tech Stack:** Python 3.11+, aiogram 3.x, systemd, asyncio, Debian 13 (Trixie) Minimal coreutils/iproute2.

**Spec:** [docs/superpowers/specs/2026-11-17-sysadmin-master-bot-design.md](file:///home/iamwebdev/Projects/Bots/docs/superpowers/specs/2026-11-17-sysadmin-master-bot-design.md)

## Global Constraints

- OS Target: Debian 13 (Trixie) Minimal, no required pre-installed `sudo`.
- Privilege: Systemd service runs directly as `User=root` for unrestricted host administration.
- Execution environment: All commands executed via `asyncio.create_subprocess_shell` must include `DEBIAN_FRONTEND=noninteractive` and `stdin=asyncio.subprocess.DEVNULL`.
- Output Limit: Telegram message limit is 4096 characters; outputs > 3800 chars must be streamed as `BufferedInputFile` (.txt document).
- Security: Every handler and callback must enforce `auth_manager.is_authenticated(user_id)`.

## Review Focus

1. Command timeouts: Long-running shell commands (e.g. `ping`, `top`, interactive prompts) must terminate after 60s without blocking the bot event loop.
2. Output escaping: Shell stdout/stderr containing `<` or `>` must be HTML-escaped before inserting into Telegram `<pre>` tags.
3. Empty command / Missing file: `/sh` with empty string or `/getfile` on nonexistent/forbidden file must return clear error message rather than crashing.
4. Duplicate boot alert: Bot restarts without host reboot must not send duplicate "SERVER YOQILDI" alerts; only change of `/proc/sys/kernel/random/boot_id` triggers boot notification.
5. Large log tailing: Requesting logs for a high-volume app must cap lines safely to avoid memory explosion.

---

### Task 1: Terminal Execution Module (`terminal_manager.py`)

**Files:**
- Create: `terminal_manager.py`
- Create: `tests/test_terminal_manager.py`

**Interfaces:**
- Produces:
  - `execute_command(command: str, user_id: int | None = None, timeout: int = 60) -> tuple[str, bytes | None, str]`
    Returns `(formatted_text, file_bytes_if_large, current_cwd)`
  - `get_user_cwd(user_id: int) -> str`
  - `reset_user_cwd(user_id: int)`

- [ ] **Step 1: Write unit tests in `tests/test_terminal_manager.py`**

```python
import pytest
import os
import asyncio
from terminal_manager import execute_command, get_user_cwd, reset_user_cwd

@pytest.mark.asyncio
async def test_execute_simple_command():
    text, file_data, cwd = await execute_command("echo 'Hello Master'", user_id=123)
    assert "Hello Master" in text
    assert file_data is None

@pytest.mark.asyncio
async def test_execute_cd_tracking():
    reset_user_cwd(123)
    initial_cwd = get_user_cwd(123)
    text, file_data, new_cwd = await execute_command("cd /tmp && pwd", user_id=123)
    assert get_user_cwd(123) == "/tmp"

@pytest.mark.asyncio
async def test_execute_large_output():
    # Produce > 4000 characters
    cmd = "python3 -c 'print(\"A\" * 5000)'"
    text, file_data, cwd = await execute_command(cmd, user_id=123)
    assert file_data is not None
    assert len(file_data) >= 5000

@pytest.mark.asyncio
async def test_execute_timeout():
    text, file_data, cwd = await execute_command("sleep 5", user_id=123, timeout=1)
    assert "Timeout" in text or "vaqt tugadi" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_terminal_manager.py -v`  
Expected: ModuleNotFoundError: No module named 'terminal_manager'

- [ ] **Step 3: Implement `terminal_manager.py`**

Implement `execute_command` with:
- Per-user CWD dict: `user_cwds: dict[int, str] = {}`
- Regex to detect `cd <dir>` and update CWD.
- `asyncio.create_subprocess_shell` with `env={"DEBIAN_FRONTEND": "noninteractive", "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")}`.
- `asyncio.wait_for(..., timeout=timeout)`.
- If stdout + stderr length > 3800 bytes, prepare UTF-8 bytes for Telegram document file upload.
- HTML-escaping `html.escape()` for terminal outputs rendered inside `<pre>` tags.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_terminal_manager.py -v`  
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add terminal_manager.py tests/test_terminal_manager.py
git commit -m "feat: add root terminal execution manager with cwd tracking and output paging"
```

---

### Task 2: Boot Notifier & Systemd Autostart (`boot_notifier.py` and `install_service.sh`)

**Files:**
- Create: `boot_notifier.py`
- Create: `install_service.sh`
- Create: `server-master-bot.service`
- Create: `tests/test_boot_notifier.py`

**Interfaces:**
- Produces:
  - `get_current_boot_id() -> str`
  - `get_network_ips() -> dict[str, str]` (keys: `public`, `local`)
  - `is_new_boot() -> bool`
  - `mark_boot_notified(boot_id: str)`
  - `format_boot_alert() -> str`
  - `check_boot_and_notify(bot: Bot) -> bool`

- [ ] **Step 1: Write unit tests in `tests/test_boot_notifier.py`**

```python
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import boot_notifier

def test_get_current_boot_id():
    boot_id = boot_notifier.get_current_boot_id()
    assert isinstance(boot_id, str)
    assert len(boot_id) > 0

def test_is_new_boot_logic(tmp_path):
    test_state_file = tmp_path / "system_state.json"
    with patch("boot_notifier.STATE_FILE", str(test_state_file)):
        # Initially no state file, so is_new_boot should be True
        assert boot_notifier.is_new_boot() is True
        current_id = boot_notifier.get_current_boot_id()
        boot_notifier.mark_boot_notified(current_id)
        # Now it shouldn't be a new boot
        assert boot_notifier.is_new_boot() is False

def test_format_boot_alert():
    text = boot_notifier.format_boot_alert()
    assert "SERVER ISHGA TUSHDI" in text or "SERVER YOQILDI" in text
    assert "Uptime" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_boot_notifier.py -v`  
Expected: ModuleNotFoundError: No module named 'boot_notifier'

- [ ] **Step 3: Implement `boot_notifier.py`, `install_service.sh`, and `server-master-bot.service`**

Implement `boot_notifier.py`:
- Reads `/proc/sys/kernel/random/boot_id` (fallback to uptime calculation).
- Persists state in `data/system_state.json`.
- `get_network_ips()`: reads `hostname -I` for local, and quick fallback check (`curl -s --connect-timeout 2 ifconfig.me`) for public.
- Formats message with hostname, IPs, uptime, kernel version.
- `check_boot_and_notify`: broadcast to all active admins if `is_new_boot()`.

Create `server-master-bot.service`:
- Unit file with `User=root`, `Restart=always`, `RestartSec=5`.

Create `install_service.sh`:
- Detects current directory and `.venv/bin/python`.
- Generates `/etc/systemd/system/server-master-bot.service`.
- Runs `systemctl daemon-reload` and `systemctl enable --now server-master-bot`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_boot_notifier.py -v`  
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add boot_notifier.py install_service.sh server-master-bot.service tests/test_boot_notifier.py
git commit -m "feat: add boot notifier and Debian 13 systemd autostart installer"
```

---

### Task 3: Project & Process Supervision (`project_manager.py`)

**Files:**
- Create: `project_manager.py`
- Create: `tests/test_project_manager.py`

**Interfaces:**
- Produces:
  - `scan_all_projects() -> dict[str, list[dict]]`
    (Categories: `systemd`, `pm2`, `docker`, `python_node`)
  - `control_project(proj_type: str, proj_id: str, action: str) -> tuple[bool, str]`
    (`action` in `restart`, `stop`, `start`)
  - `get_project_logs(proj_type: str, proj_id: str, lines: int = 40) -> str`
  - `kill_process_by_pid(pid: int, signal: int = 15) -> tuple[bool, str]`

- [ ] **Step 1: Write unit tests in `tests/test_project_manager.py`**

```python
import pytest
from unittest.mock import patch, MagicMock
import project_manager

def test_scan_all_projects_structure():
    projects = project_manager.scan_all_projects()
    assert "systemd" in projects
    assert "pm2" in projects
    assert "docker" in projects
    assert "processes" in projects

@pytest.mark.asyncio
async def test_kill_process_validation():
    # Attempting to kill PID 1 or negative should be rejected
    ok, msg = await project_manager.kill_process_by_pid(1)
    assert ok is False
    assert "xavfli" in msg.lower() or "ruxsat" in msg.lower()

@pytest.mark.asyncio
async def test_control_project_invalid_action():
    ok, msg = await project_manager.control_project("systemd", "nginx", "invalid_action")
    assert ok is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_project_manager.py -v`  
Expected: ModuleNotFoundError: No module named 'project_manager'

- [ ] **Step 3: Implement `project_manager.py`**

- `scan_all_projects()`:
  - Scans PM2 apps if `pm2` command is available (`pm2 jlist`).
  - Scans Docker containers if `docker` command is available (`docker ps -a --format '{{json .}}'`).
  - Scans systemd app services from `/etc/systemd/system/` (ignoring system targets and `.wants`).
  - Scans unmanaged Python/Node processes from `ps -eo pid,user,%cpu,%mem,args` (filtering out the bot's own PID).
- `control_project(proj_type, proj_id, action)`:
  - For systemd: `systemctl {action} {proj_id}`.
  - For pm2: `pm2 {action} {proj_id}`.
  - For docker: `docker {action} {proj_id}`.
- `kill_process_by_pid(pid, sig)`:
  - Protects PID 1, PID of current bot, and PID of system init daemons.
  - Sends `os.kill(pid, sig)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_project_manager.py -v`  
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add project_manager.py tests/test_project_manager.py
git commit -m "feat: add project manager for systemd, pm2, docker and process lifecycle"
```

---

### Task 4: Docker & Network Managers (`docker_manager.py` and `network_manager.py`)

**Files:**
- Create: `docker_manager.py`
- Create: `network_manager.py`
- Create: `tests/test_network_docker.py`

**Interfaces:**
- `docker_manager`:
  - `is_docker_installed() -> bool`
  - `get_containers_summary() -> list[dict]`
  - `get_container_logs(container_id: str, tail: int = 50) -> str`
- `network_manager`:
  - `get_listening_ports() -> list[dict]` (port, proto, pid, program, address)
  - `format_listening_ports() -> str`
  - `get_active_connections_count() -> dict[str, int]`

- [ ] **Step 1: Write unit tests in `tests/test_network_docker.py`**

```python
import pytest
import network_manager
import docker_manager

def test_network_manager_ports():
    ports = network_manager.get_listening_ports()
    assert isinstance(ports, list)
    text = network_manager.format_listening_ports()
    assert isinstance(text, str)
    assert "PORT" in text or "Eshitilayotgan" in text or "port" in text.lower()

def test_docker_installed_check():
    res = docker_manager.is_docker_installed()
    assert isinstance(res, bool)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_network_docker.py -v`  
Expected: ModuleNotFoundError: No module named 'network_manager'

- [ ] **Step 3: Implement `network_manager.py` and `docker_manager.py`**

- `network_manager.py`: Runs `ss -tulpn` or parses `/proc/net/tcp` if `ss` unavailable. Parses port numbers, listening IP (`0.0.0.0` or `127.0.0.1`), process name. Formats clean Telegram monospace table.
- `docker_manager.py`: Executes `docker` CLI commands asynchronously with fallback handling when Docker is not installed or daemon is stopped.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_network_docker.py -v`  
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add docker_manager.py network_manager.py tests/test_network_docker.py
git commit -m "feat: add docker manager and network port inspection manager"
```

---

### Task 5: File & System Clean Manager (`file_manager.py`)

**Files:**
- Create: `file_manager.py`
- Create: `tests/test_file_manager.py`

**Interfaces:**
- Produces:
  - `tail_file(filepath: str, lines: int = 40) -> tuple[bool, str]`
  - `prepare_file_for_download(filepath: str, max_size_mb: int = 45) -> tuple[bool, str, bytes | None, str]`
  - `clean_system_cache() -> dict[str, str]`

- [ ] **Step 1: Write unit tests in `tests/test_file_manager.py`**

```python
import pytest
import tempfile
import os
import file_manager

def test_tail_file():
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        for i in range(100):
            f.write(f"Line {i}\n")
        f_path = f.name
    try:
        ok, content = file_manager.tail_file(f_path, lines=10)
        assert ok is True
        assert "Line 99" in content
        assert "Line 0" not in content
    finally:
        os.remove(f_path)

def test_prepare_file_nonexistent():
    ok, msg, data, filename = file_manager.prepare_file_for_download("/non/existent/file.txt")
    assert ok is False
    assert "topilmadi" in msg.lower() or "not found" in msg.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_file_manager.py -v`  
Expected: ModuleNotFoundError: No module named 'file_manager'

- [ ] **Step 3: Implement `file_manager.py`**

- `tail_file(filepath, lines)`: reads last `lines` from file using seek or `tail -n` command.
- `prepare_file_for_download(filepath, max_size_mb=45)`: checks existence and size limit (Telegram bot upload limit is 50MB); returns bytes for `BufferedInputFile`.
- `clean_system_cache()`: runs `journalctl --vacuum-time=2d`, `apt-get clean`, `docker system prune -f` asynchronously and reports cleaned status / freed disk space.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_file_manager.py -v`  
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add file_manager.py tests/test_file_manager.py
git commit -m "feat: add file manager for remote download, tail and system cache cleanup"
```

---

### Task 6: UI & Keyboards Expansion (`keyboards.py`)

**Files:**
- Modify: `keyboards.py`

**Interfaces:**
- Produces:
  - Updated `admin_main_keyboard` with:
    `[ 📊 Server Statlari ] [ ⚡️ Top Jarayonlar ]`
    `[ 🚀 Loyihalar & Saytlar ] [ 💻 Terminal & Shell ]`
    `[ ⚙️ Servislar & Docker ] [ 🌐 Tarmoq & Portlar ]`
    `[ 📜 Loglar & Tozalash ] [ 🔔 Tizim Holati ]`
    `[ 🚪 Chiqish ]`
  - `get_projects_inline_keyboard(projects: dict)`
  - `get_project_action_keyboard(proj_type: str, proj_id: str)`
  - `get_terminal_inline_keyboard()`
  - `get_network_inline_keyboard()`
  - `get_clean_confirm_keyboard()`

- [ ] **Step 1: Write keyboard unit test in `tests/test_keyboards.py`**

```python
import keyboards
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup

def test_admin_main_keyboard_buttons():
    kb = keyboards.admin_main_keyboard
    all_texts = [btn.text for row in kb.keyboard for btn in row]
    assert "🚀 Loyihalar & Saytlar" in all_texts
    assert "💻 Terminal & Shell" in all_texts
    assert "🌐 Tarmoq & Portlar" in all_texts
    assert "📜 Loglar & Tozalash" in all_texts

def test_projects_keyboard():
    dummy = {
        "systemd": [{"name": "my-api", "status": "active"}],
        "pm2": [],
        "docker": [],
        "processes": []
    }
    ikb = keyboards.get_projects_inline_keyboard(dummy)
    assert isinstance(ikb, InlineKeyboardMarkup)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_keyboards.py -v`  
Expected: AssertionError

- [ ] **Step 3: Update `keyboards.py`**

Add all new menus and inline keyboards with clear emoji indicators and callback actions.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_keyboards.py -v`  
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add keyboards.py tests/test_keyboards.py
git commit -m "feat: update reply and inline keyboards for master tool features"
```

---

### Task 7: Master Tool Handlers & Background Integration (`main.py` & `background_tasks.py`)

**Files:**
- Modify: `main.py`
- Modify: `background_tasks.py`

**Interfaces:**
- Connects all modules to aiogram 3 dispatcher:
  - FSM State `TerminalStates.active_session`
  - `/sh <cmd>`, `/cmd <cmd>`, `/getfile <path>`, `/tail <path>`
  - Handlers for `🚀 Loyihalar & Saytlar`, `💻 Terminal & Shell`, `🌐 Tarmoq & Portlar`, `📜 Loglar & Tozalash`
  - Callback queries: `proj_act_*`, `kill_pid_*`, `term_quick_*`, `net_refresh`, `clean_cache_confirm`
  - In `background_tasks.py`: call `boot_notifier.check_boot_and_notify(bot)` on worker startup.

- [ ] **Step 1: Write integration test for dispatching in `tests/test_main_integration.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Chat, User
import main

@pytest.mark.asyncio
async def test_auth_check_in_terminal_handler():
    # Unauthenticated user should be denied
    msg = MagicMock(spec=Message)
    msg.from_user = User(id=9999999, is_bot=False, first_name="Hacker")
    msg.text = "/sh whoami"
    msg.answer = AsyncMock()
    with patch("auth_manager.is_authenticated", return_value=False):
        await main.terminal_command_handler(msg)
        assert msg.answer.called
        assert "ruxsat" in msg.answer.call_args[0][0].lower() or "login" in msg.answer.call_args[0][0].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main_integration.py -v`  
Expected: AttributeError or test failure

- [ ] **Step 3: Implement new handlers in `main.py` and hook into `background_tasks.py`**

- Connect terminal execution with output file upload (`BufferedInputFile`) when large.
- Connect project list renderer and callbacks for start/stop/restart/logs/kill.
- Connect network ports viewer.
- Connect file downloader (`/getfile`).
- Connect cache cleaner with confirmation button.
- Integrate `boot_notifier.check_boot_and_notify(bot)` into `background_tasks.start_server_monitoring(bot)`.

- [ ] **Step 4: Run all tests in test suite**

Run: `pytest tests/ -v`  
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add main.py background_tasks.py tests/test_main_integration.py
git commit -m "feat: integrate master tool handlers, terminal FSM, and boot notifier"
```

---

### Task 8: Verification, Documentation & End-to-End Test

**Files:**
- Modify: `README.md`
- Create: `tests/test_e2e_suite.py`

- [ ] **Step 1: Run end-to-end regression and sanity tests**

Run: `pytest tests/ -v`  
Expected: All tests PASS.

- [ ] **Step 2: Update `README.md`**

Document all new Master Tool capabilities:
- Root terminal execution (`/sh <cmd>` and interactive terminal).
- Project supervision (PM2, Docker, Systemd, Python/Node).
- Debian 13 minimal autostart setup (`./install_service.sh`).
- Boot alert notification.
- Port inspection and system cleanup.

- [ ] **Step 3: Commit**

```bash
git add README.md tests/test_e2e_suite.py
git commit -m "docs: update README with Master Tool documentation and instructions"
```
