"""
Small two-language dictionary for fixed interface words.

Django's gettext machinery needs .po files compiled with the gettext tools,
which are awkward to install on Windows. Every string the site needs is here
instead - one Python dict, editable without any build step.
"""

STRINGS = {
    "home": ("Home", "\u09b9\u09cb\u09ae"),
    "programs": ("Programs", "\u09aa\u09cd\u09b0\u09cb\u0997\u09cd\u09b0\u09be\u09ae"),
    "teachers": ("Teachers", "\u09b6\u09bf\u0995\u09cd\u09b7\u0995\u09ae\u09a3\u09cd\u09a1\u09b2\u09c0"),
    "notices": ("Notices", "\u09a8\u09cb\u099f\u09bf\u09b6"),
    "results": ("Results", "\u09ab\u09b2\u09be\u09ab\u09b2"),
    "gallery": ("Gallery", "\u0997\u09cd\u09af\u09be\u09b2\u09be\u09b0\u09bf"),
    "videos": ("Video lectures", "\u09ad\u09bf\u09a1\u09bf\u0993 \u0995\u09cd\u09b2\u09be\u09b8"),
    "downloads": ("Downloads", "\u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1"),
    "blog": ("Blog", "\u09ac\u09cd\u09b2\u0997"),
    "contact": ("Contact", "\u09af\u09cb\u0997\u09be\u09af\u09cb\u0997"),
    "admission": ("Admission", "\u09ad\u09b0\u09cd\u09a4\u09bf"),
    "apply_now": ("Apply now", "\u098f\u0996\u09a8\u0987 \u0986\u09ac\u09c7\u09a6\u09a8 \u0995\u09b0\u09c1\u09a8"),
    "apply_online": ("Apply online", "\u0985\u09a8\u09b2\u09be\u0987\u09a8\u09c7 \u0986\u09ac\u09c7\u09a6\u09a8"),
    "about_us": ("About us", "\u0986\u09ae\u09be\u09a6\u09c7\u09b0 \u09b8\u09ae\u09cd\u09aa\u09b0\u09cd\u0995\u09c7"),
    "why_us": ("Why Onnesha", "\u0995\u09c7\u09a8 \u0985\u09a8\u09cd\u09ac\u09c7\u09b7\u09be"),
    "our_programs": ("Our programs", "\u0986\u09ae\u09be\u09a6\u09c7\u09b0 \u09aa\u09cd\u09b0\u09cb\u0997\u09cd\u09b0\u09be\u09ae"),
    "latest_notices": ("Latest notices", "\u09b8\u09b0\u09cd\u09ac\u09b6\u09c7\u09b7 \u09a8\u09cb\u099f\u09bf\u09b6"),
    "meet_teachers": ("Meet our teachers", "\u0986\u09ae\u09be\u09a6\u09c7\u09b0 \u09b6\u09bf\u0995\u09cd\u09b7\u0995\u09ae\u09a3\u09cd\u09a1\u09b2\u09c0"),
    "view_all": ("View all", "\u09b8\u09ac \u09a6\u09c7\u0996\u09c1\u09a8"),
    "read_more": ("Read more", "\u09ac\u09bf\u09b8\u09cd\u09a4\u09be\u09b0\u09bf\u09a4"),
    "download": ("Download", "\u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1"),
    "watch": ("Watch", "\u09a6\u09c7\u0996\u09c1\u09a8"),
    "class": ("Class", "\u09b6\u09cd\u09b0\u09c7\u09a3\u09bf"),
    "subject": ("Subject", "\u09ac\u09bf\u09b7\u09df"),
    "subjects": ("Subjects", "\u09ac\u09bf\u09b7\u09df\u09b8\u09ae\u09c2\u09b9"),
    "monthly_fee": ("Monthly fee", "\u09ae\u09be\u09b8\u09bf\u0995 \u09ab\u09bf"),
    "students": ("Students", "\u09b6\u09bf\u0995\u09cd\u09b7\u09be\u09b0\u09cd\u09a5\u09c0"),
    "success_rate": ("Success rate", "\u09b8\u09be\u09ab\u09b2\u09cd\u09af\u09c7\u09b0 \u09b9\u09be\u09b0"),
    "since": ("Since", "\u09aa\u09cd\u09b0\u09a4\u09bf\u09b7\u09cd\u09a0\u09bf\u09a4"),
    "find_result": ("Find your result", "\u0986\u09aa\u09a8\u09be\u09b0 \u09ab\u09b2\u09be\u09ab\u09b2 \u0996\u09c1\u0981\u099c\u09c1\u09a8"),
    "student_id": ("Student ID", "\u09b6\u09bf\u0995\u09cd\u09b7\u09be\u09b0\u09cd\u09a5\u09c0 \u0986\u0987\u09a1\u09bf"),
    "merit_list": ("Merit list", "\u09ae\u09c7\u09a7\u09be \u09a4\u09be\u09b2\u09bf\u0995\u09be"),
    "position": ("Position", "\u09ae\u09c7\u09a7\u09be\u09b8\u09cd\u09a5\u09be\u09a8"),
    "marks": ("Marks", "\u09a8\u09ae\u09cd\u09ac\u09b0"),
    "grade": ("Grade", "\u0997\u09cd\u09b0\u09c7\u09a1"),
    "name": ("Name", "\u09a8\u09be\u09ae"),
    "phone": ("Phone", "\u09ae\u09cb\u09ac\u09be\u0987\u09b2"),
    "school": ("School / college", "\u09b8\u09cd\u0995\u09c1\u09b2 / \u0995\u09b2\u09c7\u099c"),
    "guardian": ("Guardian name", "\u0985\u09ad\u09bf\u09ad\u09be\u09ac\u0995\u09c7\u09b0 \u09a8\u09be\u09ae"),
    "guardian_phone": ("Guardian phone", "\u0985\u09ad\u09bf\u09ad\u09be\u09ac\u0995\u09c7\u09b0 \u09ae\u09cb\u09ac\u09be\u0987\u09b2"),
    "address": ("Address", "\u09a0\u09bf\u0995\u09be\u09a8\u09be"),
    "message": ("Message", "\u09ac\u09be\u09b0\u09cd\u09a4\u09be"),
    "send": ("Send", "\u09aa\u09be\u09a0\u09be\u09a8"),
    "submit": ("Submit", "\u099c\u09ae\u09be \u09a6\u09bf\u09a8"),
    "search": ("Search", "\u0996\u09c1\u0981\u099c\u09c1\u09a8"),
    "no_items": ("Nothing here yet.", "\u098f\u0996\u09a8\u09cb \u0995\u09bf\u099b\u09c1 \u09a8\u09c7\u0987\u0964"),
    "all": ("All", "\u09b8\u09ac"),
    "shorts": ("Shorts", "\u09b6\u09b0\u09cd\u099f\u09b8"),
    "lectures": ("Lectures", "\u09b2\u09c7\u0995\u099a\u09be\u09b0"),
    "staff_login": ("Staff login", "\u09b8\u09cd\u099f\u09be\u09ab \u09b2\u0997\u0987\u09a8"),
    "call_us": ("Call us", "\u0995\u09b2 \u0995\u09b0\u09c1\u09a8"),
    "admission_open": ("Admission open", "\u09ad\u09b0\u09cd\u09a4\u09bf \u099a\u09b2\u099b\u09c7"),
    "thanks_application": (
        "Thank you. We have received your application and will call you soon.",
        "\u09a7\u09a8\u09cd\u09af\u09ac\u09be\u09a6\u0964 \u0986\u09aa\u09a8\u09be\u09b0 \u0986\u09ac\u09c7\u09a6\u09a8 \u09aa\u09c7\u09df\u09c7\u099b\u09bf, \u09b6\u09c0\u0998\u09cd\u09b0\u0987 \u09af\u09cb\u0997\u09be\u09af\u09cb\u0997 \u0995\u09b0\u09be \u09b9\u09ac\u09c7\u0964",
    ),
    "thanks_message": (
        "Thank you. Your message has reached us.",
        "\u09a7\u09a8\u09cd\u09af\u09ac\u09be\u09a6\u0964 \u0986\u09aa\u09a8\u09be\u09b0 \u09ac\u09be\u09b0\u09cd\u09a4\u09be \u0986\u09ae\u09be\u09a6\u09c7\u09b0 \u0995\u09be\u099b\u09c7 \u09aa\u09cc\u0981\u099b\u09c7\u099b\u09c7\u0964",
    ),
    "result_not_found": (
        "No result found for that ID in this exam.",
        "\u098f\u0987 \u0986\u0987\u09a1\u09bf\u09a4\u09c7 \u098f\u0987 \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be\u09b0 \u0995\u09cb\u09a8\u09cb \u09ab\u09b2\u09be\u09ab\u09b2 \u09aa\u09be\u0993\u09df\u09be \u09af\u09be\u09df\u09a8\u09bf\u0964",
    ),
    "exam": ("Exam", "\u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be"),
    "total": ("Total", "\u09ae\u09cb\u099f"),
    "out_of": ("out of", "\u098f\u09b0 \u09ae\u09a7\u09cd\u09af\u09c7"),
    "published_on": ("Published", "\u09aa\u09cd\u09b0\u0995\u09be\u09b6\u09bf\u09a4"),
    "quick_links": ("Quick links", "\u09a6\u09cd\u09b0\u09c1\u09a4 \u09b2\u09bf\u0999\u09cd\u0995"),
    "follow_us": ("Follow us", "\u0986\u09ae\u09be\u09a6\u09c7\u09b0 \u09b8\u09be\u09a5\u09c7 \u09a5\u09be\u0995\u09c1\u09a8"),
    "interested_subjects": (
        "Which subjects are you interested in?",
        "\u0995\u09cb\u09a8 \u09ac\u09bf\u09b7\u09df\u0997\u09c1\u09b2\u09cb \u09aa\u09dc\u09a4\u09c7 \u099a\u09be\u09a8?",
    ),
}


def t(key, lang="en"):
    pair = STRINGS.get(key)
    if not pair:
        return key
    return pair[1] if lang == "bn" else pair[0]
