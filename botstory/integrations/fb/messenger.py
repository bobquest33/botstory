import json
import logging
from ... import utils

logger = logging.getLogger(__file__)


class FBInterface:
    type = 'interface.facebook'

    def __init__(self,
                 api_uri='https://graph.facebook.com/v2.6',
                 token=None):
        """

        :param token: should take from os.environ['FB_ACCESS_TOKEN']
        """
        self.api_uri = api_uri
        self.processor = None
        self.token = token

    async def send_text_message(self, session, recipient, text, options=[]):
        """
        async send message to the facebook user (recipient)

        :param session:
        :param recipient:
        :param text:
        :param options:

        :return:
        """

        if not options:
            options = []

        message = {
            'text': text,
        }

        quick_replies = [{**reply, 'content_type': 'text'} for reply in options]
        if len(quick_replies) > 0:
            message['quick_replies'] = quick_replies

        async with session.post(
                        self.api_uri + '/me/messages/',
                params={
                    'access_token': self.token,
                },
                headers={
                    'Content-Type': 'application/json'
                },
                data=json.dumps({
                    'recipient': {
                        'id': recipient.facebook_user_id,
                    },
                    'message': message,
                })) as resp:
            return await resp.json()

    async def get_session(self, user_id):
        # TODO: should get from extensions
        return self.session

    async def get_user(self, user_id):
        # TODO: should get from extensions
        return self.user

    async def handle(self, entry):
        logger.debug('')
        logger.debug('> handle <')
        logger.debug('')
        logger.debug('  entry: {}'.format(entry))
        for e in entry:
            messaging = e.get('messaging', [])
            logger.debug('  messaging: {}'.format(messaging))

            if len(messaging) == 0:
                logger.warning('  entry {} list lack of "messaging" field'.format(e))

            for m in messaging:
                logger.debug('  m: {}'.format(m))
                message = {
                    'session': await self.get_session(m['sender']['id']),
                    'user': await self.get_user(m['sender']['id']),
                }
                raw_message = m.get('message', {})

                if raw_message == {}:
                    logger.warning('  entry {} "message" field is empty'.format(e))

                logger.debug('  raw_message: {}'.format(raw_message))

                data = {}
                text = raw_message.get('text', None)
                if text is not None:
                    data['text'] = {
                        'raw': text,
                    }
                else:
                    logger.warning('  entry {} "text"'.format(e))

                quick_reply = raw_message.get('quick_reply', None)
                if quick_reply is not None:
                    data['option'] = quick_reply['payload']

                message['data'] = data

                await self.processor.match_message(message)
