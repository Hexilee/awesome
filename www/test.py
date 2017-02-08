import asyncio
import orm
from models import Users, next_id
import hashlib

loop = asyncio.get_event_loop()


async def test():
    await orm.create_pool(loop=loop, user='lichenxi', password='Lichenxi20000110', db='awesome')
    for i in range(20):
        user_name = 'Robot%s' % str(i)
        user_email = '%s@example.com' % user_name
        user_id = next_id()
        user_password1 = hashlib.sha1(('%s:%s' % (user_email, user_email)).encode('utf-8')).hexdigest()
        user_password2 = hashlib.sha1(('%s:%s' % (user_id, user_password1)).encode('utf-8')).hexdigest()
        user = Users(id=user_id, email=user_email, name=user_name, password=user_password2, image=user_email)
        await user.save()

        # for name in ['Python', 'Java', 'Cpp']:
        #     u = Users(name=name, email='%s@example.com' % name, password='password', image='about:blank',)
        #     await u.save()
        #
        # my_id1 = await Users.find('001486046302169681e507fc7844bcaa09e7cea1af17a29000')
        # print(my_id1.name)
        #
        # # await Users.delete('0014859201505236139fca0300c4a53b3ec52bf92e5d961000')
        # # u = Users(id='0014859201505236139fca0300c4a53b3ec52bf92e5d961000', name='Eric', email='test@example.com',
        # #           password='password', image='about:blank')
        # # await u.update()
        # #
        # my_id2 = await Users.findall(where='name=?', args=['Lee'])
        # print(my_id2)

        # my_num = await Users.findnumber(select_field='count(name)', where='`name`=?', args=['Eric', ])


if __name__ == '__main__':
    loop.run_until_complete(test())
    loop.close()
