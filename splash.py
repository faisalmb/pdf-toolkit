# -*- coding: utf-8 -*-
"""
splash.py
شاشة البداية: تظهر فورًا عند تشغيل البرنامج (قبل تحميل PyMuPDF وباقي
الواجهة) ببطاقة تحمل الأيقونة والاسم وشريط تقدّم، بدل انتظار ثوانٍ بلا
أي شيء على الشاشة. تعتمد على PyQt فقط حتى تظهر بأسرع ما يمكن.
"""
import os

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QPainterPath
from PyQt5.QtWidgets import QSplashScreen

from theme import COLOR_PRIMARY, COLOR_PRIMARY_SOFT, COLOR_TEXT, COLOR_TEXT_MUTED, COLOR_BORDER, UI_FONT

_W, _H = 440, 250


class Splash(QSplashScreen):
    def __init__(self, icon_path=None, title="PDF Merger", subtitle="", message="", rtl=True):
        pm = QPixmap(_W, _H)
        pm.fill(Qt.transparent)
        super().__init__(pm, Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._icon = QIcon(icon_path) if icon_path and os.path.exists(icon_path) else None
        self._title = title
        self._subtitle = subtitle
        self._message = message
        self._progress = 0
        self._rtl = rtl

    def step(self, progress: int, message: str = None):
        """يحدّث الشريط والرسالة ويرسم فورًا (لا توجد حلقة أحداث بعد)."""
        self._progress = max(0, min(100, progress))
        if message is not None:
            self._message = message
        self.repaint()

    def drawContents(self, p: QPainter):
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        # اتجاه الكتابة: بدونه يُرتَّب النص العربي المختلط بكلمات لاتينية خطأ
        p.setLayoutDirection(Qt.RightToLeft if self._rtl else Qt.LeftToRight)
        card = QRectF(6, 6, _W - 12, _H - 12)
        path = QPainterPath()
        path.addRoundedRect(card, 16, 16)
        p.fillPath(path, QColor("#FFFFFF"))
        p.setPen(QColor(COLOR_BORDER))
        p.drawPath(path)

        if self._icon is not None:
            self._icon.paint(p, int(_W / 2 - 36), 34, 72, 72)

        p.setPen(QColor(COLOR_TEXT))
        f = QFont(UI_FONT, 17)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 116, _W, 34), Qt.AlignCenter, self._title)

        p.setPen(QColor(COLOR_TEXT_MUTED))
        p.setFont(QFont(UI_FONT, 9))
        p.drawText(QRectF(20, 150, _W - 40, 22), Qt.AlignCenter, self._subtitle)

        # شريط التقدّم
        bar = QRectF(60, 192, _W - 120, 8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(COLOR_PRIMARY_SOFT))
        p.drawRoundedRect(bar, 4, 4)
        if self._progress:
            filled = QRectF(bar.x(), bar.y(), bar.width() * self._progress / 100.0, bar.height())
            p.setBrush(QColor(COLOR_PRIMARY))
            p.drawRoundedRect(filled, 4, 4)

        p.setPen(QColor(COLOR_TEXT_MUTED))
        p.setFont(QFont(UI_FONT, 9))
        p.drawText(QRectF(0, 206, _W, 22), Qt.AlignCenter, self._message)
