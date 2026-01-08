"""
Модули для работы с хранилищем данных
"""
from .memory import add_memory, get_history, get_recent_history
from .email_subscribers import (
    add_email_subscriber,
    remove_email_subscriber,
    get_email_subscribers,
    load_email_subscribers
)
from .user_data import (
    UserPhone,
    UserBookingData,
    UserWeeekWorkspace,
    UserAuth,
    get_user_phone,
    set_user_phone,
    get_user_booking_data,
    set_user_booking_data
)
from .user_records import (
    UserRecords,
    get_user_records,
    add_user_record,
    remove_user_record,
    get_user_records_list,
    format_user_record
)

__all__ = [
    'add_memory',
    'get_history',
    'get_recent_history',
    'add_email_subscriber',
    'remove_email_subscriber',
    'get_email_subscribers',
    'load_email_subscribers',
    'UserPhone',
    'UserBookingData',
    'UserWeeekWorkspace',
    'UserAuth',
    'get_user_phone',
    'set_user_phone',
    'get_user_booking_data',
    'set_user_booking_data',
    'UserRecords',
    'get_user_records',
    'add_user_record',
    'remove_user_record',
    'get_user_records_list',
    'format_user_record',
]
