import json
import lxc
import jsonlib
import nodeinfo
import lxclib
import cpyutils

class LXCContainer(lxc.Container, jsonlib.Serializable):
    @classmethod
    def pick(cls, containername):
        c = cls(containername)
        if c.defined:
            return c
        return None
    
    def __str__(self):
        return "<a href=\"%s\">%s</a>" % (self.name, self.name)

    """    
    def serialize(self):
        s = jsonlib.ObjectSerializer()
        return s.serialize(self)
    """
    
    def json(self):
        return json.dumps(self.serialize(), indent = 2, sort_keys = True)
    
def get_containers():
    containers = {}
    cnames = lxc.list_containers()
    for cname in cnames:
        current_container = LXCContainer.pick(cname)
        containers[cname] = current_container.serialize()
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
        new_container = lxclib.LXCContainer(self.name)
        if new_container.defined:
            return False, "container %s already defined" % (self.name)
        new_container.create(None, args={"distribution": "%s" % self.distribution, "release": "%s" % self.release, "architecture": "%s" % self.architecture})
        # print s.serialize(new_container)
        if new_container.defined:
            return True, cpyutils.restutils.response_json(new_container.serialize())
        else:
            return False, cpyutils.restutils.error(500, "failed to create a container")
