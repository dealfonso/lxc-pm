#! /usr/bin/env python
# coding: utf-8
#
# LXC Platform Manager (lxc-pm)
# Copyright (C) 2015 - GRyCAP - Universitat Politecnica de Valencia
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 

import bottle
import cpyutils.restutils
import lxciaas.nodeinfo as nodeinfo
import lxciaas.lxclib as lxclib

app = cpyutils.restutils.get_app()

# In order to use basic authentication, it is enough to use the decorator
#   @bottle.auth_basic(check_pass)
# right before the name of the function that is serving a REST route. Then
# You'd have to implement your authentication backend (e.g. database or a
# simple password check)'
def check_pass(username, password):
    return username == password

# https://realpython.com/blog/python/api-integration-in-python/
# http://docs.python-requests.org/en/master/user/authentication/

@app.route('/')
def get_server_info():
    return cpyutils.restutils.response_json(nodeinfo.get_nodeinfo())

@app.route('/:containername', method = 'POST')
def create_container(containername):
    json = {}
    request = None
    try:
        # Grab the JSON info from the request
        json = bottle.request.json

        # We have to add the name of the container because lxclib.Request needs it
        json['name'] = containername
        
        # Let's try to build a request from the JSON received
        request = lxclib.Request.from_json(json)
    except:
        json = None
        request = None
        
    if json is None or request is None:
        return cpyutils.restutils.error(400, "Malformed json")

    # Now we'll try to create the container
    result, explanation = request.create_container()
    if result:
        return cpyutils.restutils.response_txt(explanation)
    else:
        return cpyutils.restutils.error(409, explanation)

@app.route('/:containername', method = 'GET')
def get_container(containername):
    container = lxclib.LXCContainer.pick(containername)
    if container is None:
        return cpyutils.restutils.error(404, "container %s not found" % containername)
    return cpyutils.restutils.response_json(container.serialize())

@app.route('/:containername/start', method = 'PUT')
def start_container(containername):
    container = lxclib.LXCContainer.pick(containername)
    if container is None:
        return cpyutils.restutils.error(404, "container %s not found" % containername)
    container.start()
    if container.state == "RUNNING":
        return cpyutils.restutils.response_json(container.serialize())
    return cpyutils.restutils.error(500, "could not start container %s" % containername)

@app.route('/:containername/stop', method = 'PUT')
def stop_container(containername):
    container = lxclib.LXCContainer.pick(containername)
    if container is None:
        return cpyutils.restutils.error(404, "container %s not found" % containername)
    container.stop()
    if container.state == "STOPPED":
        return cpyutils.restutils.response_json(container.serialize())
    return cpyutils.restutils.error(500, "could not stop container %s" % containername)

@app.route('/:containername', method = 'DELETE')
def delete_container(containername):
    container = lxclib.LXCContainer.pick(containername)
    if container is None:
        return cpyutils.restutils.error(404, "container %s not found" % containername)
    container.destroy()
    if not container.defined:
        return cpyutils.restutils.response_json(container.serialize())
    return cpyutils.restutils.error(500, "could not destroy container %s" % containername)

def main_function():
    #r = Request.from_json({"name": "mycont", "distribution":"ubuntu","release":"xenial"})
    #r.create_container()
    cpyutils.restutils.run('0.0.0.0', 10000)
    
if __name__ == '__main__':
    main_function()