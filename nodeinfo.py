import lxclib
import psutil
import version

def get_nodeinfo():
    return {
        "containers": lxclib.get_containers(),
        "cpu": psutil.cpu_count(),
        "memory": psutil.virtual_memory().total,
        "version": version.VERSION
    }

if __name__ == '__main__':
    import json
    print json.dumps(get_nodeinfo(),indent=4)