#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from coroweb import get, post
from aiohttp import web
from models import Users

__author__ = 'Li Chenxi'


@get('/index')
async def index(request):
    users = await Users.findall()
    return {
        '__template__': 'test.html',
        'users': users
    }
