"""Management command for testing the email pipeline locally.

Generates fake emails and runs them through the pipeline with mocked
or real external services, depending on flags.

Usage:
    python manage.py test_pipeline                  # 1 fake email, all mocked
    python manage.py test_pipeline --count 5        # 5 fake emails
    python manage.py test_pipeline --with-ai        # Real Claude API call
    python manage.py test_pipeline --with-chat      # Real Chat webhook post
"""

import os

from django.core.management.base import BaseCommand

from apps.emails.services.ai_processor import AIProcessor
from apps.emails.services.chat_notifier import ChatNotifier
from apps.emails.services.fake_data import make_fake_emails, make_fake_triage
from apps.emails.services.pipeline import save_email_to_db


class Command(BaseCommand):
    help = "Test the email pipeline locally with fake data (no Gmail polling)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=1,
            help="Number of fake emails to process (default: 1)",
        )
        parser.add_argument(
            "--with-ai",
            action="store_true",
            help="Use real Claude API for triage (costs ~$0.001 per email)",
        )
        parser.add_argument(
            "--with-chat",
            action="store_true",
            help="Post results to real Google Chat webhook",
        )

    def handle(self, **options):
        count = options["count"]
        with_ai = options["with_ai"]
        with_chat = options["with_chat"]

        self.stdout.write(f"\nGenerating {count} fake email(s)...\n")

        # Generate fake emails
        fake_emails = make_fake_emails(count)

        # Set up AI processor (real or mocked)
        ai_processor = None
        if with_ai:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                self.stderr.write(
                    self.style.ERROR(
                        "ANTHROPIC_API_KEY not set. Cannot use --with-ai without it."
                    )
                )
                return
            ai_processor = AIProcessor(anthropic_api_key=api_key)
            self.stdout.write(self.style.WARNING("AI: REAL (Claude API)"))
        else:
            self.stdout.write("AI: MOCKED (fake triage results)")

        if with_chat:
            self.stdout.write(self.style.WARNING("Chat: REAL (Google Chat webhook)"))
        else:
            self.stdout.write("Chat: MOCKED (no webhook calls)")

        self.stdout.write("")

        # Process each email
        saved_emails = []
        for i, email_msg in enumerate(fake_emails):
            self.stdout.write(
                f"[{i + 1}/{count}] Processing: {email_msg.subject[:60]}..."
            )

            # Triage: real AI or fake (index matches email for realistic pairing)
            if with_ai and ai_processor:
                triage = ai_processor.process(email_msg, gmail_poller=None)
                self.stdout.write(
                    f"  AI result: {triage.category} / {triage.priority} "
                    f"(model: {triage.model_used}, "
                    f"tokens: {triage.input_tokens}+{triage.output_tokens})"
                )
            else:
                triage = make_fake_triage(index=i)
                self.stdout.write(
                    f"  Fake result: {triage.category} / {triage.priority}"
                )

            # Save to DB
            email_obj = save_email_to_db(email_msg, triage)
            saved_emails.append(email_obj)
            self.stdout.write(
                f"  Saved: Email #{email_obj.pk} "
                f"(message_id={email_obj.message_id})"
            )

        # Chat notification
        if with_chat and saved_emails:
            webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")
            if not webhook_url:
                self.stderr.write(
                    self.style.ERROR(
                        "GOOGLE_CHAT_WEBHOOK_URL not set. Skipping chat notification."
                    )
                )
            else:
                notifier = ChatNotifier(webhook_url=webhook_url)
                result = notifier.notify_new_emails(saved_emails)
                if result:
                    self.stdout.write(
                        self.style.SUCCESS("Chat notification sent.")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("Chat notification failed or suppressed.")
                    )

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Done. {len(saved_emails)} email(s) processed and saved."))
        self.stdout.write(f"  AI:   {'REAL (Claude)' if with_ai else 'MOCKED'}")
        self.stdout.write(f"  Chat: {'REAL (webhook)' if with_chat else 'MOCKED'}")
        self.stdout.write(f"  DB:   {len(saved_emails)} record(s) written")

        if with_ai and ai_processor:
            stats = AIProcessor.get_usage_stats()
            self.stdout.write(
                f"  AI usage: {stats['total_calls']} call(s), "
                f"{stats['total_input_tokens']} input + "
                f"{stats['total_output_tokens']} output tokens"
            )
