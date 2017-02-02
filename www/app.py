#!/user/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
import json
import os
import time
import orm
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from coroweb import add_routes, add_static
from aiohttp import web

logging.basicConfig(level=logging.INFO)


async def logger_factory(app, handler):
    print(handler)
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return await handler(request)

    return logger


async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            r.content_type = 'text/html;charset=utf-8'
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])  # 重定向到另一个路径
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(  # default函数将传入r作为参数再输出一个结果作为dumps的参数，这里是强行转为dict
                    body=json.dumps(r, ensure_ascii=False, default=lambda obj: obj.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and 100 <= r < 600:
            return web.Response(status=r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and 100 <= t < 600:
                return web.Response(status=t, body=str(m))
    return response


def datetime_filter(t):
    my_time = int(time.time() - t)
    if my_time < 60:
        return u'1分钟前'
    if my_time < 3600:
        return u'%s分钟前' % (my_time//60)
    if my_time < 86400:
        return u'%s小时前' % (my_time//3600)
    if my_time < 604800:
        return u'%s天前' % (my_time//86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


async def init(my_loop):
    app = web.Application(loop=my_loop, middlewares=[logger_factory, response_factory])
    add_routes(app, 'handlers')
    srv = await my_loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('Server started at http://localhost:9000...')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
