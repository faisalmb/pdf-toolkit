# -*- coding: utf-8 -*-
"""
pdf_engine.py
طبقة منطق PDF منفصلة عن واجهة المستخدم.
مسؤولة عن: فتح الملفات، توليد المعاينات، تحليل النطاقات، الدمج والحفظ.
فصلها عن الواجهة يسهّل الصيانة والاختبار ويمنع تكرار الكود.
"""
import os
import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger("pdf_engine")

# أقصى بُعد (بالبكسل) للمصغّرة. الصفحة تُرسم مباشرة بهذا الحجم بدل رسمها
# أكبر ثم تصغيرها في الواجهة، فيقل عمل المعالج والذاكرة.
THUMB_MAX = 180


def human_name(p: str) -> str:
    """اسم الملف فقط بدون المسار الكامل، مع حماية من القيم غير المتوقعة."""
    try:
        return os.path.basename(p)
    except (TypeError, ValueError) as e:
        logger.warning("human_name failed for %r: %s", p, e)
        return str(p)


def parse_range(expr: str, total_pages: int) -> List[int]:
    """
    يحوّل تعبير نطاق نصي (مثل '1-3,5,7-end' أو 'all') إلى قائمة أرقام صفحات
    0-based صحيحة ومرتبة وضمن الحدود.
    يرمي ValueError برسالة عربية واضحة لو التعبير غير صالح، بدل الانهيار
    بخطأ بايثون مبهم.
    """
    expr = (expr or "").strip().lower()
    if expr in ("", "all"):
        return list(range(total_pages))

    pages = set()
    parts = [p.strip() for p in expr.split(",") if p.strip()]
    if not parts:
        raise ValueError("النطاق فارغ أو غير صالح")

    for part in parts:
        try:
            if "-" in part:
                a, b = [x.strip() for x in part.split("-", 1)]
                a_idx = total_pages - 1 if a == "end" else int(a) - 1
                b_idx = total_pages - 1 if b == "end" else int(b) - 1
                lo = max(0, min(a_idx, b_idx))
                hi = min(total_pages - 1, max(a_idx, b_idx))
                pages.update(range(lo, hi + 1))
            else:
                idx = total_pages - 1 if part == "end" else int(part) - 1
                pages.add(idx)
        except ValueError:
            raise ValueError(f"جزء غير صالح في النطاق: '{part}'")

    result = sorted(i for i in pages if 0 <= i < total_pages)
    if not result:
        raise ValueError("لا توجد صفحات ضمن النطاق المُدخل")
    return result


@dataclass
class PageRef:
    """مرجع لصفحة واحدة ضمن خطة الدمج: أي ملف، أي رقم صفحة، وبأي دوران.
    kind يميّز نوع المصدر: 'pdf' صفحة من ملف PDF، 'image' صورة تتحول لصفحة كاملة."""
    doc_path: str
    page_num: int
    rot: int = 0
    kind: str = "pdf"  # "pdf" أو "image"


# مستويات الضغط: كل مستوى يحدد دقة الصور القصوى (DPI) وجودة JPEG.
# القيمة 0 = بدون ضغط. الأرقام مدروسة لتوازن الحجم مقابل الجودة.
COMPRESSION_LEVELS = {
    0: {"name_ar": "بدون ضغط", "name_en": "None", "dpi": None, "jpg_quality": None},
    1: {"name_ar": "خفيف", "name_en": "Light", "dpi": 200, "jpg_quality": 85},
    2: {"name_ar": "متوسط", "name_en": "Medium", "dpi": 150, "jpg_quality": 70},
    3: {"name_ar": "قوي", "name_en": "Strong", "dpi": 96, "jpg_quality": 50},
}


@dataclass
class RenderedImage:
    """صورة مرسومة كبكسلات RGB خام (بدون ترميز PNG) تُحوَّل مباشرة إلى QImage
    في الواجهة، فنوفّر الضغط ثم فك الضغط لكل صفحة."""
    width: int
    height: int
    stride: int
    samples: bytes


@dataclass
class PdfDocInfo:
    """معلومات أساسية عن ملف PDF تم تحميله."""
    path: str
    page_count: int
    needs_password: bool = False


class ThumbnailCache:
    """
    كاش LRU للمصغّرات بمفتاح (المسار، رقم الصفحة، الدوران).
    يمنع إعادة توليد نفس الصورة أكثر من مرة. القيم بكسلات خام
    (RenderedImage) وليست QPixmap حتى تبقى هذه الوحدة بدون أي اعتماد
    على PyQt. الحد ٢٠٠ عنصر (~٢٠ ميجابايت) حتى لا يثقل الذاكرة.
    """

    def __init__(self, max_items: int = 200):
        self._store: "OrderedDict[Tuple[str, int, int], RenderedImage]" = OrderedDict()
        self.max_items = max_items

    def get(self, key: Tuple[str, int, int]) -> Optional["RenderedImage"]:
        img = self._store.get(key)
        if img is not None:
            self._store.move_to_end(key)
        return img

    def put(self, key: Tuple[str, int, int], img: "RenderedImage") -> None:
        self._store[key] = img
        self._store.move_to_end(key)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def invalidate_path(self, path: str) -> None:
        """يحذف كل المصغّرات المرتبطة بملف معيّن (مثلاً عند إزالته من القائمة)."""
        for k in [k for k in self._store if k[0] == path]:
            del self._store[k]

    def clear(self) -> None:
        self._store.clear()


class PdfEngine:
    """
    الواجهة الرئيسية للتعامل مع ملفات PDF.
    تحافظ على مستندات fitz مفتوحة طوال فترة الجلسة (بدل فتح/قفل متكرر)
    عبر open_documents، وتُغلق كل شي صراحة في close_all().

    PyMuPDF غير آمن للاستخدام من عدة خيوط في نفس الوقت، لذلك كل وصول
    للمستندات يمر عبر self.lock: خيط المعاينات وخيط الدمج والواجهة
    يتناوبون عليها بدل أن يلمسوها معًا (وهو ما قد يسبب انهيار البرنامج).
    """

    def __init__(self):
        self.open_documents: Dict[str, "fitz.Document"] = {}
        self.thumb_cache = ThumbnailCache()
        self.lock = threading.RLock()

    # ---------------- إدارة فتح/قفل الملفات ----------------
    @staticmethod
    def is_image_path(path: str) -> bool:
        """هل المسار يشير لصورة (بناءً على الامتداد)؟"""
        ext = os.path.splitext(path)[1].lower()
        return ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp")

    def _image_to_doc(self, path: str) -> "fitz.Document":
        """يحوّل ملف صورة إلى مستند PDF بصفحة واحدة بنفس أبعاد الصورة."""
        img_doc = fitz.open(path)
        rect = img_doc[0].rect  # أبعاد الصورة بالنقاط
        pdfbytes = img_doc.convert_to_pdf()
        img_doc.close()
        return fitz.open("pdf", pdfbytes)

    def _get_doc(self, path: str) -> "fitz.Document":
        """يرجع مستند fitz مفتوح مسبقًا، أو يفتحه لأول مرة ويحفظه للاستخدام لاحقًا.
        لو كان المسار صورة، يحوّلها تلقائيًا لمستند PDF بصفحة واحدة."""
        with self.lock:
            doc = self.open_documents.get(path)
            if doc is not None:
                return doc
            if self.is_image_path(path):
                doc = self._image_to_doc(path)
            else:
                doc = fitz.open(path)
            self.open_documents[path] = doc
            return doc

    def probe_file(self, path: str) -> PdfDocInfo:
        """
        يفحص الملف عند الإضافة مباشرة: يتأكد أنه PDF/صورة صالح، وهل محمي بكلمة سر.
        يرمي استثناء واضح لو الملف تالف أو غير قابل للفتح.
        """
        is_img = self.is_image_path(path)
        with self.lock:
            try:
                doc = self._get_doc(path)
            except Exception as e:
                kind = "صورة" if is_img else "PDF"
                raise ValueError(f"تعذر فتح الملف كـ {kind} صالح: {e}")

            if not is_img and doc.needs_pass:
                # نغلقه ونزيله من الكاش لأنه غير قابل للاستخدام بدون كلمة سر
                doc.close()
                self.open_documents.pop(path, None)
                raise ValueError("الملف محمي بكلمة سر — لا يمكن دمجه حاليًا")

            return PdfDocInfo(path=path, page_count=doc.page_count, needs_password=False)

    def page_count(self, path: str) -> int:
        """عدد صفحات ملف مفتوح (0 لو تعذّر فتحه)."""
        try:
            with self.lock:
                return self._get_doc(path).page_count
        except Exception:
            return 0

    def close_path(self, path: str) -> None:
        """يغلق ملف معين ويزيله من الكاش (يُستخدم عند حذف ملف من القائمة)."""
        with self.lock:
            doc = self.open_documents.pop(path, None)
            if doc is not None:
                try:
                    doc.close()
                except Exception as e:
                    logger.warning("Failed closing %s: %s", path, e)
            self.thumb_cache.invalidate_path(path)

    def close_all(self) -> None:
        with self.lock:
            for path, doc in list(self.open_documents.items()):
                try:
                    doc.close()
                except Exception as e:
                    logger.warning("Failed closing %s: %s", path, e)
            self.open_documents.clear()
            self.thumb_cache.clear()

    # ---------------- توليد المصغّرات ----------------
    def _render(self, page_ref: PageRef, scale: float) -> RenderedImage:
        with self.lock:
            doc = self._get_doc(page_ref.doc_path)
            page = doc.load_page(page_ref.page_num)
            matrix = fitz.Matrix(scale, scale).prerotate(page_ref.rot)
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
            return RenderedImage(width=pix.width, height=pix.height,
                                 stride=pix.stride, samples=pix.samples)

    def render_thumbnail(self, page_ref: PageRef, max_px: int = THUMB_MAX) -> RenderedImage:
        """
        يولّد مصغّرة لصفحة معيّنة مرسومة مباشرة بحيث لا يتجاوز أكبر بُعد فيها
        max_px، مستفيدًا من الكاش إن وُجدت نفس الصفحة بنفس الدوران من قبل.
        الملف يُفتح مرة واحدة فقط (عبر _get_doc) ويبقى مفتوحًا لباقي الجلسة.
        """
        key = (page_ref.doc_path, page_ref.page_num, page_ref.rot)
        with self.lock:
            cached = self.thumb_cache.get(key)
            if cached is not None:
                return cached
            rect = self._get_doc(page_ref.doc_path).load_page(page_ref.page_num).rect
            img = self._render(page_ref, max_px / max(rect.width, rect.height, 1))
            self.thumb_cache.put(key, img)
            return img

    def render_full_page(self, page_ref: PageRef, scale: float = 1.0) -> RenderedImage:
        """يولّد صورة الصفحة بالحجم الكامل لاستخدامها في المعاينة والمحرّر."""
        return self._render(page_ref, scale)

    def expand_file_to_pages(self, path: str, range_expr: str) -> List[PageRef]:
        """يحوّل ملف + تعبير نطاق إلى قائمة PageRef (دون توليد صور بعد)."""
        with self.lock:
            page_count = self._get_doc(path).page_count
        selected_indices = parse_range(range_expr, page_count)
        return [PageRef(doc_path=path, page_num=i, rot=0) for i in selected_indices]

    # ---------------- الدمج ----------------
    def merge(
        self,
        page_refs: List[PageRef],
        output_path: str,
        compression_level: int = 0,
        progress_cb=None,
        is_cancelled=None,
        stamps=None,
        stage_cb=None,
    ) -> "MergeResult":
        """
        يدمج قائمة صفحات في ملف PDF واحد ويحفظه.
        compression_level: 0=بدون، 1=خفيف، 2=متوسط، 3=قوي (انظر COMPRESSION_LEVELS).
        progress_cb(done, total) يُستدعى بعد كل صفحة لتحديث شريط التقدم.
        stage_cb(name) يُستدعى عند بداية كل مرحلة: "pages" ثم "stamps"
                (لو وُجدت) ثم "compress" (لو مطلوب) ثم "save"، حتى تعرض
                الواجهة ما يجري بدل شريط واقف أثناء الضغط والحفظ.
        is_cancelled() دالة تُستدعى دوريًا؛ لو رجعت True يتوقف الدمج فورًا.
        stamps: قائمة اختيارية بأختام/تواقيع/نصوص تُطبَّق على صفحات الناتج
                (كل عنصر StampSpec يحدد رقم صفحة الناتج والموضع والمحتوى).
        يرجع MergeResult يحتوي حجم الملف قبل وبعد الضغط حتى تعرض الواجهة
        نسبة التصغير الفعلية.
        """
        if not page_refs:
            raise ValueError("لا توجد صفحات للدمج")

        optimize = compression_level and compression_level > 0
        tmp_path = output_path + ".tmp"
        # نمسك القفل طوال الدمج: MuPDF يشارك حالة داخلية بين كل المستندات،
        # فلا نسمح لخيط المعاينات بالرسم في نفس الوقت.
        self.lock.acquire()
        merged_doc = fitz.open()
        total = len(page_refs)

        def stage(name):
            if stage_cb is not None:
                stage_cb(name)

        try:
            stage("pages")
            for idx, ref in enumerate(page_refs):
                if is_cancelled is not None and is_cancelled():
                    return MergeResult(output_path=output_path, cancelled=True)

                src = self._get_doc(ref.doc_path)
                merged_doc.insert_pdf(src, from_page=ref.page_num, to_page=ref.page_num)

                if ref.rot % 360 != 0:
                    last_page = merged_doc[-1]
                    last_page.set_rotation((last_page.rotation + ref.rot) % 360)

                if progress_cb is not None:
                    progress_cb(idx + 1, total)

            # تطبيق الأختام/التواقيع/النصوص على صفحات الناتج بعد تجميعها
            if stamps:
                stage("stamps")
                self._apply_stamps(merged_doc, stamps)

            size_before = None

            if optimize:
                # نقدّر حجم الملف "قبل" الضغط من جدول الكائنات بدل حفظه
                # فعليًا مرة إضافية (كان يضاعف الكتابة على القرص والوقت)
                size_before = self._estimate_saved_size(merged_doc)

                # تصغير الصور داخل المستند حسب مستوى الضغط المختار
                stage("compress")
                self._downsample_images(merged_doc, compression_level)

                stage("save")
                merged_doc.save(tmp_path, garbage=4, deflate=True, clean=True)
            else:
                stage("save")
                merged_doc.save(tmp_path)

            os.replace(tmp_path, output_path)

            size_after = os.path.getsize(output_path)
            if size_before is not None:
                size_before = max(size_before, size_after)
            return MergeResult(
                output_path=output_path,
                cancelled=False,
                size_before=size_before,
                size_after=size_after,
                optimized=bool(optimize),
                compression_level=compression_level,
            )
        finally:
            merged_doc.close()
            self.lock.release()
            # لو فشل الحفظ أو أُلغي في المنتصف لا نترك ملفات مؤقتة على القرص
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError as e:
                    logger.warning("Could not remove temp file %s: %s", tmp_path, e)

    @staticmethod
    def _estimate_saved_size(doc: "fitz.Document") -> int:
        """
        يقدّر حجم المستند لو حُفظ بدون ضغط، من جدول الكائنات مباشرة:
        نص قاموس كل كائن + طول بيانات الـ stream المسجّل في /Length
        + الهوامش الثابتة لكل كائن (obj/endobj، stream/endstream، سطر xref).
        لا يقرأ بيانات الصور نفسها، فهو سريع ولا يستهلك ذاكرة إضافية.
        """
        total = 170  # الترويسة والـ trailer وجدول xref
        for xref in range(1, doc.xref_length()):
            try:
                total += len(doc.xref_object(xref, compressed=True)) + 38
                if doc.xref_is_stream(xref):
                    kind, val = doc.xref_get_key(xref, "Length")
                    if kind == "xref":  # الطول مخزّن في كائن منفصل
                        val = doc.xref_object(int(val.split()[0])).strip()
                    if kind in ("int", "xref"):
                        total += int(val) + 20
                    else:
                        total += len(doc.xref_stream_raw(xref)) + 20
            except Exception:
                continue
        return total

    def _downsample_images(self, doc: "fitz.Document", level: int) -> None:
        """
        يصغّر الصور المضمّنة داخل المستند حسب مستوى الضغط، باستخدام
        الواجهة الرسمية rewrite_images التي تعيد ترميز الصور بأمان مع
        تحديث بيانات الفلتر/مساحة اللون بشكل صحيح.

        ملاحظة: الطريقة القديمة (update_stream بـ JPEG خام) كانت تُفسد
        الصور لأنها لا تحدّث /Filter في قاموس الصورة، فينتج عنها ملف
        فارغ وخطأ "insufficient data for an image". rewrite_images يتجنّب
        هذا تمامًا.
        """
        spec = COMPRESSION_LEVELS.get(level)
        if not spec or spec["jpg_quality"] is None:
            return
        quality = spec["jpg_quality"]
        target_dpi = spec["dpi"] or 150

        try:
            doc.rewrite_images(
                dpi_threshold=target_dpi + 24,  # نلمس فقط الصور الأعلى دقة
                dpi_target=target_dpi,
                quality=quality,
                lossy=True,
                lossless=True,
                color=True,
                gray=True,
                bitonal=False,  # نترك الصور ثنائية اللون (نص ممسوح) كما هي
            )
        except Exception as e:
            # غير قاتل: لو فشلت إعادة الترميز نكمل بالضغط العام فقط
            logger.warning("rewrite_images failed (non-fatal): %s", e)

    @staticmethod
    def _detect_background_color(page, rect):
        """
        يكتشف لون خلفية المنطقة المراد حذفها بأخذ عيّنات من البكسلات
        المحيطة بها مباشرة (خارج المستطيل بقليل). يرجع اللون كـ (r,g,b)
        بقيم 0..1. لو فشل الاكتشاف يرجع أبيض كحل احتياطي آمن.

        الفكرة: بدل ملء المنطقة بأبيض ثابت (الذي قد يترك مربعًا أبيض
        واضحًا فوق خلفية ملوّنة)، نملؤها بلون الخلفية المجاورة فيبدو
        وكأن النص/الصورة المحددة فقط اختفت بينما الخلفية باقية كما هي.
        """
        try:
            pad = 3  # بكسلات حول المنطقة لأخذ العيّنة منها
            samples = []
            # نرندر شريطًا رفيعًا فوق وتحت المنطقة لأخذ عيّنة الخلفية
            page_rect = page.rect
            for band in (
                fitz.Rect(rect.x0, max(page_rect.y0, rect.y0 - pad - 2),
                          rect.x1, max(page_rect.y0, rect.y0 - 1)),  # شريط فوق
                fitz.Rect(rect.x0, min(page_rect.y1, rect.y1 + 1),
                          rect.x1, min(page_rect.y1, rect.y1 + pad + 2)),  # شريط تحت
            ):
                if band.is_empty or band.width < 1 or band.height < 1:
                    continue
                pix = page.get_pixmap(clip=band, colorspace=fitz.csRGB, alpha=False)
                if pix.width == 0 or pix.height == 0:
                    continue
                # متوسط ألوان البكسلات في هذا الشريط
                data = pix.samples
                n = pix.width * pix.height
                if n == 0:
                    continue
                r = sum(data[i*3] for i in range(n)) / n
                g = sum(data[i*3+1] for i in range(n)) / n
                b = sum(data[i*3+2] for i in range(n)) / n
                samples.append((r, g, b))
            if samples:
                r = sum(s[0] for s in samples) / len(samples) / 255.0
                g = sum(s[1] for s in samples) / len(samples) / 255.0
                b = sum(s[2] for s in samples) / len(samples) / 255.0
                return (r, g, b)
        except Exception as e:
            logger.debug("Background detection failed, using white: %s", e)
        return (1, 1, 1)

    @staticmethod
    def _shape_arabic(text: str) -> str:
        """يعالج النص العربي (وصل الحروف + ترتيب RTL صحيح) ليُكتب سليمًا في PDF.
        يدعم النص المختلط (عربي + إنجليزي + أرقام). يعمل بأمان حتى لو لم
        يحتوِ النص أي عربية، ويتجاهل المعالجة بهدوء لو لم تتوفر المكتبات."""
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text

    @staticmethod
    def _stamp_rect(page, st) -> "fitz.Rect":
        """
        مستطيل العنصر بإحداثيات الصفحة غير المدوّرة. المحرّر يحفظ النسب
        (x, y, w, h) على الصفحة كما يراها المستخدم (بعد الدوران)، بينما
        PyMuPDF يرسم بإحداثيات الصفحة قبل الدوران؛ derotation_matrix تحوّل
        بينهما، فيقع العنصر في نفس المكان الذي وضعه المستخدم.
        """
        pw, ph = page.rect.width, page.rect.height
        visible = fitz.Rect(st.x * pw, st.y * ph, (st.x + st.w) * pw, (st.y + st.h) * ph)
        return (visible * page.derotation_matrix).normalize()

    def _apply_stamps(self, doc: "fitz.Document", stamps) -> None:
        """يطبّق العناصر (صور/نصوص/حذف مناطق) على صفحات المستند الناتج.
        ترتيب التطبيق: نطبّق الحذف (redaction) أولًا لكل صفحة، ثم باقي
        العناصر، حتى لا يُمسح ما أضافه المستخدم فوق منطقة محذوفة."""
        # نجمع الحذوفات حسب الصفحة لتطبيقها دفعة واحدة (أكفأ وأنظف)
        redactions = {}
        others = []
        for st in stamps:
            if st.page_index < 0 or st.page_index >= doc.page_count:
                continue
            if st.kind == "redact":
                redactions.setdefault(st.page_index, []).append(st)
            else:
                others.append(st)

        # 1) تطبيق الحذف (redaction): يمسح فعليًا النص/الصور داخل المنطقة،
        #    ويملأ المكان بلون الخلفية المحيط (بدل الأبيض الثابت) حتى يبدو
        #    وكأن العنصر المحدد فقط اختفى دون تشويه خلفية الصفحة.
        for page_idx, reds in redactions.items():
            page = doc[page_idx]
            for st in reds:
                rect = self._stamp_rect(page, st)
                fill = self._detect_background_color(page, rect)
                page.add_redact_annot(rect, fill=fill)
            try:
                # images=False: لا نمسح الصور كاملة لو لمستها المنطقة جزئيًا؛
                # graphics فقط داخل المنطقة. هذا يحافظ على بقية محتوى الصفحة.
                page.apply_redactions()
            except Exception as e:
                logger.warning("apply_redactions failed on page %s: %s", page_idx, e)

        # 2) تطبيق الصور والنصوص فوق الصفحة
        for st in others:
            page = doc[st.page_index]
            if st.kind == "image":
                try:
                    # keep_proportion=False: الصورة تملأ المستطيل كما يعرضها المحرّر
                    # تمامًا (المحرّر يسمح بتغيير العرض والارتفاع كلٌّ على حدة)
                    page.insert_image(self._stamp_rect(page, st), filename=st.content,
                                      overlay=True, rotate=page.rotation,
                                      keep_proportion=False)
                except Exception as e:
                    logger.warning("Failed inserting stamp image: %s", e)
            elif st.kind == "text":
                pw, ph = page.rect.width, page.rect.height
                # خط القاعدة على الصفحة كما يراها المستخدم، ثم نحوّله لإحداثيات
                # الصفحة غير المدوّرة ونكتب النص مدوّرًا معها حتى يظهر مستقيمًا
                point = fitz.Point(st.x * pw, st.y * ph + st.font_size) * page.derotation_matrix
                fontfile = st.font_file or None
                # نعالج النص للعربية (وصل + ترتيب RTL) فقط عند استخدام خط
                # يدعم العربي؛ الخطوط القياسية لا تعرض العربي أصلًا
                content = self._shape_arabic(st.content) if fontfile else st.content
                common = dict(fontsize=st.font_size, color=st.color,
                              rotate=page.rotation, overlay=True)
                if fontfile:
                    font_args = dict(fontfile=fontfile, fontname="customfont")
                else:
                    font_args = dict(fontname=st.font_name or "helv")
                try:
                    page.insert_text(point, content, **common, **font_args)
                except Exception as e:
                    logger.warning("Font failed (%s), falling back to helv", e)
                    try:
                        page.insert_text(point, content, **common)
                    except Exception as e2:
                        logger.warning("Failed inserting stamp text: %s", e2)



@dataclass
class MergeResult:
    """نتيجة عملية الدمج: المسار، هل أُلغيت، وأحجام الملف قبل/بعد الضغط إن وُجدت."""
    output_path: str
    cancelled: bool = False
    size_before: Optional[int] = None
    size_after: Optional[int] = None
    optimized: bool = False
    compression_level: int = 0


@dataclass
class StampSpec:
    """
    مواصفة عنصر يُطبَّق على صفحة في الناتج.
    kind يكون أحد: "image" (صورة/ختم/توقيع)، "text" (نص)، "redact" (حذف منطقة).
    الإحداثيات x,y,w,h كنسب مئوية (0..1) من أبعاد الصفحة حتى تبقى صحيحة
    مهما كان حجم الصفحة الفعلي.
    """
    page_index: int          # رقم الصفحة في الناتج (0-based)
    kind: str                # "image" أو "text" أو "redact"
    content: str = ""        # مسار الصورة، أو النص المكتوب (فارغ للحذف)
    x: float = 0.1
    y: float = 0.1
    w: float = 0.2           # للصور والحذف
    h: float = 0.1           # للصور والحذف
    font_size: float = 14.0  # للنص فقط
    color: tuple = (0.0, 0.0, 0.0)  # لون النص (RGB 0..1)
    font_name: str = "helv"  # اسم خط PDF القياسي للنص
    font_file: str = ""      # مسار ملف خط مخصص (للخطوط العربية المرفقة)
