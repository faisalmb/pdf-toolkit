# -*- coding: utf-8 -*-
"""
PDF Merger v4 - main_app.py
أداة دمج PDF بواجهة محسّنة ثنائية اللغة (عربي/إنجليزي):
- زر تبديل لغة فوري يغيّر كل نصوص الواجهة واتجاهها (RTL/LTR)
- خط النظام الواضح (Segoe UI على ويندوز) لعرض أفضل للعربية والإنجليزية
- هوية بصرية مستقلة (theme.py): ألوان متناسقة، بطاقات، أزرار بأدوار واضحة
- عرض نسبة الضغط الفعلية بعد الدمج عند تفعيل خيار التحسين
- ترتيب أوضح للأزرار حسب الأولوية، وتحسين عرض شبكة المعاينات
- إضافة ملفات بالسحب/الإفلات أو بالزر، مع فحص صلاحية الملف فور إضافته
- ترتيب الملفات: سحب-وإفلات + أزرار ↑ ↓ ⤒ ⤓
- تحديد نطاق صفحات لكل ملف (مثال: 1-3,5,7-end أو all)
- معاينات مصغّرة تُولَّد في خيط خلفية منفصل (لا تجميد للواجهة)
- إعادة ترتيب/حذف/تدوير/تكرار صفحة + تراجع عن الحذف
- شريط تقدم أثناء توليد المعاينات والدمج
"""
import sys
import os
import logging

from PyQt5.QtCore import Qt, QSize, QPoint, QThread
from PyQt5.QtGui import QIcon, QPixmap, QImage, QFont, QTransform
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QMenu, QAction, QAbstractItemView,
    QLabel, QDialog, QSizePolicy, QLineEdit, QCheckBox, QProgressBar, QSplitter,
    QFrame, QSlider, QSpinBox, QScrollArea, QComboBox, QStackedWidget
)

from pdf_engine import (
    PdfEngine, PageRef, human_name, parse_range,
    COMPRESSION_LEVELS, StampSpec, THUMB_MAX,
)
from workers import ThumbnailWorker, MergeWorker, rendered_to_qimage
from i18n import Translator
import dialogs
from theme import build_stylesheet, FONT_FAMILY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pdf_merger_ui")

# حجم بطاقة الصفحة: المصغّرة + سطران (اسم الملف ورقم الصفحة) + الحواف.
# يُضبط صراحة لكل بطاقة لأن Qt لا يحسب حواف الـ QSS فيقصّ السطر الثاني.
PAGE_CARD = QSize(THUMB_MAX + 30, THUMB_MAX + 90)
USERROLE_PAGEINFO = Qt.UserRole + 1
USERROLE_FILEPATH = Qt.UserRole + 2
USERROLE_PAGEROT = Qt.UserRole + 3
USERROLE_PAGEUID = Qt.UserRole + 4
USERROLE_THUMBREADY = Qt.UserRole + 5   # True بعد وصول المصغّرة الحقيقية

_PLACEHOLDER_ICON = None


def placeholder_icon() -> QIcon:
    """بطاقة "هيكلية" رمادية بشكل صفحة بخطوط نص باهتة، تُعرض مكان المصغّرة
    حتى تجهز، بدل بطاقة بيضاء فارغة توحي بأن شيئًا لم يحدث."""
    global _PLACEHOLDER_ICON
    if _PLACEHOLDER_ICON is None:
        from PyQt5.QtGui import QPainter, QColor
        from PyQt5.QtCore import QRectF
        w, h = int(THUMB_MAX / 1.414), THUMB_MAX
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor("#E2E4E9"))
        p.setBrush(QColor("#F3F4F7"))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 4, 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E4E6EB"))
        m = w * 0.14
        p.drawRoundedRect(QRectF(m, h * 0.1, w * 0.45, 7), 3, 3)
        for i, frac in enumerate((0.72, 0.6, 0.68, 0.5, 0.7, 0.62, 0.4)):
            p.drawRoundedRect(QRectF(m, h * 0.22 + i * 15, (w - 2 * m) * frac / 0.72, 5), 2.5, 2.5)
        p.end()
        icon = QIcon()
        icon.addPixmap(pm, QIcon.Normal)
        icon.addPixmap(pm, QIcon.Selected)
        _PLACEHOLDER_ICON = icon
    return _PLACEHOLDER_ICON


def _refresh_style(widget: QWidget):
    """يجبر Qt على إعادة تطبيق QSS بعد تغيير خاصية ديناميكية (property) مثل variant/role."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def human_filesize(num_bytes: int, tr: Translator) -> str:
    size = float(num_bytes)
    units = [tr.t("unit_bytes"), tr.t("unit_kb"), tr.t("unit_mb"), tr.t("unit_gb")]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} {units[-1]}"


def truncate_filename(name: str, max_chars: int = 14) -> str:
    """يقصّ اسم الملف الطويل بأناقة (...) بدل تركه يُقطع بشكل عشوائي داخل البطاقة."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    budget = max_chars - (len(ext) + 1 if ext else 0) - 1
    if len(stem) <= budget or budget <= 0:
        return name if len(name) <= max_chars else name[:max_chars - 1] + "…"
    return f"{stem[:budget]}…{('.' + ext) if ext else ''}"


# ---------------- حوار نطاق الصفحات ----------------
class RangeDialog(QDialog):
    def __init__(self, parent, tr: Translator, file_label="", page_count=0, existing="all"):
        super().__init__(parent)
        self.tr_ = tr
        self.page_count = page_count
        self.setWindowTitle(tr.t("range_dialog_title", name=file_label))
        self.setMinimumWidth(360)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        count_label = QLabel(tr.t("range_page_count", count=page_count))
        count_label.setProperty("role", "panel-header")
        lay.addWidget(count_label)

        hint_label = QLabel(tr.t("range_hint"))
        hint_label.setProperty("role", "hint")
        lay.addWidget(hint_label)

        self.edit = QLineEdit(self)
        self.edit.setText(existing if existing else "all")
        lay.addWidget(self.edit)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        lay.addWidget(self.error_label)

        btns = QHBoxLayout()
        btns.addStretch(1)
        okb = QPushButton(tr.t("btn_ok"))
        okb.setProperty("variant", "primary")
        cancelb = QPushButton(tr.t("btn_cancel"))
        okb.clicked.connect(self._validate_and_accept)
        cancelb.clicked.connect(self.reject)
        btns.addWidget(cancelb)
        btns.addWidget(okb)
        lay.addLayout(btns)

    def _validate_and_accept(self):
        try:
            parse_range(self.edit.text().strip(), self.page_count)
            self.accept()
        except ValueError as e:
            self.error_label.setText(str(e))

    def get_value(self):
        return self.edit.text().strip()


# ---------------- عارض صورة صفحة بالحجم الكامل ----------------
class FullPageViewer(QDialog):
    def __init__(self, parent, tr: Translator, pixmap, title=""):
        super().__init__(parent)
        self.tr_ = tr
        self.setWindowTitle(title)
        self.base_pixmap = pixmap
        self.resize(700, 820)

        lay = QVBoxLayout(self)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setPixmap(self.base_pixmap)
        lay.addWidget(self.image_label, 1)

        zb = QHBoxLayout()
        zb.addStretch(1)
        self.zoom_out = QPushButton(tr.t("zoom_out"))
        self.zoom_out.setProperty("variant", "ghost")
        self.zoom_in = QPushButton(tr.t("zoom_in"))
        self.zoom_in.setProperty("variant", "ghost")
        zb.addWidget(self.zoom_out)
        zb.addWidget(self.zoom_in)
        zb.addStretch(1)
        lay.addLayout(zb)

        self.zoom_factor = 1.0
        self.zoom_in.clicked.connect(lambda: self.apply_zoom(1.25))
        self.zoom_out.clicked.connect(lambda: self.apply_zoom(0.8))

    def apply_zoom(self, factor):
        self.zoom_factor *= factor
        w = max(1, int(self.base_pixmap.width() * self.zoom_factor))
        h = max(1, int(self.base_pixmap.height() * self.zoom_factor))
        scaled = self.base_pixmap.scaled(QSize(w, h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)


# محرّر التوقيع/الختم في ملف مستقل (editor.py)؛ نعيد تصدير أسمائه هنا
# حتى يبقى الاستيراد القديم `from main_app import AnnotateDialog` يعمل.
from editor import (  # noqa: E402
    FONT_REGISTRY, PDF_FONTS, AnnotateDialog, _EditorCanvas, _font_display_to_file,
)


class PDFMergerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.tr_ = Translator(lang="ar")
        self.engine = PdfEngine()

        self.pdf_paths = []
        self.per_file_ranges = {}
        self.last_dir = os.getcwd()
        # كل عنصر: (الموضع، بطاقة الصفحة نفسها) حتى يرجع التراجع البطاقة
        # كما كانت بمعرّفها وأيقونتها ودورانها وتواقيعها
        self._undo_stack = []
        # أختام/تواقيع/نصوص مُعلّقة: مفتاحها معرّف فريد للصفحة (uid)،
        # تُجمع وقت الدمج وتُحوّل إلى StampSpec حسب الموضع النهائي للصفحة
        self._page_stamps = {}  # page_uid -> list[dict]
        self._page_uid_counter = 0
        self._items_by_uid = {}     # page_uid -> QListWidgetItem (لتسليم المصغّرات)
        # حالة آخر مزامنة بين قائمة الملفات وشبكة الصفحات: تسمح بتحديث ما
        # تغيّر فقط بدل إعادة بناء كل الصفحات (ومسح تعديلات المستخدم)
        self._applied_ranges = {}   # path -> النطاق الذي بُنيت به صفحاته
        self._synced_order = []     # ترتيب الملفات عند آخر مزامنة
        self._thumb_done = 0
        self._thumb_total = 0

        self._thumb_worker = None
        self._merge_worker = None
        self._merge_progress_dialog = None

        self.setGeometry(100, 100, 1220, 760)
        self.init_ui()
        self.setAcceptDrops(True)
        self.apply_language()

    # ---------------- UI ----------------
    def init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(10)

        # -------- رأس التطبيق: العنوان + زر اللغة --------
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.title_label = QLabel()
        self.title_label.setProperty("role", "title")
        title_box.addWidget(self.title_label)
        self.subtitle_label = QLabel()
        self.subtitle_label.setProperty("role", "subtitle")
        title_box.addWidget(self.subtitle_label)
        header.addLayout(title_box)
        header.addStretch(1)
        self.btn_lang = QPushButton()
        self.btn_lang.setProperty("variant", "lang")
        self.btn_lang.setCursor(Qt.PointingHandCursor)
        self.btn_lang.clicked.connect(self.toggle_language)
        header.addWidget(self.btn_lang)
        main.addLayout(header)

        # -------- شريط أدوات علوي (بطاقة بصف واحد) --------
        # إجراءات الإضافة في جهة، وإعداد الضغط في الجهة الأخرى يفصلهما خط.
        # أزرار الحذف/التفريغ نُقلت للوحة الملفات حتى لا تجاور أزرار الإضافة.
        topbar_card = QWidget()
        topbar_card.setProperty("role", "topbar")
        topbar = QHBoxLayout(topbar_card)
        topbar.setContentsMargins(14, 10, 14, 10)
        topbar.setSpacing(8)

        self.btn_add = QPushButton()
        self.btn_add.setProperty("variant", "primary")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add_images = QPushButton()
        self.btn_add_images.setCursor(Qt.PointingHandCursor)
        self.btn_ranges = QPushButton()
        self.btn_ranges.setCursor(Qt.PointingHandCursor)

        topbar.addWidget(self.btn_add)
        topbar.addWidget(self.btn_add_images)
        topbar.addWidget(self.btn_ranges)
        topbar.addStretch(1)

        vdiv = QFrame()
        vdiv.setProperty("role", "vdivider")
        topbar.addWidget(vdiv)
        topbar.addSpacing(6)

        # التحكم بقوة الضغط (slider بأربع درجات)؛ الشرح يظهر كتلميح عند المرور
        comp_row = topbar
        self.compression_label = QLabel()
        self.compression_label.setProperty("role", "panel-header")
        comp_row.addWidget(self.compression_label)

        self.compression_slider = QSlider(Qt.Horizontal)
        self.compression_slider.setMinimum(0)
        self.compression_slider.setMaximum(3)
        self.compression_slider.setValue(0)
        self.compression_slider.setSingleStep(1)
        self.compression_slider.setPageStep(1)
        self.compression_slider.setTickPosition(QSlider.TicksBelow)
        self.compression_slider.setTickInterval(1)
        self.compression_slider.setFixedWidth(160)
        self.compression_slider.setCursor(Qt.PointingHandCursor)
        self.compression_slider.valueChanged.connect(self._on_compression_changed)
        comp_row.addWidget(self.compression_slider)

        self.compression_value_label = QLabel()
        self.compression_value_label.setProperty("role", "compression-badge")
        self.compression_value_label.setMinimumWidth(56)
        self.compression_value_label.setAlignment(Qt.AlignCenter)
        comp_row.addWidget(self.compression_value_label)

        main.addWidget(topbar_card)

        # -------- لوحتان رئيسيتان --------
        split = QSplitter(self)
        split.setOrientation(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        # -------- لوحة الملفات --------
        files_panel = QWidget()
        files_panel.setProperty("role", "panel")
        fv = QVBoxLayout(files_panel)
        fv.setContentsMargins(14, 12, 14, 12)
        fv.setSpacing(8)

        self.files_panel_title = QLabel()
        self.files_panel_title.setProperty("role", "panel-header")
        fv.addWidget(self.files_panel_title)

        self.files_list_widget = QListWidget()
        self.files_list_widget.setProperty("role", "files-list")
        self.files_list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.files_list_widget.setMovement(QListWidget.Static)
        self.files_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.files_list_widget.setDragEnabled(True)
        self.files_list_widget.setAcceptDrops(True)
        self.files_list_widget.setDropIndicatorShown(True)
        self.files_list_widget.setDefaultDropAction(Qt.MoveAction)
        fv.addWidget(self.files_list_widget, 1)

        # شريط ترتيب الملفات: مجمّع بصريًا كوحدة واحدة متجاورة
        order_bar = QHBoxLayout()
        order_bar.setSpacing(4)
        self.btn_top = QPushButton()
        self.btn_up = QPushButton()
        self.btn_down = QPushButton()
        self.btn_bottom = QPushButton()
        for b in (self.btn_top, self.btn_up, self.btn_down, self.btn_bottom):
            b.setProperty("variant", "ghost")
            b.setCursor(Qt.PointingHandCursor)
            order_bar.addWidget(b)
        order_bar.addStretch(1)
        fv.addLayout(order_bar)

        # خط فاصل خفيف قبل أزرار الحذف (إجراء مختلف الطبيعة عن الترتيب)
        sep = QFrame()
        sep.setProperty("role", "divider")
        fv.addWidget(sep)

        danger_row = QHBoxLayout()
        danger_row.setSpacing(6)
        self.btn_remove_files = QPushButton()
        self.btn_remove_files.setProperty("variant", "danger")
        self.btn_remove_files.setCursor(Qt.PointingHandCursor)
        self.btn_clear = QPushButton()
        self.btn_clear.setProperty("variant", "danger")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        danger_row.addWidget(self.btn_remove_files, 1)
        danger_row.addWidget(self.btn_clear, 1)
        fv.addLayout(danger_row)

        split.addWidget(files_panel)

        # -------- لوحة الصفحات --------
        pages_panel = QWidget()
        pages_panel.setProperty("role", "panel")
        pv = QVBoxLayout(pages_panel)
        pv.setContentsMargins(14, 12, 14, 12)
        pv.setSpacing(8)

        # رأس اللوحة: العنوان والتلميح في جهة، وشارة تقدّم المعاينات في الأخرى
        pages_header = QHBoxLayout()
        pages_titles = QVBoxLayout()
        pages_titles.setSpacing(2)
        self.pages_panel_title = QLabel()
        self.pages_panel_title.setProperty("role", "panel-header")
        pages_titles.addWidget(self.pages_panel_title)
        self.pages_panel_hint = QLabel()
        self.pages_panel_hint.setProperty("role", "hint")
        pages_titles.addWidget(self.pages_panel_hint)
        pages_header.addLayout(pages_titles)
        pages_header.addStretch(1)
        pv.addLayout(pages_header)

        # تقدّم تجهيز المعاينات: نص + شريط رفيع، يظهر فقط أثناء العمل
        self.thumb_progress_box = QWidget()
        self.thumb_progress_box.setProperty("role", "transparent")
        tpb = QHBoxLayout(self.thumb_progress_box)
        tpb.setContentsMargins(0, 0, 0, 0)
        tpb.setSpacing(10)
        self.thumb_progress_label = QLabel("")
        self.thumb_progress_label.setProperty("role", "hint")
        tpb.addWidget(self.thumb_progress_label)
        self.thumb_progress_bar = QProgressBar()
        self.thumb_progress_bar.setProperty("role", "thin")
        self.thumb_progress_bar.setTextVisible(False)
        tpb.addWidget(self.thumb_progress_bar, 1)
        self.thumb_progress_box.setVisible(False)
        pv.addWidget(self.thumb_progress_box)

        self.pages_list_widget = QListWidget()
        self.pages_list_widget.setProperty("role", "pages-grid")
        self.pages_list_widget.setViewMode(QListWidget.IconMode)
        self.pages_list_widget.setIconSize(QSize(THUMB_MAX, THUMB_MAX))
        # تحديد حجم خانة ثابت (Grid) صراحة وبارتفاع كافٍ لاستيعاب الأيقونة
        # + سطرين نص (اسم الملف ورقم الصفحة) دون قص. UniformItemSizes متعمّد
        # تركه معطّلًا لأنه يجبر كل العناصر على حجم الأيقونة فقط ويخفي النص.
        # WordWrap مفعّل حتى يظهر السطر الثاني (رقم الصفحة) بدل قصّه.
        self.pages_list_widget.setGridSize(QSize(PAGE_CARD.width() + 10, PAGE_CARD.height() + 10))
        self.pages_list_widget.setResizeMode(QListWidget.Adjust)
        self.pages_list_widget.setWordWrap(True)
        self.pages_list_widget.setTextElideMode(Qt.ElideMiddle)
        self.pages_list_widget.setSpacing(4)
        self.pages_list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        # Static (بدل Snap) يجعل السحب والإسقاط لإعادة الترتيب أكثر موثوقية
        # في وضع IconMode: العنصر ينتقل لموضعه الجديد بدل أن يبقى حرًا.
        self.pages_list_widget.setMovement(QListWidget.Static)
        self.pages_list_widget.setFlow(QListWidget.LeftToRight)
        self.pages_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pages_list_widget.setDragEnabled(True)
        self.pages_list_widget.setAcceptDrops(True)
        self.pages_list_widget.setDropIndicatorShown(True)
        self.pages_list_widget.setDefaultDropAction(Qt.MoveAction)
        self.pages_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        # حالة فارغة: إرشاد بدل شبكة بيضاء صامتة قبل إضافة أي ملف
        self.pages_empty_label = QLabel()
        self.pages_empty_label.setProperty("role", "empty-state")
        self.pages_empty_label.setAlignment(Qt.AlignCenter)
        self.pages_empty_label.setWordWrap(True)
        self.pages_stack = QStackedWidget()
        self.pages_stack.setProperty("role", "transparent")
        self.pages_stack.addWidget(self.pages_empty_label)
        self.pages_stack.addWidget(self.pages_list_widget)
        pv.addWidget(self.pages_stack, 1)

        # شريط أسهم ترتيب الصفحة المحددة (يظهر فقط عند تحديد صفحة)
        self.page_order_bar = QWidget()
        self.page_order_bar.setProperty("role", "page-toolbar")
        self.page_order_bar.setAttribute(Qt.WA_StyledBackground, True)
        pob = QHBoxLayout(self.page_order_bar)
        pob.setContentsMargins(10, 4, 10, 4)
        pob.setSpacing(4)
        self.page_order_label = QLabel()
        self.page_order_label.setProperty("role", "hint")
        pob.addWidget(self.page_order_label)
        # أزرار بنصوص صريحة (البداية / للخلف / للأمام / النهاية) لتفادي
        # أي لبس في اتجاه الأسهم بين العربي (RTL) والإنجليزي (LTR).
        self.btn_page_first = QPushButton()
        self.btn_page_back = QPushButton()
        self.btn_page_fwd = QPushButton()
        self.btn_page_last = QPushButton()
        for b in (self.btn_page_first, self.btn_page_back, self.btn_page_fwd, self.btn_page_last):
            b.setProperty("variant", "ghost")
            b.setCursor(Qt.PointingHandCursor)
            pob.addWidget(b)
        pob.addStretch(1)
        self.page_order_bar.setVisible(False)  # يظهر عند تحديد صفحة
        pv.addWidget(self.page_order_bar)

        # شريط سفلي: الإجراء الرئيسي (حفظ) بارز يمين، أزرار ثانوية يسار
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.btn_refresh = QPushButton()
        self.btn_refresh.setProperty("variant", "ghost")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_undo = QPushButton()
        self.btn_undo.setProperty("variant", "ghost")
        self.btn_undo.setCursor(Qt.PointingHandCursor)
        self.btn_undo.setEnabled(False)
        bottom.addWidget(self.btn_refresh)
        bottom.addWidget(self.btn_undo)
        bottom.addStretch(1)
        self.btn_merge = QPushButton()
        self.btn_merge.setProperty("variant", "primary")
        self.btn_merge.setCursor(Qt.PointingHandCursor)
        self.btn_merge.setMinimumWidth(160)
        bottom.addWidget(self.btn_merge)
        pv.addLayout(bottom)

        split.addWidget(pages_panel)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([320, 880])
        main.addWidget(split, 1)

        # شريط حالة سفلي صغير
        status_bar = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setProperty("role", "status")
        status_bar.addWidget(self.status_label)
        status_bar.addStretch(1)
        main.addLayout(status_bar)

        # -------- إشارات --------
        self.btn_add.clicked.connect(self.add_pdfs_dialog)
        self.btn_add_images.clicked.connect(self.add_images_dialog)
        self.btn_ranges.clicked.connect(self.set_ranges_for_selected_file)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_remove_files.clicked.connect(self.remove_selected_files)
        self.btn_merge.clicked.connect(self.merge_pdfs)
        self.btn_refresh.clicked.connect(self.refresh_thumbnails)
        self.btn_undo.clicked.connect(self.undo_delete_page)

        self.btn_up.clicked.connect(lambda: self.move_selected_files(-1))
        self.btn_down.clicked.connect(lambda: self.move_selected_files(1))
        self.btn_top.clicked.connect(lambda: self.move_selected_files_to_edge(top=True))
        self.btn_bottom.clicked.connect(lambda: self.move_selected_files_to_edge(top=False))

        # أسهم ترتيب الصفحة المحددة
        self.btn_page_back.clicked.connect(lambda: self.move_selected_page(-1))
        self.btn_page_fwd.clicked.connect(lambda: self.move_selected_page(1))
        self.btn_page_first.clicked.connect(lambda: self.move_selected_page_to_edge(first=True))
        self.btn_page_last.clicked.connect(lambda: self.move_selected_page_to_edge(first=False))
        self.pages_list_widget.itemSelectionChanged.connect(self._on_page_selection_changed)

        try:
            self.files_list_widget.model().rowsMoved.connect(lambda *args: self.on_files_reordered())
        except Exception as e:
            logger.warning("Could not connect rowsMoved signal: %s", e)

        self.pages_list_widget.customContextMenuRequested.connect(self.show_pages_context_menu)
        self.pages_list_widget.itemDoubleClicked.connect(self.open_full_page_viewer)

    # ---------------- اللغة ----------------
    def toggle_language(self):
        self.tr_.toggle()
        self.apply_language()

    def apply_language(self):
        """يطبّق اللغة الحالية على كل عناصر الواجهة الثابتة، ويعيد بناء العناصر الديناميكية (قوائم الملفات/الصفحات)."""
        t = self.tr_.t
        self.setWindowTitle(t("app_title"))
        self.title_label.setText(t("app_title"))
        self.subtitle_label.setText(t("app_subtitle"))
        self.btn_lang.setText(t("lang_button"))

        self.setLayoutDirection(Qt.RightToLeft if self.tr_.is_rtl else Qt.LeftToRight)

        self.btn_add.setText(t("btn_add_files"))
        self.btn_add_images.setText(t("btn_add_images"))
        self.btn_ranges.setText(t("btn_ranges"))
        self.btn_clear.setText(t("btn_clear"))
        self.compression_label.setText(t("compression_label"))
        self.compression_slider.setToolTip(t("compression_hint"))
        self.compression_value_label.setToolTip(t("compression_hint"))
        self._update_compression_label()

        self.files_panel_title.setText(t("files_panel_title"))
        self.btn_top.setText(t("btn_top"))
        self.btn_up.setText(t("btn_up"))
        self.btn_down.setText(t("btn_down"))
        self.btn_bottom.setText(t("btn_bottom"))
        self.btn_remove_files.setText(t("btn_remove_files"))

        self.pages_panel_title.setText(t("pages_panel_title"))
        self.pages_panel_hint.setText(t("pages_panel_hint"))
        self.pages_empty_label.setText(t("pages_empty_hint"))
        self.btn_merge.setText(t("btn_merge"))
        # أزرار ترتيب الصفحة بنصوص صريحة + سهم يطابق اتجاه اللغة
        self.btn_page_first.setText(t("page_first"))
        self.btn_page_back.setText(t("page_back"))
        self.btn_page_fwd.setText(t("page_forward"))
        self.btn_page_last.setText(t("page_last"))
        self.btn_refresh.setText(t("btn_refresh"))
        self.btn_undo.setText(t("btn_undo"))

        self._update_status_bar()
        self.refresh_files_list()
        self._relabel_page_items()

    def _on_compression_changed(self, value):
        self._update_compression_label()

    def _update_compression_label(self):
        """يحدّث شارة مستوى الضغط بالنص المناسب حسب قيمة الـ slider واللغة."""
        level = self.compression_slider.value()
        keys = {0: "compression_none", 1: "compression_light",
                2: "compression_medium", 3: "compression_strong"}
        self.compression_value_label.setText(self.tr_.t(keys.get(level, "compression_none")))

    def _next_page_uid(self) -> int:
        self._page_uid_counter += 1
        return self._page_uid_counter

    def _update_status_bar(self):
        t = self.tr_.t
        n_files = len(self.pdf_paths)
        n_pages = self.pages_list_widget.count()
        self.pages_stack.setCurrentWidget(self.pages_list_widget if n_pages else self.pages_empty_label)
        self.btn_merge.setEnabled(n_pages > 0)
        self.status_label.setText(
            f"{t('status_files_count', n=n_files)}    •    {t('status_pages_count', n=n_pages)}"
        )

    def _relabel_page_items(self):
        for i in range(self.pages_list_widget.count()):
            item = self.pages_list_widget.item(i)
            if item.data(USERROLE_PAGEINFO):
                self._mark_annotated(item, bool(self._page_stamps.get(item.data(USERROLE_PAGEUID))))

    def _page_label(self, page_num_zero_based: int) -> str:
        return (f"صفحة {page_num_zero_based + 1}" if self.tr_.is_rtl
                else f"Page {page_num_zero_based + 1}")

    def _card_label(self, doc_path: str, page_num_zero_based: int) -> str:
        """النص الموحّد المعروض تحت كل بطاقة صفحة: اسم ملف مختصر + رقم صفحة."""
        return f"{truncate_filename(human_name(doc_path))}\n{self._page_label(page_num_zero_based)}"

    # ------------- Drag & Drop على النافذة -------------
    _ACCEPTED_EXT = (".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if u.toLocalFile().lower().endswith(self._ACCEPTED_EXT):
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e):
        paths = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(self._ACCEPTED_EXT):
                paths.append(p)
        if paths:
            self.add_paths(paths)

    # ------------- لوحة الملفات -------------
    def add_pdfs_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, self.tr_.t("btn_add_files"), self.last_dir, "PDF (*.pdf)")
        if file_paths:
            self.last_dir = os.path.dirname(file_paths[0])
            self.add_paths(file_paths)

    def add_images_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, self.tr_.t("msg_add_images_dialog"), self.last_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp)"
        )
        if file_paths:
            self.last_dir = os.path.dirname(file_paths[0])
            self.add_paths(file_paths)

    def add_paths(self, file_paths):
        t = self.tr_.t
        rejected = []
        # فحص الملفات الكبيرة قد يأخذ لحظة: مؤشر انتظار بدل واجهة تبدو متجمدة
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for p in file_paths:
                if p in self.pdf_paths:
                    continue
                try:
                    self.engine.probe_file(p)
                except ValueError as e:
                    rejected.append((human_name(p), str(e)))
                    continue
                self.pdf_paths.append(p)
                self.per_file_ranges.setdefault(p, "all")
            self.refresh_files_list()
            self.update_page_list()
        finally:
            QApplication.restoreOverrideCursor()

        if rejected:
            # كل ملف مرفوض في سطر ضمن بطاقة تفاصيل (الاسم ← السبب)
            dialogs.warning(self, t("msg_files_skipped_title"), "", details=rejected)

    def refresh_files_list(self):
        t = self.tr_.t
        self.files_list_widget.clear()
        for p in self.pdf_paths:
            # سطران: اسم الملف، ثم عدد صفحاته (والنطاق لو لم يكن "الكل")
            details = t("file_item_pages", n=self.engine.page_count(p))
            rng = self.per_file_ranges.get(p, "all")
            if rng.strip().lower() not in ("", "all"):
                details += "  •  " + t("file_item_range", r=rng)
            it = QListWidgetItem(f"{human_name(p)}\n{details}")
            it.setToolTip(p)
            it.setData(USERROLE_FILEPATH, p)
            it.setFlags(it.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.files_list_widget.addItem(it)
        self._update_status_bar()

    def on_files_reordered(self):
        new_order = []
        for i in range(self.files_list_widget.count()):
            it = self.files_list_widget.item(i)
            p = it.data(USERROLE_FILEPATH)
            if p:
                new_order.append(p)
        if new_order and new_order != self.pdf_paths:
            self.pdf_paths = new_order
            self.update_page_list()

    def remove_selected_files(self):
        rows = sorted([self.files_list_widget.row(it) for it in self.files_list_widget.selectedItems()], reverse=True)
        removed = set()
        for r in rows:
            it = self.files_list_widget.item(r)
            p = it.data(USERROLE_FILEPATH)
            if p in self.pdf_paths:
                self.pdf_paths.remove(p)
                self.per_file_ranges.pop(p, None)
                self._applied_ranges.pop(p, None)
                removed.add(p)
        if removed:
            # نحذف بطاقات هذه الملفات فقط؛ باقي الصفحات تبقى بتعديلاتها
            for row in reversed(range(self.pages_list_widget.count())):
                item = self.pages_list_widget.item(row)
                if self._item_path(item) in removed:
                    self._forget_item(self.pages_list_widget.takeItem(row))
            kept_undo = []
            for row, item in self._undo_stack:
                if self._item_path(item) in removed:
                    self._forget_item(item)
                else:
                    kept_undo.append((row, item))
            self._undo_stack = kept_undo
            self.btn_undo.setEnabled(bool(self._undo_stack))
            for p in removed:
                self.engine.close_path(p)
        self.refresh_files_list()
        self.update_page_list()

    def set_ranges_for_selected_file(self):
        t = self.tr_.t
        items = self.files_list_widget.selectedItems()
        if not items:
            dialogs.info(self, t("msg_attention"), t("msg_select_file_first"))
            return
        for it in items:
            p = it.data(USERROLE_FILEPATH)
            if not p:
                continue
            try:
                info = self.engine.probe_file(p)
            except ValueError as e:
                dialogs.warning(self, t("msg_error"), t("msg_open_failed", name=human_name(p), error=e))
                continue
            dlg = RangeDialog(self, self.tr_, human_name(p), info.page_count, self.per_file_ranges.get(p, "all"))
            ok = dlg.exec_()
            if ok == QDialog.Accepted:
                self.per_file_ranges[p] = dlg.get_value()
        self.update_page_list()
        self.refresh_files_list()

    def clear_all(self):
        if self._thumb_worker is not None:
            self._thumb_worker.clear()
        self.files_list_widget.clear()
        self.pages_list_widget.clear()
        self.pdf_paths.clear()
        self.per_file_ranges.clear()
        self._applied_ranges.clear()
        self._synced_order = []
        self._items_by_uid.clear()
        self._undo_stack.clear()
        self._page_stamps.clear()
        self.btn_undo.setEnabled(False)
        self.engine.close_all()
        self._update_status_bar()

    # ------------- تحريك الملفات (أزرار) -------------
    def move_selected_files(self, delta: int):
        t = self.tr_.t
        items = self.files_list_widget.selectedItems()
        if not items:
            dialogs.info(self, t("msg_attention"), t("msg_select_files_to_move"))
            return

        rows = sorted([self.files_list_widget.row(it) for it in items])
        if delta > 0:
            rows = list(reversed(rows))
        changed = False
        for r in rows:
            new_r = r + delta
            if 0 <= new_r < self.files_list_widget.count():
                self.pdf_paths[r], self.pdf_paths[new_r] = self.pdf_paths[new_r], self.pdf_paths[r]
                changed = True
        if changed:
            selected_paths = [it.data(USERROLE_FILEPATH) for it in items]
            self.refresh_files_list()
            for i in range(self.files_list_widget.count()):
                it = self.files_list_widget.item(i)
                if it.data(USERROLE_FILEPATH) in selected_paths:
                    it.setSelected(True)
            self.update_page_list()

    def move_selected_files_to_edge(self, top: bool = True):
        t = self.tr_.t
        items = self.files_list_widget.selectedItems()
        if not items:
            dialogs.info(self, t("msg_attention"), t("msg_select_files_to_move"))
            return

        selected_paths = [it.data(USERROLE_FILEPATH) for it in items]
        rest = [p for p in self.pdf_paths if p not in selected_paths]
        self.pdf_paths = (selected_paths + rest) if top else (rest + selected_paths)

        self.refresh_files_list()
        for i in range(self.files_list_widget.count()):
            it = self.files_list_widget.item(i)
            if it.data(USERROLE_FILEPATH) in selected_paths:
                it.setSelected(True)
        self.update_page_list()

    # ------------- ترتيب الصفحات بالأسهم -------------
    def _on_page_selection_changed(self):
        """يُظهر/يخفي شريط أسهم الترتيب حسب وجود صفحة محددة، ويحدّث التسمية."""
        items = self.pages_list_widget.selectedItems()
        if items:
            row = self.pages_list_widget.row(items[0])
            total = self.pages_list_widget.count()
            self.page_order_bar.setVisible(True)
            self.page_order_label.setText(
                self.tr_.t("page_order_label", pos=row + 1, total=total)
            )
            # تعطيل الأسهم غير المنطقية عند الحواف
            self.btn_page_first.setEnabled(row > 0)
            self.btn_page_back.setEnabled(row > 0)
            self.btn_page_fwd.setEnabled(row < total - 1)
            self.btn_page_last.setEnabled(row < total - 1)
        else:
            self.page_order_bar.setVisible(False)

    def _move_page_row(self, from_row: int, to_row: int):
        """ينقل صفحة من موضع لآخر مع الحفاظ على كل بياناتها وتحديدها."""
        if from_row == to_row or from_row < 0:
            return
        item = self.pages_list_widget.takeItem(from_row)
        if item is None:
            return
        self.pages_list_widget.insertItem(to_row, item)
        self.pages_list_widget.setCurrentItem(item)
        item.setSelected(True)
        self.pages_list_widget.doItemsLayout()
        self._on_page_selection_changed()

    def move_selected_page(self, delta: int):
        items = self.pages_list_widget.selectedItems()
        if not items:
            return
        row = self.pages_list_widget.row(items[0])
        new_row = row + delta
        if 0 <= new_row < self.pages_list_widget.count():
            self._move_page_row(row, new_row)

    def move_selected_page_to_edge(self, first: bool = True):
        items = self.pages_list_widget.selectedItems()
        if not items:
            return
        row = self.pages_list_widget.row(items[0])
        target = 0 if first else self.pages_list_widget.count() - 1
        self._move_page_row(row, target)

    # ------------- لوحة الصفحات -------------
    # ---- بطاقات الصفحات ----
    @staticmethod
    def _item_path(item):
        info = item.data(USERROLE_PAGEINFO) if item is not None else None
        return info['doc_path'] if info else None

    @staticmethod
    def _item_ref(item) -> PageRef:
        info = item.data(USERROLE_PAGEINFO)
        return PageRef(doc_path=info['doc_path'], page_num=info['page_num'],
                       rot=int(item.data(USERROLE_PAGEROT) or 0))

    def _make_page_item(self, ref: PageRef, icon: QIcon = None) -> QListWidgetItem:
        """ينشئ بطاقة صفحة ويسجّلها. بدون أيقونة جاهزة تظهر بطاقة هيكلية
        وتُطلب المصغّرة من الخلفية."""
        ready = icon is not None and not icon.isNull()
        item = QListWidgetItem(icon if ready else placeholder_icon(),
                               self._card_label(ref.doc_path, ref.page_num))
        item.setData(USERROLE_THUMBREADY, ready)
        uid = self._next_page_uid()
        item.setData(USERROLE_PAGEINFO, {'doc_path': ref.doc_path, 'page_num': ref.page_num})
        item.setData(USERROLE_PAGEROT, ref.rot)
        item.setData(USERROLE_PAGEUID, uid)
        item.setFlags(item.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        item.setTextAlignment(Qt.AlignCenter)
        item.setSizeHint(PAGE_CARD)
        self._items_by_uid[uid] = item
        if not ready:
            self._queue_thumbnails([item])
        return item

    def _forget_item(self, item):
        """ينسى بطاقة حُذفت نهائيًا (مع تواقيعها) حتى لا تبقى في الذاكرة."""
        uid = item.data(USERROLE_PAGEUID)
        self._items_by_uid.pop(uid, None)
        self._page_stamps.pop(uid, None)

    def update_page_list(self):
        """
        يزامن شبكة الصفحات مع قائمة الملفات ونطاقاتها، ويغيّر فقط ما يلزم:
        - ملف جديد: تُضاف صفحاته في النهاية.
        - نطاق تغيّر: تُزال الصفحات الخارجة منه وتُدرج الجديدة في مكانها.
        - ترتيب الملفات تغيّر: تُنقل صفحات كل ملف (ومعها ما أُدرج بعدها) ككتلة.
        الدوران والتكرار والترتيب اليدوي والتواقيع تبقى كما هي.
        """
        t = self.tr_.t
        lw = self.pages_list_widget
        flat = [lw.item(i) for i in range(lw.count())]
        before = list(flat)

        known_order = [p for p in self.pdf_paths if p in self._synced_order]
        if known_order != [p for p in self._synced_order if p in self.pdf_paths]:
            flat = self._regroup_by_file(flat)

        for path in self.pdf_paths:
            want = self.per_file_ranges.get(path, "all")
            applied = self._applied_ranges.get(path)
            if applied == want:
                continue
            try:
                refs = self.engine.expand_file_to_pages(path, want)
            except ValueError as e:
                dialogs.warning(self, t("msg_range_error_title"), f"{human_name(path)}: {e}")
                continue
            except Exception as e:
                logger.exception("Failed expanding %s", path)
                dialogs.warning(self, t("msg_error"), t("msg_read_failed", name=human_name(path), error=e))
                continue
            if applied is None:
                flat.extend(self._make_page_item(r) for r in refs)
            else:
                flat = self._apply_range_change(flat, path, refs)
            self._applied_ranges[path] = want

        self._synced_order = list(self.pdf_paths)
        if [id(i) for i in flat] != [id(i) for i in before]:
            lw.setUpdatesEnabled(False)
            for row in reversed(range(lw.count())):
                lw.takeItem(row)
            for item in flat:
                lw.addItem(item)
            lw.setUpdatesEnabled(True)
        self._update_status_bar()

    def _regroup_by_file(self, flat):
        """يرتّب البطاقات ككتل حسب ترتيب الملفات الجديد. الصفحات المُدرجة من
        ملفات خارج القائمة تبقى ملتصقة بكتلة الملف الذي سبقها."""
        groups = {p: [] for p in self.pdf_paths}
        anchor, leading, orphans = None, [], []
        for item in flat:
            p = self._item_path(item)
            if p in groups:
                if anchor is None:
                    groups[p].extend(leading)
                    leading = []
                anchor = p
                groups[p].append(item)
            elif anchor is not None:
                groups[anchor].append(item)
            else:
                leading.append(item)
        orphans.extend(leading)
        return [it for p in self.pdf_paths for it in groups[p]] + orphans

    def _apply_range_change(self, flat, path, refs):
        """يطبّق نطاقًا جديدًا لملف واحد دون لمس بطاقات الملفات الأخرى."""
        wanted = {r.page_num for r in refs}
        result = []
        for item in flat:
            info = item.data(USERROLE_PAGEINFO)
            if info['doc_path'] == path and info['page_num'] not in wanted:
                self._forget_item(item)
            else:
                result.append(item)
        present = {item.data(USERROLE_PAGEINFO)['page_num']
                   for item in result if self._item_path(item) == path}
        for ref in refs:
            if ref.page_num in present:
                continue
            # نضعها قبل أول صفحة من نفس الملف رقمها أكبر، وإلا بعد آخر صفحة منه
            pos, last_own = None, None
            for idx, item in enumerate(result):
                if self._item_path(item) != path:
                    continue
                last_own = idx
                if item.data(USERROLE_PAGEINFO)['page_num'] > ref.page_num:
                    pos = idx
                    break
            if pos is None:
                pos = len(result) if last_own is None else last_own + 1
            result.insert(pos, self._make_page_item(ref))
            present.add(ref.page_num)
        return result

    # ---- المصغّرات في الخلفية ----
    def _queue_thumbnails(self, items):
        if not items:
            return
        if self._thumb_worker is None:
            self._thumb_worker = ThumbnailWorker(self.engine, parent=self)
            self._thumb_worker.page_ready.connect(self._on_thumbnail_ready)
            self._thumb_worker.page_failed.connect(self._on_thumbnail_failed)
            self._thumb_worker.finished.connect(self._on_thumb_worker_finished)
        self._thumb_worker.enqueue((it.data(USERROLE_PAGEUID), self._item_ref(it)) for it in items)
        self._thumb_total += len(items)
        self._update_thumb_progress()
        if not self._thumb_worker.isRunning():
            # أولوية منخفضة: الرسم يأخذ ما يفيض من المعالج فقط ولا يثقل الجهاز
            self._thumb_worker.start(QThread.LowPriority)

    def refresh_thumbnails(self):
        """يعيد توليد مصغّرات كل الصفحات (زر "تحديث المعاينات")."""
        self.engine.thumb_cache.clear()
        lw = self.pages_list_widget
        self._queue_thumbnails([lw.item(i) for i in range(lw.count())])

    @staticmethod
    def _thumb_icon(pm: QPixmap) -> QIcon:
        """أيقونة بنفس الصورة في حالة التحديد، حتى لا يصبغها Qt بالأزرق."""
        icon = QIcon()
        icon.addPixmap(pm, QIcon.Normal)
        icon.addPixmap(pm, QIcon.Selected)
        return icon

    def _update_thumb_progress(self):
        busy = self._thumb_done < self._thumb_total
        self.thumb_progress_box.setVisible(busy)
        if busy:
            self.thumb_progress_label.setText(
                self.tr_.t("generating_previews", done=self._thumb_done, total=self._thumb_total))
            self.thumb_progress_bar.setMaximum(self._thumb_total)
            self.thumb_progress_bar.setValue(self._thumb_done)

    def _on_thumbnail_ready(self, uid, rendered_rot, image):
        self._thumb_done += 1
        self._update_thumb_progress()
        item = self._items_by_uid.get(uid)
        if item is None:
            return
        pm = QPixmap.fromImage(image)
        # لو دوّر المستخدم الصفحة قبل وصول مصغّرتها، ندوّر الصورة بالفرق فقط
        delta = (int(item.data(USERROLE_PAGEROT) or 0) - rendered_rot) % 360
        if delta:
            pm = pm.transformed(QTransform().rotate(delta))
        item.setIcon(self._thumb_icon(pm))
        item.setData(USERROLE_THUMBREADY, True)

    def _on_thumbnail_failed(self, uid, error_msg):
        self._thumb_done += 1
        self._update_thumb_progress()
        logger.warning("Thumbnail %s failed: %s", uid, error_msg)

    def _on_thumb_worker_finished(self):
        if self._thumb_worker is not None and self._thumb_worker.pending():
            # وصلت مهام بعد آخر فحص للطابور مباشرة: نكمل
            self._thumb_worker.start(QThread.LowPriority)
            return
        self._thumb_done = self._thumb_total = 0
        self._update_thumb_progress()

    def show_pages_context_menu(self, pos: QPoint):
        t = self.tr_.t
        item = self.pages_list_widget.itemAt(pos)
        menu = QMenu(self)
        if item:
            act_preview = QAction(t("ctx_preview"), self)
            act_annotate = QAction(t("ctx_annotate"), self)
            act_rot_right = QAction(t("ctx_rotate_right"), self)
            act_rot_left = QAction(t("ctx_rotate_left"), self)
            act_dup = QAction(t("ctx_duplicate"), self)
            act_ins_before = QAction(t("ctx_insert_before"), self)
            act_ins_after = QAction(t("ctx_insert_after"), self)
            act_del = QAction(t("ctx_delete"), self)

            act_preview.triggered.connect(lambda: self.open_full_page_viewer(item))
            act_annotate.triggered.connect(lambda: self.annotate_page(item))
            act_rot_right.triggered.connect(lambda: self.rotate_page(item, +90))
            act_rot_left.triggered.connect(lambda: self.rotate_page(item, -90))
            act_dup.triggered.connect(lambda: self.duplicate_page(item))
            act_ins_before.triggered.connect(lambda: self.insert_pages_at(item, before=True))
            act_ins_after.triggered.connect(lambda: self.insert_pages_at(item, before=False))
            act_del.triggered.connect(lambda: self.delete_page(item))

            menu.addAction(act_preview)
            menu.addAction(act_annotate)
            menu.addSeparator()
            menu.addAction(act_rot_right)
            menu.addAction(act_rot_left)
            menu.addAction(act_dup)
            menu.addSeparator()
            menu.addAction(act_ins_before)
            menu.addAction(act_ins_after)
            menu.addSeparator()
            menu.addAction(act_del)
        else:
            menu.addAction(QAction(t("ctx_no_page"), self)).setEnabled(False)
        menu.exec_(self.pages_list_widget.mapToGlobal(pos))

    def rotate_page(self, item, delta):
        t = self.tr_.t
        row = self.pages_list_widget.row(item)
        if row < 0:
            return
        new_rot = (int(item.data(USERROLE_PAGEROT) or 0) + delta) % 360
        item.setData(USERROLE_PAGEROT, new_rot)
        # ندوّر صورة المصغّرة الموجودة بدل إعادة رسم الصفحة من الـ PDF.
        # لو لم تصل المصغّرة بعد، ستُدوَّر تلقائيًا عند وصولها.
        icon = item.icon()
        if item.data(USERROLE_THUMBREADY):
            try:
                pm = icon.pixmap(QSize(THUMB_MAX, THUMB_MAX)).transformed(QTransform().rotate(delta))
                item.setIcon(self._thumb_icon(pm))
            except Exception as e:
                logger.exception("Rotate preview failed")
                dialogs.warning(self, t("msg_error"), t("msg_rotate_error", error=e))

    def duplicate_page(self, item):
        row = self.pages_list_widget.row(item)
        if row < 0:
            return
        dup = self._make_page_item(self._item_ref(item),
                                   icon=item.icon() if item.data(USERROLE_THUMBREADY) else None)
        self.pages_list_widget.insertItem(row + 1, dup)
        # IconMode لا يعيد حساب مواقع البطاقات تلقائيًا دائمًا عند الإدراج
        # في المنتصف؛ نجبره صراحة لتفادي تراكب بصري بين البطاقات
        self.pages_list_widget.doItemsLayout()
        self._update_status_bar()

    def insert_pages_at(self, item, before=True):
        """يدرج صفحات من ملف PDF أو صور جديدة قبل/بعد الصفحة المحددة مباشرة."""
        t = self.tr_.t
        row = self.pages_list_widget.row(item)
        if row < 0:
            return
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, t("msg_insert_files_dialog"), self.last_dir,
            "PDF & Images (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp)"
        )
        if not file_paths:
            return
        self.last_dir = os.path.dirname(file_paths[0])

        new_refs = []
        rejected = []
        for p in file_paths:
            try:
                self.engine.probe_file(p)
                new_refs.extend(self.engine.expand_file_to_pages(p, "all"))
            except ValueError as e:
                rejected.append(f"{human_name(p)}: {e}")
        if rejected:
            dialogs.warning(self, t("msg_files_skipped_title"),
                                t("msg_some_files_rejected", list="\n".join(rejected)))
        if not new_refs:
            return

        # البطاقات تُدرج فورًا والمصغّرات تُرسم في الخلفية، فلا تتجمد
        # الواجهة حتى مع إدراج ملف من مئات الصفحات
        insert_at = row if before else row + 1
        for offset, ref in enumerate(new_refs):
            self.pages_list_widget.insertItem(insert_at + offset, self._make_page_item(ref))
        self.pages_list_widget.doItemsLayout()
        self._update_status_bar()

    def annotate_page(self, item):
        """يفتح نافذة التوقيع/الختم/الكتابة على الصفحة المحددة."""
        t = self.tr_.t
        uid = item.data(USERROLE_PAGEUID)
        try:
            pm = QPixmap.fromImage(rendered_to_qimage(self.engine.render_full_page(self._item_ref(item))))
        except Exception as e:
            logger.exception("Annotate preview failed")
            dialogs.error(self, t("msg_error"), t("msg_preview_error", error=e))
            return

        existing = self._page_stamps.get(uid, [])
        dlg = AnnotateDialog(self, self.tr_, pm, existing_stamps=existing)
        if dlg.exec_() == QDialog.Accepted:
            self._page_stamps[uid] = dlg.get_stamps()
            self._mark_annotated(item, bool(self._page_stamps[uid]))

    def _mark_annotated(self, item, has_stamps: bool):
        """يضيف إشارة ✍️ لاسم البطاقة لو فيها تواقيع/أختام."""
        info = item.data(USERROLE_PAGEINFO)
        base = self._card_label(info['doc_path'], info['page_num'])
        item.setText(("✍️ " + base) if has_stamps else base)

    def delete_page(self, item):
        t = self.tr_.t
        row = self.pages_list_widget.row(item)
        if row < 0:
            return
        if dialogs.confirm(self, t("msg_confirm_delete_title"), t("msg_confirm_delete_body"),
                           yes_text=t("btn_delete"), no_text=t("btn_cancel"), danger=True):
            # نحتفظ بالبطاقة نفسها (معرّفها، أيقونتها، دورانها، تواقيعها)
            # حتى يعيدها التراجع كما كانت تمامًا
            self._undo_stack.append((row, self.pages_list_widget.takeItem(row)))
            self.btn_undo.setEnabled(True)
            self._update_status_bar()

    def undo_delete_page(self):
        if not self._undo_stack:
            return
        row, item = self._undo_stack.pop()
        insert_at = min(row, self.pages_list_widget.count())
        self.pages_list_widget.insertItem(insert_at, item)
        self.pages_list_widget.doItemsLayout()
        if not self._undo_stack:
            self.btn_undo.setEnabled(False)
        self._update_status_bar()

    def open_full_page_viewer(self, item):
        t = self.tr_.t
        info = item.data(USERROLE_PAGEINFO)
        try:
            pm = QPixmap.fromImage(rendered_to_qimage(self.engine.render_full_page(self._item_ref(item))))
            title = t("viewer_title", name=human_name(info['doc_path']), page=info['page_num'] + 1)
            viewer = FullPageViewer(self, self.tr_, pm, title)
            viewer.exec_()
        except Exception as e:
            logger.exception("Full page preview failed")
            dialogs.error(self, t("msg_error"), t("msg_preview_error", error=e))

    # ------------- الدمج -------------
    def _random_filename(self) -> str:
        """يولّد اسم ملف عشوائي افتراضي للناتج: PDF_ + تاريخ ووقت + لاحقة قصيرة."""
        import datetime
        import random
        import string
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"PDF_{stamp}_{suffix}.pdf"

    def merge_pdfs(self):
        t = self.tr_.t
        if self.pages_list_widget.count() == 0:
            dialogs.warning(self, t("msg_attention"), t("msg_add_pages_first"))
            return

        # نقترح اسمًا عشوائيًا افتراضيًا حتى لا يضطر المستخدم لكتابته
        default_name = self._random_filename()
        default_path = os.path.join(self.last_dir, default_name)
        output_path, _ = QFileDialog.getSaveFileName(self, t("msg_merge_dialog_title"), default_path, "PDF (*.pdf)")
        if not output_path:
            return
        self.last_dir = os.path.dirname(output_path)

        final_list = []
        stamps = []
        for i in range(self.pages_list_widget.count()):
            it = self.pages_list_widget.item(i)
            info = it.data(USERROLE_PAGEINFO)
            rot = int(it.data(USERROLE_PAGEROT) or 0)
            uid = it.data(USERROLE_PAGEUID)
            if info:
                final_list.append(PageRef(doc_path=info['doc_path'], page_num=info['page_num'], rot=rot))
                # نحوّل أي أختام/تواقيع/نصوص مرتبطة بهذه الصفحة إلى StampSpec
                # برقم صفحتها النهائي (i) في الناتج
                for st in self._page_stamps.get(uid, []):
                    stamps.append(StampSpec(
                        page_index=i,
                        kind=st['kind'],
                        content=st.get('content', ''),
                        x=st.get('x', 0.1), y=st.get('y', 0.1),
                        w=st.get('w', 0.2), h=st.get('h', 0.1),
                        font_size=st.get('font_size', 14.0),
                        color=st.get('color', (0.0, 0.0, 0.0)),
                        font_name=st.get('font_name', 'helv'),
                        font_file=st.get('font_file', ''),
                    ))

        compression_level = self.compression_slider.value()

        progress = dialogs.TaskProgressDialog(self, t("msg_merge_progress_title"), self.tr_)
        self._merge_progress_dialog = progress
        self._merge_page_count = len(final_list)

        self._merge_worker = MergeWorker(
            self.engine, final_list, output_path,
            compression_level=compression_level, stamps=stamps, parent=self
        )
        self._merge_worker.progress.connect(self._on_merge_progress)
        self._merge_worker.stage.connect(self._on_merge_stage)
        self._merge_worker.succeeded.connect(self._on_merge_succeeded)
        self._merge_worker.failed.connect(self._on_merge_failed)
        self._merge_worker.cancelled.connect(self._on_merge_cancelled)
        progress.canceled.connect(self._merge_worker.request_cancel)

        progress.set_progress(0, len(final_list))
        progress.show()
        self._merge_worker.start()

    def _on_merge_progress(self, done, total):
        if self._merge_progress_dialog is not None:
            self._merge_progress_dialog.set_progress(done, total)

    def _on_merge_stage(self, name):
        """يحدّث نافذة التقدّم بالمرحلة الحالية. الضغط والحفظ مدتهما غير
        معروفة فيظهر شريط متحرك، ولا يمكن إلغاؤهما في منتصف الكتابة."""
        dlg = self._merge_progress_dialog
        if dlg is None or name == "pages":
            return
        dlg.set_stage(self.tr_.t(f"stage_{name}"), determinate=False, cancellable=False)

    def _close_merge_progress(self):
        if self._merge_progress_dialog is not None:
            self._merge_progress_dialog.close()
            self._merge_progress_dialog.deleteLater()
            self._merge_progress_dialog = None

    def _on_merge_succeeded(self, result):
        t = self.tr_.t
        self._close_merge_progress()

        details = [
            (t("result_file"), human_name(result.output_path)),
            (t("result_folder"), os.path.dirname(result.output_path)),
            (t("result_pages"), self._merge_page_count),
        ]
        if result.optimized and result.size_before and result.size_after:
            ratio = (1 - (result.size_after / result.size_before)) * 100 if result.size_before > 0 else 0
            level_keys = {1: "compression_light", 2: "compression_medium", 3: "compression_strong"}
            details.append((t("result_compression"), t(level_keys.get(result.compression_level, "compression_light"))))
            details.append((t("result_before"), human_filesize(result.size_before, self.tr_)))
            details.append((t("result_after"), human_filesize(result.size_after, self.tr_)))
            details.append((t("result_saving"), f"{max(ratio, 0):.0f}%"))
        elif result.size_after:
            details.append((t("result_size"), human_filesize(result.size_after, self.tr_)))

        dialogs.success(self, t("msg_merge_success_title"), t("result_saved_text"),
                        details=details, open_path=result.output_path)
        self.clear_all()

    def _on_merge_failed(self, error_msg):
        t = self.tr_.t
        self._close_merge_progress()
        dialogs.error(self, t("msg_error"), t("msg_merge_failed", error=error_msg))

    def _on_merge_cancelled(self):
        t = self.tr_.t
        self._close_merge_progress()
        dialogs.info(self, t("msg_merge_cancelled_title"), t("msg_merge_cancelled_body"))

    def closeEvent(self, event):
        # نطلب الإيقاف من الاثنين أولًا ثم ننتظر: خيط المعاينات قد يكون
        # منتظرًا قفل المحرّك الذي يمسكه الدمج
        if self._thumb_worker is not None:
            self._thumb_worker.cancel()
        if self._merge_worker is not None:
            self._merge_worker.request_cancel()
        for worker in (self._merge_worker, self._thumb_worker):
            if worker is not None:
                worker.wait()
        self.engine.close_all()
        event.accept()


def main(app=None, splash=None):
    """app/splash يمرّرهما launcher.py (شاشة البداية)؛ التشغيل المباشر ينشئ التطبيق هنا."""
    if app is None:
        if sys.platform == "win32":
            # معرّف ثابت للتطبيق حتى يُظهر شريط المهام أيقونته الخاصة بدل أيقونة بايثون
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PDFMerger.App")
            except Exception:
                pass
        app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    from resources import resource_path
    icon_path = resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from theme import UI_FONT
    default_font = QFont(UI_FONT, 10)
    app.setFont(default_font)

    w = PDFMergerApp()
    if splash is not None:
        splash.step(100)
    w.show()
    if splash is not None:
        splash.finish(w)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
