import base64
import json
import unittest
from urllib.parse import parse_qs
from tools.switchctl import encode_form, rsa_password, ssh_binding


class ProtocolTests(unittest.TestCase):
    def test_vendor_form_keeps_special_characters(self):
        obj = json.loads(encode_form({"username": "a&b", "password": "x+y/= z"}))
        self.assertEqual(len(obj), 1)
        fields = parse_qs(next(iter(obj)))
        self.assertEqual(fields, {"_ds": ["1"], "username": ["a&b"], "password": ["x+y/= z"], "_de": ["1"]})

    def test_rsa_password_pkcs1_padding(self):
        # Exponent 1 makes the padded message observable with a synthetic modulus.
        encoded = rsa_password('test', 'ff' * 128, exponent=1)
        message = base64.b64decode(encoded)
        self.assertEqual(len(message), 128)
        self.assertTrue(message.startswith(b'\0\x02'))
        self.assertTrue(message.endswith(b'\0test'))
        self.assertNotIn(0, message[2:-5])
        with self.assertRaises(ValueError):
            rsa_password('x' * 118, 'ff' * 128, exponent=1)

    def test_only_ssh_binding_is_selected(self):
        data = {"lists": [{"list": "default", "methods": ["lang('aaa','lblMethodLocal')"]}],
                "lines": [{"val": 2, "name": "lang('line','lblSsh')", "list": ""},
                          {"val": 3, "name": "lang('line','lblHttp')", "list": ""}]}
        self.assertEqual(ssh_binding(data), {"list_2": "default"})
        self.assertEqual(data['lines'][1]['list'], '')

    def test_nonlocal_default_authentication_is_refused(self):
        data = {"lists": [{"list": "default", "methods": ["radius"]}],
                "lines": [{"val": 2, "name": "lang('line','lblSsh')", "list": ""}]}
        with self.assertRaises(ValueError):
            ssh_binding(data)


if __name__ == '__main__':
    unittest.main()
