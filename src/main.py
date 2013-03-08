from gevent import monkey
monkey.patch_all()

from bottle import route, run, request
from bottle import put, post
from bottle import default_app

import os, sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)


DEBUG = True

import logging
logging.basicConfig(
    format="%(asctime)s %(levelname) 7s %(module)s: %(message)s",
    stream=sys.stdout,
    level=DEBUG and logging.DEBUG or logging.WARN)
logger = logging.getLogger(__file__)


# simple REST API
devices = set()

@route('/push/')
def index():
    return ('<h1>Registered devices</h1>',
            '<br/>'.join('<strong>%s</strong>' % x for x in devices))

@put('/push/device/')
def register_device():
    devices.add(request.forms.token)
    return "ok"

@post('/push/device/')
def send_notification():
    apns.put(request.forms.token, request.forms.msg)
    return 'ok'


# start apn service
CERTIFICATE = ROOT_DIR+'/config/apns_cert.development.pem' 

from apns import APNS
logger.info("Connecting to APNs ...")
apns = APNS(CERTIFICATE)
apns.start()
assert apns.wait_status(30)


if __name__ == '__main__':
    run(server='gevent', host='0.0.0.0', port=8080, debug=DEBUG, reloader=False)
else:
    application = default_app()
