import asyncio
from www import orm
from www.models import Users

loop = asyncio.get_event_loop()


async def test():
    await orm.create_pool(loop=loop, user='lichenxi', password='Lichenxi20000110', db='awesome')

    # u = Users(name='Eric', email='eric@example.com', password='password', image='about:blank',
    #           id='1114859201505236139fca0300c4a53b3ec52bf92e5d961000')
    #
    # await u.save()

    my_id1 = await Users.find('0014859201505236139fca0300c4a53b3ec52bf92e5d961000')
    print(my_id1)

    await Users.delete('0014859201505236139fca0300c4a53b3ec52bf92e5d961000')
    # u = Users(id='0014859201505236139fca0300c4a53b3ec52bf92e5d961000', name='Eric', email='test@example.com',
    #           password='password', image='about:blank')
    # await u.update()
    #
    my_id2 = await Users.findall(where='name=?', args=['Eric'])
    print(my_id2)

    my_num = await Users.findnumber(where='name=?', args=['Eric'], select_field='name')


if __name__ == '__main__':
    loop.run_until_complete(test())
    loop.close()
