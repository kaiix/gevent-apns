from gevent import monkey
monkey.patch_all()

import socket
import ssl
import time
import struct
import json

import gevent
from gevent.queue import Queue, Empty
from gevent import Timeout

import logging
import sys

logging.basicConfig(
    format="%(asctime)s %(levelname) 7s %(module)s: %(message)s",
    stream=sys.stdout,
    level=logging.DEBUG)
logger = logging.getLogger(__file__)


class APNSNotification(object):
    def __init__(self, device_token, alert, badge=None, sound=None, extras=None,
                 identifier=0, expiry=None):
        self.token = device_token.decode('hex')
        self.alert = alert
        if len(self.token) != 32:
            raise ValueError
        if not isinstance(alert, basestring):
            raise ValueError

        self.badge = badge
        self.sound = sound
        self.extras = extras

        # fields for enhanced format
        self.identifier = identifier
        if not expiry:
            self.expiry = long(time.time() + 86400)  # expired the next day

    def _pack(self):
        """ Enhanced notification format

        message format is, |COMMAND|IDENTIFIER|EXPIRY|TOKENLEN|TOKEN|PAYLOADLEN|PAYLOAD|
        """
        payload = self.get_payload()
        result = struct.pack('!BIIH32sH%ds' % len(payload),
                             1, self.identifier, self.expiry, 32, self.token,
                             len(payload), payload)
        return result

    def get_payload(self):
        """ JSON object with max size of 256 bytes.
        
        payload = {
            aps : {
                alert: "message" || {
                    body: "message",
                    action-loc-key: "button" || None,
                    loc-key: "key",
                    loc-args: ["arg"],
                    launch-image: image_file_name_app_bundle,
                },
                badge: 1,
                sound: sound_file_name_in_app_bundle
            },
            ...
        }
        """
        payload = {"aps": {}}
        if self.alert:
            payload["aps"]["alert"] = self.alert
        if self.badge:
            payload["aps"]["badge"] = self.badge
        if self.sound:
            payload["aps"]["sound"] = self.sound
        if self.extras:
            payload.update(self.extras)
        return json.dumps(payload)

    def __str__(self):
        return self._pack()


class APNSError(Exception):
    APNS_ERROR_CODES = {
        0: "No errors encountered",
        1: "Processing error",
        2: "Missing device token",
        3: "Missing topic",
        4: "Missing payload",
        5: "Invalid token size",
        6: "Invalid topic size",
        7: "Invalid payload size",
        8: "Invalid token",
        255: "None (unknown)",
        -1: "Malformed error-response packet"
    }

    def __init__(self, error_response):
        try:
            self.command, self.status_code, self.identifier = \
                    struct.unpack("!BBI", error_response)
        except struct.error:
            self.status_code = -1
        self.message = self.APNS_ERROR_CODES.get(self.status_code, 255)


class APNS(object):
    SANDBOX_PUSH_SERVER_ADDRESS = ("gateway.sandbox.push.apple.com", 2195)
    SANDBOX_FEEDBACK_SERVER_ADDRESS = ("feedback.sandbox.push.apple.com", 2196)

    PRODUCTION_PUSH_SERVER_ADDRESS = ("gateway.push.apple.com", 2195)
    PRODUCTION_FEEDBACK_SERVER_ADDRESS = ("feedback.push.apple.com", 2196)

    def __init__(self, certificate, sandbox=True, timeout=None):
        self.certificate = certificate
        if sandbox:
            self._push_server = self.SANDBOX_PUSH_SERVER_ADDRESS
            self._feedback_server = self.SANDBOX_FEEDBACK_SERVER_ADDRESS
        else:
            self._push_server = self.PRODUCTION_PUSH_SERVER_ADDRESS
            self._feedback_server = self.PRODUCTION_FEEDBACK_SERVER_ADDRESS
        self._conn = None
        self._connected = False
        self._push_queue = Queue()
        self._push_service = None
        self._read_error_service = None
        self._last_error = None
        self._feedback_service = None
        self._feedback_queue = Queue()

    def start(self):
        if self._push_service is None:
            self._push_service = gevent.spawn(self._start_service)

    def _start_service(self):
        try:
            while True:
                logger.info("Push service starting ...")
                self._conn = self._connect(self._push_server)
                self._read_error_service = gevent.spawn(self._read_error, self._conn)
                self._connected = True

                while self._connected:
                    notif = self._push_queue.get()
                    try:
                        self._conn.send(str(notif))
                    except Exception as e:
                        #TODO: set last_error
                        logger.error(e)
                        self._push_queue.put(notif)
                        self._connected = False
                self._conn.close()
                self._conn = None

                self._push_service = None
                self._read_error_service = None
        except gevent.GreenletExit:
            logger.info("Push service exit")

    def _connect(self, server):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        wrapped = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv3,
                                  certfile=self.certificate)
        wrapped.connect_ex(server)
        return wrapped

    def _read_error(self, conn):
        logger.info("Read error service starting ...")
        try:
            while self._connected:
                response = conn.read(1+1+4)
                self._connected = False
                if not response:  # remote socket closed, and response will be ''
                    break
                self._last_error = APNSError(response)
                logger.warn("error response: `{}`".format(self._last_error.message))
                gevent.sleep(0)
        except gevent.GreenletExit:
            logger.info("Read error service exit")
 
    def _feedback(self):
        logger.info("Feedback service starting ...")
        try:
            conn = self._connect(self._feedback_server)
            while True:
                response = conn.read(4+2+32)
                if not response:  # remote socket closed, and response will be ''
                    break
                try:
                    payload = struct.unpack("!IH32s", response)
                    self._feedback_queue.put((payload[0], payload[2]))
                except struct.error:
                    pass
            conn.close()
            self._feedback_service = None
        except gevent.GreenletExit:
            logger.info("Feedback service exit")

    def get_feedback(self, timeout=None, block=True):
        if self._feedback_service is None:
            self._feedback_service = gevent.spawn(self._feedback)
        try:
            return self._feedback_queue.get(block=block, timeout=timeout)
        except Empty:
            return None

    def get_last_error(self):
        return self._last_error

    def get_status(self):
        return self._connected

    def wait_status(self, timeout):
        try:
            if isinstance(timeout, (int, float)):
                with Timeout(timeout):
                    while not self._connected:
                        gevent.sleep(1)
        finally:
            return self._connected

    def stop(self):
        ''' stop all current running greenlet '''
        if self._push_service:
            gevent.kill(self._push_service)
            self._push_service = None

        if self._read_error_service:
            gevent.kill(self._read_error_service)
            self._read_error_service = None

        if self._feedback_service:
            gevent.kill(self._feedback_service)
            self._feedback_service = None

    def put(self, device_token, msg, sound='default'):
        notif = APNSNotification(device_token, alert=msg, sound=sound)
        self.put_notification(notif)

    def put_notification(self, notif):
        self._push_queue.put(notif)

