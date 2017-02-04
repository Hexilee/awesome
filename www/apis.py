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


class Page(object):
    """
    Page object for display pages
    """

    def __init__(self, item_count, page_index=1, page_size=10):
        """
        Init Pagination by item_count, page_index and page_size.

        >>> p1 = Page(100, 1)
        >>> p1.page_count
        10
        >>> p1.offset
        0
        >>> p1.limit
        10
        >>> p2 = Page(90, 9, 10)
        >>> p2.page_count
        9
        >>> p2.offset
        80
        >>> p2.limit
        10
        >>> p3 = Page(91, 10, 10)
        >>> p3.page_count
        10
        >>> p3.offset
        90
        >>> p3.limit
        10
        """
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = int(item_count // page_size) + (1 if item_count % page_size != 0 else 0)
        if item_count == 0 or page_index > self.page_count:
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_count > self.page_index
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count: %s, page_size: %s, page_count: %s, offset: %s, ' \
               'limit: %s, page_index: %s, has_next: %s, has_previous: %s' % (
                   self.item_count, self.page_size, self.page_count, self.offset,
                   self.limit, self.page_index, self.has_next, self.has_previous
               )
    __repr__ = __str__

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
