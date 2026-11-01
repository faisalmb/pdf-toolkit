# -*- coding: utf-8 -*-
"""
workers.py
عمليات تعمل في Thread منفصل عن واجهة المستخدم (QThread) حتى لا تتجمد
الواجهة أثناء توليد المعاينات أو الدمج لملفات كبيرة.
"""
import logging
import threading
from collections import deque
from typing import Iterable, Tuple

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from pdf_engine import PdfEngine, PageRef, RenderedImage

logger = logging.getLogger("workers")


def rendered_to_qimage(img: RenderedImage) -> QImage:
    """يحوّل بكسلات RGB خام إلى QImage مستقلة (copy حتى لا تعتمد على البايتات)."""
    return QImage(img.samples, img.width, img.height, img.stride, QImage.Format_RGB888).copy()


class ThumbnailWorker(QThread):
    """
    يولّد مصغّرات الصفحات في الخلفية من طابور مهام (uid البطاقة + مرجع الصفحة)،
    ويبعث إشارة لكل صفحة جاهزة. الواجهة تضيف مهام جديدة للطابور متى شاءت
    (إضافة ملف، إدراج صفحات...) بدل إلغاء كل شيء وإعادة رسم كل الصفحات.
    يعمل بأولوية منخفضة حتى لا يُثقل الجهاز، ويتوقف تلقائيًا عند فراغ الطابور.
    QImage (وليس QPixmap) آمنة للإنشاء خارج خيط الواجهة، فالتحويل يتم هنا.
    """
    page_ready = pyqtSignal(int, int, QImage)   # uid, الدوران المرسوم, الصورة
    page_failed = pyqtSignal(int, str)          # uid, رسالة الخطأ

    def __init__(self, engine: PdfEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._jobs = deque()
        self._jobs_lock = threading.Lock()
        self._stopped = False

    def enqueue(self, jobs: Iterable[Tuple[int, PageRef]]) -> None:
        with self._jobs_lock:
            self._jobs.extend(jobs)

    def pending(self) -> int:
        with self._jobs_lock:
            return len(self._jobs)

    def clear(self) -> None:
        """يُفرغ الطابور (مثلاً عند مسح كل الملفات)."""
        with self._jobs_lock:
            self._jobs.clear()

    def cancel(self) -> None:
        """إيقاف نهائي (عند إغلاق البرنامج)."""
        self._stopped = True
        self.clear()

    def run(self):
        while not self._stopped:
            with self._jobs_lock:
                if not self._jobs:
                    break
                uid, ref = self._jobs.popleft()
            try:
                img = rendered_to_qimage(self.engine.render_thumbnail(ref))
                self.page_ready.emit(uid, ref.rot, img)
            except Exception as e:
                logger.warning("Thumbnail failed for %s page %s: %s", ref.doc_path, ref.page_num, e)
                self.page_failed.emit(uid, str(e))


class MergeWorker(QThread):
    """ينفّذ عملية الدمج كاملة في الخلفية مع بث تقدّم حي للواجهة."""
    progress = pyqtSignal(int, int)     # done, total
    stage = pyqtSignal(str)             # "pages" / "stamps" / "compress" / "save"
    succeeded = pyqtSignal(object)      # MergeResult
    failed = pyqtSignal(str)            # رسالة الخطأ
    cancelled = pyqtSignal()

    def __init__(self, engine: PdfEngine, page_refs,
                 output_path: str, compression_level: int = 0,
                 stamps=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.page_refs = page_refs
        self.output_path = output_path
        self.compression_level = compression_level
        self.stamps = stamps
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def run(self):
        try:
            def progress_cb(done, total):
                self.progress.emit(done, total)

            def is_cancelled():
                return self._cancel_requested

            result = self.engine.merge(
                self.page_refs,
                self.output_path,
                compression_level=self.compression_level,
                progress_cb=progress_cb,
                is_cancelled=is_cancelled,
                stamps=self.stamps,
                stage_cb=self.stage.emit,
            )

            if result.cancelled:
                self.cancelled.emit()
            else:
                self.succeeded.emit(result)
        except Exception as e:
            logger.exception("Merge failed")
            self.failed.emit(str(e))
