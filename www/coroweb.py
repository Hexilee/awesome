#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import inspect
import logging
import functools
from urllib import parse
from aiohttp import web

# from apis import APIError

__author__ = 'Li Chenxi'


def get(path):
    """
    Define decorator @get('/path')
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = 'GET'
        wrapper.__path__ = path
        return wrapper

    return decorator


def post(path):
    """
    Define decorator @post('/path')
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = 'POST'
        wrapper.__path__ = path
        return wrapper

    return decorator


"""
对以下部分的解释：
    def foo(a, b, *, c, d=10):
        pass
    其中c, d均为KEYWORD_ONLY
    c的default为inspect.Parameter.empty
    d的default为10
"""


def get_required_args(fn):  # 相对源码有改动
    args = list()
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)  # 返回a、b、c类kwargs的name


def get_named_args(fn):  # 相对源码有改动
    args = list()
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            args.append(name)
    return tuple(args)  # 返回c, d两类的name


def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True
    return False


def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False  # 判断是否有**kwargs


def has_request_args(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind not in (
                inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.KEYWORD_ONLY)):
            raise ValueError(
                'request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found  # 判断是否有request参数以便统一接口


class RequestHandler(object):
    def __init__(self, app, fn):
        self._app = app  # TODO: 引入app的作用是什么
        self._func = fn
        self._has_request_args = has_request_args(fn)
        self._has_var_kw_args = has_var_kw_args(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_args = get_named_args(fn)
        self._required_args = get_required_args(fn)

    async def __call__(self, request):
        kw = None
        if self._has_var_kw_args or self._has_named_kw_args or self._required_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-Type.')  # 相对源代码有改动, 源码报错？
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(text='JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)  # **dict做参数时吧dict转化为key = value形式
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]  # TODO: v是list()吗？
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_args and self._named_args:
                # 排除了**kw的存在
                copy = dict()
                for name in self._named_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
                # check name args:
                for k, v in request.match_info.items():
                    if k in kw:
                        logging.warning('Duplicate arg name in named arg and kw args: %s args: %s' % k)
                    kw[k] = v

        # check required kw
        if self._required_args:
            for name in self._required_args:
                if not name in kw:
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        # except APIError as e:
        #     return dict(error=e.error, data=e.data, message=e.message)
        except ValueError as v:
            raise v


def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')  # __file__获得脚本当前路径和脚本名
    app.router.add_static('/static', path)
    logging.info('add static %s => %s' % ('/static', path))


def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__path__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not define in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info(
        'add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))


def add_routes(app, module_name):
    n = module_name.rfind('.')  # str.rfind(string) 在str中找到string最后出现的位置, 找不到则返回-1
    if n == -1:
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n + 1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    # TODO:弄清__import__的参数明细， globals(), locals()
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__path__', None)
            if method and path:
                add_route(app, fn)
    """
    if mod = __import__(module_name[:n], globals(), locals(), [name]) =
    import module_name[:n] as mod,
    import module_name[:n].name as mod.name

    """
    """
    locals()局部名字空间
    globals()全局名字空间

    """