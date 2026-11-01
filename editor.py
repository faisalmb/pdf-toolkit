# -*- coding: utf-8 -*-
"""
editor.py
محرّر التوقيع/الختم/الكتابة على صفحة واحدة: لوحة تفاعلية (_EditorCanvas)
لسحب العناصر وتغيير حجمها، ونافذة (AnnotateDialog) بلوحة خصائص جانبية.
مفصول عن main_app.py حتى يبقى ملف الواجهة الرئيسية أصغر وأسهل صيانة.
"""
import os

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QDialog, QLineEdit, QSpinBox, QScrollArea, QComboBox,
)

from i18n import Translator
import dialogs


# ---------------- لوحة تحرير تفاعلية: سحب + تغيير حجم العناصر ----------------
# سجل الخطوط الموحّد. كل خط: اسم العرض -> dict فيه:
#   pdf_name: اسم خط PDF القياسي (للخطوط اللاتينية المدمجة في PDF)
#   file: اسم ملف الخط المرفق (للخطوط العربية) أو None
#   arabic: هل يدعم العربية؟
#   qt: (عائلة خط Qt للمعاينة على الشاشة، غامق؟)
FONT_REGISTRY = {
    "Helvetica":      {"pdf_name": "helv", "file": None, "arabic": False, "qt": ("Arial", False)},
    "Helvetica Bold": {"pdf_name": "hebo", "file": None, "arabic": False, "qt": ("Arial", True)},
    "Times":          {"pdf_name": "tiro", "file": None, "arabic": False, "qt": ("Times New Roman", False)},
    "Times Bold":     {"pdf_name": "tibo", "file": None, "arabic": False, "qt": ("Times New Roman", True)},
    "Courier":        {"pdf_name": "cour", "file": None, "arabic": False, "qt": ("Courier New", False)},
    "Courier Bold":   {"pdf_name": "cobo", "file": None, "arabic": False, "qt": ("Courier New", True)},
    # خطوط عربية مرفقة (تدعم العربي والإنجليزي)
    "Amiri (عربي)":      {"pdf_name": "customfont", "file": "Amiri-Regular.ttf", "arabic": True, "qt": ("Amiri", False)},
    "Amiri Bold (عربي)": {"pdf_name": "customfont", "file": "Amiri-Bold.ttf", "arabic": True, "qt": ("Amiri", True)},
    "Cairo (عربي)":      {"pdf_name": "customfont", "file": "Cairo-Variable.ttf", "arabic": True, "qt": ("Cairo", False)},
}

# توافقية للخلف: قاموس قديم كان يربط اسم العرض باسم خط PDF
PDF_FONTS = {name: info["pdf_name"] for name, info in FONT_REGISTRY.items()}


def _font_display_to_file(disp: str):
    """يرجع المسار المطلق لملف خط مرفق حسب اسم العرض، أو None للخطوط القياسية."""
    info = FONT_REGISTRY.get(disp)
    if not info or not info["file"]:
        return None
    try:
        from resources import resource_path
        import os as _os
        p = resource_path(_os.path.join("fonts", info["file"]))
        return p if _os.path.exists(p) else None
    except Exception:
        return None


# نحمّل خطوط العرض في Qt مرة واحدة (للمعاينة الصحيحة على الشاشة)
_QT_FONTS_LOADED = False


def _ensure_qt_fonts_loaded():
    global _QT_FONTS_LOADED
    if _QT_FONTS_LOADED:
        return
    try:
        from PyQt5.QtGui import QFontDatabase
        for info in FONT_REGISTRY.values():
            if info["file"]:
                fp = _font_display_to_file_by_filename(info["file"])
                if fp:
                    QFontDatabase.addApplicationFont(fp)
    except Exception:
        pass
    _QT_FONTS_LOADED = True


def _font_display_to_file_by_filename(filename: str):
    try:
        from resources import resource_path
        import os as _os
        p = resource_path(_os.path.join("fonts", filename))
        return p if _os.path.exists(p) else None
    except Exception:
        return None


# أحجام مقابض تغيير الحجم وحدود الالتقاط (بالبكسل على الشاشة)
_HANDLE = 12


class _EditorCanvas(QLabel):
    """
    لوحة تعرض صورة الصفحة وتسمح بإضافة عناصر (صور/نصوص/حذف مناطق) فوقها،
    ثم سحبها لتغيير الموضع وتغيير حجمها عبر مقبض في الزاوية السفلية.
    كل العناصر تُخزّن بإحداثيات نسبية (0..1) من أبعاد الصفحة.

    يبث:
    - selection_changed(index)  عند تغيّر العنصر المحدد (-1 = لا شيء)
    - geometry_changed()        بعد سحب/تحجيم لتحديث أي معاينة خارجية
    """
    from PyQt5.QtCore import pyqtSignal as _sig
    selection_changed = _sig(int)
    geometry_changed = _sig()
    edit_text_requested = _sig(int)  # نقر مزدوج على نص لتحريره

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self._base = pixmap          # الصورة الأصلية بالحجم الكامل
        self._zoom = 1.0             # عامل التكبير الحالي
        self._apply_zoom()
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        # كل عنصر: dict(kind, content, x, y, w, h, font_size, color, font_name, pixmap?)
        self.items = []
        self.selected = -1
        self._mode = None       # "move"/"resize"/"pan"/"draw_redact" أثناء السحب
        self._drag_start = None
        self._scroll_area = None     # مرجع لمنطقة التمرير (للسحب باليد عند الزوم)
        self._pan_start = None       # (mouse_global, h_value, v_value)
        self._placing_redact = False  # وضع رسم منطقة الحذف بالسحب
        self._redact_origin = None

    def set_scroll_area(self, area):
        self._scroll_area = area

    def start_redact_mode(self):
        """يفعّل وضع رسم منطقة الحذف: السحبة التالية على فراغ ترسم مستطيل حذف."""
        self._placing_redact = True
        self.setCursor(Qt.CrossCursor)

    def _apply_zoom(self):
        """يعيد قياس الصورة المعروضة حسب عامل التكبير الحالي."""
        w = max(1, int(self._base.width() * self._zoom))
        h = max(1, int(self._base.height() * self._zoom))
        scaled = self._base.scaled(QSize(w, h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)
        self.setFixedSize(scaled.size())
        self.update()

    def set_zoom(self, zoom):
        self._zoom = max(0.4, min(zoom, 4.0))
        self._apply_zoom()

    def get_zoom(self):
        return self._zoom

    # ---- تحويل إحداثيات بين بكسل اللوحة ونِسب الصورة ----
    def _img_geom(self):
        pm = self.pixmap()
        if pm is None:
            return 0, 0, 1, 1
        pw, ph = pm.width(), pm.height()
        off_x = (self.width() - pw) / 2
        off_y = (self.height() - ph) / 2
        return off_x, off_y, pw, ph

    def _to_ratio(self, px, py):
        off_x, off_y, pw, ph = self._img_geom()
        return (px - off_x) / pw, (py - off_y) / ph

    def set_items(self, items):
        self.items = items
        self.update()

    def set_selected(self, idx):
        self.selected = idx
        self.selection_changed.emit(idx)
        self.update()

    # ---- رسم العناصر ----
    def _item_rect_px(self, it):
        """يرجع مستطيل العنصر بالبكسل على اللوحة (x, y, w, h)."""
        off_x, off_y, pw, ph = self._img_geom()
        x = off_x + it['x'] * pw
        y = off_y + it['y'] * ph
        if it['kind'] in ('image', 'redact'):
            w = it['w'] * pw
            h = it['h'] * ph
        else:
            # النص: الارتفاع من حجم الخط الفعلي والعرض من قياس الخط نفسه
            from PyQt5.QtGui import QFontMetrics
            fs_px = self._pt_to_px(it['font_size'])
            h = fs_px * 1.4
            w = max(QFontMetrics(self._text_font(it)).horizontalAdvance(it['content']), 20)
        return x, y, w, h

    def _pt_to_px(self, pt):
        """يحوّل نقاط PDF إلى بكسلات على الشاشة حسب ارتفاع الصفحة الفعلي.
        الصورة الأساسية مرسومة بمقياس 1 (بكسل = نقطة)، فالنسبة بين الارتفاع
        المعروض وارتفاعها تعطي المقياس الصحيح لأي مقاس صفحة (لا A4 فقط)."""
        _, _, _, ph = self._img_geom()
        return pt * ph / max(self._base.height(), 1)

    def _text_font(self, it):
        from PyQt5.QtGui import QFont as _QFont
        info = FONT_REGISTRY.get(it.get('font_name_disp', 'Helvetica'), {})
        fam, bold = info.get('qt', ("Arial", False))
        qf = _QFont(fam)
        # pixelSize وليس pointSize: حجم النقطة في Qt يُضرب في DPI الشاشة
        qf.setPixelSize(max(4, int(round(self._pt_to_px(it['font_size'])))))
        qf.setBold(bold)
        return qf

    def _scaled_stamp(self, it, w, h):
        """صورة الختم بالحجم المعروض، مخزّنة حتى لا يُعاد تحجيمها مع كل رسم.
        أثناء السحب/التحجيم نستخدم تحجيمًا سريعًا، وبعد الإفلات تحجيمًا ناعمًا."""
        size = (int(max(w, 1)), int(max(h, 1)))
        smooth = self._mode is None
        cached = it.get('_scaled')
        if cached is not None and cached[0] == size and (cached[1] or not smooth):
            return cached[2]
        mode = Qt.SmoothTransformation if smooth else Qt.FastTransformation
        pm = it['pixmap'].scaled(size[0], size[1], Qt.IgnoreAspectRatio, mode)
        it['_scaled'] = (size, smooth, pm)
        return pm

    def paintEvent(self, event):
        super().paintEvent(event)
        from PyQt5.QtGui import QPainter, QPen, QColor, QFont as _QFont, QBrush
        pm = self.pixmap()
        if pm is None:
            return
        _, _, pw, ph = self._img_geom()
        painter = QPainter(self)
        for idx, it in enumerate(self.items):
            x, y, w, h = self._item_rect_px(it)
            if it['kind'] == 'image' and it.get('pixmap') is not None:
                painter.drawPixmap(int(x), int(y), self._scaled_stamp(it, w, h))
            elif it['kind'] == 'text':
                col = it.get('color', (0, 0, 0))
                painter.setPen(QColor(int(col[0]*255), int(col[1]*255), int(col[2]*255)))
                painter.setFont(self._text_font(it))
                # خط القاعدة عند y + حجم الخط، تمامًا كما يكتبه المحرّك في الـ PDF
                painter.drawText(int(x), int(y + self._pt_to_px(it['font_size'])), it['content'])
            elif it['kind'] == 'redact':
                # منطقة حذف: نرسمها كمستطيل أحمر شبه شفاف ليعرف المستخدم
                # ما الذي سيُحذف (في الناتج تُمسح فعليًا وتصبح بيضاء)
                painter.setPen(QPen(QColor("#C0392B"), 2, Qt.DashLine))
                painter.setBrush(QBrush(QColor(192, 57, 43, 60)))
                painter.drawRect(int(x), int(y), int(w), int(h))
                painter.setBrush(Qt.NoBrush)

            # إطار التحديد + مقبض التحجيم
            if idx == self.selected:
                pen = QPen(QColor("#7A2333"))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(int(x), int(y), int(w), int(h))
                # مقبض الزاوية السفلية اليمنى
                painter.setBrush(QColor("#7A2333"))
                painter.drawRect(int(x + w - _HANDLE), int(y + h - _HANDLE), _HANDLE, _HANDLE)
        painter.end()

    # ---- التقاط الماوس ----
    def _hit_test(self, mx, my):
        """يرجع (index, mode) لأعلى عنصر تحت المؤشر؛ mode='resize' لو فوق المقبض."""
        for idx in reversed(range(len(self.items))):
            x, y, w, h = self._item_rect_px(self.items[idx])
            # منطقة المقبض
            if (x + w - _HANDLE <= mx <= x + w + 4) and (y + h - _HANDLE <= my <= y + h + 4):
                return idx, "resize"
            if x <= mx <= x + w and y <= my <= y + h:
                return idx, "move"
        return -1, None

    def mousePressEvent(self, event):
        mx, my = event.pos().x(), event.pos().y()

        # وضع رسم منطقة حذف: نبدأ مستطيلًا جديدًا
        if self._placing_redact:
            rx, ry = self._to_ratio(mx, my)
            self._redact_origin = (rx, ry)
            new_red = {"kind": "redact", "x": rx, "y": ry, "w": 0.001, "h": 0.001}
            self.items.append(new_red)
            self.set_selected(len(self.items) - 1)
            self._mode = "draw_redact"
            return

        idx, mode = self._hit_test(mx, my)
        self.set_selected(idx)
        if idx >= 0:
            it = self.items[idx]
            self._mode = mode
            self._drag_start = (mx, my, it['x'], it['y'],
                                it.get('w', 0.2), it.get('h', 0.1), it.get('font_size', 14))
        else:
            # ضغط على فراغ + مكبّر => بدء السحب باليد (pan)
            if self._scroll_area is not None:
                self._mode = "pan"
                hbar = self._scroll_area.horizontalScrollBar()
                vbar = self._scroll_area.verticalScrollBar()
                self._pan_start = (event.globalPos(), hbar.value(), vbar.value())
                self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        mx, my = event.pos().x(), event.pos().y()
        # تغيير شكل المؤشر حسب المنطقة (في وضع الخمول)
        if self._mode is None:
            if self._placing_redact:
                self.setCursor(Qt.CrossCursor)
                return
            idx, mode = self._hit_test(mx, my)
            if mode == "resize":
                self.setCursor(Qt.SizeFDiagCursor)
            elif mode == "move":
                self.setCursor(Qt.SizeAllCursor)
            elif self._scroll_area is not None and self._zoom > 1.0:
                self.setCursor(Qt.OpenHandCursor)  # يلمّح أن السحب باليد متاح
            else:
                self.setCursor(Qt.ArrowCursor)
            return

        # السحب باليد (pan)
        if self._mode == "pan" and self._pan_start is not None:
            start_pos, h0, v0 = self._pan_start
            delta = event.globalPos() - start_pos
            self._scroll_area.horizontalScrollBar().setValue(int(h0 - delta.x()))
            self._scroll_area.verticalScrollBar().setValue(int(v0 - delta.y()))
            return

        # رسم منطقة الحذف بالسحب
        if self._mode == "draw_redact" and self._redact_origin is not None:
            ox, oy = self._redact_origin
            cx, cy = self._to_ratio(mx, my)
            it = self.items[self.selected]
            it['x'] = min(ox, cx)
            it['y'] = min(oy, cy)
            it['w'] = max(abs(cx - ox), 0.005)
            it['h'] = max(abs(cy - oy), 0.005)
            self.update()
            return

        if self.selected < 0 or self._drag_start is None:
            return
        off_x, off_y, pw, ph = self._img_geom()
        sx, sy, ix, iy, iw, ih, ifs = self._drag_start
        dx = (mx - sx) / pw
        dy = (my - sy) / ph
        it = self.items[self.selected]

        if self._mode == "move":
            it['x'] = min(max(ix + dx, 0.0), 0.99)
            it['y'] = min(max(iy + dy, 0.0), 0.99)
        elif self._mode == "resize":
            if it['kind'] in ('image', 'redact'):
                it['w'] = min(max(iw + dx, 0.03), 1.0)
                it['h'] = min(max(ih + dy, 0.02), 1.0)
            else:
                factor = 1.0 + (dx + dy)
                it['font_size'] = float(min(max(ifs * factor, 6), 200))
        self.update()
        self.geometry_changed.emit()

    def mouseReleaseEvent(self, event):
        # إنهاء وضع رسم الحذف
        if self._mode == "draw_redact":
            self._placing_redact = False
            self._redact_origin = None
            self.setCursor(Qt.ArrowCursor)
            self.geometry_changed.emit()
        if self._mode == "pan":
            self.setCursor(Qt.OpenHandCursor if self._zoom > 1.0 else Qt.ArrowCursor)
        self._mode = None
        self._drag_start = None
        self._pan_start = None
        self.update()  # إعادة رسم الختم بالتحجيم الناعم بعد الإفلات

    def mouseDoubleClickEvent(self, event):
        """نقر مزدوج على نص => طلب تحريره (نقل التركيز لحقل النص)."""
        mx, my = event.pos().x(), event.pos().y()
        idx, _ = self._hit_test(mx, my)
        if idx >= 0 and self.items[idx]['kind'] == 'text':
            self.set_selected(idx)
            self.edit_text_requested.emit(idx)


class AnnotateDialog(QDialog):
    """
    محرر تفاعلي لإضافة توقيع/ختم (صورة) أو نص على صفحة:
    - تُضاف العناصر في وسط الصفحة، ثم تُسحب لتغيير الموضع
    - مقبض في الزاوية السفلية لتغيير الحجم (أو حجم خط النص)
    - النص يدعم: نوع الخط، الحجم، اللون، وتحرير المحتوى
    العناصر تُخزّن بإحداثيات ونِسب (0..1) حتى تبقى صحيحة عند الدمج.
    """
    def __init__(self, parent, tr: Translator, page_pixmap, existing_stamps=None):
        super().__init__(parent)
        self.tr_ = tr
        self.setWindowTitle(tr.t("annot_title"))
        self.resize(900, 820)
        self._stamp_pixmaps = {}
        _ensure_qt_fonts_loaded()  # لتحميل خطوط العرض العربية في Qt للمعاينة

        display = page_pixmap.scaled(QSize(560, 740), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        root = QHBoxLayout(self)
        root.setSpacing(12)

        # ===== العمود الأيسر: اللوحة =====
        left = QVBoxLayout()
        left.setSpacing(8)
        hint = QLabel(tr.t("annot_hint"))
        hint.setProperty("role", "hint")
        hint.setWordWrap(True)
        left.addWidget(hint)

        # شريط الزوم
        zoom_bar = QHBoxLayout()
        zoom_bar.setSpacing(6)
        self.btn_zoom_out = QPushButton("🔍−")
        self.btn_zoom_out.setProperty("variant", "ghost")
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.setFixedWidth(48)
        self.btn_zoom_in = QPushButton("🔍+")
        self.btn_zoom_in.setProperty("variant", "ghost")
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.setFixedWidth(48)
        self.btn_zoom_reset = QPushButton(tr.t("annot_zoom_reset"))
        self.btn_zoom_reset.setProperty("variant", "ghost")
        self.btn_zoom_reset.setCursor(Qt.PointingHandCursor)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setProperty("role", "hint")
        zoom_bar.addWidget(self.btn_zoom_out)
        zoom_bar.addWidget(self.btn_zoom_in)
        zoom_bar.addWidget(self.btn_zoom_reset)
        zoom_bar.addWidget(self.zoom_label)
        zoom_bar.addStretch(1)
        left.addLayout(zoom_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignCenter)
        self.canvas = _EditorCanvas(display)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.edit_text_requested.connect(self._on_edit_text_requested)
        self.canvas.set_scroll_area(scroll)   # لتفعيل السحب باليد (pan)
        scroll.setWidget(self.canvas)
        left.addWidget(scroll, 1)
        root.addLayout(left, 1)

        self.btn_zoom_in.clicked.connect(lambda: self._zoom_by(1.25))
        self.btn_zoom_out.clicked.connect(lambda: self._zoom_by(0.8))
        self.btn_zoom_reset.clicked.connect(lambda: self._set_zoom(1.0))

        # ===== العمود الأيمن: الأدوات والخصائص =====
        side = QVBoxLayout()
        side.setSpacing(10)

        self.btn_image = QPushButton(tr.t("annot_add_image"))
        self.btn_image.setCursor(Qt.PointingHandCursor)
        self.btn_text = QPushButton(tr.t("annot_add_text"))
        self.btn_text.setCursor(Qt.PointingHandCursor)
        self.btn_redact = QPushButton(tr.t("annot_add_redact"))
        self.btn_redact.setCursor(Qt.PointingHandCursor)
        self.btn_redact.clicked.connect(self._start_redact)
        side.addWidget(self.btn_image)
        side.addWidget(self.btn_text)
        side.addWidget(self.btn_redact)

        # حقل إدخال النص
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText(tr.t("annot_text_placeholder"))
        self.text_edit.textChanged.connect(self._on_text_content_changed)
        side.addWidget(self.text_edit)

        # ---- لوحة خصائص النص ----
        self.props_title = QLabel(tr.t("annot_props_title"))
        self.props_title.setProperty("role", "panel-header")
        side.addWidget(self.props_title)

        self.props_hint = QLabel(tr.t("annot_props_hint_none"))
        self.props_hint.setProperty("role", "hint")
        self.props_hint.setWordWrap(True)
        side.addWidget(self.props_hint)

        # الخط
        font_row = QHBoxLayout()
        self.font_label = QLabel(tr.t("annot_text_font"))
        self.font_label.setProperty("role", "hint")
        self.font_combo = QComboBox()
        self.font_combo.addItems(list(FONT_REGISTRY.keys()))
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        font_row.addWidget(self.font_label)
        font_row.addWidget(self.font_combo, 1)
        side.addLayout(font_row)

        # الحجم
        size_row = QHBoxLayout()
        self.size_label = QLabel(tr.t("annot_text_size"))
        self.size_label.setProperty("role", "hint")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 200)
        self.size_spin.setValue(18)
        self.size_spin.valueChanged.connect(self._on_size_changed)
        size_row.addWidget(self.size_label)
        size_row.addWidget(self.size_spin, 1)
        side.addLayout(size_row)

        # اللون
        color_row = QHBoxLayout()
        self.color_label = QLabel(tr.t("annot_text_color"))
        self.color_label.setProperty("role", "hint")
        self.btn_color = QPushButton()
        self.btn_color.setCursor(Qt.PointingHandCursor)
        self.btn_color.clicked.connect(self._pick_color)
        self._current_color = (0.0, 0.0, 0.0)
        self._update_color_button()
        color_row.addWidget(self.color_label)
        color_row.addWidget(self.btn_color, 1)
        side.addLayout(color_row)

        side.addStretch(1)

        self.btn_delete = QPushButton(tr.t("annot_delete_selected"))
        self.btn_delete.setProperty("variant", "danger")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._delete_selected)
        side.addWidget(self.btn_delete)

        self.btn_clear = QPushButton(tr.t("annot_clear"))
        self.btn_clear.setProperty("variant", "ghost")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_all)
        side.addWidget(self.btn_clear)

        self.count_label = QLabel("")
        self.count_label.setProperty("role", "hint")
        side.addWidget(self.count_label)

        btns = QHBoxLayout()
        cancel = QPushButton(tr.t("btn_cancel"))
        cancel.clicked.connect(self.reject)
        apply_b = QPushButton(tr.t("annot_apply"))
        apply_b.setProperty("variant", "primary")
        apply_b.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(apply_b)
        side.addLayout(btns)

        root.addLayout(side)

        self.btn_image.clicked.connect(self._add_image)
        self.btn_text.clicked.connect(self._add_text)

        # تحميل العناصر الموجودة مسبقًا
        self.canvas.items = self._load_existing(existing_stamps or [])
        self.canvas.update()
        self._set_props_enabled(False)
        self._update_count()

    # ---------- تحميل/تحويل ----------
    def _load_existing(self, stamps):
        items = []
        for st in stamps:
            it = dict(st)
            if it['kind'] == 'image':
                pm = self._stamp_pixmaps.get(it['content']) or QPixmap(it['content'])
                self._stamp_pixmaps[it['content']] = pm
                it['pixmap'] = pm
            else:
                # نضمن وجود حقل اسم العرض للخط
                it.setdefault('font_name_disp', self._disp_from_pdf(it.get('font_name', 'helv')))
            items.append(it)
        return items

    @staticmethod
    def _disp_from_pdf(pdf_font):
        for disp, code in PDF_FONTS.items():
            if code == pdf_font:
                return disp
        return "Helvetica"

    # ---------- إضافة عناصر ----------
    def _cascade_pos(self):
        """يعطي موضعًا متدرّجًا لكل عنصر جديد حتى لا تتكدّس العناصر فوق بعضها."""
        n = len(self.canvas.items)
        base = 0.15 + (n % 6) * 0.08
        return min(base, 0.7), min(base, 0.7)

    def _add_image(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.tr_.t("annot_image_dialog"), os.getcwd(),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp)"
        )
        if not paths:
            return
        chosen = paths[0]
        pm = QPixmap(chosen)
        self._stamp_pixmaps[chosen] = pm
        # نسبة أبعاد الصورة لضبط ارتفاع مناسب
        aspect = (pm.height() / pm.width()) if pm.width() else 0.4
        w = 0.25
        h = max(0.05, min(w * aspect, 0.4))
        px, py = self._cascade_pos()
        self.canvas.items.append({
            "kind": "image", "content": chosen,
            "x": px, "y": py, "w": w, "h": h, "pixmap": pm,
        })
        self.canvas.set_selected(len(self.canvas.items) - 1)
        self._update_count()

    def _add_text(self):
        txt = self.text_edit.text().strip()
        if not txt:
            dialogs.info(self, self.tr_.t("msg_attention"),
                                    self.tr_.t("annot_empty_text"))
            return
        px, py = self._cascade_pos()
        disp = self.font_combo.currentText()
        self.canvas.items.append({
            "kind": "text", "content": txt,
            "x": px, "y": py,
            "font_size": float(self.size_spin.value()),
            "color": self._current_color,
            "font_name": PDF_FONTS.get(disp, "helv"),
            "font_name_disp": disp,
            "font_file": _font_display_to_file(disp) or "",
        })
        self.canvas.set_selected(len(self.canvas.items) - 1)
        # نمسح حقل النص حتى لا يُضاف نفس النص بالخطأ مرة أخرى
        self.text_edit.blockSignals(True)
        self.text_edit.clear()
        self.text_edit.blockSignals(False)
        self._update_count()

    def _start_redact(self):
        """يفعّل وضع رسم منطقة الحذف: المستخدم يسحب على الصفحة لتحديد المنطقة."""
        self.canvas.start_redact_mode()
        dialogs.info(self, self.tr_.t("msg_attention"),
                               self.tr_.t("annot_redact_hint"))

    def _delete_selected(self):
        idx = self.canvas.selected
        if 0 <= idx < len(self.canvas.items):
            self.canvas.items.pop(idx)
            self.canvas.set_selected(-1)
            self._update_count()

    def _clear_all(self):
        self.canvas.items = []
        self.canvas.set_selected(-1)
        self._update_count()

    # ---------- مزامنة الخصائص مع العنصر المحدد ----------
    def _on_selection_changed(self, idx):
        if 0 <= idx < len(self.canvas.items) and self.canvas.items[idx]['kind'] == 'text':
            it = self.canvas.items[idx]
            self._set_props_enabled(True)
            self.props_hint.setVisible(False)
            self.text_edit.blockSignals(True)
            self.text_edit.setText(it['content'])
            self.text_edit.blockSignals(False)
            self.size_spin.blockSignals(True)
            self.size_spin.setValue(int(it['font_size']))
            self.size_spin.blockSignals(False)
            self.font_combo.blockSignals(True)
            self.font_combo.setCurrentText(it.get('font_name_disp', 'Helvetica'))
            self.font_combo.blockSignals(False)
            self._current_color = it.get('color', (0.0, 0.0, 0.0))
            self._update_color_button()
        else:
            self._set_props_enabled(False)
            self.props_hint.setVisible(True)

    def _set_props_enabled(self, on):
        for w in (self.font_combo, self.size_spin, self.btn_color,
                  self.font_label, self.size_label, self.color_label):
            w.setEnabled(on)

    def _on_edit_text_requested(self, idx):
        """عند النقر المزدوج على نص: ننقل التركيز لحقل النص ونحدد محتواه
        بالكامل ليسهل على المستخدم حذف جزء ومواصلة الكتابة."""
        if 0 <= idx < len(self.canvas.items) and self.canvas.items[idx]['kind'] == 'text':
            self.text_edit.setFocus()
            self.text_edit.selectAll()

    def _selected_text_item(self):
        idx = self.canvas.selected
        if 0 <= idx < len(self.canvas.items) and self.canvas.items[idx]['kind'] == 'text':
            return self.canvas.items[idx]
        return None

    def _on_text_content_changed(self, text):
        it = self._selected_text_item()
        if it is not None:
            it['content'] = text
            self.canvas.update()

    def _on_font_changed(self, disp):
        it = self._selected_text_item()
        if it is not None:
            it['font_name_disp'] = disp
            it['font_name'] = PDF_FONTS.get(disp, "helv")
            it['font_file'] = _font_display_to_file(disp) or ""
            self.canvas.update()

    def _on_size_changed(self, val):
        it = self._selected_text_item()
        if it is not None:
            it['font_size'] = float(val)
            self.canvas.update()

    def _pick_color(self):
        from PyQt5.QtWidgets import QColorDialog
        from PyQt5.QtGui import QColor
        c0 = QColor(int(self._current_color[0]*255), int(self._current_color[1]*255),
                    int(self._current_color[2]*255))
        c = QColorDialog.getColor(c0, self, self.tr_.t("annot_pick_color"))
        if c.isValid():
            self._current_color = (c.red()/255.0, c.green()/255.0, c.blue()/255.0)
            self._update_color_button()
            it = self._selected_text_item()
            if it is not None:
                it['color'] = self._current_color
                self.canvas.update()

    def _update_color_button(self):
        r, g, b = [int(v*255) for v in self._current_color]
        self.btn_color.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #C9CDD6; border-radius: 6px; min-height: 22px;"
        )

    def _update_count(self):
        self.count_label.setText(self.tr_.t("annot_count", n=len(self.canvas.items)))

    # ---------- الزوم ----------
    def _zoom_by(self, factor):
        self._set_zoom(self.canvas.get_zoom() * factor)

    def _set_zoom(self, zoom):
        self.canvas.set_zoom(zoom)
        self.zoom_label.setText(f"{int(self.canvas.get_zoom() * 100)}%")

    def get_stamps(self):
        """يرجع العناصر بصيغة قابلة للتخزين (بدون كائنات QPixmap)."""
        out = []
        for it in self.canvas.items:
            d = {k: v for k, v in it.items() if k != 'pixmap' and not k.startswith('_')}
            out.append(d)
        return out


# ---------------- التطبيق الرئيسي ----------------
