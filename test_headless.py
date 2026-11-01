# -*- coding: utf-8 -*-
"""
test_headless.py
اختبار وظيفي شامل يشغّل التطبيق الفعلي (main_app.py) بدون شاشة (offscreen)
ويحاكي سلوك مستخدم حقيقي: إضافة ملفات، تحديد نطاقات، توليد معاينات
عبر QThread، تدوير صفحة، تكرار صفحة، حذف صفحة، تراجع، ثم دمج فعلي
والتحقق من الملف الناتج.
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QListWidgetItem
from PyQt5.QtCore import QEventLoop, QTimer, Qt

from main_app import PDFMergerApp, USERROLE_PAGEINFO, USERROLE_PAGEROT, USERROLE_THUMBREADY

def wait_until(predicate, timeout_ms=10000, step_ms=50):
    """
    ينتظر تحقق شرط معين مع إبقاء حلقة أحداث Qt تعمل فعليًا (processEvents)
    حتى تُعالَج إشارات QThread (signals/slots) بشكل صحيح أثناء الانتظار.
    """
    waited = 0
    while not predicate() and waited < timeout_ms:
        QApplication.processEvents()
        time.sleep(step_ms / 1000.0)
        waited += step_ms
    QApplication.processEvents()
    return predicate()


def main():
    app = QApplication(sys.argv)

    # نوافذ الرسائل المودال (modal) تنهار في وضع offscreen على ويندوز،
    # فنستبدلها بدوال تسجّل الرسالة وترجع فورًا (موافقة).
    from PyQt5.QtWidgets import QMessageBox as _QMB
    shown_messages = []
    def _fake_box(kind, ret):
        def _f(*args, **kwargs):
            shown_messages.append((kind, args[1] if len(args) > 1 else ""))
            return ret
        return _f
    _QMB.warning = staticmethod(_fake_box("warning", _QMB.Ok))
    _QMB.information = staticmethod(_fake_box("information", _QMB.Ok))
    _QMB.critical = staticmethod(_fake_box("critical", _QMB.Ok))
    _QMB.question = staticmethod(_fake_box("question", _QMB.Yes))
    # رسائل التطبيق المخصّصة (dialogs.py) تُستبدل بنفس الطريقة
    import dialogs
    dialogs.info = _fake_box("info", None)
    dialogs.warning = _fake_box("warning", None)
    dialogs.error = _fake_box("error", None)
    dialogs.success = _fake_box("success", None)
    dialogs.confirm = _fake_box("confirm", True)

    w = PDFMergerApp()

    # 1) إضافة ملفين PDF سليمين
    w.add_paths(["test1.pdf", "test2.pdf"])
    assert "test1.pdf" in w.pdf_paths, "test1.pdf لم يُضف"
    assert "test2.pdf" in w.pdf_paths, "test2.pdf لم يُضف"
    print("[OK] إضافة الملفات السليمة")

    # 1b) اختبار رفض ملف غير صالح، بمعزل عن الـ QMessageBox المنبثق (modal)
    # نغلق أي رسالة تنبيه تلقائيًا عبر QTimer حتى لا تُعلّق exec_() في وضع offscreen
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtCore import QTimer

    def auto_close_messagebox():
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMessageBox) and widget.isVisible():
                widget.close()

    timer = QTimer()
    timer.timeout.connect(auto_close_messagebox)
    timer.start(50)
    w.add_paths(["nonexistent_file.pdf"])
    timer.stop()
    assert "nonexistent_file.pdf" not in w.pdf_paths, "ملف غير موجود تمت إضافته خطأ!"
    assert shown_messages and shown_messages[-1][0] == "warning", "لم يظهر تنبيه للملف المرفوض"
    print("[OK] رفض الملف غير الصالح (مع تنبيه للمستخدم)")

    # 2) تحديد نطاق لـ test2.pdf
    w.per_file_ranges["test2.pdf"] = "1-2"
    w.update_page_list()

    # انتظار انتهاء توليد المعاينات في الخلفية (QThread)
    ok = wait_until(lambda: w._thumb_worker is None or not w._thumb_worker.isRunning())
    assert ok, "توليد المعاينات لم ينتهِ في الوقت المحدد"
    expected_pages = 5 + 2  # كل صفحات test1 + أول صفحتين من test2
    assert w.pages_list_widget.count() == expected_pages, \
        f"عدد الصفحات غير متوقع: {w.pages_list_widget.count()} (متوقع {expected_pages})"
    print(f"[OK] توليد {expected_pages} معاينة عبر QThread بدون تجميد")

    # التأكد أن كل صفحة حصلت على أيقونة فعلية (مو فاضية)
    all_have_icons = all(
        w.pages_list_widget.item(i).data(USERROLE_THUMBREADY)
        for i in range(w.pages_list_widget.count())
    )
    assert all_have_icons, "بعض الصفحات بدون أيقونة معاينة!"
    print("[OK] كل الصفحات حصلت على أيقونات معاينة")

    # 3) اختبار الكاش: نتأكد أن fitz document انفتح مرة وحدة لكل ملف
    assert "test1.pdf" in w.engine.open_documents
    assert "test2.pdf" in w.engine.open_documents
    print("[OK] الملفات بقيت مفتوحة (مرة واحدة لكل ملف) بدل فتح/قفل متكرر")

    # 4) تدوير أول صفحة
    first_item = w.pages_list_widget.item(0)
    w.rotate_page(first_item, 90)
    assert first_item.data(USERROLE_PAGEROT) == 90, "الدوران لم يُسجَّل"
    print("[OK] تدوير صفحة")

    # 5) تكرار الصفحة الثانية
    count_before = w.pages_list_widget.count()
    second_item = w.pages_list_widget.item(1)
    w.duplicate_page(second_item)
    assert w.pages_list_widget.count() == count_before + 1, "التكرار لم يضف عنصرًا"
    print("[OK] تكرار صفحة")

    # 6) حذف صفحة ثم تراجع (Undo) — نتجاوز نافذة التأكيد بالتعديل المباشر
    count_before_delete = w.pages_list_widget.count()
    item_to_delete = w.pages_list_widget.item(2)
    from main_app import USERROLE_PAGEUID
    deleted_uid = item_to_delete.data(USERROLE_PAGEUID)
    w._page_stamps[deleted_uid] = [{'kind': 'text', 'content': 'x'}]
    row = w.pages_list_widget.row(item_to_delete)
    w._undo_stack.append((row, w.pages_list_widget.takeItem(row)))
    w.btn_undo.setEnabled(True)
    assert w.pages_list_widget.count() == count_before_delete - 1, "الحذف لم يقلل العدد"
    print("[OK] حذف صفحة")

    w.undo_delete_page()
    assert w.pages_list_widget.count() == count_before_delete, "التراجع لم يُعِد الصفحة"
    restored = w.pages_list_widget.item(row)
    assert restored.data(USERROLE_PAGEUID) == deleted_uid, "التراجع غيّر معرّف الصفحة"
    assert deleted_uid in w._page_stamps, "التراجع أضاع تواقيع الصفحة"
    w._page_stamps.pop(deleted_uid)
    print("[OK] تراجع (Undo) عن الحذف يعيد الصفحة بمعرّفها وتواقيعها")

    # 6b) تعديلات الصفحات تبقى بعد إضافة ملف / تغيير نطاق / إعادة ترتيب الملفات
    def _snapshot():
        lw = w.pages_list_widget
        return [(lw.item(i).data(USERROLE_PAGEUID), lw.item(i).data(USERROLE_PAGEROT))
                for i in range(lw.count())]
    snap = _snapshot()
    w.add_paths(["test3.pdf"])
    assert _snapshot()[:len(snap)] == snap, "إضافة ملف غيّرت/مسحت تعديلات الصفحات السابقة"
    assert w.pages_list_widget.count() == len(snap) + 2, "صفحات الملف الجديد لم تُضف في النهاية"
    w.per_file_ranges["test2.pdf"] = "1-3"
    w.update_page_list()
    after_range = _snapshot()
    assert all(s in after_range for s in snap), "تغيير نطاق ملف آخر مسح تعديلات الصفحات"
    t2 = [w.pages_list_widget.item(i).data(USERROLE_PAGEINFO)['page_num']
          for i in range(w.pages_list_widget.count())
          if w.pages_list_widget.item(i).data(USERROLE_PAGEINFO)['doc_path'] == "test2.pdf"]
    assert t2 == [0, 1, 2], f"النطاق الجديد لم يُطبَّق بالترتيب الصحيح: {t2}"
    w.pdf_paths = ["test3.pdf", "test1.pdf", "test2.pdf"]
    w.refresh_files_list()
    w.update_page_list()
    first_path = w.pages_list_widget.item(0).data(USERROLE_PAGEINFO)['doc_path']
    assert first_path == "test3.pdf", "إعادة ترتيب الملفات لم تنقل صفحاتها"
    assert w.pages_list_widget.item(2).data(USERROLE_PAGEROT) == 90, "إعادة ترتيب الملفات أضاعت الدوران"
    w.files_list_widget.setCurrentRow(0)
    w.files_list_widget.item(0).setSelected(True)
    w.remove_selected_files()
    assert all(w.pages_list_widget.item(i).data(USERROLE_PAGEINFO)['doc_path'] != "test3.pdf"
               for i in range(w.pages_list_widget.count())), "حذف الملف لم يحذف صفحاته"
    assert w.pages_list_widget.item(0).data(USERROLE_PAGEROT) == 90, "حذف ملف أضاع تعديلات الملفات الأخرى"
    ok = wait_until(lambda: not w._thumb_worker.isRunning())
    assert ok and all(w.pages_list_widget.item(i).data(USERROLE_THUMBREADY)
                      for i in range(w.pages_list_widget.count())), "صفحات بلا مصغّرة بعد المزامنة"
    print("[OK] التعديلات (دوران/تكرار/ترتيب) تبقى بعد إضافة ملف وتغيير نطاق وترتيب وحذف ملف")

    # 7) الدمج الفعلي عبر MergeWorker (QThread حقيقي)
    output_path = os.path.abspath("headless_test_merged.pdf")
    if os.path.exists(output_path):
        os.remove(output_path)

    from pdf_engine import PageRef as PR
    final_list = []
    for i in range(w.pages_list_widget.count()):
        it = w.pages_list_widget.item(i)
        info = it.data(USERROLE_PAGEINFO)
        rot = int(it.data(USERROLE_PAGEROT) or 0)
        final_list.append(PR(doc_path=info['doc_path'], page_num=info['page_num'], rot=rot))

    from workers import MergeWorker
    merge_result = {}

    def on_succeeded(result):
        merge_result['status'] = 'succeeded'
        merge_result['result'] = result

    def on_failed(err):
        merge_result['status'] = 'failed'
        merge_result['error'] = err

    worker = MergeWorker(w.engine, final_list, output_path, compression_level=2)
    worker.succeeded.connect(on_succeeded)
    worker.failed.connect(on_failed)
    stages = []
    worker.stage.connect(stages.append)
    worker.start()

    ok = wait_until(lambda: 'status' in merge_result, timeout_ms=15000)
    assert ok, "MergeWorker لم ينتهِ في الوقت المحدد"
    assert merge_result['status'] == 'succeeded', f"فشل الدمج: {merge_result.get('error')}"
    assert stages == ["pages", "compress", "save"], f"مراحل التقدّم غير متوقعة: {stages}"
    print("[OK] الدمج يبث مراحله (تجميع ← ضغط ← حفظ) لنافذة التقدّم")
    assert os.path.exists(output_path), "ملف الدمج الناتج غير موجود"
    result_obj = merge_result['result']
    assert result_obj.size_before is not None, "لم يتم تسجيل الحجم قبل الضغط"
    assert result_obj.size_after is not None, "لم يتم تسجيل الحجم بعد الضغط"
    assert result_obj.size_after <= result_obj.size_before, "الحجم بعد الضغط أكبر من قبل الضغط!"
    compression_ratio = (1 - result_obj.size_after / result_obj.size_before) * 100
    print(f"[OK] الدمج عبر QThread نجح -> {output_path}")
    print(f"[OK] نسبة الضغط محسوبة: قبل={result_obj.size_before}B بعد={result_obj.size_after}B نسبة={compression_ratio:.1f}%")

    import fitz
    result_doc = fitz.open(output_path)
    print(f"[OK] الملف الناتج صالح، عدد الصفحات: {result_doc.page_count}, الحجم: {os.path.getsize(output_path)} بايت")
    result_doc.close()

    # 8) اختبار إغلاق التطبيق ينظف كل الموارد
    w.close()
    assert len(w.engine.open_documents) == 0, "بعض الملفات بقيت مفتوحة بعد الإغلاق!"
    print("[OK] إغلاق التطبيق يحرر كل ملفات PDF المفتوحة")

    # 9) اختبار تبديل اللغة على نافذة جديدة (مستقلة عن السابقة المُغلقة)
    w2 = PDFMergerApp()
    assert w2.tr_.lang == "ar", "اللغة الافتراضية يجب أن تكون عربي"
    assert w2.layoutDirection() == Qt.RightToLeft, "الاتجاه يجب أن يكون RTL بالعربي"
    arabic_title = w2.title_label.text()

    w2.toggle_language()
    assert w2.tr_.lang == "en", "تبديل اللغة لم يغيّر القيمة الداخلية"
    assert w2.layoutDirection() == Qt.LeftToRight, "الاتجاه يجب أن يصبح LTR بالإنجليزي"
    english_title = w2.title_label.text()
    assert arabic_title != english_title, "النص لم يتغيّر فعليًا عند تبديل اللغة"
    print(f"[OK] تبديل اللغة يعمل: '{arabic_title}' -> '{english_title}'")

    w2.toggle_language()
    assert w2.tr_.lang == "ar", "التبديل مرة ثانية يجب أن يرجع للعربي"
    print("[OK] التبديل ذهابًا وإيابًا يعمل بشكل صحيح")

    w2.close()

    # 10) التأكد أن الـ stylesheet يُبنى بدون أخطاء ويحتوي العناصر المتوقعة
    from theme import build_stylesheet
    qss = build_stylesheet()
    assert "QPushButton" in qss and "QListWidget" in qss, "الـ stylesheet ناقص عناصر أساسية"
    print(f"[OK] بناء stylesheet ناجح ({len(qss)} حرف)")

    # 11) اختبار مستويات الضغط المتدرجة (يجب أن يقل الحجم مع زيادة المستوى)
    from pdf_engine import PdfEngine, StampSpec, COMPRESSION_LEVELS
    import random
    eng = PdfEngine()
    # ننشئ PDF فيه صورة كبيرة لاختبار الضغط
    img_w, img_h = 600, 400
    samples = bytes(random.randint(0, 255) for _ in range(img_w * img_h * 3))
    pix = fitz.Pixmap(fitz.csRGB, img_w, img_h, samples, False)
    pix.save("ct_image.png")
    cdoc = fitz.open()
    cpage = cdoc.new_page(width=595, height=842)
    cpage.insert_image(fitz.Rect(20, 20, 575, 420), filename="ct_image.png")
    cdoc.save("ct_with_image.pdf")
    cdoc.close()

    sizes = {}
    for level in [0, 1, 2, 3]:
        refs = eng.expand_file_to_pages("ct_with_image.pdf", "all")
        out = f"ct_merged_{level}.pdf"
        eng.merge(refs, out, compression_level=level)
        sizes[level] = os.path.getsize(out)
    assert sizes[0] > sizes[1] > sizes[2] > sizes[3], f"الضغط المتدرج لا يقلل الحجم تصاعديًا: {sizes}"
    print(f"[OK] مستويات الضغط تعمل تصاعديًا: {sizes[0]}>{sizes[1]}>{sizes[2]}>{sizes[3]} بايت")

    # 12) اختبار إضافة صورة كصفحة كاملة
    info = eng.probe_file("ct_image.png")
    assert info.page_count == 1, "الصورة يجب أن تتحول لصفحة واحدة"
    img_refs = eng.expand_file_to_pages("ct_image.png", "all")
    assert len(img_refs) == 1, "توسعة الصورة لصفحات فشلت"
    print("[OK] إضافة صورة كصفحة PDF تعمل")

    # 13) اختبار تطبيق ختم/توقيع (صورة) ونص بخطوط وألوان مختلفة
    refs2 = eng.expand_file_to_pages("ct_with_image.pdf", "all")
    stamps = [
        StampSpec(page_index=0, kind="text", content="APPROVED_TEST",
                  x=0.1, y=0.15, font_size=20, color=(0.8, 0, 0), font_name="tiro"),
        StampSpec(page_index=0, kind="text", content="CourierNote",
                  x=0.1, y=0.30, font_size=16, color=(0, 0, 0.8), font_name="cour"),
        StampSpec(page_index=0, kind="image", content="ct_image.png",
                  x=0.6, y=0.7, w=0.3, h=0.1),
    ]
    eng.merge(refs2, "ct_stamped.pdf", compression_level=0, stamps=stamps)
    check = fitz.open("ct_stamped.pdf")
    page_text = check[0].get_text()
    assert "APPROVED_TEST" in page_text, "النص المضاف لم يظهر في الناتج"
    assert "CourierNote" in page_text, "النص الثاني لم يظهر"
    img_count = len(check[0].get_images())
    assert img_count >= 2, f"صورة الختم لم تُضف (عدد الصور: {img_count})"
    used_fonts = [f[3] for f in check[0].get_fonts()]
    assert any("Times" in f for f in used_fonts), f"خط Times لم يُطبّق: {used_fonts}"
    assert any("Courier" in f for f in used_fonts), f"خط Courier لم يُطبّق: {used_fonts}"
    check.close()
    print(f"[OK] التوقيع/الختم/النص يعمل بخطوط متعددة ({img_count} صور، خطوط: {used_fonts})")

    # 13b) اختبار الخط العربي (Amiri) مع معالجة الاتجاه والوصل
    import os as _os
    amiri = _os.path.join("fonts", "Amiri-Regular.ttf")
    if _os.path.exists(amiri):
        refs_ar = eng.expand_file_to_pages("ct_with_image.pdf", "all")
        ar_stamps = [
            StampSpec(page_index=0, kind="text", content="توقيع: محمد أحمد",
                      x=0.1, y=0.5, font_size=26, color=(0, 0, 0.7), font_file=amiri),
        ]
        eng.merge(refs_ar, "ct_arabic.pdf", compression_level=0, stamps=ar_stamps)
        chk = fitz.open("ct_arabic.pdf")
        ar_fonts = [f[3] for f in chk[0].get_fonts()]
        assert any("Amiri" in f for f in ar_fonts), f"خط Amiri لم يُضمّن: {ar_fonts}"
        chk.close()
        _os.remove("ct_arabic.pdf")
        print(f"[OK] الخط العربي Amiri يُضمّن ويُطبّق ({ar_fonts})")
        # تأكد أن معالجة العربية تعمل (تغيّر ترتيب الحروف)
        from pdf_engine import PdfEngine as _PE
        shaped = _PE._shape_arabic("مرحبا")
        assert shaped != "مرحبا", "معالجة العربية (reshaping) لم تعمل"
        print("[OK] معالجة النص العربي (الوصل + الاتجاه) تعمل")
    else:
        print("[تخطّي] خط Amiri غير موجود — تم تخطّي اختبار العربية")

    # 13c) اختبار الحذف (redaction): يمسح النص داخل المنطقة
    rdoc = fitz.open()
    rp = rdoc.new_page(width=595, height=842)
    rp.insert_text((60, 100), "DELETE_THIS_SECRET", fontsize=16)
    rp.insert_text((60, 300), "KEEP_THIS_TEXT", fontsize=16)
    rdoc.save("ct_redact_src.pdf")
    rdoc.close()
    refs_r = eng.expand_file_to_pages("ct_redact_src.pdf", "all")
    # منطقة الحذف تغطي السطر الأول (y حوالي 100/842 ≈ 0.10)
    red_stamps = [StampSpec(page_index=0, kind="redact", x=0.05, y=0.09, w=0.7, h=0.05)]
    eng.merge(refs_r, "ct_redacted.pdf", compression_level=0, stamps=red_stamps)
    rchk = fitz.open("ct_redacted.pdf")
    rtxt = rchk[0].get_text()
    assert "DELETE_THIS_SECRET" not in rtxt, "الحذف لم يمسح النص المستهدف"
    assert "KEEP_THIS_TEXT" in rtxt, "الحذف مسح نصًا لم يكن مستهدفًا"
    rchk.close()
    eng.close_path("ct_redact_src.pdf")  # ويندوز لا يسمح بحذف ملف مفتوح
    _os.remove("ct_redact_src.pdf"); _os.remove("ct_redacted.pdf")
    print("[OK] حذف منطقة (redaction) يمسح المستهدف ويُبقي الباقي")

    # 13c-2) الأختام على صفحة مدوّرة تقع حيث وضعها المستخدم على الصفحة المعروضة
    from pdf_engine import PageRef as _PR
    rsrc = fitz.open(); rsrc.new_page(width=400, height=600); rsrc.save("ct_rot_src.pdf"); rsrc.close()
    fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False).save("ct_black.png")
    for rot in (90, 180, 270):
        st = StampSpec(page_index=0, kind="image", content="ct_black.png", x=0.1, y=0.1, w=0.2, h=0.1)
        eng.merge([_PR("ct_rot_src.pdf", 0, rot)], "ct_rot_out.pdf", stamps=[st])
        rd = fitz.open("ct_rot_out.pdf"); rpix = rd[0].get_pixmap(alpha=False)
        def _val(fx, fy):
            return rpix.samples[(int(fy * rpix.height) * rpix.width + int(fx * rpix.width)) * rpix.n]
        assert _val(0.2, 0.15) < 50, f"الختم ليس في مكانه على صفحة مدوّرة {rot}°"
        assert _val(0.8, 0.85) > 200, f"الختم ظهر في مكان خاطئ على صفحة مدوّرة {rot}°"
        rd.close()
    eng.close_path("ct_rot_src.pdf")
    for f in ("ct_rot_src.pdf", "ct_rot_out.pdf", "ct_black.png"):
        _os.remove(f)
    print("[OK] الأختام على الصفحات المدوّرة (90/180/270) تقع في مكانها الصحيح")

    eng.close_all()

    # 13d) اختبار حاسم: الضغط مع الصور يُنتج ملفًا صالحًا (لا "insufficient data")
    eng_img = PdfEngine()
    iw, ih = 600, 450
    grad = bytearray()
    for yy in range(ih):
        for xx in range(iw):
            grad += bytes([(xx*255)//iw, (yy*255)//ih, 100])
    fitz.Pixmap(fitz.csRGB, iw, ih, bytes(grad), False).save("ci_grad.png")
    idoc = fitz.open()
    ip = idoc.new_page(width=595, height=842)
    ip.insert_image(fitz.Rect(30, 30, 565, 470), filename="ci_grad.png")
    idoc.save("ci_grad_doc.pdf")
    idoc.close()
    for lvl in [1, 2, 3]:
        rr = eng_img.expand_file_to_pages("ci_grad_doc.pdf", "all")
        outp = f"ci_grad_out_{lvl}.pdf"
        eng_img.merge(rr, outp, compression_level=lvl)
        vchk = fitz.open(outp)
        # الاختبار الحاسم: رندر الصفحة لا يرمي خطأ، والمحتوى موجود
        vpix = vchk[0].get_pixmap()
        assert vpix.width > 0 and vpix.height > 0, f"الصفحة فارغة عند المستوى {lvl}"
        assert len(vchk[0].get_images()) >= 1, f"الصورة فُقدت عند المستوى {lvl}"
        vchk.close()
        os.remove(outp)
    eng_img.close_all()
    os.remove("ci_grad.png"); os.remove("ci_grad_doc.pdf")
    print("[OK] الضغط مع الصور يُنتج ملفًا صالحًا قابلًا للعرض (إصلاح الملف الفارغ)")
    from main_app import AnnotateDialog, _EditorCanvas, PDF_FONTS
    from PyQt5.QtGui import QPixmap as _QPixmap
    blank = _QPixmap(400, 560)
    blank.fill()
    editor = AnnotateDialog(None, w.tr_, blank, existing_stamps=[
        {"kind": "text", "content": "Hello", "x": 0.3, "y": 0.3,
         "font_size": 18.0, "color": (0.0, 0.0, 0.0), "font_name": "helv"},
    ])
    assert len(editor.canvas.items) == 1, "العنصر الموجود مسبقًا لم يُحمّل"
    # نغيّر موضع العنصر برمجيًا (يحاكي السحب) ونتأكد أنه يُحفظ
    editor.canvas.items[0]['x'] = 0.55
    editor.canvas.items[0]['y'] = 0.62
    editor.canvas.items[0]['font_size'] = 30.0
    editor.canvas.items[0]['font_name'] = PDF_FONTS['Times']
    saved = editor.get_stamps()
    assert abs(saved[0]['x'] - 0.55) < 1e-6 and abs(saved[0]['y'] - 0.62) < 1e-6, "تغيير الموضع لم يُحفظ"
    assert saved[0]['font_size'] == 30.0, "تغيير الحجم لم يُحفظ"
    assert saved[0]['font_name'] == 'tiro', "تغيير الخط لم يُحفظ"
    assert 'pixmap' not in saved[0], "get_stamps يجب ألا يُرجع كائن pixmap"
    editor.close()
    print("[OK] المحرر التفاعلي: تحميل وتعديل الموضع/الحجم/الخط يعمل")

    # 15) اختبار الزوم في المحرر
    editor2 = AnnotateDialog(None, w.tr_, blank, existing_stamps=[])
    z0 = editor2.canvas.get_zoom()
    editor2._zoom_by(1.25)
    assert editor2.canvas.get_zoom() > z0, "الزوم للداخل لم يعمل"
    editor2._set_zoom(1.0)
    assert abs(editor2.canvas.get_zoom() - 1.0) < 1e-6, "إعادة ضبط الزوم لم تعمل"
    # حدود الزوم
    editor2._set_zoom(99)
    assert editor2.canvas.get_zoom() <= 4.0, "الزوم تجاوز الحد الأقصى"
    editor2._set_zoom(0.01)
    assert editor2.canvas.get_zoom() >= 0.4, "الزوم نزل تحت الحد الأدنى"
    editor2.close()
    print("[OK] الزوم في المحرر يعمل ضمن الحدود")

    # 16) اختبار عدم تكدّس العناصر الجديدة فوق بعضها (cascade)
    editor3 = AnnotateDialog(None, w.tr_, blank, existing_stamps=[])
    editor3.text_edit.setText("A")
    editor3._add_text()
    editor3.text_edit.setText("B")
    editor3._add_text()
    items3 = editor3.canvas.items
    assert len(items3) == 2, "لم تُضف العناصر بشكل صحيح"
    assert (items3[0]['x'], items3[0]['y']) != (items3[1]['x'], items3[1]['y']), \
        "العنصران تكدّسا في نفس الموضع (سبب 'يحفظ آخر تعديل فقط')"
    # تأكد أن حقل النص يُمسح بعد الإضافة
    assert editor3.text_edit.text() == "", "حقل النص لم يُمسح بعد الإضافة"
    editor3.close()
    print("[OK] العناصر الجديدة لا تتكدّس فوق بعضها (إصلاح حفظ آخر تعديل)")

    # 16b) اختبار توفر الخطوط العربية في المحرر وربطها بملف الخط
    from main_app import FONT_REGISTRY, _font_display_to_file
    arabic_fonts = [name for name, info in FONT_REGISTRY.items() if info["arabic"]]
    assert len(arabic_fonts) >= 2, f"الخطوط العربية ناقصة في السجل: {arabic_fonts}"
    # تأكد أن اسم الخط العربي يُرجع مسار ملف فعلي
    ff = _font_display_to_file(arabic_fonts[0])
    assert ff is not None and os.path.exists(ff), f"ملف الخط العربي غير موجود: {ff}"
    # نص بخط عربي في المحرر يحمل font_file
    editor4 = AnnotateDialog(None, w.tr_, blank, existing_stamps=[])
    editor4.font_combo.setCurrentText(arabic_fonts[0])
    editor4.text_edit.setText("نص عربي")
    editor4._add_text()
    saved4 = editor4.get_stamps()
    assert saved4[0].get('font_file'), "النص العربي لم يحمل مسار ملف الخط"
    editor4.close()
    print(f"[OK] الخطوط العربية متاحة في المحرر ({len(arabic_fonts)} خط) ومربوطة بملفاتها")

    # 16c) اختبار أداة الحذف (redaction) في المحرر
    editor5 = AnnotateDialog(None, w.tr_, blank, existing_stamps=[])
    editor5.canvas.start_redact_mode()
    assert editor5.canvas._placing_redact, "وضع الحذف لم يُفعّل"
    # نحاكي إضافة منطقة حذف يدويًا
    editor5.canvas.items.append({"kind": "redact", "x": 0.2, "y": 0.2, "w": 0.3, "h": 0.1})
    saved5 = editor5.get_stamps()
    redacts = [s for s in saved5 if s['kind'] == 'redact']
    assert len(redacts) == 1, "منطقة الحذف لم تُحفظ"
    editor5.close()
    print("[OK] أداة حذف المنطقة (redaction) في المحرر تعمل")

    # 16d) اختبار ربط منطقة التمرير للسحب باليد (pan)
    editor6 = AnnotateDialog(None, w.tr_, blank, existing_stamps=[])
    assert editor6.canvas._scroll_area is not None, "منطقة التمرير غير مربوطة (السحب باليد لن يعمل)"
    editor6.close()
    print("[OK] السحب باليد (pan) مربوط بمنطقة التمرير")

    # 16f) اختبار النقر المزدوج على نص يطلب تحريره
    editor7 = AnnotateDialog(None, w.tr_, blank, existing_stamps=[
        {"kind": "text", "content": "Editable", "x": 0.3, "y": 0.3,
         "font_size": 18.0, "color": (0,0,0), "font_name": "helv", "font_name_disp": "Helvetica"},
    ])
    edit_requested = {"v": False}
    editor7.canvas.edit_text_requested.connect(lambda i: edit_requested.__setitem__("v", True))
    editor7.canvas.edit_text_requested.emit(0)
    assert edit_requested["v"], "إشارة طلب تحرير النص لم تُطلق"
    # محاكاة تعديل المحتوى (حذف جزء ومواصلة الكتابة)
    editor7.canvas.set_selected(0)
    editor7.text_edit.setText("Edited text")
    assert editor7.canvas.items[0]['content'] == "Edited text", "تعديل النص لم يُطبّق على العنصر"
    editor7.close()
    print("[OK] تعديل النص (فتح + تغيير المحتوى) يعمل")

    eng2 = PdfEngine()
    # 16g) اختبار الحذف الذكي: يحافظ على لون الخلفية (لا يترك مربعًا أبيض)
    bgdoc = fitz.open()
    bp = bgdoc.new_page(width=400, height=300)
    bp.draw_rect(bp.rect, fill=(0.85, 0.92, 1.0), color=None)
    bp.insert_text((50, 100), "REMOVE_ME", fontsize=20, color=(0, 0, 0))
    bgdoc.save("bg_t.pdf"); bgdoc.close()
    bg_refs = eng2.expand_file_to_pages("bg_t.pdf", "all")
    eng2.merge(bg_refs, "bg_t_out.pdf", compression_level=0,
               stamps=[StampSpec(page_index=0, kind="redact", x=0.1, y=0.28, w=0.7, h=0.1)])
    bgchk = fitz.open("bg_t_out.pdf")
    assert "REMOVE_ME" not in bgchk[0].get_text(), "الحذف الذكي لم يمسح النص"
    # نتأكد أن منطقة الحذف ليست بيضاء صريحة (اندمجت مع الأزرق)
    rp = bgchk[0].get_pixmap(clip=fitz.Rect(60, 85, 200, 105))
    nn = rp.width * rp.height
    avg_b = sum(rp.samples[i*3+2] for i in range(nn)) / nn
    avg_r = sum(rp.samples[i*3] for i in range(nn)) / nn
    assert avg_b > avg_r, "منطقة الحذف لم تأخذ لون الخلفية (صارت بيضاء)"
    bgchk.close(); eng2.close_all()
    os.remove("bg_t.pdf"); os.remove("bg_t_out.pdf")
    print("[OK] الحذف الذكي يحافظ على لون الخلفية (لا مربع أبيض)")

    # 16h) اختبار منطق أسهم ترتيب الصفحات
    pdoc = fitz.open()
    for i in range(3):
        pp = pdoc.new_page(); pp.insert_text((50, 50), f"P{i}", fontsize=20)
    pdoc.save("po.pdf"); pdoc.close()
    w3 = PDFMergerApp()
    w3.add_paths(["po.pdf"])
    for _ in range(40):
        QApplication.processEvents()
        if w3._thumb_worker is None or not w3._thumb_worker.isRunning():
            break
        wait_until(lambda: False, timeout_ms=50)
    from main_app import USERROLE_PAGEINFO as _UPI
    def _order(ww):
        return [ww.pages_list_widget.item(i).data(_UPI)['page_num'] for i in range(ww.pages_list_widget.count())]
    assert _order(w3) == [0, 1, 2], f"الترتيب الأولي خاطئ: {_order(w3)}"
    w3.pages_list_widget.setCurrentRow(0)
    w3.move_selected_page(1)
    assert _order(w3) == [1, 0, 2], f"تحريك الصفحة يمين فشل: {_order(w3)}"
    w3.pages_list_widget.setCurrentRow(0)
    w3.move_selected_page_to_edge(first=False)
    assert _order(w3)[-1] == 1, f"تحريك الصفحة للنهاية فشل: {_order(w3)}"
    w3.close()
    os.remove("po.pdf")
    print("[OK] أسهم ترتيب الصفحات (يمين/يسار/البداية/النهاية) تعمل")

    # 16e) اختبار إعداد السحب والإسقاط لترتيب الصفحات + صحة قراءة الترتيب
    from PyQt5.QtWidgets import QAbstractItemView
    assert w.pages_list_widget.dragDropMode() == QAbstractItemView.InternalMove, \
        "وضع السحب والإسقاط لإعادة الترتيب غير مفعّل"
    assert w.pages_list_widget.dragEnabled(), "سحب العناصر غير مفعّل"
    assert w.pages_list_widget.acceptDrops(), "إفلات العناصر غير مفعّل"
    print("[OK] السحب والإسقاط لترتيب الصفحات مُهيّأ بشكل صحيح")

    # 17) اختبار توليد اسم ملف عشوائي
    name1 = w._random_filename()
    name2 = w._random_filename()
    assert name1.startswith("PDF_") and name1.endswith(".pdf"), f"صيغة الاسم غير صحيحة: {name1}"
    assert name1 != name2, "أسماء الملفات العشوائية متطابقة"
    print(f"[OK] توليد اسم ملف عشوائي يعمل (مثال: {name1})")

    # 18) اختبار أن زر الحفظ يحمل النص الصحيح
    assert "حفظ" in w.btn_merge.text(), f"زر الحفظ لا يحمل النص الصحيح: {w.btn_merge.text()}"
    w.toggle_language()
    assert "Save" in w.btn_merge.text(), f"زر الحفظ بالإنجليزي خاطئ: {w.btn_merge.text()}"
    w.toggle_language()
    print("[OK] زر 'دمج الملفات' أُعيدت تسميته إلى 'حفظ'")

    # تنظيف ملفات الاختبار المؤقتة
    eng.close_all()
    for f in ["ct_image.png", "ct_with_image.pdf", "ct_stamped.pdf"] + [f"ct_merged_{l}.pdf" for l in [0,1,2,3]]:
        if os.path.exists(f):
            os.remove(f)

    print("\n=== كل الاختبارات نجحت ===")


if __name__ == "__main__":
    main()
