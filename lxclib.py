import json
import lxc
import jsonlib
import nodeinfo
import cpyutils
import types

def file_to_strings(filename):
    valid_lines = []
    try:
        f_lines = open(filename)
        for line in f_lines:
            line = line.split('#',1)[0]
            line = line.strip()
            if line != "":
                valid_lines.append(line)
    except:
        pass

    return valid_lines

def file_to_json(filename):
    result = {}
    for line in file_to_strings(filename):
        l_ar = line.split('=', 1)
        if len(l_ar) == 2:
            k, v = l_ar
            k = k.strip()
            v = v.strip()
            if k in result:
                if type(result[k]) != types.ListType:
                    result[k] = [ result[k] ]
                result[k].append(v)
            else:
                result[k] = v

    return result

class LXCContainer(lxc.Container, jsonlib.Serializable):
    @classmethod
    def pick(cls, containername):
        c = cls(containername)
        if c.defined:
            c.get_extra_info()
            return c
        return None
    
    def __str__(self):
        return self.json()

    def get_extra_info(self):
        self._get_config_info()
        self.config = file_to_json(self.config_file_name)

    def _get_config_info(self):
        config_running = {}

        if self.running:
            for key in self.get_keys():
                config_running[key] = self.get_running_config_item(key)

        self.config_running = config_running
            
    def get_jsonable(self):
        jsonable_info = self.serialize()
        ips = self.get_ips()
        jsonable_info['ip_addresses'] = ips
        return jsonable_info
    
    def json(self):
        return json.dumps(self.get_jsonable(), indent = 2, sort_keys = True)
    
def get_containers():
    containers = []
    cnames = lxc.list_containers()
    for cname in cnames:
        current_container = LXCContainer.pick(cname)
        containers.append(current_container.get_jsonable())
    return containers    
    
class Request:
    def __init__(self, name):
        self.name = name
        self.distribution = None
        self.release = None
        self.architecture = None
        
    @classmethod
    def from_json(cls, json_):
        if 'distribution' not in json_ or 'release' not in json_:
            return None
        if 'name' not in json_:
            return None
        request = cls(json_['name'])
        request.architecture = "amd64" # i386
        if 'architecture' in json_:
            request.architecture = json_['architecture']
        request.distribution = json_['distribution']
        request.release = json_['release']
        return request
    
    def create_container(self):
        new_container = LXCContainer(self.name)
        if new_container.defined:
            return False, "container %s already defined" % (self.name)
        new_container.create(None, args={"distribution": "%s" % self.distribution, "release": "%s" % self.release, "architecture": "%s" % self.architecture})
        # print s.serialize(new_container)
        if new_container.defined:
            return True, new_container
        else:
            return False, new_container.json()

if __name__ == "__main__":
    c = LXCContainer.pick("onedock-test")
    print c.json()
