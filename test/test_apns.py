# coding: utf-8
import time
import unittest

import os, sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, ROOT_DIR + '/src')

from apns import APNSNotification, APNS

TEST_DEVICE_TOKEN = None

class TestNotification(unittest.TestCase):
    def setUp(self):
        self.device_token = TEST_DEVICE_TOKEN

    def test_compose_message(self):
        notif = APNSNotification(
            device_token=self.device_token,
            alert='foobar',
            badge=1,
            sound='default',
            )
        import struct
        command, identifier, expiry, token_len, token, payload_len, payload = \
                struct.unpack('!BIIH32sH%ds' % len(notif.get_payload()), str(notif))
        self.assertEquals(command, 1)
        self.assertEquals(identifier, 0)
        self.assertTrue(expiry > 0)
        self.assertEquals(token_len, 32)
        self.assertEquals(payload_len, len(notif.get_payload()))
        self.assertEquals(payload, notif.get_payload())

    def test_payload_should_not_contain_unused_notification_fields(self):
        notif = APNSNotification(
            device_token=self.device_token,
            alert='foobar',
            )
        import json
        payload = json.loads(notif.get_payload())
        self.assertNotIn("badge", payload["aps"]) 
        self.assertNotIn("sound", payload["aps"])


class TestService(unittest.TestCase):
    def setUp(self):
        self.device_token = TEST_DEVICE_TOKEN
        self.notif = APNSNotification(
            device_token=self.device_token,
            alert='foobar',
            badge=1,
            sound='default',
            )
        self.apns = APNS(ROOT_DIR+'/config/apns_cert.development.pem')
        self.apns.start()
        self.assertTrue(self.apns.wait_status(30))

    def test_basic(self):
        print 'Connected', self.apns.get_status()
        self.apns.stop()

    def test_send_notification(self):
        self.apns.put_notification(self.notif)
        time.sleep(1)

    def test_send_error_notification(self):
        self.notif.token = 'abcd'
        self.apns.put_notification(self.notif)
        import time
        time.sleep(1)
        self.assertTrue(self.apns.get_last_error())
        self.assertEqual(self.apns.get_last_error().status_code, 8)

    def test_feedback(self):
        item = self.apns.get_feedback(timeout=5)
        print item


if __name__ == '__main__':
    unittest.main()

