"""Fake email factory for dev/testing and dry-run mode.

Generates realistic Indian business emails across categories,
priorities, and languages for the VIPL Email Agent pipeline.
"""

from datetime import datetime, timedelta

import pytz

from .dtos import EmailMessage, TriageResult

IST = pytz.timezone("Asia/Kolkata")

# ---------------------------------------------------------------------------
# Sample email pool (11 emails covering all categories + spam)
# ---------------------------------------------------------------------------

_SAMPLE_EMAILS = [
    # 0 - Government/Tender (English, CRITICAL)
    {
        "sender_name": "Rajesh Patil",
        "sender_email": "rajesh.patil@mahatenders.gov.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Tender Notice - IT Infrastructure Upgrade for ZP Nagpur (Ref: ZPN/IT/2026/047)",
        "body": (
            "Dear Sir/Madam,\n\n"
            "This is to inform you that Zilla Parishad Nagpur has issued a tender for "
            "IT Infrastructure Upgrade under e-Procurement. The last date for submission "
            "is 18-Mar-2026. EMD of Rs. 2,50,000 is required.\n\n"
            "Kindly find the attached tender document and submit your bid on the "
            "e-Procurement portal before the deadline.\n\n"
            "Regards,\nRajesh Patil\nDistrict Informatics Officer"
        ),
        "attachment_count": 1,
        "attachment_names": ["ZPN_IT_2026_047_tender.pdf"],
    },
    # 1 - Sales Lead (English, HIGH)
    {
        "sender_name": "Priya Sharma",
        "sender_email": "priya.sharma@techmahindra.com",
        "inbox": "sales@vidarbhainfotech.com",
        "subject": "Inquiry - Web Application Development for Internal Portal",
        "body": (
            "Hi Team,\n\n"
            "We are looking for a development partner to build an internal employee "
            "portal. The project scope includes leave management, attendance tracking, "
            "and a dashboard for HR analytics.\n\n"
            "Could you share your company profile and a rough estimate? Budget is "
            "approximately 15-20 lakhs. Timeline: 3 months.\n\n"
            "Best regards,\nPriya Sharma\nManager - IT Procurement\nTech Mahindra Ltd."
        ),
        "attachment_count": 0,
        "attachment_names": [],
    },
    # 2 - Support Request (Hindi, MEDIUM)
    {
        "sender_name": "Amit Deshmukh",
        "sender_email": "amit.deshmukh@nagpurmc.gov.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Software mein error aa raha hai - Property Tax Module",
        "body": (
            "Namaskar,\n\n"
            "Humne aapke dwara develop kiya gaya Property Tax Module install kiya hai. "
            "Kal se login karne par 'Session Expired' error aa raha hai. Humari poori "
            "team ka kaam ruk gaya hai.\n\n"
            "Kripya jaldi se jaldi is issue ko resolve karein. Humein aaj ke andar "
            "fix chahiye.\n\n"
            "Dhanyavaad,\nAmit Deshmukh\nNagpur Municipal Corporation"
        ),
        "attachment_count": 1,
        "attachment_names": ["error_screenshot.png"],
    },
    # 3 - Complaint (Marathi, HIGH)
    {
        "sender_name": "Suresh Wankhede",
        "sender_email": "suresh.w@rediffmail.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Website kaam karat nahi - 3 divas zale",
        "body": (
            "Namaskar Shreyas saheb,\n\n"
            "Amchya company che website magchya 3 divsapasun band aahe. Amhi phone "
            "kela pan konihi uthavla nahi. Amchya clients amhala vichart aahet ki "
            "website ka band aahe. Yache business var vaait parinam hot aahe.\n\n"
            "Krupaya lavkarat lavkar he solve kara, nahitar amhala dusrya company "
            "kadun kaam karun ghyave lagel.\n\n"
            "Suresh Wankhede\nWankhede Traders, Amravati"
        ),
        "attachment_count": 0,
        "attachment_names": [],
    },
    # 4 - Partnership (English, MEDIUM)
    {
        "sender_name": "Ankit Joshi",
        "sender_email": "ankit@cloudspark.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Partnership Proposal - Cloud Hosting & Managed Services",
        "body": (
            "Dear Vidarbha Infotech Team,\n\n"
            "CloudSpark is an AWS Advanced Partner based in Pune. We are expanding our "
            "channel partner network in Vidarbha region and would like to explore a "
            "partnership with your company.\n\n"
            "We offer competitive margins on cloud hosting, managed services, and "
            "DevOps consulting. Happy to schedule a call this week.\n\n"
            "Regards,\nAnkit Joshi\nBusiness Development\nCloudSpark Technologies Pvt. Ltd."
        ),
        "attachment_count": 1,
        "attachment_names": ["CloudSpark_Partner_Program_2026.pdf"],
    },
    # 5 - Vendor (English, LOW)
    {
        "sender_name": "Neha Kulkarni",
        "sender_email": "neha.kulkarni@deltaprinters.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Updated Price List - Printers & Cartridges (March 2026)",
        "body": (
            "Dear Sir,\n\n"
            "Please find attached our updated price list for printers, toners, and "
            "cartridges effective March 2026. We are offering a 12% discount on bulk "
            "orders placed before 31st March.\n\n"
            "Let us know if you need any quotations.\n\n"
            "Thanks & Regards,\nNeha Kulkarni\nDelta Printers & Peripherals"
        ),
        "attachment_count": 1,
        "attachment_names": ["Delta_PriceList_Mar2026.xlsx"],
    },
    # 6 - Internal (English, LOW)
    {
        "sender_name": "Shreyas Ugemuge",
        "sender_email": "shreyas@vidarbhainfotech.com",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "Team standup notes - 11 March",
        "body": (
            "Hi all,\n\n"
            "Quick standup notes:\n"
            "- Aniket: ZP Nagpur tender docs being prepared, will submit by Thursday\n"
            "- Pooja: NMC property tax module hotfix deployed, monitoring\n"
            "- Shreyas: Email agent v2 Phase 2 in progress\n\n"
            "No blockers. Next standup: Wednesday 10:30 AM.\n\n"
            "- Shreyas"
        ),
        "attachment_count": 0,
        "attachment_names": [],
    },
    # 7 - General Inquiry (English/Hindi mix, MEDIUM)
    {
        "sender_name": "Vishal Raut",
        "sender_email": "vishal.raut@gmail.com",
        "inbox": "sales@vidarbhainfotech.com",
        "subject": "Website development ka rate kya hai?",
        "body": (
            "Hello ji,\n\n"
            "Mera naam Vishal hai, Chandrapur se. Mujhe apne kirana store ke liye ek "
            "website banwani hai jisme product list ho aur WhatsApp pe order aa sake. "
            "Kitna charge hoga aur kitne din lagenge?\n\n"
            "Mera budget zyada nahi hai, 20-25 thousand ke andar ho jaye to accha hai.\n\n"
            "Thanks,\nVishal Raut"
        ),
        "attachment_count": 0,
        "attachment_names": [],
    },
    # 8 - Spam (English, obvious spam patterns)
    {
        "sender_name": "Marketing Solutions",
        "sender_email": "noreply@bulk-mail-promo.xyz",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "URGENT!! Guaranteed 10x ROI - Limited Time Offer!!!",
        "body": (
            "Dear Business Owner,\n\n"
            "CONGRATULATIONS! You have been selected for our EXCLUSIVE digital "
            "marketing package. Act NOW and get 10x ROI GUARANTEED or your money "
            "back!! This offer expires in 24 HOURS.\n\n"
            "Click here to claim: http://totally-legit-offer.xyz/claim?id=98234\n\n"
            "Unsubscribe: reply STOP (but why would you? This is FREE MONEY!)"
        ),
        "attachment_count": 0,
        "attachment_names": [],
    },
    # 9 - Government/Tender (Marathi, CRITICAL)
    {
        "sender_name": "Pramod Gaikwad",
        "sender_email": "pramod.gaikwad@pwd.maharashtra.gov.in",
        "inbox": "info@vidarbhainfotech.com",
        "subject": "E-Tender - Nagpur PWD CCTV Surveillance System (Bid No: PWD/NAG/2026/112)",
        "body": (
            "Prati,\nVidarbha Infotech Pvt. Ltd.\n\n"
            "Maharashtra Public Works Department, Nagpur Division yancha maarphat "
            "CCTV Surveillance System chi e-Tender prakriya suru keli aahe. "
            "Andhajit kimmat Rs. 45,00,000/-. Shevtachi tarikh 22 March 2026.\n\n"
            "Kaksha: 50 cameras, NVR, control room setup, 1 varsha AMC.\n\n"
            "E-Tender portal var bid submit karave. Attached document pahave.\n\n"
            "Pramod Gaikwad\nExecutive Engineer\nPWD Nagpur Division"
        ),
        "attachment_count": 2,
        "attachment_names": ["PWD_NAG_2026_112_NIT.pdf", "BOQ_CCTV.xlsx"],
    },
    # 10 - Sales Lead (English, HIGH)
    {
        "sender_name": "Dr. Meena Bhatia",
        "sender_email": "meena.bhatia@orangecityhospital.com",
        "inbox": "sales@vidarbhainfotech.com",
        "subject": "Re: Hospital Management System - Demo Request",
        "body": (
            "Dear Team,\n\n"
            "Thank you for the brochure. We are interested in your Hospital Management "
            "System for our 200-bed facility. Can you arrange a demo next week? "
            "We also need integration with our existing lab equipment (Roche and Siemens).\n\n"
            "Our IT head Mr. Kadam will coordinate. His number: +91 98230 XXXXX.\n\n"
            "Regards,\nDr. Meena Bhatia\nDirector\nOrange City Hospital, Nagpur"
        ),
        "attachment_count": 0,
        "attachment_names": [],
    },
]

# Pre-computed triage results matching each sample email (by index)
_SAMPLE_TRIAGES = [
    # 0 - Government/Tender
    TriageResult(
        category="Government/Tender",
        priority="CRITICAL",
        summary="ZP Nagpur tender for IT Infrastructure Upgrade. EMD Rs 2.5L, deadline 18 Mar 2026.",
        draft_reply="Respected Sir, Thank you for sharing the tender notice. We will review the documents and submit our bid before the deadline. Regards, Vidarbha Infotech.",
        reasoning="Government tender with near deadline and significant EMD. Requires immediate attention.",
        language="English",
        tags=["tender", "government", "nagpur", "deadline"],
        suggested_assignee="Aniket",
        model_used="fake-data",
    ),
    # 1 - Sales Lead
    TriageResult(
        category="Sales Lead",
        priority="HIGH",
        summary="Tech Mahindra looking for web app dev partner. Budget 15-20L, 3 month timeline.",
        draft_reply="Dear Priya, Thank you for reaching out. We would be happy to discuss this project. Please find our company profile attached. Can we schedule a call this week? Best regards, Vidarbha Infotech.",
        reasoning="High-value sales lead from a large enterprise. Budget and timeline clearly stated.",
        language="English",
        tags=["sales", "web-development", "enterprise"],
        suggested_assignee="Shreyas",
        model_used="fake-data",
    ),
    # 2 - Support Request
    TriageResult(
        category="Support Request",
        priority="MEDIUM",
        summary="NMC Property Tax Module showing Session Expired error. Team blocked since yesterday.",
        draft_reply="Namaskar Amit ji, Aapki problem ki jaankari mili hai. Humari team abhi is issue ko dekh rahi hai. Jaldi se jaldi fix karke aapko update denge. Dhanyavaad.",
        reasoning="Active support issue blocking client work. Needs same-day resolution but not SLA-critical yet.",
        language="Hindi",
        tags=["support", "bug", "nmc", "property-tax"],
        suggested_assignee="Pooja",
        model_used="fake-data",
    ),
    # 3 - Complaint
    TriageResult(
        category="Complaint",
        priority="HIGH",
        summary="Client website down for 3 days, no phone response. Threatening to switch vendors.",
        draft_reply="Namaskar Suresh saheb, Tumchya website babat amhala maahiti aahe. Amchi team lavkarat lavkar he solve karil. Amhi aaj tumchyashi contact karto. Kshama magto. Dhanyavaad.",
        reasoning="Escalated complaint. Client frustrated with 3-day downtime and lack of response. Risk of losing client.",
        language="Marathi",
        tags=["complaint", "website-down", "escalation"],
        suggested_assignee="Shreyas",
        model_used="fake-data",
    ),
    # 4 - Partnership
    TriageResult(
        category="Partnership",
        priority="MEDIUM",
        summary="CloudSpark (AWS Partner, Pune) proposing channel partnership for Vidarbha region.",
        draft_reply="Dear Ankit, Thank you for the partnership proposal. We are interested in exploring this further. Let us schedule a call this week to discuss details. Regards, Vidarbha Infotech.",
        reasoning="Legitimate partnership proposal from AWS partner. Worth exploring but not urgent.",
        language="English",
        tags=["partnership", "aws", "cloud"],
        suggested_assignee="Shreyas",
        model_used="fake-data",
    ),
    # 5 - Vendor
    TriageResult(
        category="Vendor",
        priority="LOW",
        summary="Updated printer/cartridge price list from Delta Printers. 12% bulk discount until March end.",
        draft_reply="Dear Neha, Thank you for the updated price list. We will review and reach out if we need any quotations. Regards, Vidarbha Infotech.",
        reasoning="Routine vendor price update. No action needed unless procurement is planned.",
        language="English",
        tags=["vendor", "printers", "price-list"],
        suggested_assignee="",
        model_used="fake-data",
    ),
    # 6 - Internal
    TriageResult(
        category="Internal",
        priority="LOW",
        summary="Team standup notes for 11 March. No blockers reported.",
        draft_reply="",
        reasoning="Internal standup notes. No response needed.",
        language="English",
        tags=["internal", "standup"],
        suggested_assignee="",
        model_used="fake-data",
    ),
    # 7 - General Inquiry
    TriageResult(
        category="General Inquiry",
        priority="MEDIUM",
        summary="Small business owner from Chandrapur asking for kirana store website. Budget Rs 20-25K.",
        draft_reply="Hello Vishal ji, Aapki inquiry ke liye dhanyavaad. Ek basic website with product listing aur WhatsApp integration Rs 20,000-25,000 mein ho jayegi. Timeline 7-10 din. Kya hum kal call pe baat kar sakte hain? Regards, Vidarbha Infotech.",
        reasoning="Small-value lead but straightforward project. Standard response with pricing.",
        language="Hindi",
        tags=["inquiry", "website", "small-business"],
        suggested_assignee="",
        model_used="fake-data",
    ),
    # 8 - Spam
    TriageResult(
        category="General Inquiry",
        priority="LOW",
        summary="Spam email - bulk marketing with fake ROI guarantees.",
        draft_reply="",
        reasoning="Obvious spam: bulk sender domain, ALL CAPS, urgency tactics, suspicious links.",
        language="English",
        tags=["spam"],
        suggested_assignee="",
        model_used="fake-data",
        is_spam=True,
        spam_score=0.95,
    ),
    # 9 - Government/Tender (Marathi)
    TriageResult(
        category="Government/Tender",
        priority="CRITICAL",
        summary="PWD Nagpur CCTV tender. Estimated Rs 45L, 50 cameras + NVR + AMC. Deadline 22 Mar 2026.",
        draft_reply="Prati Pramod saheb, Tender mahiti milali. Amhi documents review karun lavkarat bid submit karu. Dhanyavaad.",
        reasoning="High-value government tender with approaching deadline. Requires immediate team action.",
        language="Marathi",
        tags=["tender", "government", "pwd", "cctv", "nagpur"],
        suggested_assignee="Aniket",
        model_used="fake-data",
    ),
    # 10 - Sales Lead
    TriageResult(
        category="Sales Lead",
        priority="HIGH",
        summary="Orange City Hospital wants HMS demo for 200-bed facility. Lab equipment integration needed.",
        draft_reply="Dear Dr. Bhatia, Thank you for your interest. We will arrange a demo next week. Our team will coordinate with Mr. Kadam for scheduling. Regards, Vidarbha Infotech.",
        reasoning="High-value healthcare lead. Existing interest (follow-up to brochure). Demo requested.",
        language="English",
        tags=["sales", "hospital", "hms", "demo"],
        suggested_assignee="Shreyas",
        model_used="fake-data",
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def make_fake_email(index: int = 0) -> EmailMessage:
    """Return a single fake EmailMessage from the sample pool.

    Args:
        index: Index into the sample pool (wraps around).
    """
    sample = _SAMPLE_EMAILS[index % len(_SAMPLE_EMAILS)]
    now = datetime.now(IST) - timedelta(minutes=index * 7)

    return EmailMessage(
        thread_id=f"fake_thread_{index:04d}",
        message_id=f"fake_msg_{index:04d}",
        inbox=sample["inbox"],
        sender_name=sample["sender_name"],
        sender_email=sample["sender_email"],
        subject=sample["subject"],
        body=sample["body"],
        timestamp=now,
        attachment_count=sample["attachment_count"],
        attachment_names=list(sample["attachment_names"]),
        attachment_details=[],
        gmail_link=f"https://mail.google.com/mail/u/0/#inbox/fake_thread_{index:04d}",
    )


def make_fake_emails(count: int = 5) -> list:
    """Return a list of fake EmailMessages.

    Cycles through the sample pool if count exceeds pool size.
    """
    return [make_fake_email(index=i) for i in range(count)]


def make_fake_triage(index: int = 0) -> TriageResult:
    """Return a hardcoded TriageResult for dry-run / dev mode.

    Args:
        index: Index into the sample triage pool (wraps around).
              Matches the email at the same index.
    """
    return _SAMPLE_TRIAGES[index % len(_SAMPLE_TRIAGES)]
