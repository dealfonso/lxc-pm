'''            
"network": [
                {
                    "index": 0, 
                    "ipv4_gateway": "", 
                    "name": "", 
                    "veth_pair": "", 
                    "mtu": "", 
                    "ipv6_gateway": "", 
                    "flags": "up", 
                    "ipv4": "", 
                    "ipv6": "", 
                    "hwaddr": "00:16:3e:1e:89:6b", 
                    "link": "lxcbr0", 
                    "script_up": "", 
                    "script_down": "", 
                    "type": "veth"
                }
'''

import jsonlib
import json
import cpyutils.iputils
import random

class NetworkDefinition(jsonlib.Serializable):
    _JSON_FIELDS_required = [ 'name', 'link', 'type' ]

    @classmethod
    def from_json(cls, json_str):
        o = jsonlib.Serializable.from_json(cls(None, None, None), json_str)
        if o is None:
            raise Exception("could not create object from json '%s'" % json_str)
        return o

    def __init__(self, name, link, type):
        self._name = name
        self.link = link
        self.type = type
        self._last_lease = None
        self._leases = []

    def add_lease(self, lease):
        if self._check_hwaddr_in_leases(lease.hwaddr): return False
        if self._check_ipv4_in_leases(lease.ipv4): return False
        self._leases.append(lease)
        return True

    def _check_hwaddr_in_leases(self, hwaddr):
        for lease in self._leases:
            if lease.hwaddr == hwaddr: return True
        return False

    def _check_ipv4_in_leases(self, ipv4):
        for lease in self._leases:
            if lease.ipv4 == ipv4: return True
        return False

    def get_lease(self):
        return None

class NetworkDefinition_MAC_Prefix(NetworkDefinition):
    _JSON_FIELDS_default = { 'hwaddrprefix': '40:00:00' }

    @staticmethod
    def gen_hex_mac_prefix(original_mac):
        mac = (original_mac.upper()).strip()
        parts = mac.split(':')
        if len(parts) > 6:
            return None
        if len(parts) > 1:
            # let's think that it is a : separated mac
            for p in parts:
                if len(p) != 2:
                    return None
            mac = ''.join(parts)
        for c in mac:
            if c not in '0123456789ABCDEF':
                return None
        return mac

    @classmethod
    def from_json(cls, json_str):
        o = jsonlib.Serializable.from_json(cls(None, None, None), json_str)
        
        mac_prefix = cls.gen_hex_mac_prefix(o.hwaddrprefix)
        if mac_prefix is None: raise Exception("Bad MAC mask format %s" % o.hwaddrprefix) 

        o._mac_prefix = int(mac_prefix, 16)
        o._mac_tail = 0
        o._mac_tail_bits = (12 - len(mac_prefix)) * 4
        for i in range(0, 12 - len(mac_prefix)):
            o._mac_prefix = (o._mac_prefix << 4)
            o._mac_tail = (o._mac_tail << 4) | 0xf 
        
        return o

    def _gen_mac(self):
        new_mac = ("%x" % (self._mac_prefix | (random.getrandbits(self._mac_tail_bits) & self._mac_tail))).lower()
        mac_str = ':'.join([new_mac[i:i+2] for i in range(0, len(new_mac), 2)])
        return mac_str

    def get_lease(self):
        max_attempts = 10
        mac = self._gen_mac()

        while max_attempts > 0 and self._check_hwaddr_in_leases(mac):
            mac = self._gen_mac()
            max_attempts = max_attempts - 1

        if max_attempts == 0:
            return None

        lease = NetworkConfiguration(self)
        lease.hwaddr = mac
        return lease

class NetworkDefinition_IP_Range(NetworkDefinition_MAC_Prefix):
    _JSON_FIELDS_default = { 'hwaddrprefix': '40:00:00', 'ipv4mask': '192.168.1.1/24' }
    def get_lease(self):
        return None

class NetworkDefinition_Pair(NetworkDefinition):
    _JSON_FIELDS_required = [ 'name', 'link', 'type' ]
    _JSON_FIELDS_default = { 'iphw': [ { 'ipv4': '192.168.1.1', 'hwaddr': '40:00:00:00:00:01' } ] }

    @classmethod
    def from_json(cls, json_str):
        o = jsonlib.Serializable.from_json(cls(None, None, None), json_str)
        if o is not None:
            for lease in o.iphw:
                if not cpyutils.iputils.check_ip(lease['ipv4']): raise Exception("bad ip format: %s" % lease['ipv4'])
                if not cpyutils.iputils.check_mac(lease['hwaddr']): raise Exception("bad hw address format: %s" % lease['hwaddr'])
        else:
            raise Exception("could not create object from json '%s'" % json_str)
        return o

class NetworkConfiguration(jsonlib.Serializable):
    _JSON_FIELDS_required = [ 'link', 'hwaddr', 'type' ]
    _JSON_FIELDS_default = { 'ipv4': None }

    @classmethod
    def from_json(cls, json_str):
        o = jsonlib.Serializable.from_json(cls(None), json_str)
        if o is not None:
            if not cpyutils.iputils.check_mac(o.hwaddr): raise Exception("mac format is not valid")
        return o

    def __init__(self, network_definition):
        self._network_definition = network_definition
        self.link = network_definition.link
        self.hwaddr = None
        self.type = network_definition.type
        self.ipv4 = None

if __name__ == "__main__":

    n = json.dumps( {
            'name': 'public_dhcp',
            'link': 'br0',
            'type': 'veth',
            'iphw': [
                { 'ipv4': '10.0.0.1', 'hwaddr': '60:00:00:00:00:01' }
            ]
        }
    , indent = 4)

    m = NetworkDefinition_MAC_Prefix.from_json(n)
    print m.get_lease()
    print m.get_lease()
    print m.get_lease()
    print m.get_lease()
    print m.get_lease()

    #print NetworkDefinition_Pair.from_json(n)
    #print NetworkDefinition_IP_Range.from_json(n)

    '''
    d = NetworkDefinition.from_json(
        '{\
            "name": "basic", \
            "link": "br0", \
            "type": "veth", \
            "hwaddr": "40:00:00:00:00:01"\
        }')
    print d
    '''
    # print o
    # print json.dumps(o.serialize(), indent=4)
