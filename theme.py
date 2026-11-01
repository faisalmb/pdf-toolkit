# -*- coding: utf-8 -*-
"""
theme.py
نظام التصميم البصري للتطبيق: لوحة ألوان، تايبوغرافي، وQSS متكامل.

فكرة الهوية البصرية:
لون أساسي عنابي دافئ (Burgundy) بدل الأحمر الصارخ التقليدي لأدوات PDF —
يعطي إحساسًا أكثر احترافية وهدوءًا. خلفيات رمادية فاتحة جدًا مع بطاقات
بيضاء بحواف مدورة وظل خفيف لخلق عمق بصري دون مبالغة. الخط الأساسي
Segoe UI (مدمج في كل نسخ ويندوز ويعرض العربية بوضوح ممتاز)، مع Tahoma
كخط احتياطي يدعم العربي أيضًا في حال عدم توفر Segoe UI لأي سبب.
"""

# ---------------- لوحة الألوان ----------------
COLOR_PRIMARY = "#7A2333"        # عنابي دافئ — اللون الأساسي للعلامة والأزرار الرئيسية
COLOR_PRIMARY_HOVER = "#8E2A3D"
COLOR_PRIMARY_PRESSED = "#651C29"
COLOR_PRIMARY_SOFT = "#F7E9EB"   # خلفية فاتحة جدًا من نفس العائلة، لشارات وحالات التحديد

COLOR_ACCENT = "#1F8A70"         # أخضر زمردي هادئ — للنجاح ونسبة الضغط الإيجابية
COLOR_ACCENT_SOFT = "#E6F4F1"

COLOR_BG = "#F4F5F7"             # خلفية النافذة العامة
COLOR_SURFACE = "#FFFFFF"        # خلفية البطاقات واللوحات
COLOR_SURFACE_ALT = "#FAFAFB"    # خلفية بديلة لمناطق فرعية (مثل منطقة المعاينة)

COLOR_BORDER = "#E2E4E9"
COLOR_BORDER_STRONG = "#C9CDD6"

COLOR_TEXT = "#23262B"
COLOR_TEXT_MUTED = "#6B7280"
COLOR_TEXT_ON_PRIMARY = "#FFFFFF"

COLOR_DANGER = "#C0392B"
COLOR_DANGER_SOFT = "#FBEAE8"

COLOR_WARNING = "#B7791F"        # كهرماني — للتنبيهات
COLOR_WARNING_SOFT = "#FDF3E1"

import sys as _sys

# خط الواجهة الأساسي حسب النظام، وكلها تعرض العربية جيدًا:
# ويندوز: Segoe UI، ماك: خط النظام (SF + Geeza Pro للعربي)، لينكس: Noto/DejaVu
if _sys.platform == "darwin":
    UI_FONT = ".AppleSystemUIFont"
elif _sys.platform.startswith("linux"):
    UI_FONT = "Noto Sans"
else:
    UI_FONT = "Segoe UI"

FONT_FAMILY = (f'"{UI_FONT}", "Segoe UI", "Helvetica Neue", "Noto Sans Arabic", '
               '"DejaVu Sans", "Tahoma", "Arial", sans-serif')

# نقاط حجم الخط — تدرّج بسيط وواضح
FS_TITLE = 15
FS_SUBTITLE = 12
FS_BODY = 11
FS_SMALL = 10


def build_stylesheet() -> str:
    """يبني QSS كامل للتطبيق بالاعتماد على متغيرات اللوحة أعلاه."""
    return f"""
    /* ===== الأساس ===== */
    QWidget {{
        background-color: {COLOR_BG};
        color: {COLOR_TEXT};
        font-family: {FONT_FAMILY};
        font-size: {FS_BODY}pt;
    }}

    QLabel {{
        background: transparent;
    }}

    QLabel[role="title"] {{
        font-size: {FS_TITLE}pt;
        font-weight: 600;
        color: {COLOR_TEXT};
    }}

    QLabel[role="panel-header"] {{
        font-size: {FS_SUBTITLE}pt;
        font-weight: 600;
        color: {COLOR_TEXT};
        padding: 2px 0;
    }}

    QLabel[role="hint"] {{
        font-size: {FS_SMALL}pt;
        color: {COLOR_TEXT_MUTED};
    }}

    QLabel[role="subtitle"] {{
        font-size: {FS_SMALL}pt;
        color: {COLOR_TEXT_MUTED};
    }}

    /* حالة فارغة: نص إرشادي داخل إطار متقطّع بدل مساحة بيضاء صامتة */
    QLabel[role="empty-state"] {{
        background-color: {COLOR_SURFACE_ALT};
        border: 2px dashed {COLOR_BORDER_STRONG};
        border-radius: 10px;
        color: {COLOR_TEXT_MUTED};
        font-size: {FS_SUBTITLE}pt;
        padding: 24px;
    }}

    /* شارة تقدّم المعاينات بجانب عنوان لوحة الصفحات */
    QLabel[role="progress-badge"] {{
        background-color: {COLOR_PRIMARY_SOFT};
        color: {COLOR_PRIMARY};
        border-radius: 6px;
        padding: 3px 10px;
        font-size: {FS_SMALL}pt;
    }}

    /* حاويات داخل البطاقات البيضاء: شفافة حتى لا تظهر أشرطة رمادية */
    QWidget[role="transparent"] {{
        background: transparent;
    }}

    /* شريط ترتيب الصفحة المحددة: شريط أدوات خفيف داخل اللوحة */
    QWidget[role="page-toolbar"] {{
        background-color: {COLOR_PRIMARY_SOFT};
        border-radius: 8px;
    }}
    QWidget[role="page-toolbar"] QLabel {{
        color: {COLOR_PRIMARY};
        font-weight: 600;
    }}

    QFrame[role="divider"] {{
        background-color: {COLOR_BORDER};
        border: none;
        max-height: 1px;
        min-height: 1px;
    }}
    QFrame[role="vdivider"] {{
        background-color: {COLOR_BORDER};
        border: none;
        max-width: 1px;
        min-width: 1px;
    }}

    QLabel[role="status"] {{
        font-size: {FS_SMALL}pt;
        color: {COLOR_TEXT_MUTED};
        padding: 4px 2px;
    }}

    QLabel[role="error"] {{
        color: {COLOR_DANGER};
        font-size: {FS_SMALL}pt;
    }}

    /* ===== الأزرار العامة ===== */
    QPushButton {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: 8px;
        padding: 7px 14px;
        font-size: {FS_BODY}pt;
    }}
    QPushButton:hover {{
        background-color: {COLOR_PRIMARY_SOFT};
        border-color: {COLOR_PRIMARY};
        color: {COLOR_PRIMARY};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_PRIMARY_SOFT};
    }}
    QPushButton:disabled {{
        color: {COLOR_TEXT_MUTED};
        border-color: {COLOR_BORDER};
        background-color: {COLOR_SURFACE_ALT};
    }}

    /* ===== الزر الأساسي (الإجراء الرئيسي) ===== */
    QPushButton[variant="primary"] {{
        background-color: {COLOR_PRIMARY};
        color: {COLOR_TEXT_ON_PRIMARY};
        border: 1px solid {COLOR_PRIMARY};
        font-weight: 600;
        padding: 9px 20px;
    }}
    QPushButton[variant="primary"]:hover {{
        background-color: {COLOR_PRIMARY_HOVER};
        border-color: {COLOR_PRIMARY_HOVER};
        color: {COLOR_TEXT_ON_PRIMARY};
    }}
    QPushButton[variant="primary"]:pressed {{
        background-color: {COLOR_PRIMARY_PRESSED};
    }}
    QPushButton[variant="primary"]:disabled {{
        background-color: {COLOR_BORDER_STRONG};
        border-color: {COLOR_BORDER_STRONG};
        color: {COLOR_SURFACE};
    }}

    /* ===== زر ثانوي خفيف (أزرار الترتيب، التحديث) ===== */
    QPushButton[variant="ghost"] {{
        background-color: transparent;
        border: 1px solid transparent;
        color: {COLOR_TEXT_MUTED};
        padding: 6px 10px;
    }}
    QPushButton[variant="ghost"]:hover {{
        background-color: {COLOR_SURFACE_ALT};
        border-color: {COLOR_BORDER};
        color: {COLOR_TEXT};
    }}

    /* ===== زر خطر (حذف) ===== */
    QPushButton[variant="danger"] {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_DANGER};
        color: {COLOR_DANGER};
    }}
    QPushButton[variant="danger"]:hover {{
        background-color: {COLOR_DANGER_SOFT};
    }}

    /* ===== زر تبديل اللغة ===== */
    QPushButton[variant="lang"] {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: 14px;
        padding: 5px 16px;
        font-size: {FS_SMALL}pt;
        font-weight: 600;
        color: {COLOR_TEXT_MUTED};
    }}
    QPushButton[variant="lang"]:hover {{
        border-color: {COLOR_PRIMARY};
        color: {COLOR_PRIMARY};
    }}

    /* ===== البطاقات / اللوحات ===== */
    QWidget[role="panel"] {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 10px;
    }}

    QWidget[role="topbar"] {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 10px;
    }}

    /* ===== القوائم ===== */
    QListWidget {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 6px;
        outline: none;
    }}
    QListWidget::item {{
        border-radius: 6px;
        padding: 6px;
        margin: 2px;
        color: {COLOR_TEXT};
    }}
    QListWidget::item:selected {{
        background-color: {COLOR_PRIMARY_SOFT};
        color: {COLOR_PRIMARY};
        border: 1px solid {COLOR_PRIMARY};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {COLOR_SURFACE_ALT};
    }}

    /* قائمة الصفحات (IconMode) تحتاج خلفية مختلفة قليلًا لإبراز البطاقات */
    QListWidget[role="pages-grid"] {{
        background-color: {COLOR_SURFACE_ALT};
    }}
    QListWidget[role="pages-grid"]::item {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 8px 6px 6px 6px;
        margin: 4px;
        font-size: {FS_SMALL}pt;
    }}

    /* قائمة الملفات: صفوف أوضح بسطرين (الاسم + عدد الصفحات/النطاق) */
    QListWidget[role="files-list"]::item {{
        padding: 8px 10px;
        margin: 2px 0;
        border-bottom: 1px solid {COLOR_BORDER};
        border-radius: 6px;
    }}
    QListWidget[role="pages-grid"]::item:selected {{
        border: 2px solid {COLOR_PRIMARY};
        background-color: {COLOR_PRIMARY_SOFT};
    }}
    QListWidget[role="pages-grid"]::item:hover:!selected {{
        border-color: {COLOR_BORDER_STRONG};
    }}

    /* ===== مدخل النص ===== */
    QLineEdit {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: 8px;
        padding: 7px 10px;
        font-size: {FS_BODY}pt;
        selection-background-color: {COLOR_PRIMARY_SOFT};
        selection-color: {COLOR_PRIMARY};
    }}
    QLineEdit:focus {{
        border: 1px solid {COLOR_PRIMARY};
    }}

    /* ===== خانة الاختيار ===== */
    QCheckBox {{
        spacing: 8px;
        font-size: {FS_BODY}pt;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid {COLOR_BORDER_STRONG};
        background: {COLOR_SURFACE};
    }}
    QCheckBox::indicator:hover {{
        border-color: {COLOR_PRIMARY};
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLOR_PRIMARY};
        border-color: {COLOR_PRIMARY};
    }}

    /* ===== الفاصل (Splitter) ===== */
    QSplitter::handle {{
        background-color: {COLOR_BG};
        width: 6px;
    }}
    QSplitter::handle:hover {{
        background-color: {COLOR_BORDER_STRONG};
    }}

    /* ===== شريط التمرير ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLOR_BORDER_STRONG};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLOR_TEXT_MUTED};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {COLOR_BORDER_STRONG};
        border-radius: 5px;
        min-width: 30px;
    }}

    /* ===== مربعات الحوار والرسائل ===== */
    QDialog {{
        background-color: {COLOR_BG};
    }}

    /* رسائل التطبيق ونافذة التقدّم (dialogs.py) */
    QDialog[role="message"] {{
        background-color: {COLOR_SURFACE};
    }}
    QLabel[role="msg-title"] {{
        font-size: {FS_SUBTITLE + 1}pt;
        font-weight: 600;
        color: {COLOR_TEXT};
    }}
    QLabel[role="msg-body"] {{
        font-size: {FS_BODY}pt;
        color: {COLOR_TEXT_MUTED};
    }}
    QLabel[role="progress-count"] {{
        font-size: {FS_SUBTITLE + 2}pt;
        font-weight: 600;
        color: {COLOR_PRIMARY};
    }}
    QFrame[role="details"] {{
        background-color: {COLOR_SURFACE_ALT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
    }}
    QLabel[role="detail-key"] {{
        color: {COLOR_TEXT_MUTED};
        font-size: {FS_SMALL}pt;
    }}
    QLabel[role="detail-value"] {{
        color: {COLOR_TEXT};
        font-weight: 600;
    }}

    /* زر خطر ممتلئ (تأكيد الحذف) */
    QPushButton[variant="danger-solid"] {{
        background-color: {COLOR_DANGER};
        border: 1px solid {COLOR_DANGER};
        color: {COLOR_TEXT_ON_PRIMARY};
        font-weight: 600;
    }}
    QPushButton[variant="danger-solid"]:hover {{
        background-color: #A93226;
        border-color: #A93226;
        color: {COLOR_TEXT_ON_PRIMARY};
    }}

    /* شريط تقدّم العمليات الطويلة: سميك ومدوّر */
    QProgressBar[role="task"] {{
        border: none;
        border-radius: 6px;
        background-color: {COLOR_PRIMARY_SOFT};
        min-height: 12px;
        max-height: 12px;
    }}
    QProgressBar[role="task"]::chunk {{
        background-color: {COLOR_PRIMARY};
        border-radius: 6px;
    }}

    /* شريط رفيع لتقدّم المعاينات داخل لوحة الصفحات */
    QProgressBar[role="thin"] {{
        border: none;
        border-radius: 3px;
        background-color: {COLOR_BORDER};
        min-height: 6px;
        max-height: 6px;
    }}
    QProgressBar[role="thin"]::chunk {{
        background-color: {COLOR_PRIMARY};
        border-radius: 3px;
    }}
    QMessageBox {{
        background-color: {COLOR_SURFACE};
    }}

    /* ===== شريط التقدم ===== */
    QProgressDialog {{
        background-color: {COLOR_SURFACE};
    }}
    QProgressBar {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        background-color: {COLOR_SURFACE_ALT};
        text-align: center;
        height: 18px;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_PRIMARY};
        border-radius: 5px;
    }}

    /* ===== القوائم المنبثقة (سياق) ===== */
    QMenu {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 7px 18px;
        border-radius: 6px;
        font-size: {FS_BODY}pt;
    }}
    QMenu::item:selected {{
        background-color: {COLOR_PRIMARY_SOFT};
        color: {COLOR_PRIMARY};
    }}
    QMenu::separator {{
        height: 1px;
        background: {COLOR_BORDER};
        margin: 6px 4px;
    }}

    /* ===== شارة نسبة الضغط ===== */
    QLabel[role="compression-badge"] {{
        background-color: {COLOR_ACCENT_SOFT};
        color: {COLOR_ACCENT};
        border-radius: 6px;
        padding: 4px 10px;
        font-weight: 600;
        font-size: {FS_SMALL}pt;
    }}
    """
