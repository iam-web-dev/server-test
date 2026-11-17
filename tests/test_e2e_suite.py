import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import boot_notifier
import docker_manager
import file_manager
import keyboards
import network_manager
import project_manager
import server_monitor
import terminal_manager


class TestE2ESuite(unittest.IsolatedAsyncioTestCase):
    async def test_full_pipeline_terminal_and_cwd(self):
        # 1. Execute terminal command
        text, file_bytes, cwd = await terminal_manager.execute_command("echo 'E2E_OK'", user_id=999)
        self.assertIn("E2E_OK", text)
        self.assertIsNone(file_bytes)

    async def test_full_pipeline_projects_scanner(self):
        # 2. Project scanner returns valid dict structure
        projs = project_manager.scan_all_projects()
        self.assertIn("systemd", projs)
        self.assertIn("pm2", projs)
        self.assertIn("docker", projs)
        self.assertIn("processes", projs)

    def test_full_pipeline_network_ports(self):
        # 3. Ports table formatting
        text = network_manager.format_listening_ports()
        self.assertTrue(len(text) > 0)

    def test_full_pipeline_boot_alert(self):
        # 4. Boot alert text formatting
        alert_text = boot_notifier.format_boot_alert()
        self.assertIn("SERVER", alert_text)
        self.assertIn("Uptime", alert_text)

    def test_full_pipeline_keyboards_integration(self):
        # 5. Admin main keyboard has all master tool options
        all_buttons = [btn.text for row in keyboards.admin_main_keyboard.keyboard for btn in row]
        required_buttons = [
            "📊 Server Statlari",
            "⚡️ Top Jarayonlar",
            "🚀 Loyihalar & Saytlar",
            "💻 Terminal & Shell",
            "⚙️ Servislar & Docker",
            "🌐 Tarmoq & Portlar",
            "📜 Loglar & Tozalash",
            "🔔 Tizim Holati",
            "🚪 Chiqish",
        ]
        for btn in required_buttons:
            self.assertIn(btn, all_buttons)

    async def test_full_pipeline_cache_clean(self):
        # 6. Cache cleanup function executes safely
        res = await file_manager.clean_system_cache()
        self.assertEqual(res["status"], "success")
        self.assertIn("details", res)


if __name__ == "__main__":
    unittest.main()
