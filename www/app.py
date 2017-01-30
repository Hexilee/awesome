#!/user/bin/env python3
# -*- coding: utf-8 -*-
import logging
import asyncio
import os
import json
import time
from datetime import datetime
from aiohttp import web

logging.basicConfig(level=logging.INFO)


def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')

async def init(my_loop):
    app = web.Application(loop=my_loop)
    app.router.add_route('GET', '/', index)
    srv = await my_loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('Server started at http://localhost:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()