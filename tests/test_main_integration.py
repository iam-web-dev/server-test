import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User

class TestMainIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_auth_check_in_terminal_handler(self):
        import main
        msg = MagicMock(spec=Message)
        msg.from_user = User(id=9999999, is_bot=False, first_name="Hacker")
        msg.text = "/sh whoami"
        msg.answer = AsyncMock()

        with patch("auth_manager.is_authenticated", return_value=False):
            await main.terminal_command_handler(msg)
            self.assertTrue(msg.answer.called)
            answer_text = msg.answer.call_args[0][0].lower()
            self.assertTrue("ruxsat" in answer_text or "login" in answer_text)

    async def test_boot_check_in_background_tasks(self):
        import background_tasks
        mock_bot = MagicMock()
        with patch("boot_notifier.check_boot_and_notify", new_callable=AsyncMock) as mock_boot:
            mock_boot.return_value = True
            with patch("background_tasks.check_services_and_alert", new_callable=AsyncMock):
                with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
                    try:
                        await background_tasks.start_server_monitoring(mock_bot)
                    except asyncio.CancelledError:
                        pass
            self.assertTrue(mock_boot.called)

if __name__ == "__main__":
    unittest.main()
