import functools
import json
from .universal_analytics.tracker import Tracker

from ...utils import queue


class GAStatistics:
    type = 'interface.tracker'
    """
    pageview: [ page path ]
    event: category, action, [ label [, value ] ]
    social: network, action [, target ]
    timing: category, variable, time [, label ]
    """

    def __init__(self,
                 tracking_id,
                 story_tracking_template='{story}/{part}',
                 new_message_tracking_template='receive: {data}',
                 ):
        """
        :param tracking_id: should be like UA-XXXXX-Y
        """
        self.tracking_id = tracking_id
        self.story_tracking_template = story_tracking_template
        self.new_message_tracking_template = new_message_tracking_template

    def get_tracker(self, user):
        return Tracker(
            account=self.tracking_id,
            client_id=user and user['_id'],
        )

    def event(self, user,
              event_category=None,
              event_action=None,
              event_label=None,
              event_value=None,
              ):
        queue.add(
            functools.partial(self.get_tracker(user).send,
                              'event', event_category, event_action, event_label, event_value
                              )
        )

    def story(self, user, story_name, story_part_name):
        queue.add(
            functools.partial(self.get_tracker(user).send,
                              'pageview', self.story_tracking_template.format(story=story_name,
                                                                              part=story_part_name),
                              )
        )

    def new_message(self, user, data):
        queue.add(
            functools.partial(self.get_tracker(user).send,
                              'pageview', self.new_message_tracking_template.format(data=json.dumps(data)),
                              )
        )

    def new_user(self, user):
        queue.add(
            functools.partial(self.get_tracker(user).send,
                              'event',
                              'new_user', 'start', 'new user starts chat'
                              )
        )
