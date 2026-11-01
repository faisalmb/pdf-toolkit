# PDF Merger

**English** | [العربية](README.ar.md)

A desktop app for merging PDF files and images, arranging their pages, and
signing, stamping or annotating them before saving one clean PDF.
The interface is bilingual: Arabic (right to left) and English (left to right).
It runs on Windows, macOS and Linux.

Built with Python, PyQt5 and PyMuPDF. Version 11.0.0.

**[⬇️ Download the latest release](https://github.com/faisalmb/pdf-toolkit/releases/latest)**: [Windows](https://github.com/faisalmb/pdf-toolkit/releases/latest/download/PDFMerger-Setup-11.0.0.exe) · [macOS](https://github.com/faisalmb/pdf-toolkit/releases/latest/download/PDFMerger-11.0.0-macOS-arm64.dmg) · [Linux](https://github.com/faisalmb/pdf-toolkit/releases/latest/download/PDFMerger-11.0.0-linux-x86_64.tar.gz)

---

## Contents

- [Features](#features)
- [Download and install](#download-and-install)
- [Using the app](#using-the-app)
- [Run from source](#run-from-source)
- [Building packages](#building-packages)
- [Project structure](#project-structure)
- [How it works](#how-it-works)
- [Testing](#testing)
- [Version history](#version-history)
- [License](#license)

---

## Features

**Files and pages**
- Add PDF files and images (PNG, JPG, BMP, GIF, TIFF, WebP) with a button or by
  drag and drop. Each image becomes a full page.
- Choose a page range per file, such as `1-3,5`. The range is checked as you type.
- See every page as a thumbnail and reorder by dragging, or with the
  Start / Back / Forward / End buttons.
- Rotate, duplicate and delete pages, and undo the last delete.
- Insert pages from another PDF or from images before or after any page.
- Reorder whole files. Your page edits are kept when you add files,
  change ranges or reorder.

**Sign, stamp and write on pages**
- An interactive page editor opens from a page's right-click menu.
- Place a signature or stamp image, or a text box. Drag to move, and drag the
  corner handle to resize.
- Text options: font (Helvetica, Times, Courier, and bundled Arabic fonts
  Amiri and Cairo), size from 6 to 200, colour, and editable content.
  Arabic text is shaped and ordered correctly, including mixed Arabic and
  English text.
- **Remove area**: drag a rectangle to truly delete everything inside it in
  the output (a redaction, not just a cover). The app fills the area with the
  surrounding background colour, so no white box is left.
- Zoom up to 400% and pan by dragging.
- Stamps stay in the right place on rotated pages and on any page size.

**Saving**
- Four compression levels: None, Light, Medium and Strong. They lower the
  resolution and JPEG quality of images inside the PDF.
- A progress window shows each stage (collecting pages, stamps, compressing,
  saving), and you can cancel it.
- When it finishes, the app shows the size before and after and the saving
  in percent. Buttons open the file or its folder.
- The output file is suggested a unique name such as
  `PDF_20261101_141210_k3x9.pdf`.
- Atomic save: the app writes a temporary file and then swaps it in, so a crash
  never leaves a half-written PDF.

**Comfort and speed**
- Thumbnails are drawn in a low-priority background thread, so the window
  never freezes. Placeholder cards and a progress bar show while they load.
- A splash screen appears as soon as you launch the app.
- Each file is opened only once. Thumbnails are kept in a small cache of
  about 20 MB.
- Encrypted or broken files are rejected when you add them, with a clear
  reason.

---

## Download and install

Ready-made packages are published automatically on the **[Releases](https://github.com/faisalmb/pdf-toolkit/releases)** page
with every update (see [Automatic builds](#automatic-builds-github-actions)).

| System | File | Install |
|---|---|---|
| Windows 10/11 (x64) | [`PDFMerger-Setup-11.0.0.exe`](https://github.com/faisalmb/pdf-toolkit/releases/latest/download/PDFMerger-Setup-11.0.0.exe) | Run it. It installs for the current user, so no admin rights are needed. |
| macOS (Apple Silicon) | [`PDFMerger-11.0.0-macOS-arm64.dmg`](https://github.com/faisalmb/pdf-toolkit/releases/latest/download/PDFMerger-11.0.0-macOS-arm64.dmg) | Open it and drag **PDFMerger** into **Applications**. |
| Linux (x86_64) | [`PDFMerger-11.0.0-linux-x86_64.tar.gz`](https://github.com/faisalmb/pdf-toolkit/releases/latest/download/PDFMerger-11.0.0-linux-x86_64.tar.gz) | Extract it and run `./install.sh`. |

### Windows notes
- The installer puts the app in `%LOCALAPPDATA%\Programs\PDF Merger`, adds a
  Start menu shortcut (and an optional desktop one) and an uninstaller in
  *Installed apps*. Its wizard is available in Arabic or English.
- The app is built as a normal folder (not a single self-extracting exe) and
  without UPX compression. This avoids the most common reason Windows
  Defender wrongly flags Python apps.
- The installer is not code-signed, so **SmartScreen** may show
  "Windows protected your PC" after you download it. Click **More info**, then
  **Run anyway**. If **Smart App Control** is on, Windows 11 blocks unsigned
  apps with no way to allow them.
- Signing the installer (for example with Azure Trusted Signing or a code
  signing certificate) or publishing in the Microsoft Store removes these
  warnings. You can report a Defender false positive at
  <https://www.microsoft.com/wdsi/filesubmission>.

### macOS notes
- The app is not signed or notarised. The first time, right-click
  **PDFMerger** in Applications, choose **Open**, then **Open** again.
- The automatic build targets Apple Silicon. For an Intel Mac, build it on
  an Intel Mac with `./build_mac.sh`.

### Linux notes
- `install.sh` installs into `~/.local/share/pdfmerger` and adds a menu entry,
  with no `sudo` needed. Remove it with `./uninstall.sh`.
- It needs the usual Qt/X11 libraries found on desktop distributions. If it
  does not start on Ubuntu or Debian:
  ```bash
  sudo apt install libxcb-xinerama0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0
  ```

---

## Using the app

1. **Add files**: use **Add files**, **Add images as pages**, or drop files on
   the window.
2. **Set ranges** (optional): pick a file in the files panel and set its page
   range. The default is all pages.
3. **Arrange pages**: drag thumbnails, or select a page and use the
   arrow buttons under the preview.
4. **Edit pages**: right-click a page to rotate, duplicate, delete, insert
   pages before or after it, or open **Sign / Stamp / Write**. Pages with
   stamps show a ✍️ mark.
5. **Choose compression** with the slider.
6. **Save**. Pick a location, watch the progress, then open the file or folder.

The language button at the top switches between Arabic and English at once,
including the layout direction.

---

## Run from source

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
python launcher.py      # with splash screen
# or
python main_app.py      # straight to the main window
```

Dependencies (`requirements.txt`): PyQt5, PyMuPDF, arabic-reshaper and
python-bidi.

---

## Building packages

PyInstaller can't cross-compile, so build each system's package on that
system. Every build uses [`PDFMerger.spec`](PDFMerger.spec), which produces
a folder build (onedir) without UPX.

| System | Command | Output |
|---|---|---|
| Windows | `build_exe.bat` | `installer_output\PDFMerger-Setup-11.0.0.exe` and `dist\PDFMerger\` |
| macOS | `./build_mac.sh` | `installer_output/PDFMerger-11.0.0-macOS-<arch>.dmg` and `dist/PDFMerger.app` |
| Linux | `./build_linux.sh` | `installer_output/PDFMerger-11.0.0-linux-<arch>.tar.gz` and `dist/PDFMerger/` |

- **Windows** also needs [Inno Setup 6](https://jrsoftware.org/isinfo.php)
  for the installer (`winget install JRSoftware.InnoSetup`). Without it the
  script builds only the app folder.
- **macOS** needs Pillow (the script installs it) to turn `app_icon.png` into
  an `.icns` icon.
- Keep the `fonts/` folder next to the spec. If it is missing the build still
  works, but the Arabic fonts are not bundled.

### Automatic builds (GitHub Actions)

[`.github/workflows/build.yml`](.github/workflows/build.yml):
- **Every push to `main`** runs the tests, then builds all three packages
  and publishes them as a new GitHub Release tagged
  `v11.0.0-build.<run number>`. That release becomes the latest one.
- Pushing a version tag (`git tag v11.0.0 && git push origin v11.0.0`)
  publishes a release named after that tag instead.
- Pull requests only run the tests. Commits that change only `.md` files
  don't trigger a build.
- You can also run it by hand from **Actions → build → Run workflow**. The
  packages then appear as workflow artifacts, and no release is made.
- The version number comes from `APP_VERSION` in `PDFMerger.spec`.

---

## Project structure

| Path | Purpose |
|---|---|
| `launcher.py` | Entry point for packaged builds: shows the splash, then loads the app |
| `main_app.py` | Main window: files panel, page grid, toolbar, save flow |
| `editor.py` | Sign / stamp / write / remove-area page editor |
| `pdf_engine.py` | All PDF work (open, probe, render, merge, stamp, compress), with no UI |
| `workers.py` | Background threads for thumbnails and merging |
| `dialogs.py` | Styled message boxes and the staged progress window |
| `splash.py` | Splash screen |
| `theme.py` | Colours, fonts and the Qt stylesheet |
| `i18n.py` | All UI text in Arabic and English, and the direction switch |
| `resources.py` | Finds bundled files (fonts, icon) in source and packaged runs |
| `fonts/` | Bundled Amiri and Cairo fonts |
| `test_headless.py`, `make_test_fixtures.py` | End-to-end tests and their sample PDFs |
| `PDFMerger.spec` | PyInstaller build for all platforms |
| `build_exe.bat`, `installer.iss`, `version_info.txt` | Windows build and Inno Setup installer |
| `build_mac.sh` | macOS `.app` and `.dmg` |
| `build_linux.sh`, `packaging/linux/` | Linux tarball, `.desktop` entry, install and uninstall scripts |
| `app_icon.ico`, `app_icon.png` | App icon (Windows; macOS and Linux) |

---

## How it works

- **UI and engine are separate.** `pdf_engine.PdfEngine` has no Qt widgets.
  The window builds a list of page references (file, page, rotation) and
  stamp specs, and hands them to the engine.
- **One lock for PyMuPDF.** PyMuPDF is not thread-safe. Every document access
  goes through one re-entrant lock, held for the whole merge.
- **Thumbnails.** A `ThumbnailWorker` QThread takes a queue of jobs. It renders
  each page as raw RGB pixels at its final size, turns them into a `QImage` in
  the worker, and caches the result in an LRU cache of 200 items.
- **Edits that survive.** Each page card has a stable id. Adding files or
  changing ranges updates only the affected file's pages, so rotation,
  duplicates, manual order and stamps stay in place.
- **Stamps.** Positions are stored as fractions of the page size. On save,
  they go through the page's derotation matrix, so they land correctly on
  rotated pages.
- **Compression.** PyMuPDF `rewrite_images` re-encodes only images above the
  target DPI. The "before" size is estimated from the xref table, so the file
  is saved only once.
- **Arabic text.** `arabic-reshaper` and `python-bidi` prepare the text, which
  is then written with an embedded Amiri or Cairo font.

---

## Testing

`test_headless.py` runs the real app without a screen and acts like a user:
- adds valid and invalid files, and sets ranges
- waits for thumbnails, then rotates, duplicates, deletes and undoes pages
- checks that edits survive re-syncs
- merges at every compression level
- applies image, text and Arabic stamps, including on rotated pages
- runs redaction, cancels a merge, rejects encrypted files, and switches
  language

```bash
python make_test_fixtures.py
QT_QPA_PLATFORM=offscreen python test_headless.py
```

On Windows PowerShell, set the variable first:
`$env:QT_QPA_PLATFORM="offscreen"; python test_headless.py`.
The run ends with `=== كل الاختبارات نجحت ===` ("all tests passed").

---

## Version history

- **v11**:
  - Edits are no longer lost when adding files or changing ranges.
  - Undo restores a page with its stamps.
  - Thread-safe PyMuPDF access.
  - Lighter thumbnails and a single save when compressing.
  - Correct stamps on rotated pages.
  - Redesigned toolbar, styled dialogs, staged progress window, loading
    placeholders and splash screen.
  - A Windows installer built to avoid Defender false positives.
  - Builds for macOS and Linux.
- **v10**:
  - Fixed blank output ("insufficient data for an image") when compressing,
    by switching to `rewrite_images`.
  - Clear text page-move buttons replaced the arrows.
- **v9**:
  - Page-move buttons.
  - Double-click to edit text.
  - Background-aware area removal.
- **v8**:
  - Bundled Arabic fonts.
  - Redaction ("remove area").
  - Pan while zoomed.
- **v7**:
  - Multiple stamps no longer stack on top of each other.
  - Editor zoom.
  - Unique suggested file names.
  - "Save" button.
- **v5**:
  - Compression slider.
  - Images as pages.
  - Insert pages anywhere.
  - Interactive sign / stamp / write editor.
- **v4**:
  - Arabic / English interface.
  - Real compression ratio.
  - New visual identity and status bar.
- **Earlier**:
  - Background thumbnails and merging.
  - Atomic save.
  - Early file checks.
  - Undo.
  - Engine split from the UI.

---

## License

The source code of this project is released under the [MIT License](LICENSE).

Third-party parts keep their own licenses:
- **Amiri** and **Cairo** fonts: SIL Open Font License 1.1.
- **PyMuPDF**: GNU AGPL v3 (or a commercial license from Artifex).
- **PyQt5**: GNU GPL v3 (or a commercial license from Riverbank Computing).

The packaged apps (exe, dmg, tar.gz) bundle PyMuPDF and PyQt5, so in
practice they are distributed under the AGPL/GPL terms. That is fine for a
free app whose source code is public.
