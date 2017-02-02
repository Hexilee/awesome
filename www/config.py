#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config_default
import config_override

__author__ = 'Li Chenxi'


class Dict(dict):
    """
    Simple dict support refer as x.y
    """

    def __init__(self, **kw):
        super(Dict, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute %s" % key)

    def __setattr__(self, key, value):
        self[key] = value


def merge(default, override):
    r = dict()
    for k, v in default.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r


def to_dict(input_d):
    output_d = Dict()
    for k, v in input_d.items():
        output_d[k] = to_dict(v) if isinstance(v, dict) else v
    return output_d


config = merge(config_default.config, config_override.config)
config = to_dict(config)