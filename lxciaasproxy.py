import requests
import time
import cpyutils.log
import cpyutils.eventloop
import logging
import json
import jsonlib
import threading
import bottle
import cpyutils.restutils

_logger = cpyutils.log.Log("lxc-pmg")
_logger.setup("/tmp/lxciaas-proxyd.log")

PERIOD_POLL_HOSTS = 30
PERIOD_POLL_HOST = 1
ACCESS_USER = ""
ACCESS_TOKEN = "1cf62348-a031-4d71-b719-c266eab75f4d"
ACCESS_TOKEN = ""
DEFAULT_LXC_PM_HOST_LISTEN_PORT = 15909
DEFAULT_LXC_PM_GATHERER_LISTEN_HOST = "localhost" 
DEFAULT_LXC_PM_GATHERER_LISTEN_PORT = 15912
DEFAULT_LXC_PM_AUTH_DEFAULT_USER = ""
DEFAULT_LXC_PM_AUTH_DEFAULT_TOKEN = "1e55e7e4-b369-45d2-a484-eb6ea48d5da1"
DEFAULT_LXC_PM_AUTH_DISABLE = False
LXC_HOSTS = "localhost"

app = cpyutils.restutils.get_app()

def get_monitor():
    global _MONITOR
    try:
        _MONITOR
    except:
        _MONITOR = MonitoringInfo()
    return _MONITOR 

# In order to use basic authentication, it is enough to use the decorator
#   @bottle.auth_basic(check_pass)
# right before the name of the function that is serving a REST route. Then
# You'd have to implement your authentication backend (e.g. database or a
# simple password check)'
def check_pass(username, password):
    return (username == ACCESS_USER) and (password == ACCESS_TOKEN) 

@app.route('/')
# @bottle.auth_basic(check_pass)
def get_server_info():
    extra_headers = {
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Origin': '*'
    }
    for header, value in extra_headers.items():
        bottle.response.add_header(header, value)
    return cpyutils.restutils.response_json(get_monitor().get_jsonable())

@app.route('/:hostname')
@bottle.auth_basic(check_pass)
def get_host_info(hostname):
    monitor = get_monitor()
    if hostname not in monitor.hostsInfo:
        return cpyutils.restutils.error(404, "host %s not found" % hostname)

    hostinfo = monitor.hostsInfo[hostname]
    resp = requests.get("http://%s:%s/" % (hostinfo._hostname, hostinfo._port), auth = (hostinfo._user, hostinfo._password))

    for header_name, header_value in resp.headers.items():
        bottle.response.add_header(header_name, header_value)

    bottle.response.status = resp.status_code
    return resp.text

class HostInfo(jsonlib.Serializable):
    def __init__(self, hostname, port, user = None, password = None):
        self._hostname = hostname

        if user is not None or password is not None or not DEFAULT_LXC_PM_AUTH_DISABLE:
            if user is None:
                user = DEFAULT_LXC_PM_AUTH_DEFAULT_USER
            if password is None:
                password = DEFAULT_LXC_PM_AUTH_DEFAULT_TOKEN

        _logger.debug("user: %s, password: %s" % (user, password))

        self._port = port
        self._user = user
        self._password = password
        self._lastpoll = 0
        self.hostinfo = {}

    def poll(self):
        user = self._user
        passwd = self._password
        if user is not None or passwd is not None:
            if user is None: user = ""
            if passwd is None: passwd = ""
            resp = requests.get("http://%s:%s/" % (self._hostname, self._port), auth = (user, passwd))
        else:
            resp = requests.get("http://%s:%s/" % (self._hostname, self._port))

        if resp.status_code == 200:
            self.hostinfo = resp.json()
            self.hostinfo['hostname'] = self._hostname
            self._lastpoll = cpyutils.eventloop.now()
            return True, ""

        return False, "%d" % resp.status_code

class MonitoringInfo:
    def __init__(self):
        self.__lock_data = threading.Lock()
        self.__lock_event = threading.Lock()
        self.hostsInfo = {}

        # This is the data structure to be returned in the REST API
        # * it contains post-processing info (e.g. timestamp)
        # * it is managed as a cache to be able to return the information immediately
        #   as the data structure ready to be used with the json library is created here
        #   instead of creating it with the function get_jsonable()
        # self.hostsInfo_json = {}
        self._poll_queue = []
        self._event_next_poll_id = None

    def _postprocess_hostinfo(self, hostinfo):
        postprocessed_info = hostinfo.hostinfo
        postprocessed_info['timestamp'] = hostinfo._lastpoll
        return postprocessed_info

    def get_json(self):
        # self.__lock_data.acquire()
        json_str = json.dumps(self.get_jsonable())
        # self.__lock_data.release()
        return json_str
        
    def get_jsonable(self):
        self.__lock_data.acquire()
        hostsInfo_jsonable = {}
        hostsInfo_jsonable['hosts'] = []
        for hostname in self.hostsInfo:
            hostsInfo_jsonable['hosts'].append(self._postprocess_hostinfo(self.hostsInfo[hostname]))
        hostsInfo_jsonable['timestamp'] = cpyutils.eventloop.now()
        self.__lock_data.release()
        return hostsInfo_jsonable

    def addHost(self, hostname, port = None):
        if port is None: port = DEFAULT_LXC_PM_HOST_LISTEN_PORT
        self.__lock_data.acquire()
        self.hostsInfo[hostname] = HostInfo(hostname, port)
        # self.hostsInfo_json[hostname] = {}
        self.__lock_data.release()

    def _cancel_next_poll(self):
        self.__lock_event.acquire()
        if self._event_next_poll_id is not None:
            eventloop = cpyutils.eventloop.get_eventloop()
            eventloop.cancel_event(self._event_next_poll_id)
        self._event_next_poll_id = None
        self.__lock_event.release()

    def _schedule_next_poll(self):
        eventloop = cpyutils.eventloop.get_eventloop()
        event_next_poll = cpyutils.eventloop.Event_Periodical(0, PERIOD_POLL_HOST, callback = self.poll_next_host, description = "polling the next host")        
        eventloop.add_event(event_next_poll)

        self.__lock_event.acquire()
        self._event_next_poll_id = event_next_poll.id
        self.__lock_event.release()

    def schedule_poll(self, delay = 0):
        self._cancel_next_poll()
        eventloop = cpyutils.eventloop.get_eventloop()
        programmed_time = max(0, PERIOD_POLL_HOSTS + delay)
        eventloop.add_event(cpyutils.eventloop.Event(programmed_time, callback = self.poll, description = "polling the hosts each %ss" % PERIOD_POLL_HOSTS))

    def poll(self):
        # We'll prepare the list of hosts to poll
        self.__lock_data.acquire()
        self._poll_queue = self.hostsInfo.keys()
        self.__lock_data.release()

        self._cancel_next_poll()
        self._schedule_next_poll()

    def poll_next_host(self):
        self.__lock_data.acquire()

        # Now let's choose the host to poll
        current_host = None
        while current_host is None and len(self._poll_queue) > 0:
            current_host = self._poll_queue.pop()

            # Maybe the host has been removed from the monitor
            if current_host not in self.hostsInfo:
                current_host = None

        if current_host is not None:
            # Now poll the host
            _logger.debug("polling host %s" % current_host)

            polled, message = self.hostsInfo[current_host].poll()
            if not polled:
                _logger.error("failed to poll host %s (%s)" % (current_host, message))
            else:
                # self.hostsInfo_json[current_host] = self._postprocess_hostinfo(self.hostsInfo[current_host])
                _logger.debug("host %s polled" % current_host)

        finished_polling = (len(self._poll_queue) == 0)
        self.__lock_data.release()

        if finished_polling:
            _logger.debug("finished polling hosts")
            _logger.debug(self.get_json())
            self.schedule_poll()


def main_function():
    _logger.info("starting lxc-pmg")
    logging.getLogger().setLevel(logging.ERROR)
    logging.getLogger("[ELOOP]").setLevel(logging.ERROR)

    host_to_monitor = LXC_HOSTS.split(" ")
    for host in host_to_monitor:
        _logger.info("adding host %s to monitor" % host)
        get_monitor().addHost(host)

    cpyutils.eventloop.create_eventloop(True)
    get_monitor().schedule_poll(-PERIOD_POLL_HOSTS)
    eventloop = cpyutils.eventloop.get_eventloop()

    cpyutils.restutils.run_in_thread(DEFAULT_LXC_PM_GATHERER_LISTEN_HOST, DEFAULT_LXC_PM_GATHERER_LISTEN_PORT)
    eventloop.loop()

if __name__ == '__main__':
    main_function()
