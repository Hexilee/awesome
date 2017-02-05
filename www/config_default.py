#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Default configurations.
"""

__author__ = 'Li Chenxi'

config = {
    'debug': True,
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'lichenxi',
        'password': 'Lichenxi20000110',
        'db': 'awesome',
    },
    'session': {
        'secret': 'Awesome',
    },
    'server': {
        'host': '127.0.0.1',
        'port': 9000
    },
}
