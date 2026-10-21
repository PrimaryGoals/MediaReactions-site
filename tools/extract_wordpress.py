#!/usr/bin/env python3
"""One-time importer: WordPress export (WXR .xml) -> plain content files.

    python3 tools/extract_wordpress.py /path/to/export.xml content/

Writes the ordinary pages as HTML files with a JSON front matter block
(content/pages/<slug>.html) plus site.json (title, tagline, menu).
Skipped on purpose: password-protected pages, drafts/previews, the sample
"Hello world!" post, and the three OptimizePress pages (see
tools/capture_op_pages.py). Author e-mail addresses and the like are never
copied. Do not commit the raw export file. Standard library only.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
}

# Built with OptimizePress; captured from the live site instead.
OP_SLUGS = {'charity', 'agency', 'thank-you'}
# Placeholder / unwanted pages.
SKIP_SLUGS = {'drtv', 'patent', 'hello-world'}


def text(el, tag):
    return el.findtext(tag, namespaces=NS) or ''


def path_of(it):
    return urlparse(it.findtext('link') or '').path or '/'


def main(xml_path, out_dir):
    ch = ET.parse(xml_path).getroot().find('channel')
    items = ch.findall('item')

    id_to_path = {text(it, 'wp:post_id'): path_of(it) for it in items
                  if text(it, 'wp:post_type') in ('post', 'page')}
    # The home page of the live site is the "agency" OptimizePress page.
    for pid, p in list(id_to_path.items()):
        if p.rstrip('/').endswith('/agency') or p == '/agency/':
            id_to_path[pid] = '/'

    os.makedirs(os.path.join(out_dir, 'pages'), exist_ok=True)
    kept, skipped = [], []
    for it in items:
        if text(it, 'wp:post_type') != 'page':
            continue
        slug = text(it, 'wp:post_name')
        if (text(it, 'wp:status') != 'publish' or text(it, 'wp:post_password')
                or slug in SKIP_SLUGS or slug in OP_SLUGS):
            skipped.append(slug)
            continue
        body = text(it, 'content:encoded')
        # links written for the temporary wpengine address -> real page paths
        body = re.sub(r'https?://mediareactions\.wpengine\.com/\?page_id=(\d+)',
                      lambda m: id_to_path.get(m.group(1), '/'), body)
        meta = {
            'id': int(text(it, 'wp:post_id')),
            'title': it.findtext('title') or '',
            'slug': slug,
            'path': path_of(it),
            'modified': text(it, 'wp:post_modified'),
        }
        with open(os.path.join(out_dir, 'pages', slug + '.html'), 'w', encoding='utf-8') as f:
            f.write('---\n%s\n---\n%s\n' % (json.dumps(meta, ensure_ascii=False), body))
        kept.append(slug)

    nodes = []
    for it in items:
        if text(it, 'wp:post_type') != 'nav_menu_item':
            continue
        m = {text(x, 'wp:meta_key'): text(x, 'wp:meta_value') for x in it.findall('wp:postmeta', NS)}
        if m.get('_menu_item_type') != 'post_type':
            continue
        target = id_to_path.get(m.get('_menu_item_object_id'))
        if not target:
            continue
        nodes.append((int(text(it, 'wp:menu_order') or 0), it.findtext('title') or '', target))
    labels = {p['path']: p['title'] for p in
              (json.loads(open(os.path.join(out_dir, 'pages', s + '.html'), encoding='utf-8')
                          .read().split('\n', 2)[1]) for s in kept)}
    # The "home" page is an old situation picker; the real home page is the OptimizePress one.
    # Company pages go last, as on the live site's menu order of importance.
    company = ('/about-us/', '/contact-us/')
    nodes = [n for n in nodes if n[2] != '/home/']
    nodes.sort(key=lambda n: (n[2] in company, n[0]))
    nav = [{'label': t or labels.get(h, h), 'href': h} for _, t, h in nodes]

    site = {
        'title': ch.findtext('title') or '',
        'description': ch.findtext('description') or '',
        'url': (ch.findtext('link') or '').rstrip('/'),
        'nav': nav,
    }
    with open(os.path.join(out_dir, 'site.json'), 'w', encoding='utf-8') as f:
        json.dump(site, f, indent=1, ensure_ascii=False)

    print('pages kept: %d (%s)' % (len(kept), ', '.join(kept)))
    print('skipped: %s' % ', '.join(skipped))
    print('menu items: %d' % len(nav))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
