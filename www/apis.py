#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import inspect
import functools

"""
JSON API definition
"""

__author__ = 'Li Chenxi'


class APIError(Exception):
    """
    basic APIError
    """
    def __init__(self, error, data, message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('Error: invalid value', field, message)


class APINotFound(APIError):
    def __init__(self, field, message=''):
        super(APINotFound, self).__init__('Error: not found', field, message)


class APIPermissionError(APIError):
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('Error: request denied', 'permission', message)