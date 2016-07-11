import json
import types

class ObjectSerializer(object):
    def __init__(self):
        self.rec_list = []

    def _assign(self, d, i, v):
        if not callable(v):
            if v not in self.rec_list:
                self.rec_list.append(v)
                d[i] = self.serialize(v)
                self.rec_list.pop()
    
    def serialize(self, obj):
        try:
            l = len(obj)
        except:
            l = 0

        if l > 0:
            d = [None] * l
            i = 0
            while i < l:
                v = obj[i]
                self._assign(d, i, v)
                (d[i])['index'] = i
                i = i + 1
            return d

        self.rec_list.append(obj)
        d = {}
        for k in dir(obj):
            if k[0:1] != "_":
                v = getattr(obj, k)
                try:
                    json.dumps({k:v})
                    d[k] = v
                except:
                    self._assign(d, k, v)

        self.rec_list.pop()
        return d

class Serializable(object):
    _JSON_FIELDS_required = []
    _JSON_FIELDS_other = []
    _JSON_FIELDS_default = {}

    @classmethod
    def from_json(nd_class, nd_object, json_str):
        try:
            json_object = json.loads(json_str)
        except:
            return None
        
        for i in nd_object._JSON_FIELDS_required:
            if i not in json_object:
                return None
            nd_object.__setattr__(i, json_object[i])

        for i in nd_object._JSON_FIELDS_default:
            if i in json_object:
                nd_object.__setattr__(i, json_object[i])
            else:
                nd_object.__setattr__(i, nd_object._JSON_FIELDS_default[i])

        for i in nd_object._JSON_FIELDS_other:
            if i in json_object:
                nd_object.__setattr__(i, json_object[i])

        return nd_object

    def __str__(self):
        return json.dumps(self.serialize(), indent=4)
    
    def serialize(self):
        try:
            self.__serializer
        except:
            self.__serializer = ObjectSerializer()
        
        return self.__serializer.serialize(self)
    
