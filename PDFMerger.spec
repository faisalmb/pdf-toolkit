# -*- mode: python ; coding: utf-8 -*-
"""
PDFMerger.spec
ملف بناء PyInstaller للبرنامج على ويندوز وماك ولينكس (يُبنى كل نظام على
جهازه، فـ PyInstaller لا يبني لنظام آخر).

يبني مجلدًا (onedir) وليس ملفًا واحدًا (onefile)، وبدون ضغط UPX، مع
معلومات إصدار وأيقونة. السبب: الملف الواحد الذي يفك نفسه في مجلد مؤقت
عند كل تشغيل، والملفات المضغوطة بـ UPX، هما أكثر ما يجعل Windows Defender
يعتبر برامج PyInstaller مشبوهة خطأً. المجلد الناتج يُوزَّع عبر برنامج
التثبيت (installer.iss)، وهو أيضًا أسرع في الإقلاع.

طريقة الاستخدام:
    pip install -r requirements.txt pyinstaller
    pyinstaller --noconfirm PDFMerger.spec

الناتج:
    ويندوز: dist/PDFMerger/PDFMerger.exe (مع ملفاته بجانبه)
    ماك:    dist/PDFMerger.app
    لينكس:  dist/PDFMerger/PDFMerger
"""

import os
import sys

APP_VERSION = '11.0.0'
IS_WIN = sys.platform == 'win32'
IS_MAC = sys.platform == 'darwin'

if IS_WIN:
    _icon = 'app_icon.ico'
elif IS_MAC:
    # PyInstaller يحوّل PNG إلى icns تلقائيًا (يحتاج Pillow)
    _icon = 'app_icon.png'
else:
    _icon = None   # لينكس: الأيقونة تأتي من ملف .desktop
if _icon and not os.path.exists(_icon):
    _icon = None

_datas = []
# نضمّن مجلد الخطوط فقط إذا كان موجودًا، حتى لا يفشل البناء لو نُسي
# نسخه. لو غاب المجلد يعمل البرنامج بالخطوط اللاتينية القياسية فقط.
if os.path.isdir('fonts'):
    _datas.append(('fonts', 'fonts'))
else:
    print("=" * 60)
    print("WARNING: 'fonts' folder not found - Arabic fonts will NOT")
    print("be bundled. The app still works with standard Latin fonts.")
    print("=" * 60)
if os.path.exists('app_icon.ico'):
    _datas.append(('app_icon.ico', '.'))

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'arabic_reshaper',
        'bidi',
        'bidi.algorithm',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # مكتبات غير مستخدمة: تقليل الحجم وعدد الملفات
        'tkinter',
        'unittest',
        'pydoc',
        'PyQt5.QtNetwork',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtBluetooth',
        'PyQt5.QtMultimedia',
        'PyQt5.QtPositioning',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtSql',
        'PyQt5.QtTest',
        'PyQt5.QtXml',
        'PyQt5.QtDBus',
        'PyQt5.QtOpenGL',
        'PyQt5.QtSvg',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir: المكتبات بجانب الـ exe بدل حشرها داخله
    name='PDFMerger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX يرفع احتمال الإنذارات الكاذبة
    console=False,           # بدون نافذة Console سوداء خلف البرنامج
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
    version='version_info.txt' if IS_WIN and os.path.exists('version_info.txt') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PDFMerger',
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name='PDFMerger.app',
        icon=_icon,
        bundle_identifier='io.github.faisalmb.pdfmerger',
        version=APP_VERSION,
        info_plist={
            'CFBundleDisplayName': 'PDF Merger',
            'CFBundleShortVersionString': APP_VERSION,
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': True,  # الواجهة مصممة للوضع الفاتح
            'CFBundleDocumentTypes': [{
                'CFBundleTypeName': 'PDF Document',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['com.adobe.pdf'],
            }],
        },
    )
