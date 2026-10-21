#!/usr/bin/env python3
"""One-time capture of the three OptimizePress pages from the live site.

    python3 tools/capture_op_pages.py content/

OptimizePress stores its pages as page-builder markup that only makes sense
inside the plugin, so we save the rendered page body instead
(content/op/<slug>.html, with a JSON front matter block). Scripts and the
WordPress nonce are dropped; the opt-in form keeps posting straight to the
form provider. Run while mediareactions.com is still served by WordPress.
Standard library only.
"""
import json
import os
import re
import sys
import urllib.request

LIVE = 'https://mediareactions.com'
PAGES = [  # slug, live path, title
    ('agency', '/', 'DRTV for Agencies'),
    ('charity', '/drtv/charity/', 'DRTV for Charity'),
    ('thank-you', '/drtv/thank-you/', 'DRTV Thank You'),
]


def fetch(path):
    req = urllib.request.Request(LIVE + path, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8')


def extract(html):
    start = html.index('<div id="content_area"')
    end = html.index('<div class="full-width footer')
    body = html[start:end]
    body = re.sub(r'<script\b.*?</script>', '', body, flags=re.S)
    body = re.sub(r'<input type="hidden" (?:id="op_optin_nonce"|name="_wp_http_referer")[^>]*>', '', body)
    body = body.replace(LIVE + '/', '/').replace(LIVE, '/')
    body = body.replace('http://player.vimeo.com', 'https://player.vimeo.com')
    return body.strip()


def main(out_dir):
    os.makedirs(os.path.join(out_dir, 'op'), exist_ok=True)
    for slug, path, title in PAGES:
        body = extract(fetch(path))
        meta = {'slug': slug, 'title': title, 'path': '/' if slug == 'agency' else path}
        with open(os.path.join(out_dir, 'op', slug + '.html'), 'w', encoding='utf-8') as f:
            f.write('---\n%s\n---\n%s\n' % (json.dumps(meta), body))
        print('%s: %d bytes' % (slug, len(body)))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
