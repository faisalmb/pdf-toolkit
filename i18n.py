# -*- coding: utf-8 -*-
"""
i18n.py
نظام ترجمة بسيط يدعم التبديل الفوري بين العربية والإنجليزية في كل
الواجهة عبر زر واحد، دون إعادة تشغيل البرنامج.
"""

STRINGS = {
    "app_title": {"ar": "أداة دمج ملفات PDF", "en": "PDF Merger Tool"},
    "lang_button": {"ar": "English", "en": "العربية"},

    # شريط علوي
    "btn_add_files": {"ar": "➕ إضافة ملفات PDF", "en": "➕ Add PDF Files"},
    "btn_add_images": {"ar": "🖼️ إضافة صور كصفحات", "en": "🖼️ Add Images as Pages"},
    "btn_ranges": {"ar": "📄 نطاق صفحات الملف المحدد", "en": "📄 Page Range for Selected File"},
    "btn_clear": {"ar": "🗑️ تفريغ القائمة", "en": "🗑️ Clear All"},
    "chk_optimize": {"ar": "ضغط الملف الناتج (تصغير الحجم)", "en": "Optimize output (reduce size)"},

    # التحكم بقوة الضغط
    "compression_label": {"ar": "قوة الضغط:", "en": "Compression:"},
    "compression_none": {"ar": "بدون", "en": "None"},
    "compression_light": {"ar": "خفيف", "en": "Light"},
    "compression_medium": {"ar": "متوسط", "en": "Medium"},
    "compression_strong": {"ar": "قوي", "en": "Strong"},
    "compression_hint": {"ar": "كلما زادت القوة قلّ الحجم وقلّت جودة الصور", "en": "Higher = smaller size but lower image quality"},

    # لوحة الملفات
    "files_panel_title": {"ar": "قائمة الملفات", "en": "Files"},
    "btn_top": {"ar": "⤒ الأعلى", "en": "⤒ Top"},
    "btn_up": {"ar": "↑ أعلى", "en": "↑ Up"},
    "btn_down": {"ar": "↓ أسفل", "en": "↓ Down"},
    "btn_bottom": {"ar": "⤓ الأسفل", "en": "⤓ Bottom"},
    "btn_remove_files": {"ar": "حذف المحدد", "en": "Remove Selected"},
    # أزرار الرسائل ونافذة التقدّم
    "btn_yes": {"ar": "نعم", "en": "Yes"},
    "btn_no": {"ar": "لا", "en": "No"},
    "btn_close": {"ar": "إغلاق", "en": "Close"},
    "btn_delete": {"ar": "حذف", "en": "Delete"},
    "btn_open_file": {"ar": "فتح الملف", "en": "Open File"},
    "btn_open_folder": {"ar": "فتح المجلد", "en": "Open Folder"},
    "stage_pages": {"ar": "تجميع الصفحات… {done} من {total}", "en": "Collecting pages… {done} of {total}"},
    "stage_stamps": {"ar": "تطبيق التواقيع والأختام…", "en": "Applying signatures and stamps…"},
    "stage_compress": {"ar": "ضغط الصور وتقليل الحجم…", "en": "Compressing images…"},
    "stage_save": {"ar": "حفظ الملف على القرص…", "en": "Saving the file…"},
    "stage_cancelling": {"ar": "جاري الإلغاء…", "en": "Cancelling…"},
    "progress_hint": {"ar": "قد تستغرق الملفات الكبيرة أو الضغط القوي بعض الوقت.",
                      "en": "Large files or strong compression can take a while."},
    "result_saved_text": {"ar": "تم حفظ الملف المدمج بنجاح.", "en": "The merged file was saved successfully."},
    "result_file": {"ar": "الملف", "en": "File"},
    "result_folder": {"ar": "المجلد", "en": "Folder"},
    "result_pages": {"ar": "عدد الصفحات", "en": "Pages"},
    "result_size": {"ar": "الحجم", "en": "Size"},
    "result_compression": {"ar": "الضغط", "en": "Compression"},
    "result_before": {"ar": "الحجم قبل الضغط", "en": "Size before"},
    "result_after": {"ar": "الحجم بعد الضغط", "en": "Size after"},
    "result_saving": {"ar": "نسبة التوفير", "en": "Saved"},
    "splash_loading": {"ar": "جاري التحميل…", "en": "Loading…"},
    "app_subtitle": {"ar": "دمج، ترتيب، توقيع وضغط ملفات PDF والصور في ملف واحد",
                     "en": "Merge, reorder, sign and compress PDFs and images into one file"},
    "file_item_pages": {"ar": "{n} صفحة", "en": "{n} page(s)"},
    "file_item_range": {"ar": "النطاق: {r}", "en": "Range: {r}"},
    "files_empty_hint": {"ar": "لا توجد ملفات بعد", "en": "No files yet"},
    "pages_empty_hint": {"ar": "📂\nاسحب ملفات PDF أو صورًا وأفلتها هنا\nأو استخدم زر «إضافة ملفات PDF» بالأعلى",
                         "en": "📂\nDrag and drop PDF files or images here\nor use the “Add PDF Files” button above"},

    # لوحة الصفحات
    "pages_panel_title": {"ar": "معاينة الصفحات", "en": "Page Preview"},
    "pages_panel_hint": {"ar": "حدّد صفحة لإظهار أسهم الترتيب • كليك يمين لمزيد من الخيارات", "en": "Select a page to show ordering arrows • Right-click for more options"},
    "page_order_label": {"ar": "ترتيب الصفحة ({pos}/{total}):", "en": "Page order ({pos}/{total}):"},
    "page_first": {"ar": "البداية ⇤", "en": "⇤ First"},
    "page_back": {"ar": "للخلف →", "en": "← Back"},
    "page_forward": {"ar": "← للأمام", "en": "Forward →"},
    "page_last": {"ar": "⇥ النهاية", "en": "Last ⇥"},
    "btn_merge": {"ar": "💾 حفظ الملف", "en": "💾 Save File"},
    "btn_refresh": {"ar": "🔄 تحديث المعاينات", "en": "🔄 Refresh Previews"},
    "btn_undo": {"ar": "↩️ تراجع عن آخر حذف", "en": "↩️ Undo Last Delete"},

    # حوار النطاق
    "range_dialog_title": {"ar": "نطاق الصفحات: {name}", "en": "Page Range: {name}"},
    "range_page_count": {"ar": "عدد الصفحات: {count}", "en": "Page count: {count}"},
    "range_hint": {"ar": "اكتب النطاق (مثال: 1-3,5,7-end) أو all", "en": "Enter range (e.g. 1-3,5,7-end) or 'all'"},
    "btn_ok": {"ar": "موافقة", "en": "OK"},
    "btn_cancel": {"ar": "إلغاء", "en": "Cancel"},

    # قائمة سياق الصفحة
    "ctx_preview": {"ar": "🔍 عرض بالحجم الكامل", "en": "🔍 View Full Size"},
    "ctx_rotate_right": {"ar": "↻ تدوير 90° يمين", "en": "↻ Rotate 90° Right"},
    "ctx_rotate_left": {"ar": "↺ تدوير 90° يسار", "en": "↺ Rotate 90° Left"},
    "ctx_duplicate": {"ar": "⧉ تكرار الصفحة", "en": "⧉ Duplicate Page"},
    "ctx_delete": {"ar": "🗑️ حذف الصفحة", "en": "🗑️ Delete Page"},
    "ctx_no_page": {"ar": "لا توجد صفحة هنا", "en": "No page here"},
    "ctx_insert_before": {"ar": "⬅️ إدراج صفحات قبلها", "en": "⬅️ Insert pages before"},
    "ctx_insert_after": {"ar": "➡️ إدراج صفحات بعدها", "en": "➡️ Insert pages after"},
    "ctx_annotate": {"ar": "✍️ توقيع / ختم / كتابة", "en": "✍️ Sign / Stamp / Write"},

    # نافذة التوقيع/الختم/الكتابة
    "annot_title": {"ar": "توقيع / ختم / كتابة على الصفحة", "en": "Sign / Stamp / Write on Page"},
    "annot_hint": {"ar": "أضف عنصرًا ثم اسحبه لتغيير موضعه، واسحب المقبض السفلي لتغيير حجمه", "en": "Add an element, then drag to move it, and drag the corner handle to resize"},
    "annot_add_image": {"ar": "🖼️ إضافة صورة (توقيع/ختم)", "en": "🖼️ Add Image (signature/stamp)"},
    "annot_add_text": {"ar": "🔤 إضافة نص", "en": "🔤 Add Text"},
    "annot_text_placeholder": {"ar": "اكتب النص هنا...", "en": "Type text here..."},
    "annot_text_size": {"ar": "الحجم:", "en": "Size:"},
    "annot_text_font": {"ar": "الخط:", "en": "Font:"},
    "annot_text_color": {"ar": "اللون:", "en": "Color:"},
    "annot_clear": {"ar": "مسح الكل", "en": "Clear all"},
    "annot_apply": {"ar": "تطبيق", "en": "Apply"},
    "annot_delete_selected": {"ar": "🗑️ حذف المحدد", "en": "🗑️ Delete selected"},
    "annot_props_title": {"ar": "خصائص النص", "en": "Text properties"},
    "annot_props_hint_none": {"ar": "اختر عنصر نص لتعديل خصائصه", "en": "Select a text element to edit its properties"},
    "annot_count": {"ar": "العناصر: {n}", "en": "Elements: {n}"},
    "annot_pick_image_first": {"ar": "اختر صورة أو أضف نصًا أولًا.", "en": "Choose an image or add text first."},
    "annot_image_dialog": {"ar": "اختر صورة التوقيع أو الختم", "en": "Choose signature or stamp image"},
    "annot_empty_text": {"ar": "اكتب نصًا أولًا في الحقل.", "en": "Type some text in the field first."},
    "annot_pick_color": {"ar": "اختر لون النص", "en": "Choose text color"},
    "annot_zoom_reset": {"ar": "100%", "en": "100%"},
    "annot_add_redact": {"ar": "✂️ حذف منطقة من الصفحة", "en": "✂️ Delete Area from Page"},
    "annot_redact_hint": {"ar": "اسحب بالماوس على الصفحة لتحديد المنطقة المراد حذفها. سيُمسح النص أو الصورة بداخلها مع الحفاظ على لون الخلفية المحيط (لا يترك مربعًا أبيض).", "en": "Drag on the page to mark the area to delete. The text/image inside will be erased while keeping the surrounding background color (no white box)."},

    # عارض الصفحة الكاملة
    "viewer_title": {"ar": "معاينة: {name} - صفحة {page}", "en": "Preview: {name} - page {page}"},
    "zoom_in": {"ar": "تكبير (+)", "en": "Zoom In (+)"},
    "zoom_out": {"ar": "تصغير (-)", "en": "Zoom Out (-)"},

    # رسائل
    "msg_attention": {"ar": "تنبيه", "en": "Notice"},
    "msg_error": {"ar": "خطأ", "en": "Error"},
    "msg_select_file_first": {"ar": "اختر ملفًا أولًا من قائمة الملفات.", "en": "Please select a file from the list first."},
    "msg_select_files_to_move": {"ar": "اختر ملفًا واحدًا أو أكثر للتحريك.", "en": "Select one or more files to move."},
    "msg_add_pages_first": {"ar": "أضِف صفحات أولًا.", "en": "Please add pages first."},
    "msg_some_files_rejected": {"ar": "تم تجاهل الملفات التالية:\n{list}", "en": "The following files were skipped:\n{list}"},
    "msg_files_skipped_title": {"ar": "تعذرت إضافة بعض الملفات", "en": "Some files could not be added"},
    "msg_open_failed": {"ar": "تعذر فتح {name}: {error}", "en": "Could not open {name}: {error}"},
    "msg_read_failed": {"ar": "تعذر قراءة الملف {name}: {error}", "en": "Could not read file {name}: {error}"},
    "msg_range_error_title": {"ar": "خطأ في النطاق", "en": "Range Error"},
    "msg_preview_error": {"ar": "حدث خطأ أثناء المعاينة: {error}", "en": "An error occurred during preview: {error}"},
    "msg_rotate_error": {"ar": "تعذر تدوير المعاينة: {error}", "en": "Could not rotate preview: {error}"},
    "msg_confirm_delete_title": {"ar": "تأكيد الحذف", "en": "Confirm Delete"},
    "msg_confirm_delete_body": {"ar": "هل أنت متأكد من حذف هذه الصفحة؟", "en": "Are you sure you want to delete this page?"},
    "msg_merge_dialog_title": {"ar": "حفظ الملف المدمج", "en": "Save Merged File"},
    "msg_merge_progress_title": {"ar": "دمج PDF", "en": "Merging PDF"},
    "msg_merging": {"ar": "جاري الدمج...", "en": "Merging..."},
    "msg_merge_cancel_btn": {"ar": "إلغاء", "en": "Cancel"},
    "msg_merge_success_title": {"ar": "تم بنجاح", "en": "Success"},
    "msg_merge_success_body": {
        "ar": "تم دمج الملفات بنجاح:\n{path}\n\nالحجم النهائي: {size}",
        "en": "Files merged successfully:\n{path}\n\nFinal size: {size}",
    },
    "msg_merge_success_body_with_compression": {
        "ar": "تم دمج الملفات بنجاح:\n{path}\n\nمستوى الضغط: {level}\nالحجم قبل الضغط: {size_before}\nالحجم بعد الضغط: {size_after}\nنسبة التصغير: {ratio}",
        "en": "Files merged successfully:\n{path}\n\nCompression level: {level}\nSize before: {size_before}\nSize after: {size_after}\nReduction: {ratio}",
    },
    "msg_add_images_dialog": {"ar": "اختر صورًا لإضافتها كصفحات", "en": "Choose images to add as pages"},
    "msg_insert_files_dialog": {"ar": "اختر ملفات PDF أو صور لإدراجها", "en": "Choose PDFs or images to insert"},
    "msg_merge_failed": {"ar": "حدث خطأ أثناء الدمج: {error}", "en": "An error occurred while merging: {error}"},
    "msg_merge_cancelled_title": {"ar": "أُلغي", "en": "Cancelled"},
    "msg_merge_cancelled_body": {"ar": "تم إلغاء عملية الدمج.", "en": "The merge operation was cancelled."},
    "msg_password_protected": {"ar": "الملف محمي بكلمة سر — لا يمكن دمجه حاليًا", "en": "File is password-protected — cannot be merged currently"},
    "msg_invalid_pdf": {"ar": "تعذر فتح الملف كـ PDF صالح: {error}", "en": "Could not open file as a valid PDF: {error}"},

    # شريط حالة المعاينات
    "generating_previews": {"ar": "جاري توليد المعاينات... {done}/{total}", "en": "Generating previews... {done}/{total}"},

    # وحدات الحجم
    "unit_bytes": {"ar": "بايت", "en": "bytes"},
    "unit_kb": {"ar": "كيلوبايت", "en": "KB"},
    "unit_mb": {"ar": "ميغابايت", "en": "MB"},
    "unit_gb": {"ar": "غيغابايت", "en": "GB"},

    # شريط حالة سفلي
    "status_files_count": {"ar": "📁 {n} ملف", "en": "📁 {n} file(s)"},
    "status_pages_count": {"ar": "📄 {n} صفحة", "en": "📄 {n} page(s)"},
    "status_ready": {"ar": "جاهز", "en": "Ready"},
}


class Translator:
    """مدير اللغة الحالية: يحتفظ باللغة النشطة ويوفر دالة ترجمة بسيطة t(key, **kwargs)."""

    def __init__(self, lang="ar"):
        self.lang = lang

    def set_lang(self, lang: str):
        assert lang in ("ar", "en")
        self.lang = lang

    def toggle(self):
        self.lang = "en" if self.lang == "ar" else "ar"
        return self.lang

    @property
    def is_rtl(self) -> bool:
        return self.lang == "ar"

    def t(self, key: str, **kwargs) -> str:
        entry = STRINGS.get(key)
        if entry is None:
            return key
        text = entry.get(self.lang, entry.get("ar", key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text
