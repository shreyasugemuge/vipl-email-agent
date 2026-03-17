"""Settings views: admin configuration for rules, visibility, SLA, inboxes, webhooks, whitelist."""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import HttpResponse as _HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import (
    AssignmentRule, CategoryVisibility, SLAConfig, SenderReputation,
    SpamWhitelist, Email,
)
from apps.emails.services.dtos import VALID_CATEGORIES, VALID_PRIORITIES

from .helpers import (
    _get_team_members,
    _render_whitelist_tab,
    _require_admin,
    _unspam_matching_emails,
)

logger = logging.getLogger(__name__)


@login_required
def settings_view(request):
    """Settings page: writable for admins, read-only for triage leads, denied for members."""
    if request.user.is_admin_only:
        readonly = False
    elif request.user.can_triage:
        readonly = True
    else:
        return HttpResponseForbidden("Access denied.")

    team_members = _get_team_members()
    active_tab = request.GET.get("tab", "rules")

    # Assignment rules grouped by category (list of tuples for template iteration)
    rules_by_category = []
    for cat in VALID_CATEGORIES:
        cat_rules = list(
            AssignmentRule.objects.filter(category=cat, is_active=True)
            .select_related("assignee")
            .order_by("priority_order")
        )
        rules_by_category.append((cat, cat_rules))

    # Category visibility grouped by user
    visibility_by_user = {}
    for member in team_members:
        visibility_by_user[member.pk] = set(
            CategoryVisibility.objects.filter(user=member).values_list("category", flat=True)
        )

    # SLA config as list
    sla_configs = {
        (c.priority, c.category): c
        for c in SLAConfig.objects.all()
    }
    sla_matrix = []
    for priority in VALID_PRIORITIES:
        for category in VALID_CATEGORIES:
            cfg = sla_configs.get((priority, category))
            sla_matrix.append({
                "priority": priority,
                "category": category,
                "ack_hours": cfg.ack_hours if cfg else 1.0,
                "respond_hours": cfg.respond_hours if cfg else 24.0,
                "exists": cfg is not None,
            })

    # Monitored inboxes for Inboxes tab
    raw_inboxes = SystemConfig.get("monitored_inboxes", "") or ""
    if isinstance(raw_inboxes, str):
        monitored_inboxes = [i.strip() for i in raw_inboxes.split(",") if i.strip()]
    else:
        monitored_inboxes = []

    # Config groups for System tab
    all_configs = SystemConfig.objects.all().order_by("category", "key")
    config_groups = {}
    for cfg in all_configs:
        cat = cfg.category or "general"
        config_groups.setdefault(cat, []).append(cfg)

    # Per-category webhook URLs
    category_webhooks = []
    for cat in VALID_CATEGORIES:
        url = SystemConfig.get(f"chat_webhook_{cat.lower()}", "") or ""
        category_webhooks.append({"category": cat, "webhook_url": url})

    # Whitelist entries for Whitelist tab
    whitelist_entries = SpamWhitelist.objects.select_related("added_by").all()

    # Blocked/tracked senders for Whitelist tab
    from django.db.models import Q as _Q2
    blocked_senders = SenderReputation.objects.filter(
        _Q2(spam_count__gt=0) | _Q2(is_blocked=True)
    ).order_by("-is_blocked", "-spam_count")

    # Alert config for SLA tab
    alert_threshold = SystemConfig.get("unassigned_alert_threshold", "5")
    alert_cooldown = SystemConfig.get("unassigned_alert_cooldown_minutes", "30")

    context = {
        "active_tab": active_tab,
        "team_members": team_members,
        "rules_by_category": rules_by_category,
        "visibility_by_user": visibility_by_user,
        "sla_matrix": sla_matrix,
        "valid_categories": VALID_CATEGORIES,
        "valid_priorities": VALID_PRIORITIES,
        "monitored_inboxes": monitored_inboxes,
        "config_groups": config_groups,
        "category_webhooks": category_webhooks,
        "whitelist_entries": whitelist_entries,
        "blocked_senders": blocked_senders,
        "readonly": readonly,
        "alert_threshold": alert_threshold,
        "alert_cooldown": alert_cooldown,
    }
    return render(request, "emails/settings.html", context)


@login_required
@require_POST
def settings_rules_save(request):
    """Save assignment rules: add, remove, or reorder."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    action = request.POST.get("action", "")
    category = request.POST.get("category", "")

    if action == "add":
        assignee_id = request.POST.get("assignee_id")
        if assignee_id and category:
            assignee = get_object_or_404(User, pk=assignee_id)
            max_order = (
                AssignmentRule.objects.filter(category=category)
                .order_by("-priority_order")
                .values_list("priority_order", flat=True)
                .first()
            ) or 0
            AssignmentRule.objects.get_or_create(
                category=category,
                assignee=assignee,
                defaults={"priority_order": max_order + 1},
            )

    elif action == "remove":
        assignee_id = request.POST.get("assignee_id")
        if assignee_id and category:
            AssignmentRule.objects.filter(
                category=category, assignee_id=assignee_id,
            ).delete()

    elif action == "reorder":
        assignee_ids = request.POST.getlist("assignee_ids[]")
        for idx, aid in enumerate(assignee_ids):
            AssignmentRule.objects.filter(
                category=category, assignee_id=aid,
            ).update(priority_order=idx)

    # Return partial for the category
    rules = list(
        AssignmentRule.objects.filter(category=category, is_active=True)
        .select_related("assignee")
        .order_by("priority_order")
    )
    team_members = _get_team_members()
    return render(request, "emails/_assignment_rules.html", {
        "category": category,
        "rules": rules,
        "team_members": team_members,
        "save_success": True,
    })


@login_required
@require_POST
def settings_visibility_save(request):
    """Save category visibility for a user (replace all)."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    user_id = request.POST.get("user_id")
    categories = request.POST.getlist("categories[]")

    if user_id:
        target_user = get_object_or_404(User, pk=user_id)
        # Delete existing and recreate
        CategoryVisibility.objects.filter(user=target_user).delete()
        CategoryVisibility.objects.bulk_create([
            CategoryVisibility(user=target_user, category=cat)
            for cat in categories
            if cat in VALID_CATEGORIES
        ])

    # Return updated partial
    team_members = _get_team_members()
    visibility_by_user = {}
    for member in team_members:
        visibility_by_user[member.pk] = set(
            CategoryVisibility.objects.filter(user=member).values_list("category", flat=True)
        )
    return render(request, "emails/_category_visibility.html", {
        "team_members": team_members,
        "visibility_by_user": visibility_by_user,
        "valid_categories": VALID_CATEGORIES,
        "save_success": True,
    })


@login_required
@require_POST
def settings_sla_save(request):
    """Save SLA config for a priority x category pair."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    priority = request.POST.get("priority", "")
    category = request.POST.get("category", "")
    ack_hours = request.POST.get("ack_hours", "1.0")
    respond_hours = request.POST.get("respond_hours", "24.0")

    if priority and category:
        try:
            ack_h = float(ack_hours)
            resp_h = float(respond_hours)
        except (ValueError, TypeError):
            ack_h, resp_h = 1.0, 24.0

        SLAConfig.objects.update_or_create(
            priority=priority,
            category=category,
            defaults={"ack_hours": ack_h, "respond_hours": resp_h},
        )

    # Return updated SLA table partial
    sla_configs = {
        (c.priority, c.category): c
        for c in SLAConfig.objects.all()
    }
    sla_matrix = []
    for p in VALID_PRIORITIES:
        for c in VALID_CATEGORIES:
            cfg = sla_configs.get((p, c))
            sla_matrix.append({
                "priority": p,
                "category": c,
                "ack_hours": cfg.ack_hours if cfg else 1.0,
                "respond_hours": cfg.respond_hours if cfg else 24.0,
                "exists": cfg is not None,
            })

    return render(request, "emails/_sla_config.html", {
        "sla_matrix": sla_matrix,
        "valid_priorities": VALID_PRIORITIES,
        "valid_categories": VALID_CATEGORIES,
        "save_success": True,
    })


@login_required
@require_POST
def settings_inboxes_save(request):
    """Add or remove a monitored inbox email address."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    action = request.POST.get("action", "")
    inbox_email = request.POST.get("inbox_email", "").strip()

    cfg, _created = SystemConfig.objects.get_or_create(
        key="monitored_inboxes",
        defaults={"value": "", "value_type": "str", "category": "email"},
    )
    current = [i.strip() for i in cfg.value.split(",") if i.strip()]

    if action == "add" and inbox_email and inbox_email not in current:
        current.append(inbox_email)
    elif action == "remove" and inbox_email in current:
        current.remove(inbox_email)

    cfg.value = ",".join(current)
    cfg.save(update_fields=["value", "updated_at"])

    return render(request, "emails/_inboxes_tab.html", {
        "monitored_inboxes": current,
        "save_success": True,
    })


@login_required
@require_POST
def settings_config_save(request):
    """Save SystemConfig values for a category group."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    category = request.POST.get("category", "")
    configs_in_cat = SystemConfig.objects.filter(category=category) if category else SystemConfig.objects.none()

    for cfg in configs_in_cat:
        field_name = f"config_{cfg.key}"
        if field_name in request.POST:
            new_val = request.POST.get(field_name, "")
            cfg.value = new_val
            cfg.save(update_fields=["value", "updated_at"])
        elif cfg.value_type == "bool":
            # Unchecked checkbox means false
            cfg.value = "false"
            cfg.save(update_fields=["value", "updated_at"])

    # Rebuild config_groups for full re-render
    all_configs = SystemConfig.objects.all().order_by("category", "key")
    config_groups = {}
    for c in all_configs:
        cat = c.category or "general"
        config_groups.setdefault(cat, []).append(c)

    return render(request, "emails/_config_editor.html", {
        "config_groups": config_groups,
        "save_success": True,
    })


@login_required
@require_POST
def settings_alert_save(request):
    """Save unassigned alert threshold and cooldown settings."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    alert_threshold = request.POST.get("unassigned_alert_threshold", "").strip()
    if alert_threshold:
        SystemConfig.objects.update_or_create(
            key="unassigned_alert_threshold",
            defaults={"value": alert_threshold, "value_type": SystemConfig.ValueType.INT, "category": "alerts"},
        )

    alert_cooldown = request.POST.get("unassigned_alert_cooldown_minutes", "").strip()
    if alert_cooldown:
        SystemConfig.objects.update_or_create(
            key="unassigned_alert_cooldown_minutes",
            defaults={"value": alert_cooldown, "value_type": SystemConfig.ValueType.INT, "category": "alerts"},
        )

    return _HttpResponse(
        '<div class="px-3 py-2 bg-emerald-50 border border-emerald-200/60 rounded-lg text-xs font-medium text-emerald-700">'
        'Alert settings saved.</div>'
    )


@login_required
@require_POST
def settings_webhooks_save(request):
    """Save per-category Google Chat webhook URLs."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    for cat in VALID_CATEGORIES:
        field_name = f"webhook_{cat.lower()}"
        if field_name in request.POST:
            new_url = request.POST.get(field_name, "").strip()
            config_key = f"chat_webhook_{cat.lower()}"
            SystemConfig.objects.update_or_create(
                key=config_key,
                defaults={
                    "value": new_url,
                    "value_type": "str",
                    "category": "notifications",
                    "description": f"Google Chat webhook for {cat} emails",
                },
            )

    category_webhooks = []
    for cat in VALID_CATEGORIES:
        url = SystemConfig.get(f"chat_webhook_{cat.lower()}", "") or ""
        category_webhooks.append({"category": cat, "webhook_url": url})

    return render(request, "emails/_webhooks_tab.html", {
        "category_webhooks": category_webhooks,
        "save_success": True,
    })


@login_required
@require_POST
def whitelist_add(request):
    """Add a new whitelist entry. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    entry = request.POST.get("entry", "").strip().lower()
    entry_type = request.POST.get("entry_type", "email")

    if not entry:
        return _render_whitelist_tab(
            request, save_error="Entry cannot be empty.",
        )

    if entry_type not in ("email", "domain"):
        entry_type = "email"

    from django.db import IntegrityError, transaction

    try:
        with transaction.atomic():
            SpamWhitelist.objects.create(
                entry=entry,
                entry_type=entry_type,
                added_by=request.user,
            )
        updated = _unspam_matching_emails(entry, entry_type)
        msg = f"{entry} added to whitelist."
        if updated:
            msg += f" {updated} email(s) unmarked as spam."
        return _render_whitelist_tab(
            request, save_success=True, save_message=msg,
        )
    except IntegrityError:
        return _render_whitelist_tab(
            request, save_error=f"{entry} is already whitelisted.",
        )


@login_required
@require_POST
def whitelist_delete(request, pk):
    """Soft-delete a whitelist entry. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    wl = get_object_or_404(SpamWhitelist, pk=pk)
    wl.delete()  # soft delete via SoftDeleteModel
    return _render_whitelist_tab(
        request, save_success=True,
        save_message="Entry removed from whitelist.",
    )
