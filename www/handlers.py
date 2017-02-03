#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import re
import hashlib
import logging
import json
import base64
import asyncio
import markdown2
from coroweb import get, post
from aiohttp import web
from models import Users, Blogs, next_id, Comments
from apis import APIError, APIValueError, APINotFound, APIPermissionError
from config import config

__author__ = 'Li Chenxi'

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

COOKIE_NAME = 'qingxuanshabao'
_COOKIE_KEY = config.session.secret


def user_to_cookie(user, max_age):
    """
    Generator cookie by user
    """
    expire = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.password, expire, _COOKIE_KEY)
    cookie_list = [user.id, expire, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(cookie_list)


async def cookie_to_user(cookie_str):
    if not cookie_str:
        return None
    try:
        cookie_list = cookie_str.split('-')
        if not len(cookie_list) == 3:
            return None
        uid, expire, sha1 = cookie_list
        if int(expire) < time.time():
            return None
        user = await Users.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.password, expire, _COOKIE_KEY)
        if not sha1 == hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1_cookie')
            return None
        user.password = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


@get('/')
async def index(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit,' \
              ' sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blogs(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
        Blogs(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
        Blogs(id='3', name='Learn Python', summary=summary, created_at=time.time() - 7200),
    ]

    return {
        '__template__': 'blogs.html',
        'blogs': blogs,
        '__user__': request.__user__
    }


@get('/register')
def register():
    return {
        '__template__': 'register.html',
    }


@get('/signin')
def signin():
    return {
        '__template__': 'signin.html',
    }


@post('/api/authenticate')
async def authenticate(*, email, password):
    logging.info('HHHHHHH')
    if not email:
        raise APIValueError('email', 'Invalid email')
    if not password:
        raise APIValueError('password', 'Invalid password')
    users = await Users.findall(where='email=?', args=[email, ])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist')
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(password.encode('utf-8'))
    if not sha1.hexdigest() == user.password:
        raise APIValueError('password', 'Invalid password')
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user_to_cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')  # TODO: signout是如何工作的？
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out')
    return r


@post('/api/users')
async def api_register_user(*, email, name, password):
    if not name or not name.strip():
        raise ValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise ValueError('email')
    if not password or not _RE_SHA1.match(password):
        raise ValueError('password')
    users = await Users.findall(where='email=?', args=[email, ])
    if len(users) > 0:
        return
        # raise APIError('register: fail', 'email', 'Email is already in use!')  # TODO: 加一个重定向或者ajax验证
    uid = next_id()
    sha1_password = '%s:%s' % (uid, password)  # 二次加密
    user = Users(id=uid, name=name.strip(), email=email,
                 password=hashlib.sha1(sha1_password.encode('utf-8')).hexdigest(),
                 image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()

    # make session cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user_to_cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r
    # TODO: 返回的json如何应用？==>> app.auth_factory
    # TODO: 但是app.auth_factory仅仅应用了其的cookie属性
