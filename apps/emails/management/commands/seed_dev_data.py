"""Seed dev database with realistic users, threads, and varied states.

Creates:
- 5 users across admin/member roles
- 25 threads with varied statuses, assignments, AI suggestions, confidence tiers
- Activity logs, read states, spam threads

Usage:
    python manage.py seed_dev_data
    python manage.py seed_dev_data --reset   # Delete existing seed data first
"""

import random
from datetime import timedelta

import pytz
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import Thread, Email, ActivityLog, ThreadReadState
from apps.emails.services.dtos import EmailMessage, TriageResult
from apps.emails.services.fake_data import make_fake_email, make_fake_triage
from apps.emails.services.pipeline import save_email_to_db

IST = pytz.timezone("Asia/Kolkata")

# Dev users: (first, last, username, email, role, is_staff, is_active)
DEV_USERS = [
    ("Shreyas", "Ugemuge", "shreyas", "shreyas@vidarbhainfotech.com", User.Role.ADMIN, True, True),
    ("Aniket", "Patil", "aniket", "aniket@vidarbhainfotech.com", User.Role.ADMIN, True, True),
    ("Pooja", "Deshmukh", "pooja", "pooja@vidarbhainfotech.com", User.Role.MEMBER, False, True),
    ("Vishal", "Raut", "vishal", "vishal@vidarbhainfotech.com", User.Role.MEMBER, False, True),
    ("Sneha", "Kadam", "sneha", "sneha@vidarbhainfotech.com", User.Role.MEMBER, False, True),
    ("Rahul", "Joshi", "rahul", "rahul@vidarbhainfotech.com", User.Role.MEMBER, False, False),  # pending approval
]

PASSWORD = "devpass123"

# Extra emails beyond the 11 in fake_data.py (indices 11–24)
_EXTRA_EMAILS = [
    # 11 - Follow-up complaint
    {
        "sender_name": "Rakesh Mehta",
        "sender_email": "rakesh.mehta@mehtaexports.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Billing portal not generating invoices since Monday",
        "body": "Hi team,\n\nOur billing portal hasn't generated invoices since Monday. Clients are calling us. This is urgent — we need a fix today.\n\nRakesh Mehta\nMehta Exports",
        "category": "Support Request", "priority": "HIGH",
        "summary": "Billing portal down since Monday, no invoices generated. Client-facing impact.",
        "reasoning": "Production issue affecting billing. Client escalation risk.",
        "language": "English", "tags": ["support", "billing", "urgent"],
        "suggested_assignee": "Pooja", "confidence": "HIGH",
    },
    # 12 - Internship inquiry
    {
        "sender_name": "Sakshi Thakur",
        "sender_email": "sakshi.thakur2026@gmail.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Internship inquiry - B.Tech CSE final year",
        "body": "Dear Sir/Madam,\n\nI am a final year B.Tech CSE student at VNIT Nagpur. I am interested in a 6-month internship in web development. I have experience with React and Django.\n\nRegards,\nSakshi Thakur",
        "category": "General Inquiry", "priority": "LOW",
        "summary": "VNIT student seeking 6-month web dev internship. React + Django experience.",
        "reasoning": "Internship inquiry, not revenue-generating. Low priority but worth routing to HR.",
        "language": "English", "tags": ["internship", "hiring"],
        "suggested_assignee": "", "confidence": "MEDIUM",
    },
    # 13 - AMC renewal
    {
        "sender_name": "Manoj Kale",
        "sender_email": "manoj.kale@nmc.gov.in",
        "inbox": "sales@vidarbhainfotech.com",
        "subject": "AMC Renewal - Property Tax Module FY 2026-27",
        "body": "Dear Vidarbha Infotech,\n\nThe AMC for Property Tax Module is expiring on 31 March 2026. Please send the renewal proposal with updated terms.\n\nManoj Kale\nIT Department, NMC",
        "category": "Sales Lead", "priority": "HIGH",
        "summary": "NMC Property Tax Module AMC renewal due 31 March. Renewal proposal requested.",
        "reasoning": "Existing client AMC renewal. Revenue retention, deadline approaching.",
        "language": "English", "tags": ["amc", "renewal", "nmc", "government"],
        "suggested_assignee": "Shreyas", "confidence": "HIGH",
    },
    # 14 - Server monitoring alert
    {
        "sender_name": "UptimeRobot",
        "sender_email": "alert@uptimerobot.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Monitor is DOWN: client-portal.mehtaexports.com",
        "body": "Your monitor client-portal.mehtaexports.com is currently DOWN.\n\nStarted: 2026-03-16 09:45 IST\nReason: Connection Timeout\n\nThis is an automated alert from UptimeRobot.",
        "category": "Support Request", "priority": "CRITICAL",
        "summary": "Mehta Exports client portal is DOWN. UptimeRobot alert, connection timeout.",
        "reasoning": "Automated downtime alert for client portal. Needs immediate investigation.",
        "language": "English", "tags": ["alert", "downtime", "monitoring"],
        "suggested_assignee": "Pooja", "confidence": "HIGH",
    },
    # 15 - Quotation request
    {
        "sender_name": "Sunita Deshpande",
        "sender_email": "sunita.d@wardhaschool.edu.in",
        "inbox": "sales@vidarbhainfotech.com",
        "subject": "Quotation needed - School ERP system for 1500 students",
        "body": "Hello,\n\nWardha Public School is looking for an ERP system covering admissions, fees, attendance, and report cards. Student strength is approximately 1500.\n\nPlease share a quotation and demo availability.\n\nSunita Deshpande\nPrincipal, Wardha Public School",
        "category": "Sales Lead", "priority": "HIGH",
        "summary": "School ERP needed for 1500 students. Admissions, fees, attendance, report cards.",
        "reasoning": "Education sector lead, clear requirements. Demo + quotation requested.",
        "language": "English", "tags": ["sales", "erp", "education"],
        "suggested_assignee": "Aniket", "confidence": "HIGH",
    },
    # 16 - Spam
    {
        "sender_name": "SEO Experts Pro",
        "sender_email": "deals@seoexpertspro.biz",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Get your website to #1 on Google in 7 days!!!",
        "body": "Dear webmaster,\n\nWe guarantee first page Google rankings in just 7 days. 100% money-back guarantee. Limited slots available. Reply NOW!\n\nwww.seo-magic-results.biz",
        "category": "General Inquiry", "priority": "LOW",
        "summary": "Spam - fake SEO service promising instant Google rankings.",
        "reasoning": "Obvious spam: unrealistic promises, suspicious domain, urgency tactics.",
        "language": "English", "tags": ["spam"],
        "suggested_assignee": "", "confidence": "",
        "is_spam": True, "spam_score": 0.92,
    },
    # 17 - Payment follow-up (Hindi)
    {
        "sender_name": "Arun Gawande",
        "sender_email": "arun.gawande@zpyavatmal.gov.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Payment pending - ZP Yavatmal project invoice #VIP/2025/089",
        "body": "Namaskar,\n\nHumne aapka invoice #VIP/2025/089 receive kiya hai. Payment process mein hai, next week tak release ho jayega. Kripya patience rakhein.\n\nDhanyavaad,\nArun Gawande\nAccounts, ZP Yavatmal",
        "category": "Vendor", "priority": "MEDIUM",
        "summary": "ZP Yavatmal confirms payment for invoice VIP/2025/089, expected next week.",
        "reasoning": "Payment confirmation from government client. Track for follow-up if not received.",
        "language": "Hindi", "tags": ["payment", "government", "follow-up"],
        "suggested_assignee": "Shreyas", "confidence": "MEDIUM",
    },
    # 18 - Partnership (cloud)
    {
        "sender_name": "Kavita Nair",
        "sender_email": "kavita.nair@azurepartners.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Microsoft Azure Partner Program - Invitation to join",
        "body": "Dear Team,\n\nMicrosoft is expanding its Azure Partner Network in central India. We invite Vidarbha Infotech to apply for Silver/Gold partnership. Benefits include Azure credits, co-sell opportunities, and MPN listing.\n\nLet's schedule a call.\n\nKavita Nair\nPartner Development, Microsoft India",
        "category": "Partnership", "priority": "MEDIUM",
        "summary": "Microsoft Azure partner program invitation. Silver/Gold tier, Azure credits offered.",
        "reasoning": "Strategic partnership opportunity. Worth evaluating but not urgent.",
        "language": "English", "tags": ["partnership", "azure", "microsoft"],
        "suggested_assignee": "Shreyas", "confidence": "MEDIUM",
    },
    # 19 - Urgent complaint (Marathi)
    {
        "sender_name": "Deepak Borkar",
        "sender_email": "deepak.borkar@gmail.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "App crash hoto - Amravati Municipal water bill payment",
        "body": "Namaskar,\n\nAmravati Municipal Corporation che water bill payment app crash hot aahe. Nagarik phone karat aahet ki bill bharta yet nahi. Deadline 20 March aahe, tyapurvi fix karave.\n\nDeepak Borkar\nIT Cell, Amravati Municipal Corporation",
        "category": "Complaint", "priority": "CRITICAL",
        "summary": "Water bill payment app crashing for Amravati MC. Citizen-facing, deadline 20 March.",
        "reasoning": "Government client, citizen-facing app down. Hard deadline approaching. Critical.",
        "language": "Marathi", "tags": ["complaint", "app-crash", "government", "deadline"],
        "suggested_assignee": "Pooja", "confidence": "HIGH",
    },
    # 20 - Newsletter (low value)
    {
        "sender_name": "TechCrunch Daily",
        "sender_email": "newsletter@techcrunch.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "TechCrunch Daily: AI startups raise $2B in Q1 2026",
        "body": "Good morning!\n\nToday's top stories:\n- AI startups raise $2B in Q1 2026\n- Google announces Gemini 3.0\n- India's SaaS market grows 45% YoY\n\nRead more at techcrunch.com",
        "category": "General Inquiry", "priority": "LOW",
        "summary": "TechCrunch newsletter. No action needed.",
        "reasoning": "Automated newsletter, not business-relevant. Can be ignored.",
        "language": "English", "tags": ["newsletter", "automated"],
        "suggested_assignee": "", "confidence": "LOW",
    },
    # 21 - Recruitment agency
    {
        "sender_name": "Prashant Jha",
        "sender_email": "prashant@hirenow.co.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Python developers available - Immediate joining",
        "body": "Hello,\n\nWe have 3 Python/Django developers with 3-5 years experience available for immediate joining in Nagpur. Salary range 6-10 LPA.\n\nPlease let us know if you have openings.\n\nPrashant Jha\nHireNow Recruitment",
        "category": "Vendor", "priority": "LOW",
        "summary": "Recruitment agency offering Python/Django developers in Nagpur.",
        "reasoning": "Unsolicited vendor outreach. Low priority unless actively hiring.",
        "language": "English", "tags": ["vendor", "recruitment", "hiring"],
        "suggested_assignee": "", "confidence": "MEDIUM",
    },
    # 22 - Feature request from client
    {
        "sender_name": "Dr. Ashok Kulkarni",
        "sender_email": "ashok.k@nagpureyecare.com",
        "inbox": "sales@vidarbhainfotech.com",
        "subject": "Feature request - OPD queue display for patients",
        "body": "Dear Shreyas,\n\nWe have been using your HMS for 6 months now, very happy with it. One feature request — can you add a TV display board showing OPD queue token numbers? Patients keep asking reception.\n\nHappy to pay extra for this module.\n\nDr. Ashok Kulkarni\nNagpur Eye Care Centre",
        "category": "Support Request", "priority": "MEDIUM",
        "summary": "Existing HMS client requesting OPD queue TV display feature. Willing to pay extra.",
        "reasoning": "Feature request from paying client. Upsell opportunity. Medium priority.",
        "language": "English", "tags": ["feature-request", "hms", "client"],
        "suggested_assignee": "Aniket", "confidence": "MEDIUM",
    },
    # 23 - Compliance/audit
    {
        "sender_name": "CA Nitin Agrawal",
        "sender_email": "nitin@agrawalassociates.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "GST audit data request - FY 2025-26",
        "body": "Dear Management,\n\nAs part of the GST audit for FY 2025-26, we need the following:\n1. All invoices with GST breakup\n2. Input tax credit register\n3. E-way bill summary\n\nPlease share by 25 March.\n\nCA Nitin Agrawal\nAgrawal & Associates, Chartered Accountants",
        "category": "Internal", "priority": "MEDIUM",
        "summary": "CA requesting GST audit data for FY 2025-26. Deadline 25 March.",
        "reasoning": "Compliance requirement from auditor. Internal action needed, firm deadline.",
        "language": "English", "tags": ["compliance", "audit", "gst", "internal"],
        "suggested_assignee": "Shreyas", "confidence": "MEDIUM",
    },
    # 24 - Multi-thread follow-up (same sender as #0, different subject)
    {
        "sender_name": "Rajesh Patil",
        "sender_email": "rajesh.patil@mahatenders.gov.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Corrigendum - ZP Nagpur IT Tender deadline extended to 25 March",
        "body": "Dear Bidders,\n\nThis is to notify that the tender deadline for ZPN/IT/2026/047 has been extended to 25 March 2026 due to technical issues on the e-Procurement portal.\n\nAll other terms remain unchanged.\n\nRajesh Patil\nDistrict Informatics Officer",
        "category": "Government/Tender", "priority": "HIGH",
        "summary": "ZP Nagpur IT tender deadline extended to 25 March (was 18 March). Corrigendum.",
        "reasoning": "Important update to existing tender. Deadline extension gives more time.",
        "language": "English", "tags": ["tender", "government", "corrigendum", "deadline"],
        "suggested_assignee": "Aniket", "confidence": "HIGH",
    },
]


class Command(BaseCommand):
    help = "Seed local dev DB with 25 threads, 5 users, varied states"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete threads created by previous seed before re-seeding",
        )

    def handle(self, **options):
        if options["reset"]:
            self._reset()

        users = self._ensure_users()
        shreyas, aniket, pooja, vishal, sneha, _rahul = users

        # Build 25 thread specs: (assigned_to, assigned_by, status, confidence_override, is_auto, read_by)
        specs = [
            # -- Original 11 from fake_data pool (indices 0-10) --
            (None,     None,    "new",          "HIGH",   False, []),            # 0  tender, suggestion→Aniket
            (shreyas,  aniket,  "acknowledged", "HIGH",   False, [shreyas]),     # 1  sales, assigned+acked
            (pooja,    None,    "new",          "HIGH",   True,  []),            # 2  support, auto-assigned
            (shreyas,  aniket,  "new",          "MEDIUM", False, []),            # 3  complaint, unread
            (None,     None,    "new",          "MEDIUM", False, []),            # 4  partnership, suggestion→Shreyas
            (None,     None,    "new",          "LOW",    False, []),            # 5  vendor, no suggestion
            (shreyas,  shreyas, "closed",       "LOW",    False, [shreyas, aniket]),  # 6  internal, closed
            (vishal,   aniket,  "acknowledged", "MEDIUM", False, [vishal]),      # 7  inquiry, acked
            (None,     None,    "new",          "",       False, []),            # 8  spam
            (aniket,   shreyas, "new",          "HIGH",   False, []),            # 9  tender marathi
            (None,     None,    "reopened",     "HIGH",   False, []),            # 10 hospital, suggestion→Shreyas

            # -- Extra 14 threads (indices 11-24) --
            (pooja,    aniket,  "new",          None,     False, []),            # 11 billing urgent
            (None,     None,    "new",          None,     False, []),            # 12 internship, no suggestion
            (shreyas,  shreyas, "new",          None,     False, []),            # 13 AMC renewal
            (pooja,    None,    "acknowledged", None,     True,  [pooja]),       # 14 server down, auto+acked
            (None,     None,    "new",          None,     False, []),            # 15 school ERP, suggestion→Aniket
            (None,     None,    "new",          None,     False, []),            # 16 spam #2
            (shreyas,  aniket,  "acknowledged", None,     False, [shreyas]),     # 17 payment followup
            (None,     None,    "new",          None,     False, []),            # 18 azure partnership, suggestion→Shreyas
            (pooja,    shreyas, "new",          None,     False, []),            # 19 app crash critical
            (None,     None,    "new",          None,     False, []),            # 20 newsletter, no suggestion
            (None,     None,    "new",          None,     False, []),            # 21 recruitment, no suggestion
            (aniket,   shreyas, "acknowledged", None,     False, [aniket]),      # 22 feature request
            (sneha,    aniket,  "new",          None,     False, []),            # 23 GST audit
            (aniket,   shreyas, "new",          None,     False, []),            # 24 tender corrigendum
        ]

        now = timezone.now()
        created = 0

        for i, spec in enumerate(specs):
            assigned_to, assigned_by, status, conf_override, auto_assigned, read_by = spec

            if i < 11:
                # Use fake_data pool
                email_msg = make_fake_email(index=i)
                triage = make_fake_triage(index=i)
                if conf_override is not None:
                    triage.confidence = conf_override
            else:
                # Use extra emails
                extra = _EXTRA_EMAILS[i - 11]
                email_msg = EmailMessage(
                    thread_id=f"seed_thread_{i:04d}",
                    message_id=f"seed_msg_{i:04d}",
                    inbox=extra["inbox"],
                    sender_name=extra["sender_name"],
                    sender_email=extra["sender_email"],
                    subject=extra["subject"],
                    body=extra["body"],
                    timestamp=now - timedelta(hours=random.randint(1, 72), minutes=random.randint(0, 59)),
                    gmail_link=f"https://mail.google.com/mail/u/0/#inbox/seed_thread_{i:04d}",
                )
                triage = TriageResult(
                    category=extra["category"],
                    priority=extra["priority"],
                    summary=extra["summary"],
                    reasoning=extra["reasoning"],
                    language=extra["language"],
                    tags=extra["tags"],
                    suggested_assignee=extra["suggested_assignee"],
                    model_used="seed-data",
                    confidence=extra.get("confidence", ""),
                    is_spam=extra.get("is_spam", False),
                    spam_score=extra.get("spam_score", 0.0),
                )
                if conf_override is not None:
                    triage.confidence = conf_override

            email_msg.subject = f"[SEED] {email_msg.subject}"
            email_obj = save_email_to_db(email_msg, triage)
            thread = email_obj.thread

            # Set thread state
            thread.assigned_to = assigned_to
            thread.assigned_by = assigned_by
            thread.status = status
            thread.ai_confidence = triage.confidence
            thread.is_auto_assigned = auto_assigned
            if assigned_to:
                thread.assigned_at = now - timedelta(hours=random.randint(0, 24))
            thread.save(update_fields=[
                "assigned_to", "assigned_by", "assigned_at",
                "status", "ai_confidence", "is_auto_assigned", "updated_at",
            ])

            # Activity logs
            if assigned_to and assigned_by:
                act = ActivityLog.Action.AUTO_ASSIGNED if auto_assigned else ActivityLog.Action.ASSIGNED
                ActivityLog.objects.create(
                    thread=thread, user=assigned_by, action=act,
                    detail=f"Assigned to {assigned_to.get_full_name()}",
                )
            if status == "acknowledged" and assigned_to:
                ActivityLog.objects.create(
                    thread=thread, user=assigned_to,
                    action=ActivityLog.Action.ACKNOWLEDGED,
                    detail="Acknowledged thread",
                )
            if status == "closed" and assigned_to:
                ActivityLog.objects.create(
                    thread=thread, user=assigned_to,
                    action=ActivityLog.Action.CLOSED,
                    detail="Closed thread",
                )

            # Read states
            for u in read_by:
                ThreadReadState.objects.update_or_create(
                    thread=thread, user=u,
                    defaults={"read_at": now},
                )

            created += 1
            label = f"→ {assigned_to.username}" if assigned_to else "→ unassigned"
            conf = triage.confidence or "—"
            extra_tags = []
            if auto_assigned:
                extra_tags.append("auto")
            if triage.is_spam:
                extra_tags.append("spam")
            suffix = f" ({', '.join(extra_tags)})" if extra_tags else ""
            self.stdout.write(
                f"  [{i+1:2d}] {thread.subject[:50]:<50}  "
                f"{label:<16} {status:<14} [{conf}]{suffix}"
            )

        # Summary
        self.stdout.write("")
        unassigned = sum(1 for s in specs if s[0] is None)
        assigned = len(specs) - unassigned
        spam_count = sum(1 for i in range(len(specs)) if i == 8 or (i >= 11 and _EXTRA_EMAILS[i - 11].get("is_spam")))
        auto_count = sum(1 for s in specs if s[4])
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} threads, {len(DEV_USERS)} users."))
        self.stdout.write(f"  Assigned: {assigned}  |  Unassigned: {unassigned}  |  Spam: {spam_count}  |  Auto: {auto_count}")
        self.stdout.write("")
        self.stdout.write("Login at /accounts/login/:")
        for first, last, username, email, role, _, is_active in DEV_USERS:
            status_tag = "" if is_active else " [INACTIVE - pending approval]"
            self.stdout.write(f"  {username:10} / {PASSWORD}  ({role}){status_tag}")

    def _reset(self):
        seed_threads = Thread.all_objects.filter(subject__startswith="[SEED]")
        seed_ids = list(seed_threads.values_list("pk", flat=True))
        if seed_ids:
            ActivityLog.objects.filter(thread_id__in=seed_ids).delete()
            ThreadReadState.all_objects.filter(thread_id__in=seed_ids).delete()
            Email.all_objects.filter(thread_id__in=seed_ids).delete()
            count, _ = Thread.all_objects.filter(pk__in=seed_ids).delete()
            self.stdout.write(f"Hard-deleted {count} seed record(s).")
        else:
            self.stdout.write("No seed data to delete.")

    def _ensure_users(self):
        result = []
        for first, last, username, email, role, is_staff, is_active in DEV_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "is_staff": is_staff,
                    "is_active": is_active,
                },
            )
            if not user.has_usable_password():
                user.set_password(PASSWORD)
                user.save()
            result.append(user)
            tag = "created" if created else "exists"
            self.stdout.write(f"  User: {username} ({role}) [{tag}]")
        self.stdout.write("")
        return result
