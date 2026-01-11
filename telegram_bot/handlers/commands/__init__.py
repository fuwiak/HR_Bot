"""
Обработчики команд
"""
from .basic import start, menu, status_command, myid_command
from .rag import rag_search_command, rag_stats_command, rag_docs_command, rag_upload_command
from .weeek import (
    weeek_info_command,
    weeek_create_task_command,
    weeek_projects_command,
    weeek_create_project_command,
    weeek_update_command,
    weeek_tasks_command,
)
from .yadisk import yadisk_list_command, yadisk_search_command, yadisk_recent_command
from .email import email_check_command, email_draft_command, unsubscribe_command
from .tools import (
    summary_command,
    demo_proposal_command,
    hypothesis_command,
    report_command,
    upload_document_command,
)

__all__ = [
    # Basic
    'start',
    'menu',
    'status_command',
    'myid_command',
    # RAG
    'rag_search_command',
    'rag_stats_command',
    'rag_docs_command',
    'rag_upload_command',
    # WEEEK
    'weeek_info_command',
    'weeek_create_task_command',
    'weeek_projects_command',
    'weeek_create_project_command',
    'weeek_update_command',
    'weeek_tasks_command',
    # Yandex Disk
    'yadisk_list_command',
    'yadisk_search_command',
    'yadisk_recent_command',
    # Email
    'email_check_command',
    'email_draft_command',
    'unsubscribe_command',
    # Tools
    'summary_command',
    'demo_proposal_command',
    'hypothesis_command',
    'report_command',
    'upload_document_command',
]
