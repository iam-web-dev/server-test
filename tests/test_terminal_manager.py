import unittest
import os
import asyncio

class TestTerminalManager(unittest.IsolatedAsyncioTestCase):
    async def test_execute_simple_command(self):
        from terminal_manager import execute_command
        text, file_data, cwd = await execute_command("echo 'Hello Master'", user_id=123)
        self.assertIn("Hello Master", text)
        self.assertIsNone(file_data)

    async def test_execute_cd_tracking(self):
        from terminal_manager import execute_command, get_user_cwd, reset_user_cwd
        reset_user_cwd(123)
        text, file_data, new_cwd = await execute_command("cd /tmp && pwd", user_id=123)
        self.assertEqual(get_user_cwd(123), "/tmp")

    async def test_execute_large_output(self):
        from terminal_manager import execute_command
        # Output > 3800 bytes
        cmd = "python3 -c 'print(\"A\" * 5000)'"
        text, file_data, cwd = await execute_command(cmd, user_id=123)
        self.assertIsNotNone(file_data)
        self.assertGreaterEqual(len(file_data), 5000)

    async def test_execute_timeout(self):
        from terminal_manager import execute_command
        text, file_data, cwd = await execute_command("sleep 5", user_id=123, timeout=1)
        self.assertTrue("timeout" in text.lower() or "vaqt tugadi" in text.lower())

if __name__ == "__main__":
    unittest.main()
