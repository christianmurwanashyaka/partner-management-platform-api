from fastapi import Depends
from notification.handlers import EmailNotificationHandler
from functools import lru_cache


@lru_cache()
def get_email_handler() -> EmailNotificationHandler:
    return EmailNotificationHandler()


def get_email_notification_handler(
    email_handler: EmailNotificationHandler = Depends(get_email_handler)
) -> EmailNotificationHandler:
    return email_handler
