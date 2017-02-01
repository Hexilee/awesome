#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import aiomysql
import sys
import logging

__author__ = 'Li Chenxi'

logging.basicConfig(level=logging.DEBUG)


def log(sql, args=tuple()):
    logging.info('SQL: %s' % sql)


async def create_pool(loop, **kw):
    logging.info('creating database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


# 封装SELECT
async def select(sql, args, size=None):
    #  TODO:弄清楚log的作用和sql的数据类型
    #  TODO:什么情况下用 await？
    """

    :param sql: sql语句
    :param args: sql参数
    :param size: 返回的数据条数
    :return:
    """

    log(sql, args)
    global __pool

    async with __pool.get() as conn:  # TODO: 为什么可以用async,__pool.get()是什么
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        conn.close()
    return rs


# 封装INSERT, UPDATE, DELETE
async def execute(sql, args, autocommit=True):
    log(sql)
    affected = 0
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()  # TODO：conn.rollback()的作用是什么
                raise e
        conn.close()
        return affected


def create_args_string(num):
    my_list = list()
    for i in range(num):
        my_list.append('?')
    return ', '.join(my_list)


class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):  # attrs是关于field实例的dict
        # 排除Model本身
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称
        table_name = attrs.get('__table__', None) or name.lower()
        logging.info('found model: %s (table: %s)' % (name, table_name))
        # 获取所有field和主键名
        mappings = dict()
        fields = list()
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    if primary_key:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)

                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)  # TODO:清空attrs, 为什么没有清除primary_key？
        escaped_fields = list(map(lambda f: '`%s`' % (mappings[f].name or f), fields))  # 转换fields的实例名为sql语句.
        attrs['__mappings__'] = mappings  # 保持属性和列的对应关系
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primary_key  # 主键实例名
        attrs['__fields__'] = fields  # 主键以外的实例名
        # 构造默认的SELECT, INSERT, UPDATE和DELETE
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (
            primary_key, ', '.join(escaped_fields), table_name)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
            table_name, ', '.join(escaped_fields), primary_key, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
            table_name, ', '.join(map(lambda f: '`%s`=?' % (mappings[f].name or f), fields)), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (
            table_name, primary_key)
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model'object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def get_value(self, key):
        return getattr(self, key, None)

    # 往Model类添加class方法，就可以让所有子类调用class方法:  def func(cls):
    @classmethod
    async def find(cls, pk):  # pk是sql语句的参数
        """ find object by primary key."""
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])  # TODO:为什么不用rs[0]

    # 往Model类添加实例方法，就可以让所有子类调用实例方法：
    async def save(self):
        args = list(map(self.get_value_or_default, self.__fields__))
        args.append(self.get_value_or_default(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)

    @classmethod
    async def findall(cls, where=None, args=None, **kw):
        """ find all object by where clause."""
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = list()

        orderby = kw.get('orderby', None)
        if orderby:
            sql.append('order by')
            sql.append(orderby)

        limit = kw.get('limit', None)
        if limit:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)  # list和tuple合并
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return rs  # TODO：为什么廖大要用[cls(**r) for r in rs]

    """
    @classmethod
    async def find_number(cls, my_pdict):
        rs = cls.find_all(my_pdict)
        if rs:
            result = len(rs)
        else:
    """  # TODO: 为什么len(rs)报错

    @classmethod
    async def findnumber(cls, select_field, where=None, args=None):
        """find number by select and where."""
        sql = ['select %s _num_ from `%s`' % (select_field, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        else:
            return rs[0]['_num_']
        # TODO: findnumber函数的用法

    async def update(self):
        args = list(map(self.get_value_or_default, self.__fields__))
        primary_key = self.__primary_key__
        args.append(self.get_value_or_default(primary_key))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update by primary key: affected rows: %s' % rows)

    @classmethod
    async def delete(cls, primary_key=None):
        if primary_key:
            rows = await execute(cls.__delete__, [primary_key])
            if rows != 1:
                logging.warning('failed to delete by primary key: affected rows: %s' % rows)
        else:
            logging.warning("please use 'delete(<primary_key>)'")

    # TODO:封装create函数

    # 从mappings获取field，field中含有key的预设值
    # TODO：mapping， field各是什么？
    """
        答：
            mapping: 储存value名和对应Field实例键值对的dict
            field: 储存非primary_key的value名的list
    """

    def get_value_or_default(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default

                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value


class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0, ddl='bigint'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, primary_key=False, default=False, ddl='boolean'):
        super().__init__(name, ddl, primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0, ddl='real'):
        super().__init__(name, ddl, primary_key, default)


class TextField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='mediumtext'):
        super().__init__(name, ddl, primary_key, default)
