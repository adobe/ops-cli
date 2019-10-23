# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

#! /usr/bin/env python
"""
Class to allow easy access to the SKMS Web API

Copyright (c) 2013-2015 Adobe Systems Inc (TechOps AppDev)

"""

# This version of the class requires the following:
# - Python 2.6
# - Python support for Requests
# - Python support for JSON
# @version v1.10, 2016-06-30
import socket
import os
import getpass
import requests
import inspect
import urllib
import json
from os.path import expanduser


class WebApiClient(object):
    """Class to allow easy access to the SKMS Web API"""
    # Version Constants
    CLIENT_TYPE = "python3.7.requests"
    CLIENT_VERSION = "1.10"

    # Properties
    client_hostname = ''
    client_username = ''
    client_script = ''
    debug = False
    error_message = ''
    passkey = ''
    request_timeout = 25
    requests_obj = None
    response_dict = None
    response_header = ''
    response_str = ''
    skms_csrf_token = None
    skms_domain = 'api.skms.mycompany.com'
    skms_session_storage_file = None
    skms_session_id = None
    status = False
    trusted_cert_file_path = None
    username = ''
    verify_ssl_chain = True

    # --------------- #
    #   CONSTRUCT     #
    # --------------- #
    # This is the construct method. It can be passed the username, passkey,
    # and skms_domain settings.
    # @param string username The username to use to login to the SKMS Web API
    # @param string passkey The passkey to use to login to the SKMS Web API
    # @param string skms_domain The hostname of the SKMS that will be accessed
    def __init__(self, username, passkey, skms_domain=None,
                 enable_session_optimization=False):
        self.username = username
        self.passkey = passkey
        if skms_domain is not None:
            self.skms_domain = skms_domain

        # Set Tracking Info
        filename = inspect.stack()[1][1]
        if filename is not None:
            self.client_script = os.getcwd() + '/' + filename
        else:
            self.client_script = ''
        if socket.gethostname() is not None:
            self.client_hostname = socket.gethostname()
        else:
            self.client_hostname = ''
        if getpass.getuser() is not None:
            self.client_username = getpass.getuser()
        else:
            self.client_username = ''

        # Try to enable session optimization
        if enable_session_optimization:
            if username.strip() != '':
                home_dir = expanduser("~")
                if home_dir == '/root' or home_dir == '/root/':
                    return
                if not os.path.exists(home_dir):
                    return
                skms_dir = home_dir + '/.skms/'
                if not os.path.exists(skms_dir):
                    try:
                        os.makedirs(skms_dir)
                        if not os.path.exists(skms_dir):
                            return
                        try:
                            os.chmod(skms_dir, 0o700)
                        except OSError:
                            return
                    except OSError:
                        return
                self.enable_skms_session_optimization(
                    skms_dir + 'sess_' + username.strip() + '.json')

    # ---------------------------#
    #    CONFIGURATION METHODS   #
    # ---------------------------#
    def enable_debug_mode(self):
        """Enables debug mode which will return debug info"""
        self.debug = True

    def disable_debug_mode(self):
        """Disables the debug mode which will return debug info"""
        self.debug = False

    def get_request_timeout(self):
        """Returns the current request timeout setting"""
        return self.request_timeout

    def set_request_timeout(self, timeout):
        """Sets the request timeout setting"""
        if isinstance(timeout, int) and timeout > 0:
            self.request_timeout = timeout

    def enable_skms_session_optimization(self, skms_session_storage_file):
        """Enables Skms Session Optimization"""
        # Try to load file
        if os.path.isfile(skms_session_storage_file):
            with open(
                skms_session_storage_file, "r"
            ) as skms_session_storage_file_ptr:
                file_contents = skms_session_storage_file_ptr.read()
            if file_contents != '':
                session_info = json.loads(file_contents)
                if (
                    isinstance(session_info, dict) and
                    'skms_session_id' in session_info and
                    session_info['skms_session_id'].strip() != ""
                ):
                    self.set_skms_session_id(session_info['skms_session_id'])
                if (
                    isinstance(session_info, dict) and
                    'skms_csrf_token' in session_info and
                    isinstance(session_info['skms_csrf_token'], basestring) and
                    session_info['skms_csrf_token'].strip() != ""
                ):
                    self.set_skms_csrf_token(session_info['skms_csrf_token'])
        self.skms_session_storage_file = skms_session_storage_file

    def get_skms_session_id(self):
        """Returns the SKMS session id returned from the last request."""
        if self.skms_session_id is not None:
            return self.skms_session_id
        else:
            return False

    def set_skms_session_id(self, skms_session_id):
        """Set the SKMS session id"""
        if (
            isinstance(skms_session_id, basestring) and
            skms_session_id.strip() != ""
        ):
            self.skms_session_id = skms_session_id

    def get_skms_csrf_token(self):
        """Returns the latest SKMS CSRF Token"""
        if self.skms_csrf_token is not None:
            return self.skms_csrf_token
        else:
            return False

    def set_skms_csrf_token(self, skms_csrf_token):
        """Sets the SKMS CSRF Token"""
        self.skms_csrf_token = skms_csrf_token

    def set_trusted_cert_file_path(self, trusted_cert_file_path):
        """Sets the path to the CA file for SSL peer/chain verification"""
        if trusted_cert_file_path.strip() != "":
            self.trusted_cert_file_path = trusted_cert_file_path
        else:
            self.trusted_cert_file_path = ""

    def enable_ssl_chain_verification(self):
        """Enables SSL Chain Verification"""
        self.verify_ssl_chain = True

    def disable_ssl_chain_verification(self):
        """Disables SSL Chain Verification"""
        self.verify_ssl_chain = False

    # --------------------- #
    #    REQUEST METHODS    #
    # --------------------- #
    # Sends a request based on the passed in request_method, resource_name,
    # and param_dict
    # @param string object_name The name of the object to access via the API.
    # @param string resource_name The name of the method to access via the
    # API.
    # @param dictionary method_params A dictionary of key/value pairs that
    # represent parameters that will be passed to the method
    # @return bool True on success, false on error.
    def send_request(self, object_name, method_name, method_param_dict=None):
        """Sends a request based on the passed in parameters"""

        # Reset Properties
        self.error_message = ''
        self.response_header = ''
        self.response_str = ''
        self.response_dict = None

        # Make sure Var Dict is a dictionary
        if not isinstance(method_param_dict, dict):
            method_param_dict = {}

        # Check to see if debug flag should be passed
        if self.debug is True:
            method_param_dict['_debug'] = True

        # Tracking Data
        method_param_dict['_client_type'] = self.CLIENT_TYPE
        method_param_dict['_client_ver'] = self.CLIENT_VERSION
        method_param_dict['_client_script'] = self.client_script
        method_param_dict['_client_hostname'] = self.client_hostname
        method_param_dict['_client_username'] = self.client_username

        # Username and Passkey
        if self.username.strip() != "" and self.passkey.strip() != "":
            method_param_dict['_username'] = self.username
            method_param_dict['_passkey'] = self.passkey

        method_param_dict['_object'] = object_name
        method_param_dict['_method'] = method_name

        # Add CSRF token to param dictionary (if applicable)
        if self.skms_csrf_token is not None and self.skms_csrf_token.strip() != "":
            method_param_dict['csrf_token'] = self.skms_csrf_token
        # Instantiate Requests Object
        self.requests_obj = requests

        # Set Method Post, URL, Parameters, and Add Session Cookie
        # (if applicable)
        try:
            if (
                self.skms_session_id is not None and
                self.skms_session_id.strip() != ""
            ):
                # Using existing session
                cookie_name = 'SkmsSID'
                if (
                    '.dev.skms' in self.skms_domain or
                    'stage.skms' in self.skms_domain
                ):
                    cookie_name = 'dev_' + cookie_name

                response = self.requests_obj.post(
                    "https://" + self.skms_domain + "/web_api/",
                    data={'_parameters': json.dumps(method_param_dict)},
                    verify=self.verify_ssl_chain,
                    timeout=self.request_timeout,
                    cert=self.trusted_cert_file_path,
                    cookies={cookie_name: urllib.quote(self.skms_session_id)}
                )
            else:
                # Creating new session
                response = self.requests_obj.post(
                    "https://" + self.skms_domain + "/web_api/",
                    data={'_parameters': json.dumps(method_param_dict)},
                    verify=self.verify_ssl_chain,
                    timeout=self.request_timeout,
                    cert=self.trusted_cert_file_path
                )
            # triggers http exception if bad request (i.e. 404)
            response.raise_for_status()

            # Separate header from body
            self.response_header = response.headers
            # pull out session and csrf_token
            if 'dev_SkmsSID' in response.cookies:
                self.skms_session_id = response.cookies['dev_SkmsSID']
            elif 'SkmsSID' in response.cookies:
                self.skms_session_id = response.cookies['SkmsSID']

            if 'dev_csrf_token' in response.cookies:
                self.skms_csrf_token = response.cookies['dev_csrf_token']
            elif 'csrf_token' in response.cookies:
                self.skms_csrf_token = response.cookies['csrf_token']
            # Check Response Status
            # Sometimes type(response.text) is NoneType
            self.response_str = response.text
            response_dict = self.get_response_dictionary()
            if response_dict is False:
                self.error_message = (
                    'Unable to JSON decode the response string.'
                )
                return False

            # Check for session storage
            if self.skms_session_storage_file is not None:
                populate_session_file = True
                if not os.path.exists(self.skms_session_storage_file):
                    try:
                        with open(
                            self.skms_session_storage_file, "w"
                        ) as skms_session_storage_file_ptr:
                            skms_session_storage_file_ptr.write('')
                        os.chmod(self.skms_session_storage_file, 0o600)
                    except OSError:
                        populate_session_file = False
                if populate_session_file is True:
                    session_info = {
                        'skms_session_id': self.skms_session_id,
                        'skms_csrf_token': self.skms_csrf_token
                    }
                    session_info_str = json.dumps(session_info)
                    if session_info_str != '':
                        with open(
                            self.skms_session_storage_file, "w"
                        ) as skms_session_storage_file_ptr:
                            skms_session_storage_file_ptr.write(
                                session_info_str)

            # Determine Status
            if (
                isinstance(response_dict, dict) and
                'status' in response_dict and
                response_dict['status'].strip() != ""
            ):
                status = response_dict['status']
            else:
                if not isinstance(response_dict, dict):
                    response_dict = {}
                status = 'unknown'

            if status.lower() == "success":
                return True
            else:
                # Pull out error messages
                error_message_list = self.get_error_message_list()
                if error_message_list.__len__() > 1:
                    self.error_message = (
                        "The API returned " +
                        str(error_message_list.__len__()) +
                        " error messages:\n"
                    )
                    for key, error_message in enumerate(error_message_list):
                        self.error_message += (
                            str(key + 1) + '. ' +
                            error_message['message'] + "\n"
                        )
                elif error_message_list.__len__() == 1:
                    self.error_message = error_message_list[0]['message']
                else:
                    self.error_message = (
                        'The status was returned as "' +
                        status + '" but no errors were in the messages list.'
                    )
                return False

        except requests.RequestException as exc:
            self.error_message = type(exc).__name__
            self.status = False
            return self.status

    def get_response_header(self):
        """Returns the response header of the last request"""
        return self.response_header

    def get_response_string(self):
        """Returns the response strin gof the last request"""
        return self.response_str

    def get_response(self):
        """Alias for get_response_string"""
        return self.get_response_string()

    def get_response_dictionary(self):
        """Returns a dictionary created by decoding the returned JSON"""
        if self.response_dict is None:
            response_str = self.get_response_string()
            try:
                self.response_dict = json.loads(response_str)
            except ValueError:
                return False
            if self.response_dict is None:
                return False
        return self.response_dict

    def get_response_status(self):
        """Returns the status field from the response if it can be found."""
        response_dict = self.get_response_dictionary()
        if isinstance(response_dict, dict) and 'status' in response_dict:
            return response_dict['status']
        else:
            return ""

    def get_data_dictionary(self):
        """Returns the data dictionary"""
        response_dict = self.get_response_dictionary()
        if isinstance(response_dict, dict) and 'data' in response_dict:
            return response_dict['data']
        else:
            return {}

    def get_error_type(self):
        """Returns the error_type field from the response if found"""
        response_dict = self.get_response_dictionary()
        if isinstance(response_dict, dict) and 'error_type' in response_dict:
            return response_dict['error_type']
        else:
            return False

    def get_error_message(self):
        """returns the error message from the last request"""
        return self.error_message

    def get_message_list_by_type(self, message_type=''):
        """Returns a list of messages based on the passed in message_type"""
        ret_list = []
        response_dict = self.get_response_dictionary()
        if (
            isinstance(response_dict, dict) and
            'messages' in response_dict and
            isinstance(response_dict['messages'], list) and
            response_dict['messages'].__len__() > 0
        ):
            for message in response_dict['messages']:
                if (
                    isinstance(message_type, basestring) and
                    (message_type.strip() ==
                     "" or message['type'].lower() == message_type.lower())
                ):
                    ret_list.append(message)
        return ret_list

    def get_error_message_list(self):
        """Returns a list of messages where type=error"""
        return self.get_message_list_by_type('error')

    def get_all_message_list(self):
        """Returns a list of all messages"""
        return self.get_message_list_by_type()
