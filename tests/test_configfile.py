import unittest
from tools.configfile import enable_ssh, summarize


class ConfigTests(unittest.TestCase):
    def test_enable_preserves_unknown_lines_and_crlf(self):
        original = 'SYSTEM CONFIG FILE ::= BEGIN\r\n! comment\r\nunknown vendor thing\r\ninterface TE1\r\n eee\r\n!\r\n'
        changed = enable_ssh(original)
        self.assertEqual(changed, original.replace('BEGIN\r\n', 'BEGIN\r\nip ssh\r\n', 1))
        self.assertEqual(enable_ssh(changed), changed)

    def test_replace_only_global_plain_ssh_toggle(self):
        original = 'SYSTEM CONFIG FILE ::= BEGIN\nno ip ssh\nno ip ssh v1\ninterface TE1\n description "ip ssh"\n'
        changed = enable_ssh(original)
        self.assertEqual(changed, 'SYSTEM CONFIG FILE ::= BEGIN\nip ssh\nno ip ssh v1\ninterface TE1\n description "ip ssh"\n')

    def test_missing_header_is_refused(self):
        with self.assertRaises(ValueError):
            enable_ssh('hostname test\n')

    def test_summary_does_not_include_passwords_or_hashes(self):
        text = 'SYSTEM CONFIG FILE ::= BEGIN\n! System Version: v1.1.1.34\nusername "admin" secret encrypted DO_NOT_PRINT\nsystem name "Lab-Switch"\ninterface vlan1\n ip address 192.0.2.2/24\nip ssh\n'
        self.assertEqual(summarize(text), {"version": "v1.1.1.34", "hostname": "Lab-Switch", "ssh_enabled": True})


if __name__ == '__main__':
    unittest.main()
