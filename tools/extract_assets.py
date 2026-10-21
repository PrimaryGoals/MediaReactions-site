#!/usr/bin/env python3
"""One-time extraction of the files the static site needs from the WordPress archive.

    python3 tools/extract_assets.py /path/to/site-archive.zip static/

Copies, keeping the original WordPress paths so existing links keep working:
  * wp-content/uploads/            all images
  * the two OptimizePress stylesheets used by the landing pages, plus the few
    images those stylesheets point at.
Nothing else from the archive (PHP, plugins, config files) is copied.
Standard library only.
"""
import posixpath
import sys
import zipfile

OP = 'wp-content/plugins/optimizePressPlugin/'
WANTED_FILES = {
    OP + 'pages/marketing/1/style.min.css',
    OP + 'lib/assets/default.min.css',
    OP + 'lib/images/button-gradient.png',
    OP + 'lib/images/button-shine.png',
    OP + 'lib/images/progressbar-gradient.png',
    OP + 'lib/images/search-icon.png',
}
WANTED_PREFIXES = ('wp-content/uploads/', OP + 'pages/global/images/')
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')


def main(zip_path, out_dir):
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir() or '..' in name.split('/'):
                continue
            ok = name in WANTED_FILES or (name.startswith(WANTED_PREFIXES) and name.lower().endswith(IMAGE_EXT))
            if not ok:
                continue
            target = posixpath.join(out_dir.replace('\\', '/'), name)
            import os
            os.makedirs(posixpath.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, 'wb') as dst:
                dst.write(src.read())
            n += 1
    print('copied %d files' % n)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
