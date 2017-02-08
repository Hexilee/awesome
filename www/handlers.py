#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""  *******url handler******     """
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
from apis import APIError, APIValueError, APINotFound, APIPermissionError, Page, APIResourceNotFoundError
from config import config

__author__ = 'Li Chenxi'

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

COOKIE_NAME = 'qingxuanshabao'
_COOKIE_KEY = config.session.secret


def text_to_html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


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
async def index(request, *, page='1'):
    page_index = get_page_index(page)
    num = await Blogs.findnumber('count(id)')
    page = Page(num, page_index, 8)
    if num == 0:
        blogs = []
    else:
        blogs = await Blogs.findall(orderby='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'index.html',
        'blogs': blogs,
        'page': page,
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
    if not email:
        raise APIValueError('email', 'Invalid email')
    if not password:
        raise APIValueError('password', 'Invalid password')
    users = await Users.findall(where='email=?', args=[email, ])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist')  # TODO: 将错误返回至前端页面
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
                 image='https://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
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


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        raise e
    if p < 1:
        p = 1
    return p


@get('/manage/blogs')
async def manage_blogs(*, page=1):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }


@get('/api/blogs')  # 发送json到blog管理页面
async def api_blogs(*, page=1):
    page_index = get_page_index(page)
    num = await Blogs.findnumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blogs.findall(orderby='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)


@post('/api/blogs')  # 新建日志
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')
    blog = Blogs(user_id=request.__user__.id, user_name=request.__user__.name,
                 user_image=request.__user__.image,
                 name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog


@post('/api/blogs/{blog_id}')  # 修改日志
async def api_create_blog(blog_id, request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')

    old_blog = await Blogs.find(blog_id)
    if old_blog is None:
        raise APIResourceNotFoundError('Blogs')
    blog = Blogs(id=blog_id, user_id=request.__user__.id, user_name=request.__user__.name,
                 user_image=request.__user__.image,
                 name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.update()
    return blog


@post('/api/blogs/{blog_id}/delete')
async def blog_delete(*, blog_id, request):
    check_admin(request)
    blog = await Blogs.find(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('Blogs')
    await Blogs.delete(blog_id)
    return blog


@get('/manage/blogs/create')
def manage_create_blogs(*, id=''):  # 如果加了id，则为修改日志
    if id:
        action = '/api/blogs/%s' % id
    else:
        action = '/api/blogs'
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': action

    }


@get('/blog/{id}')
async def get_blog(request, *, id):
    blog = await Blogs.find(id)
    comments = await Comments.findall(where='blog_id=?', args=[id, ], orderby='created_at desc')
    for c in comments:
        c.html_content = text_to_html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments,
        '__user__': request.__user__
    }


@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blogs.find(id)
    return blog


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


@post('/api/blog/{blog_id}/comments')
async def api_blog_comments(request, *, blog_id, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('please sign in first')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty! ')
    blog = await Blogs.find(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comments(id=next_id(), blog_id=blog_id, user_id=user.id, user_name=user.name, user_image=user.image,
                       content=content.strip())
    await comment.save()
    return comment
