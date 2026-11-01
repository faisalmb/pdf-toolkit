# -*- coding: utf-8 -*-
"""
dialogs.py
نوافذ الرسائل ونافذة التقدّم بهوية التطبيق بدل صناديق ويندوز الافتراضية:
- رسائل (معلومة/نجاح/تنبيه/خطأ/تأكيد) بشارة ملوّنة مرسومة، عنوان واضح،
  نص، وبطاقة تفاصيل اختيارية، وأزرار بأدوار مميّزة.
- نافذة تقدّم بمراحل: اسم المرحلة، عدّاد، شريط تقدّم (ومتحرّك عند عدم
  معرفة المدة مثل الضغط والحفظ)، وزر إلغاء.

الدوال على مستوى الوحدة (info/warning/error/confirm/success...) هي ما
تستدعيه الواجهة، فيمكن للاختبارات استبدالها بسهولة.
"""
import os

from PyQt5.QtCore import Qt, QRectF, QPointF, QUrl, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath, QDesktopServices
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout,
    QProgressBar,
)

from i18n import Translator
from theme import (
    COLOR_PRIMARY, COLOR_PRIMARY_SOFT, COLOR_ACCENT, COLOR_ACCENT_SOFT,
    COLOR_DANGER, COLOR_DANGER_SOFT, COLOR_WARNING, COLOR_WARNING_SOFT,
)

# لكل نوع رسالة: لون الشارة، خلفيتها، والرمز المرسوم بداخلها
_KINDS = {
    "info":     (COLOR_PRIMARY, COLOR_PRIMARY_SOFT, "i"),
    "question": (COLOR_PRIMARY, COLOR_PRIMARY_SOFT, "?"),
    "success":  (COLOR_ACCENT, COLOR_ACCENT_SOFT, "check"),
    "warning":  (COLOR_WARNING, COLOR_WARNING_SOFT, "!"),
    "error":    (COLOR_DANGER, COLOR_DANGER_SOFT, "x"),
}


def _tr(parent) -> Translator:
    """نأخذ مترجم النافذة الأم (ليطابق لغة الواجهة الحالية)، أو العربي افتراضيًا."""
    w = parent
    while w is not None:
        tr = getattr(w, "tr_", None)
        if isinstance(tr, Translator):
            return tr
        w = w.parentWidget() if hasattr(w, "parentWidget") else None
    return Translator(lang="ar")


def badge_pixmap(kind: str, size: int = 52) -> QPixmap:
    """شارة دائرية ملوّنة برمز مرسوم بالخطوط (لا تعتمد على خطوط الإيموجي)."""
    fg, bg, glyph = _KINDS.get(kind, _KINDS["info"])
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(bg))
    p.drawEllipse(QRectF(0, 0, size, size))
    p.setBrush(QColor(fg))
    inner = size * 0.64
    off = (size - inner) / 2
    p.drawEllipse(QRectF(off, off, inner, inner))
    pen = QPen(QColor("#FFFFFF"), size * 0.075)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    c = size / 2.0
    u = inner / 2.0
    if glyph == "check":
        path = QPainterPath(QPointF(c - u * 0.42, c + u * 0.02))
        path.lineTo(QPointF(c - u * 0.1, c + u * 0.34))
        path.lineTo(QPointF(c + u * 0.45, c - u * 0.3))
        p.drawPath(path)
    elif glyph == "x":
        d = u * 0.36
        p.drawLine(QPointF(c - d, c - d), QPointF(c + d, c + d))
        p.drawLine(QPointF(c + d, c - d), QPointF(c - d, c + d))
    elif glyph == "!":
        p.drawLine(QPointF(c, c - u * 0.45), QPointF(c, c + u * 0.12))
        p.drawPoint(QPointF(c, c + u * 0.42))
    elif glyph == "i":
        p.drawPoint(QPointF(c, c - u * 0.42))
        p.drawLine(QPointF(c, c - u * 0.1), QPointF(c, c + u * 0.45))
    else:  # "?"
        path = QPainterPath(QPointF(c - u * 0.3, c - u * 0.22))
        path.cubicTo(QPointF(c - u * 0.3, c - u * 0.62), QPointF(c + u * 0.34, c - u * 0.62),
                     QPointF(c + u * 0.32, c - u * 0.24))
        path.cubicTo(QPointF(c + u * 0.3, c + u * 0.02), QPointF(c, c - u * 0.02), QPointF(c, c + u * 0.16))
        p.drawPath(path)
        p.drawPoint(QPointF(c, c + u * 0.44))
    p.end()
    return pm


class MessageDialog(QDialog):
    """رسالة بهوية التطبيق. buttons: قائمة (مفتاح، نص، نوع الزر)؛ آخر زر هو الأساسي."""

    def __init__(self, parent, kind, title, text, details=None, buttons=None):
        super().__init__(parent)
        self.setProperty("role", "message")
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if parent is not None:
            self.setLayoutDirection(parent.layoutDirection())
        self.setMinimumWidth(420)
        self.setMaximumWidth(640)
        self.result_key = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 18)
        root.setSpacing(16)

        head = QHBoxLayout()
        head.setSpacing(16)
        badge = QLabel()
        badge.setPixmap(badge_pixmap(kind))
        badge.setFixedSize(52, 52)
        head.addWidget(badge, 0, Qt.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(6)
        title_lbl = QLabel(title)
        title_lbl.setProperty("role", "msg-title")
        title_lbl.setWordWrap(True)
        texts.addWidget(title_lbl)
        if text:
            body = QLabel(text)
            body.setProperty("role", "msg-body")
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            texts.addWidget(body)
        head.addLayout(texts, 1)
        root.addLayout(head)

        if details:
            card = QFrame()
            card.setProperty("role", "details")
            grid = QGridLayout(card)
            grid.setContentsMargins(14, 10, 14, 10)
            grid.setHorizontalSpacing(18)
            grid.setVerticalSpacing(6)
            # محاذاة مطلقة لبداية السطر حسب لغة الواجهة؛ بدونها تنحاز القيم
            # اللاتينية (أسماء الملفات، الأحجام) لليسار وسط نص عربي
            rtl = self.layoutDirection() == Qt.RightToLeft
            align = (Qt.AlignRight if rtl else Qt.AlignLeft) | Qt.AlignAbsolute | Qt.AlignVCenter
            for row, (label, value) in enumerate(details):
                k = QLabel(label)
                k.setProperty("role", "detail-key")
                k.setAlignment(align)
                v = QLabel(str(value))
                v.setAlignment(align)
                v.setProperty("role", "detail-value")
                v.setWordWrap(True)
                v.setTextInteractionFlags(Qt.TextSelectableByMouse)
                grid.addWidget(k, row, 0, Qt.AlignTop)
                grid.addWidget(v, row, 1)
            grid.setColumnStretch(1, 1)
            root.addWidget(card)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        buttons = buttons or [("ok", _tr(parent).t("btn_ok"), "primary")]
        for key, label, variant in buttons:
            b = QPushButton(label)
            if variant:
                b.setProperty("variant", variant)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumWidth(96)
            b.clicked.connect(lambda _=False, k=key: self._finish(k))
            row.addWidget(b)
            if variant in ("primary", "danger-solid"):
                b.setDefault(True)
                b.setFocus()
        root.addLayout(row)

    def _finish(self, key):
        self.result_key = key
        self.accept()


def show(parent, kind, title, text, details=None, buttons=None):
    dlg = MessageDialog(parent, kind, title, text, details, buttons)
    dlg.exec_()
    return dlg.result_key


def info(parent, title, text, details=None):
    show(parent, "info", title, text, details)


def warning(parent, title, text, details=None):
    show(parent, "warning", title, text, details)


def error(parent, title, text, details=None):
    show(parent, "error", title, text, details)


def confirm(parent, title, text, yes_text=None, no_text=None, danger=False) -> bool:
    t = _tr(parent).t
    key = show(parent, "warning" if danger else "question", title, text, buttons=[
        ("no", no_text or t("btn_no"), "ghost"),
        ("yes", yes_text or t("btn_yes"), "danger-solid" if danger else "primary"),
    ])
    return key == "yes"


def success(parent, title, text, details=None, open_path=None):
    """رسالة نجاح؛ مع open_path تظهر أزرار فتح الملف ومجلده مباشرة."""
    t = _tr(parent).t
    buttons = [("close", t("btn_close"), "ghost")]
    if open_path:
        buttons = [("folder", t("btn_open_folder"), None), ("close", t("btn_close"), "ghost"),
                   ("file", t("btn_open_file"), "primary")]
    key = show(parent, "success", title, text, details, buttons)
    if open_path and key == "file":
        QDesktopServices.openUrl(QUrl.fromLocalFile(open_path))
    elif open_path and key == "folder":
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(open_path)))


class TaskProgressDialog(QDialog):
    """
    نافذة تقدّم بمراحل لعملية طويلة (الدمج والحفظ):
    - set_stage(نص، محدد؟): اسم المرحلة؛ غير المحددة (مثل الضغط والحفظ)
      تعرض شريطًا متحركًا بدل شريط واقف عند 100% يوحي بأن البرنامج علق.
    - set_progress(تم، الإجمالي): العدّاد والنسبة.
    """
    canceled = pyqtSignal()

    def __init__(self, parent, title, tr: Translator):
        super().__init__(parent)
        self.tr_ = tr
        self.setProperty("role", "message")
        self.setWindowTitle(title)
        self.setWindowFlags((self.windowFlags() | Qt.CustomizeWindowHint)
                            & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowCloseButtonHint)
        self.setModal(True)
        if parent is not None:
            self.setLayoutDirection(parent.layoutDirection())
        self.setMinimumWidth(440)
        self._cancel_requested = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 18)
        root.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(14)
        badge = QLabel()
        badge.setPixmap(badge_pixmap("info", 44))
        badge.setFixedSize(44, 44)
        head.addWidget(badge, 0, Qt.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.title_lbl = QLabel(title)
        self.title_lbl.setProperty("role", "msg-title")
        texts.addWidget(self.title_lbl)
        self.stage_lbl = QLabel("")
        self.stage_lbl.setProperty("role", "msg-body")
        texts.addWidget(self.stage_lbl)
        head.addLayout(texts, 1)
        self.count_lbl = QLabel("")
        self.count_lbl.setProperty("role", "progress-count")
        head.addWidget(self.count_lbl, 0, Qt.AlignTop)
        root.addLayout(head)

        self.bar = QProgressBar()
        self.bar.setProperty("role", "task")
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        root.addWidget(self.bar)

        self.hint_lbl = QLabel(tr.t("progress_hint"))
        self.hint_lbl.setProperty("role", "hint")
        self.hint_lbl.setWordWrap(True)
        root.addWidget(self.hint_lbl)

        row = QHBoxLayout()
        row.addStretch(1)
        self.cancel_btn = QPushButton(tr.t("btn_cancel"))
        self.cancel_btn.setProperty("variant", "ghost")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel)
        row.addWidget(self.cancel_btn)
        root.addLayout(row)

    def set_stage(self, text: str, determinate: bool = True, cancellable: bool = True):
        self.stage_lbl.setText(text)
        if determinate:
            if self.bar.maximum() == 0:
                self.bar.setRange(0, 100)
        else:
            self.bar.setRange(0, 0)  # شريط متحرك: العملية جارية لكن مدتها غير معروفة
            self.count_lbl.setText("")
        if not self._cancel_requested:
            self.cancel_btn.setEnabled(cancellable)

    def set_progress(self, done: int, total: int):
        if self.bar.maximum() == 0:
            return
        pct = int(done * 100 / total) if total else 0
        self.bar.setValue(pct)
        self.count_lbl.setText(f"{pct}%")
        self.stage_lbl.setText(self.tr_.t("stage_pages", done=done, total=total))

    def _on_cancel(self):
        self._cancel_requested = True
        self.cancel_btn.setEnabled(False)
        self.stage_lbl.setText(self.tr_.t("stage_cancelling"))
        self.canceled.emit()

    def keyPressEvent(self, event):
        # Esc يطلب الإلغاء بدل إغلاق النافذة والعملية ما زالت تعمل
        if event.key() == Qt.Key_Escape:
            if self.cancel_btn.isEnabled():
                self._on_cancel()
            return
        super().keyPressEvent(event)
