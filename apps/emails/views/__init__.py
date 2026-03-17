"""Email views package — split from monolithic views.py for maintainability."""

from .helpers import annotate_unread, get_active_viewers

from .pages import (
    thread_list, sidebar_counts_view, reports_view, activity_log, inspect, force_poll,
)
from .threads import (
    accept_thread_suggestion, reject_thread_suggestion,
    viewer_heartbeat, clear_viewer, thread_detail,
    mark_thread_unread, edit_ai_summary, edit_category, edit_priority, edit_status,
    thread_context_menu, add_note_view, assign_thread_view,
    change_thread_status_view, claim_thread_view, reassign_thread_view,
    whitelist_sender_from_thread, mark_spam, mark_not_spam,
    mark_irrelevant, revert_irrelevant, undo_spam_feedback, unblock_sender,
    bulk_assign, bulk_mark_irrelevant, bulk_undo,
)
from .settings import (
    settings_view, settings_rules_save, settings_visibility_save,
    settings_sla_save, settings_inboxes_save, settings_config_save,
    settings_alert_save, settings_webhooks_save,
    whitelist_add, whitelist_delete,
)

__all__ = [
    # helpers (used by tests)
    "annotate_unread",
    "get_active_viewers",
    # pages
    "thread_list",
    "sidebar_counts_view",
    "reports_view",
    "activity_log",
    "inspect",
    "force_poll",
    # threads
    "accept_thread_suggestion",
    "reject_thread_suggestion",
    "viewer_heartbeat",
    "clear_viewer",
    "thread_detail",
    "mark_thread_unread",
    "edit_ai_summary",
    "edit_category",
    "edit_priority",
    "edit_status",
    "thread_context_menu",
    "add_note_view",
    "assign_thread_view",
    "change_thread_status_view",
    "claim_thread_view",
    "reassign_thread_view",
    "whitelist_sender_from_thread",
    "mark_spam",
    "mark_not_spam",
    "mark_irrelevant",
    "revert_irrelevant",
    "undo_spam_feedback",
    "unblock_sender",
    "bulk_assign",
    "bulk_mark_irrelevant",
    "bulk_undo",
    # settings
    "settings_view",
    "settings_rules_save",
    "settings_visibility_save",
    "settings_sla_save",
    "settings_inboxes_save",
    "settings_config_save",
    "settings_alert_save",
    "settings_webhooks_save",
    "whitelist_add",
    "whitelist_delete",
]
