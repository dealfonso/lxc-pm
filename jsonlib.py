import json

class ObjectSerializer(object):
    def __init__(self):
        self.rec_list = []
    
    def serialize(self, obj):
        self.rec_list.append(obj)
        d = {}
        for k in dir(obj):
            if k[0:1] != "_":
                v = getattr(obj, k)
                try:
                    json.dumps({k:v})
                    d[k] = v
                except:
                    if not callable(v):
                        if v not in self.rec_list:
                            self.rec_list.append(v)
                            d[k] = self.serialize(v)
                            self.rec_list.pop()

        self.rec_list.pop()
        return d

class Serializable(object):
    def serialize(self):
        try:
            self.__serializer
        except:
            self.__serializer = ObjectSerializer()
        
        return self.__serializer.serialize(self)
    
