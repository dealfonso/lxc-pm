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
    def serialize(self):
        try:
            self.__serializer
        except:
            self.__serializer = ObjectSerializer()
        
        return self.__serializer.serialize(self)
    
