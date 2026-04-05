from __future__ import annotations

from collections.abc import Iterable


DEMO_IDENTITIES: tuple[dict[str, str], ...] = (
    {
        "individual_id": "5860356276",
        "full_name": "Amina Hassan",
        "settlement": "Kebribeyah Camp",
        "usage": "Seeded in RefuProof as the first shared person.",
    },
    {
        "individual_id": "5555444433",
        "full_name": "Sami Bekele",
        "settlement": "Jijiga Transit Site",
        "usage": "Seeded in RefuProof as the second shared person.",
    },
    {"individual_id": "7777888899", "full_name": "Nura Ali", "settlement": "Kebribeyah Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888801", "full_name": "Rahma Yusuf", "settlement": "Kebribeyah Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888802", "full_name": "Omar Aden", "settlement": "Kebribeyah Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888803", "full_name": "Hawa Noor", "settlement": "Kebribeyah Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888804", "full_name": "Abdi Farah", "settlement": "Aw Barre Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888805", "full_name": "Ifrah Ahmed", "settlement": "Aw Barre Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888806", "full_name": "Khalid Hassan", "settlement": "Aw Barre Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888807", "full_name": "Asha Ibrahim", "settlement": "Sheder Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888808", "full_name": "Mohamed Ali", "settlement": "Sheder Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888809", "full_name": "Safiya Osman", "settlement": "Sheder Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888810", "full_name": "Jama Abdirahman", "settlement": "Melkadida Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888811", "full_name": "Maryan Muse", "settlement": "Melkadida Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888812", "full_name": "Faisal Abdullahi", "settlement": "Melkadida Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888813", "full_name": "Ubah Hassan", "settlement": "Hilaweyn Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888814", "full_name": "Abukar Warsame", "settlement": "Hilaweyn Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888815", "full_name": "Samira Ismail", "settlement": "Hilaweyn Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888816", "full_name": "Yassin Adam", "settlement": "Bokolmayo Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888817", "full_name": "Hodan Nur", "settlement": "Bokolmayo Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888818", "full_name": "Mustafa Mohamud", "settlement": "Bokolmayo Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888819", "full_name": "Nasteho Jama", "settlement": "Kule Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888820", "full_name": "Ahmed Guled", "settlement": "Kule Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888821", "full_name": "Fadumo Ali", "settlement": "Tierkidi Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888822", "full_name": "Tesfaye Bekele", "settlement": "Tierkidi Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888823", "full_name": "Aster Demissie", "settlement": "Pugnido Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888824", "full_name": "Solomon Tadesse", "settlement": "Pugnido Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888825", "full_name": "Halima Ahmed", "settlement": "Jewi Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888826", "full_name": "Muktar Omar", "settlement": "Jewi Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888827", "full_name": "Roda Abdi", "settlement": "Sherkole Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888828", "full_name": "Bilal Osman", "settlement": "Sherkole Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888829", "full_name": "Fatuma Yusuf", "settlement": "Bambasi Camp", "usage": "Available for live verification."},
    {"individual_id": "7777888830", "full_name": "Dawit Kassa", "settlement": "Bambasi Camp", "usage": "Available for live verification."},
)


def get_available_demo_identities(verified_subjects: Iterable[str | None]) -> list[dict[str, str]]:
    verified = {subject for subject in verified_subjects if subject}
    return [identity for identity in DEMO_IDENTITIES if identity["individual_id"] not in verified]
