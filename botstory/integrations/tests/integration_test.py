import logging
import os

import pytest

from . import fake_server
from .. import aiohttp, fb, mongodb, mockhttp
from ... import di, Story, utils

logger = logging.getLogger(__name__)


story = None


def teardown_function(function):
    logger.debug('tear down!')
    story and story.clear()


@pytest.fixture
def build_context():
    async def builder(db, no_session=False, no_user=False):
        user = None
        if not no_user:
            user = utils.build_fake_user()
            await db.set_user(user)

        if not no_session:
            session = utils.build_fake_session(user=user)
            await db.set_session(session)

        global story
        story = Story()
        story.use(db)
        fb_interface = story.use(fb.FBInterface(page_access_token='qwerty'))
        http = story.use(mockhttp.MockHttpInterface())

        await story.start()

        return fb_interface, http, story, user

    return builder


@pytest.fixture
@pytest.mark.asyncio
def open_db():
    class AsyncDBConnection:
        def __init__(self):
            self.db_interface = mongodb.MongodbInterface(uri=os.environ.get('TEST_MONGODB_URL', 'mongo'),
                                                         db_name='test')

        async def __aenter__(self):
            await self.db_interface.start()
            await self.db_interface.clear_collections()
            return self.db_interface

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.db_interface.stop()
            await self.db_interface.clear_collections()
            self.db_interface = None

    return AsyncDBConnection


@pytest.mark.asyncio
async def test_facebook_interface_should_use_aiohttp_to_post_message(event_loop):
    async with fake_server.fake_fb.FakeFacebook(event_loop) as server:
        async with server.session() as server_session:
            # 1) setup app

            global story
            story = Story()

            try:
                story.use(fb.FBInterface(
                    webhook_url='/webhook',
                ))
                http_integration = story.use(aiohttp.AioHttpInterface())
                # TODO: could be better. Mock http interface
                http_integration.session = server_session

                await story.start()

                user = utils.build_fake_user()

                await story.say('Pryvit!', user=user)

                assert len(server.history) > 0
                req = server.history[-1]['request']
                assert req.content_type == 'application/json'
                assert await req.json() == {
                    'recipient': {
                        'id': user['facebook_user_id'],
                    },
                    'message': {
                        'text': 'Pryvit!'
                    }
                }
            finally:
                await story.stop()


@pytest.mark.asyncio
async def test_integrate_mongodb_with_facebook(open_db, build_context):
    async with open_db() as mongodb:
        facebook, _, story, user = await build_context(mongodb)

        trigger = utils.SimpleTrigger()

        @story.on('hello, world!')
        def correct_story():
            @story.part()
            def store_result(message):
                trigger.receive(message)

        await facebook.handle({
            'object': 'page',
            'entry': [{
                'id': 'PAGE_ID',
                'time': 1473204787206,
                'messaging': [{
                    'sender': {
                        'id': user['facebook_user_id'],
                    },
                    'recipient': {
                        'id': 'PAGE_ID'
                    },
                    'timestamp': 1458692752478,
                    'message': {
                        'mid': 'mid.1457764197618:41d102a3e1ae206a38',
                        'seq': 73,
                        'text': 'hello, world!'
                    }
                }
                ]
            }]
        })

        del trigger.value['session']
        assert trigger.value == {
            'user': user,
            'data': {
                'text': {
                    'raw': 'hello, world!'
                }
            }
        }


@pytest.mark.asyncio
async def test_integrate_mongodb_with_facebook_with_none_session(open_db, build_context):
    async with open_db() as mongodb:
        facebook, _, story, _ = await build_context(mongodb, no_session=True, no_user=True)

        trigger = utils.SimpleTrigger()

        @story.on('hello, world!')
        def correct_story():
            @story.part()
            def store_result_for_new_user(message):
                trigger.receive(message)

        await facebook.handle({
            'object': 'page',
            'entry': [{
                'id': 'PAGE_ID',
                'time': 1473204787206,
                'messaging': [{
                    'sender': {
                        'id': 'some-facebook-id',
                    },
                    'recipient': {
                        'id': 'PAGE_ID'
                    },
                    'timestamp': 1458692752478,
                    'message': {
                        'mid': 'mid.1457764197618:41d102a3e1ae206a38',
                        'seq': 73,
                        'text': 'hello, world!'
                    }
                }]
            }]
        })

        assert trigger.value
        assert trigger.value['data']['text']['raw'] == 'hello, world!'
        assert trigger.value['user']['facebook_user_id'] == 'some-facebook-id'


@pytest.mark.asyncio
async def test_story_on_start(open_db, build_context):
    async with open_db() as mongodb:
        facebook, http, story, _ = await build_context(mongodb)

        trigger = utils.SimpleTrigger()

        @story.on_start()
        def just_meet():
            @story.part()
            def greeting(message):
                trigger.passed()

        await story.setup()

        http.delete.assert_called_with(
            'https://graph.facebook.com/v2.6/me/thread_settings',
            params={
                'access_token': 'qwerty',
            },
            json={
                'setting_type': 'call_to_actions',
                'thread_state': 'new_thread',
            }
        )

        http.post.assert_called_with(
            'https://graph.facebook.com/v2.6/me/thread_settings',
            params={
                'access_token': 'qwerty',
            },
            json={
                'setting_type': 'call_to_actions',
                'thread_state': 'new_thread',
                'call_to_actions': [
                    {
                        'payload': 'BOT_STORY.PUSH_GET_STARTED_BUTTON'
                    }
                ]
            }
        )

        await story.start()

        await facebook.handle({
            'object': 'page',
            'entry': [{
                'id': 'PAGE_ID',
                'time': 1473204787206,
                'messaging': [{
                    'sender': {
                        'id': 'USER_ID'
                    },
                    'recipient': {
                        'id': 'PAGE_ID'
                    },
                    'timestamp': 1458692752478,
                    'postback': {
                        'payload': 'BOT_STORY.PUSH_GET_STARTED_BUTTON'
                    }
                }]
            }]
        })

        assert trigger.is_triggered


@pytest.mark.asyncio
async def test_should_not_setup_call_to_action_for_new_thread_if_we_dont_have_on_start(open_db, build_context):
    async with open_db() as mongodb:
        facebook, http, story, _ = await build_context(mongodb)

        @story.on('hi')
        def one_story():
            @story.part()
            def greeting(message):
                pass

        await story.start()

        # TODO: check whether we've told to fb that start button generate
        # `BOT_STORY.PUSH_GET_STARTED_BUTTON` payload
        assert not http.post.called, 'setup thread'
