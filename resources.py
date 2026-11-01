# -*- coding: utf-8 -*-
"""
resources.py
إدارة الموارد المرفقة (الخطوط) بحيث تعمل سواء أثناء التطوير العادي
أو بعد التغليف بـ PyInstaller (onefile). عند التغليف، يفك PyInstaller
المحتوى في مجلد مؤقت ويضع مساره في sys._MEIPASS.
"""
import os
import sys


def resource_path(relative: str) -> str:
    """يرجع المسار المطلق لمورد مرفق، يعمل في وضع التطوير وفي EXE."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


# تعريف الخطوط العربية/اللاتينية المرفقة.
# المفتاح = اسم العرض في الواجهة، القيمة = (اسم ملف الخط، يدعم العربي؟).
# الخطوط القياسية (base-14) تبقى متاحة بدون ملفات.
BUNDLED_FONTS = {
    "Amiri": ("Amiri-Regular.ttf", True),
    "Amiri Bold": ("Amiri-Bold.ttf", True),
    "Cairo": ("Cairo-Variable.ttf", True),
}


def font_file(display_name: str):
    """يرجع المسار المطلق لملف الخط المرفق، أو None لو كان خطًا قياسيًا."""
    entry = BUNDLED_FONTS.get(display_name)
    if not entry:
        return None
    path = resource_path(os.path.join("fonts", entry[0]))
    return path if os.path.exists(path) else None


def is_arabic_font(display_name: str) -> bool:
    entry = BUNDLED_FONTS.get(display_name)
    return bool(entry and entry[1])
