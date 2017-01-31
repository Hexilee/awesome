import orm
from models import Users, Blogs, Comments
import asyncio
import aiomysql
import sys

loop = asyncio.get_event_loop()


async def test():
    await orm.create_pool(loop=loop, user='lichenxi', password='Lichenxi20000110', db='awesome')

    u = Users(name='Test', email='test@example.com', password='password', image='about:blank', id='123456789')

    await u.save()

    my_id1 = await Users.find('123456789')
    print(my_id1)

    u = Users(naem='Eric', email='test@example.com', password='password', image='about:blank')
    await u.update('123456789')

    my_id2 = await Users.find_all(dict(name='Eric'))
    print(my_id2)


if __name__ == '__main__':
    loop.run_until_complete(test())
    loop.close()