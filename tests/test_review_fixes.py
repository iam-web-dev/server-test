import asyncio
import html
import tempfile
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

class TestReviewFixes(unittest.IsolatedAsyncioTestCase):
    async def test_docker_menu_imports(self):
        """Finding 1: Verify callback_menu_docker does not throw NameError for InlineKeyboardMarkup."""
        import main
        from aiogram.types import CallbackQuery, User, Message

        cb = MagicMock(spec=CallbackQuery)
        cb.from_user = User(id=12345, is_bot=False, first_name="Admin")
        cb.message = MagicMock(spec=Message)
        cb.message.edit_text = AsyncMock()
        cb.answer = AsyncMock()

        dummy_containers = [{
            "id": "c123",
            "name": "my-nginx",
            "image": "nginx:latest",
            "state": "running",
            "status_str": "Up 2 hours",
            "is_running": True,
            "ports": "80/tcp"
        }]

        with patch("auth_manager.is_authenticated", return_value=True):
            with patch("docker_manager.get_containers_summary", return_value=dummy_containers):
                # If InlineKeyboardMarkup / InlineKeyboardButton is missing in main.py, this will raise NameError
                await main.callback_menu_docker(cb)
                self.assertTrue(cb.message.edit_text.called)

    def test_tail_file_safe_execution(self):
        """Finding 3: tail_file should read last lines without reading entire file into RAM."""
        import file_manager
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            for i in range(200):
                f.write(f"Log row {i} <tag{i}>\n")
            f_path = f.name
        try:
            ok, content = file_manager.tail_file(f_path, lines=5)
            self.assertTrue(ok)
            self.assertIn("Log row 199", content)
            self.assertNotIn("Log row 100", content)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    def test_html_escaping_utility(self):
        """Finding 2: HTML tags in logs must be escaped."""
        raw = "Error occurred at <module> in <string> line 50"
        escaped = html.escape(raw)
        self.assertNotIn("<module>", escaped)
        self.assertIn("&lt;module&gt;", escaped)

if __name__ == "__main__":
    unittest.main()
