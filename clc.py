# -*- coding: utf-8 -*-
'''
CenturyLink Cloud Module
===================

.. versionadded:: 2017.7.14

The CLC cloud module allows you to manage CLC Via the CLC SDK.

:codeauthor: Stephan Looney <slooney@stephanlooney.com>


Dependencies
============

- clc-sdk Python Module

CLC SDK
-------

clc-sdk can be installed via pip:

.. code-block:: bash

    pip install clc-sdk

.. note::
  For sdk reference see: https://github.com/CenturyLinkCloud/clc-python-sdk

Configuration
=============

To use this module, set up the clc-sdk, username,password,key in the
cloud configuration at
``/etc/salt/cloud.providers`` or ``/etc/salt/cloud.providers.d/clc.conf``:

.. code-block:: yaml

    my-clc-config:
      driver: clc
      user: 'web-user'
      password: 'verybadpass'
      token: ''
      token_pass:''

.. note::

    The ``provider`` parameter in cloud provider configuration was renamed to ``driver``.
    This change was made to avoid confusion with the ``provider`` parameter that is
    used in cloud profile configuration. Cloud provider configuration now uses ``driver``
    to refer to the salt-cloud driver that provides the underlying functionality to
    connect to a cloud provider, while cloud profile configuration continues to use
    ``provider`` to refer to the cloud provider configuration that you define.

'''

# Import python libs
from __future__ import absolute_import
from random import randint
from re import findall
import pprint
import logging
import time
import os.path
import subprocess
import json
# Import salt libs
import salt.utils
import salt.utils.cloud
import salt.utils.xmlutil
#import pip
import importlib
from salt.exceptions import SaltCloudSystemExit
from flask import Flask, request
# Import salt cloud libs
import salt.config as config
import requests
# Attempt to import clc-sdk lib
try:
        importlib.import_module('clc')
        import clc
	HAS_CLC = True
except ImportError:
        HAS_CLC = False
# Disable InsecureRequestWarning generated on python > 2.6
try:
    from requests.packages.urllib3 import disable_warnings  # pylint: disable=no-name-in-module
    disable_warnings()
except Exception:
    pass

try:
    import salt.ext.six as six
    HAS_SIX = True
except ImportError:
    # Salt version <= 2014.7.0
    try:
        import six
    except ImportError:
        HAS_SIX = False

IP_RE = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

# Get logging started
log = logging.getLogger(__name__)

__virtualname__ = 'clc'


# Only load in this module if the CLC configurations are in place
def __virtual__():
    '''
    Check for CLC configuration and if required libs are available.
    '''
    if get_configured_provider() is False:
       return False

    if get_dependencies() is False:
        return False

    return __virtualname__


def get_configured_provider():
    '''
    Return the first configured instance.
    '''
    return config.is_provider_configured(
        __opts__,
        __active_provider_name__ or __virtualname__,
        ('token','token_pass', 'user', 'password',)
    )


def get_dependencies():
    '''
    Warn if dependencies aren't met.
    '''
    deps = {
        'clc': HAS_CLC,
        'six': HAS_SIX
    }
    return config.check_driver_dependencies(
        __virtualname__,
        deps
    )

def get_creds():
    user = config.get_cloud_config_value(
    'user', get_configured_provider(), __opts__, search_global=False
    )
    password = config.get_cloud_config_value(
    'password', get_configured_provider(), __opts__, search_global=False
    )
    token = config.get_cloud_config_value(
    'token', get_configured_provider(), __opts__, search_global=False
    )
    token_pass = config.get_cloud_config_value(
    'token_pass', get_configured_provider(), __opts__, search_global=False
    )
    creds = {"user":user,"password":password,"token":token,"token_pass":token_pass}
    return creds
def list_nodes_full(call=None, for_output=True):
    '''
    Return a list of the VMs that are on the provider
    '''
    if call == 'action':
        raise SaltCloudSystemExit(
            'The list_nodes_full function must be called with -f or --function.'
        )
    creds = get_creds()
    clc.v1.SetCredentials(creds["token"],creds["token_pass"])
    servers_raw = clc.v1.Server.GetServers(location=None)
    servers_raw = json.dumps(servers_raw)
    servers = json.loads(servers_raw)
    return(servers)

def avail_images(call=None):
    all_servers = list_nodes_full()
    templates = {}
    for server in all_servers:
      if server["IsTemplate"]:
          templates.update({"Template Name": server["Name"]})
    return(templates)

def avail_locations(call=None):
    creds = get_creds()
    clc.v1.SetCredentials(creds["token"],creds["token_pass"])
    locations = clc.v1.Account.GetLocations()
    return(locations)

def avail_sizes(call=None):
    return({"Sizes":"Sizes are built into templates. Choose appropriate template"})

def __virtual__():
    '''
    Check for DigitalOcean configurations
    '''
    if get_configured_provider() is False:
        return False

    if get_dependencies() is False:
        return False

    return __virtualname__


def get_configured_provider():
    return config.is_provider_configured(
        __opts__,
        __active_provider_name__ or __virtualname__,
        ('token',)
    )
def get_build_status(req_id,nodename):
    counter = 0
    req_id = str(req_id)
    while (counter < 10):
        queue = clc.v1.Blueprint.GetStatus(request_id=(req_id))
        if (queue["PercentComplete"] == 100):
            
            server_name = queue["Servers"][0]
            return(server_name)            
        else:
            counter = counter + 1
            log.info("Creating Cloud VM " + nodename + " Time out in " + str(10 - counter) + " minutes")
            time.sleep(60)
def get_ip(nodename=None,call=None):
    if nodename==None:
        nodename = 'VA1SBAFOO1308'
    print("Looking up IP for ",nodename)
    creds = get_creds()
    clc.v1.SetCredentials(creds["token"],creds["token_pass"])
    server_details = clc.v1.Server.GetServerDetails(alias=None,servers=[(nodename),])
    #server_details = json.dumps(server_details)
    #server_details = json.loads(server_details)
    for server in server_details:
        ipaddress = server["IPAddress"]
    return(ipaddress)

def create(vm_):
    creds = get_creds()
    clc.v1.SetCredentials(creds["token"],creds["token_pass"])
    cloud_profile = config.is_provider_configured(
        __opts__,
        __active_provider_name__ or __virtualname__,
        ('token',)
    )
    group = config.get_cloud_config_value(
        'group', vm_, __opts__, search_global=False, default=None,
    )
    name = vm_['name']
    description = config.get_cloud_config_value(
        'description', vm_, __opts__, search_global=False, default=None,
    )
    ram = config.get_cloud_config_value(
        'ram', vm_, __opts__, search_global=False, default=None,
    )
    backup_level = config.get_cloud_config_value(
        'backup_level', vm_, __opts__, search_global=False, default=None,
    )
    template = config.get_cloud_config_value(
        'template', vm_, __opts__, search_global=False, default=None,
    )
    password = config.get_cloud_config_value(
        'password', vm_, __opts__, search_global=False, default=None,
    )
    cpu = config.get_cloud_config_value(
        'cpu', vm_, __opts__, search_global=False, default=None,
    )
    network = config.get_cloud_config_value(
        'network', vm_, __opts__, search_global=False, default=None,
    )
    location = config.get_cloud_config_value(
        'location', vm_, __opts__, search_global=False, default=None,
    )
    if len(name) > 6:
        name = name[0:6]
    if len(password) < 9:
        password = ''
    clc_return = clc.v1.Server.Create(alias=None,location=(location),name=(name),template=(template),cpu=(cpu),ram=(ram),backup_level=(backup_level),group=(group), network=(network),description=(description),password=(password))
    req_id = clc_return["RequestID"]
    clc_servername = get_build_status(req_id,name)
    vm_['ssh_host'] = get_ip(clc_servername)
    __utils__['cloud.fire_event'](
        'event',
        'waiting for ssh',
        'salt/cloud/{0}/waiting_for_ssh'.format(name),
        sock_dir=__opts__['sock_dir'],
        args={'ip_address': vm_['ssh_host']},
        transport=__opts__['transport']
    )
    # Bootstrap!
    ret = __utils__['cloud.bootstrap'](vm_, __opts__)

    #ret.update(data)
    return({"Status":"Build Completed","Server":(clc_servername),"IP":get_ip(clc_servername)})

def destroy(name, call=None):
    print("destroying ")
