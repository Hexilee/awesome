#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from coroweb import get, post
from aiohttp import web


@get('/index')
def index(a, b=1, *, c, d=2, request):
    return web.Response(body=b'<h1>Awesome</h1>')