# -*- coding: utf-8 -*-
"""
launcher.py
نقطة تشغيل البرنامج المجمّع (PyInstaller): تُظهر شاشة البداية فورًا، ثم
تحمّل الوحدات الثقيلة (PyMuPDF والواجهة) مع تحديث شريط التقدّم، ثم تفتح
النافذة الرئيسية. التشغيل المباشر `python main_app.py` ما زال يعمل.
"""
import os
import sys

from PyQt5.QtWidgets import QApplication


def run():
    if sys.platform == "win32":
        # معرّف ثابت للتطبيق حتى يُظهر شريط المهام أيقونته الخاصة
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PDFMerger.App")
        except Exception:
            pass
    app = QApplication(sys.argv)

    from resources import resource_path
    from i18n import Translator
    from splash import Splash
    tr = Translator(lang="ar")
    splash = Splash(resource_path("app_icon.ico"), tr.t("app_title"),
                    tr.t("app_subtitle"), tr.t("splash_loading"))
    splash.show()
    splash.step(15)
    app.processEvents()

    import pdf_engine  # noqa: F401  (PyMuPDF: أثقل جزء في التحميل)
    splash.step(55)
    import main_app
    splash.step(80)
    main_app.main(app=app, splash=splash)


if __name__ == "__main__":
    run()
