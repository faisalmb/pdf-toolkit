# -*- coding: utf-8 -*-
"""
make_test_fixtures.py
ينشئ ملفات PDF التي يحتاجها test_headless.py في المجلد الحالي:
test1.pdf (5 صفحات)، test2.pdf (4 صفحات)، test3.pdf (صفحتان).
"""
import fitz

for name, n in (("test1.pdf", 5), ("test2.pdf", 4), ("test3.pdf", 2)):
    doc = fitz.open()
    for i in range(n):
        page = doc.new_page()
        page.insert_text((72, 100), f"{name} page {i + 1}", fontsize=24)
    doc.save(name)
    doc.close()
print("fixtures ok")
