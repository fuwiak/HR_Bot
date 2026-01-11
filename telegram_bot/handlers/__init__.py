"""
Обработчики для Telegram бота
"""
from .commands import (
    start,
    menu,
    status_command,
    myid_command,
    rag_search_command,
    rag_stats_command,
    rag_docs_command,
    rag_upload_command,
    weeek_info_command,
    weeek_create_task_command,
    weeek_projects_command,
    weeek_create_project_command,
    weeek_update_command,
    weeek_tasks_command,
    yadisk_list_command,
    yadisk_search_command,
    yadisk_recent_command,
    email_check_command,
    email_draft_command,
    unsubscribe_command,
    summary_command,
    demo_proposal_command,
    hypothesis_command,
    report_command,
    upload_document_command,
)
from .menu import button_callback
from .messages import reply, handle_document

__all__ = [
    # Commands
    'start',
    'menu',
    'status_command',
    'myid_command',
    'rag_search_command',
    'rag_stats_command',
    'rag_docs_command',
    'rag_upload_command',
    'weeek_info_command',
    'weeek_create_task_command',
    'weeek_projects_command',
    'weeek_create_project_command',
    'weeek_update_command',
    'weeek_tasks_command',
    'yadisk_list_command',
    'yadisk_search_command',
    'yadisk_recent_command',
    'email_check_command',
    'email_draft_command',
    'unsubscribe_command',
    'summary_command',
    'demo_proposal_command',
    'hypothesis_command',
    'report_command',
    'upload_document_command',
    # Menu
    'button_callback',
    # Messages
    'reply',
    'handle_document',
]
