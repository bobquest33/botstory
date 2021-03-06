class Invalid(BaseException):
    pass


def greeting_text(message):
    """
    more: https://developers.facebook.com/docs/messenger-platform/thread-settings/greeting-text

    :param message:
    :return:
    """
    if len(message) > 160:
        raise Invalid('greeting text should not exceed 160 length in characters')


def persistent_menu(menu):
    """
    more: https://developers.facebook.com/docs/messenger-platform/thread-settings/persistent-menu

    :param menu:
    :return:
    """
    if len(menu) > 5:
        raise Invalid('menu should not exceed 5 call to actions')

    for item in menu:
        if len(item['title']) > 30:
            raise Invalid('menu item title should not exceed 30 characters')

        if item['type'] == 'postback' and len(item['payload']) > 1000:
            raise Invalid('menu item payload should not exceed 1000 characters')


def send_text_message(text, options):
    """
    more:
    https://developers.facebook.com/docs/messenger-platform/send-api-reference/text-message
     and
    https://developers.facebook.com/docs/messenger-platform/send-api-reference/quick-replies

    :param text:
    :param options:
    :return:
    """
    if len(text) > 320:
        raise Invalid('send message text should not exceed 320 character limit')

    if isinstance(options, list):
        if len(options) > 10:
            raise Invalid('send message quick replies should not exceed 10 limit')

        for item in options:
            if len(item['title']) > 20:
                raise Invalid('send message quick replies title should not exceed 20 character limit')
            if 'content_type' not in item:
                raise Invalid('send message quick replies should have content_type')
            if item['content_type'] == 'text' and len(item['payload']) > 1000:
                raise Invalid('send message quick replies payload should not exceed 1000 character limit')
