#!/usr/bin/env python3
"""Static site generator for mediareactions.com.

    python3 build.py            # writes the finished site into ./public

Reads ./content (pages/, op/, site.json) and copies ./static verbatim.
Python 3.8+, standard library only. Contains no credentials and makes no
network requests.

URL structure matches the old WordPress site:
  /                      home (the "DRTV for Agencies" landing page)
  /drtv/charity/         landing page
  /drtv/thank-you/       landing page (opt-in thank-you)
  /<page-slug>/          ordinary pages
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
STATIC = ROOT / 'static'
OUT = ROOT / 'public'

SITE = json.loads((CONTENT / 'site.json').read_text(encoding='utf-8'))
SITE_URL = SITE['url']
BRAND = '#6C1000'
LOGO = '/wp-content/uploads/2017/02/cropped-logo.jpg'
OP = '/wp-content/plugins/optimizePressPlugin/'
CSS_VERSION = '2'

esc = html.escape


def parse_front(path):
    s = path.read_text(encoding='utf-8')
    if not s.startswith('---\n'):
        raise ValueError('missing front matter: %s' % path)
    head, body = s[4:].split('\n---\n', 1)
    return json.loads(head), body.rstrip('\n')


def load(folder):
    out = []
    for p in sorted((CONTENT / folder).glob('*.html')):
        meta, raw = parse_front(p)
        meta['raw'] = raw
        out.append(meta)
    return out


# --------------------------------------------------------------------------
# Body rendering: reproduces WordPress's wpautop() for the ordinary pages
# --------------------------------------------------------------------------

ALLBLOCKS = (r'(?:table|thead|tfoot|caption|col|colgroup|tbody|tr|td|th|div|dl|dd|dt|ul|ol|li|pre|'
             r'form|map|area|blockquote|address|math|style|p|h[1-6]|hr|fieldset|legend|section|'
             r'article|aside|hgroup|header|footer|nav|figure|figcaption|details|menu|summary)')


def wpautop(pee):
    """Port of WordPress's wpautop(): blank lines become paragraphs, single newlines become <br />."""
    if not pee.strip():
        return ''
    pee = pee.replace('\r\n', '\n').replace('\r', '\n') + '\n'
    pee = re.sub(r'<br\s*/?>\s*<br\s*/?>', '\n\n', pee)
    pee = re.sub(r'(<' + ALLBLOCKS + r'[\s/>])', r'\n\n\1', pee)
    pee = re.sub(r'(</' + ALLBLOCKS + r'>)', r'\1\n\n', pee)
    pee = re.sub(r'\n\n+', '\n\n', pee)
    chunks = [c for c in re.split(r'\n\s*\n', pee) if c != '']
    pee = ''.join('<p>' + c.strip('\n') + '</p>\n' for c in chunks)
    pee = re.sub(r'<p>\s*</p>', '', pee)
    pee = re.sub(r'<p>([^<]+)</(div|address|form)>', r'<p>\1</p></\2>', pee)
    pee = re.sub(r'<p>\s*(</?' + ALLBLOCKS + r'[^>]*>)\s*</p>', r'\1', pee)
    pee = re.sub(r'<p>(<li.+?)</p>', r'\1', pee)
    pee = re.sub(r'<p>\s*(</?' + ALLBLOCKS + r'[^>]*>)', r'\1', pee)
    pee = re.sub(r'(</?' + ALLBLOCKS + r'[^>]*>)\s*</p>', r'\1', pee)
    pee = pee.replace('<br>', '<br />').replace('<br/>', '<br />')
    pee = re.sub(r'(?<!<br />)\s*\n', '<br />\n', pee)
    pee = re.sub(r'(</?' + ALLBLOCKS + r'[^>]*>)\s*<br />', r'\1', pee)
    pee = re.sub(r'<br />(\s*</?(?:p|li|div|dl|dd|dt|th|pre|td|ul|ol)[^>]*>)', r'\1', pee)
    pee = re.sub(r'\n</p>$', '</p>', pee)
    return pee


YT_URL = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})[^\s<"]*'


def render_body(raw):
    s = re.sub(r'<!--\s*/?wp:.*?-->', '', raw)
    s = wpautop(s)
    s = re.sub(r'(\s(?:href|src))=(["\'])https?://(?:www\.)?mediareactions\.com(/[^"\']*)?\2',
               lambda m: '%s=%s%s%s' % (m.group(1), m.group(2), m.group(3) or '/', m.group(2)), s)
    return s


# --------------------------------------------------------------------------
# Contact forms: the old Infusionsoft (Keap) account is closed, so the
# landing-page forms post to FormSubmit.co, which emails each submission.
# To use another address or service, change the two constants below.
# --------------------------------------------------------------------------

FORM_TO = 'ashley@primarygoals.com'
FORM_ENDPOINT = 'https://formsubmit.co/' + FORM_TO
FORM_FIELDS = {  # Infusionsoft field name -> name shown in the email
    'inf_field_FirstName': 'First name',
    'inf_field_LastName': 'Last name',
    'inf_field_Email': 'email',  # FormSubmit uses a field called "email" as the reply-to address
    'inf_field_Phone1': 'Phone',
    'inf_field_Company': 'Company',
}


def email_forms(s):
    """Point the OptimizePress opt-in forms at FormSubmit instead of Infusionsoft."""
    def convert(m):
        form = m.group(0)
        name = re.search(r'name="inf_form_name" value="([^"]*)"', form)
        subject = 'Media Reactions contact request' + (' (%s)' % name.group(1) if name else '')
        hidden = ('<div style="display:none">'
                  '<input type="hidden" name="_subject" value="%s">'
                  '<input type="hidden" name="_next" value="%s/drtv/thank-you/">'
                  '<input type="hidden" name="_captcha" value="false">'
                  '<input type="hidden" name="_template" value="table">'
                  '<input type="text" name="_honey" tabindex="-1" autocomplete="off">'
                  '</div>') % (esc(subject), SITE_URL)
        form = re.sub(r'<div style="display:none"><input type="hidden" name="inf_form_xid".*?</div>',
                      lambda _: hidden, form, count=1, flags=re.S)
        form = re.sub(r'action="https://[^"]*infusionsoft[^"]*"', 'action="%s"' % FORM_ENDPOINT, form)
        for old, new in FORM_FIELDS.items():
            form = form.replace('name="%s"' % old, 'name="%s"' % new)
        return form
    return re.sub(r'<form\b[^>]*infusionsoft[^>]*>.*?</form>', convert, s, flags=re.S)


# --------------------------------------------------------------------------
# Page shell: the same maroon banner, menu and footer on every page
# --------------------------------------------------------------------------

def nav_html(current):
    items = []
    for n in SITE['nav']:
        cur = ' class="current-menu-item"' if n['href'] == current else ''
        items.append('<li%s><a href="%s">%s</a></li>' % (cur, esc(n['href']), esc(n['label'])))
    return ''.join(items)


def document(title, path, body, description='', noindex=False):
    full = (SITE['title'] + ' – ' + SITE['description']) if path == '/' else '%s – %s' % (title, SITE['title'])
    return '\n'.join([
        '<!doctype html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>%s</title>' % esc(full),
        '<meta name="description" content="%s">' % esc(description or SITE['description']),
        '<meta name="robots" content="noindex,follow">' if noindex else '',
        '<link rel="canonical" href="%s%s">' % (SITE_URL, esc(path)),
        '<link href="https://fonts.googleapis.com/css?family=Roboto:300,400,500,700,900" rel="stylesheet">',
        '<link rel="stylesheet" href="%slib/assets/default.min.css">' % OP,
        '<link rel="stylesheet" href="%spages/marketing/1/style.min.css">' % OP,
        '<link rel="stylesheet" href="/assets/site.css?v=%s">' % CSS_VERSION,
        '</head>',
        '<body class="op-plugin">',
        '<a class="skip" href="#content_area">Skip to content</a>',
        '<div class="container main-content">',
        '<div class="banner include-nav" style="background-color:%s">' % BRAND,
        '<div class="fixed-width cf">',
        '<div class="eight columns"><div class="op-logo"><a href="/" title="%s" rel="home">'
        '<img src="%s" alt="%s"></a></div></div>' % (esc(SITE['title']), LOGO, esc(SITE['title'])),
        '<div class="sixteen columns"><nav class="navigation fly-to-left" aria-label="Primary">'
        '<ul id="navigation-alongside">%s</ul></nav></div>' % nav_html(path),
        '</div></div>',
        body,
        '<div class="full-width footer small-footer-text"><div class="row"><div class="fixed-width">'
        '<p class="footer-copyright">Copyright 2017 - Media Reactions - All Rights Reserved</p>'
        '</div></div></div>',
        '</div>',
        '<script src="/assets/site.js?v=%s"></script>' % CSS_VERSION,
        '</body></html>',
    ])


def main():
    pages, op_pages = load('pages'), load('op')
    out = {}

    def add(path, content):
        if path in out:
            raise SystemExit('URL collision: %s' % path)
        out[path] = content

    for p in op_pages:
        add(p['path'], document(p['title'], p['path'], email_forms(p['raw']),
                                noindex=(p['slug'] == 'thank-you')))

    for p in pages:
        body = ('<div id="content_area" class="plain"><div class="fixed-width"><article>'
                '<h1>%s</h1><div class="prose">%s</div></article></div></div>' % (
                    esc(p['title']), render_body(p['raw'])))
        add(p['path'], document(p['title'], p['path'], body, noindex=(p['slug'] == 'home')))

    body = ('<div id="content_area" class="plain"><div class="fixed-width"><article><h1>Page not found</h1>'
            '<div class="prose"><p>That page doesn’t exist here. Try the <a href="/">home page</a> '
            'or one of the links in the menu above.</p></div></article></div></div>')
    out['/404.html'] = document('Page not found', '/404.html', body, noindex=True)

    urls = ''.join('<url><loc>%s%s</loc></url>' % (SITE_URL, esc(p)) for p in sorted(out)
                   if p.endswith('/') and p not in ('/home/', '/drtv/thank-you/'))
    out['/sitemap.xml'] = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls)
    out['/robots.txt'] = 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE_URL

    out['/_headers'] = '\n'.join([
        '/*',
        '  X-Content-Type-Options: nosniff',
        '  Referrer-Policy: strict-origin-when-cross-origin',
        '  X-Frame-Options: SAMEORIGIN',
        '',
        '/wp-content/*',
        '  Cache-Control: public, max-age=31536000',
        '',
        '# Keep the temporary pages.dev addresses (previews) out of search engines',
        'https://:project.pages.dev/*',
        '  X-Robots-Tag: noindex',
        'https://:version.:project.pages.dev/*',
        '  X-Robots-Tag: noindex',
        '',
    ])
    out['/_redirects'] = '\n'.join([
        '# Old WordPress addresses that now point at the home page',
        '/agency / 301',
        '/agency/ / 301',
        '/drtv /drtv/charity/ 301',
        '/drtv/ /drtv/charity/ 301',
        '/drtv/agency / 301',
        '/drtv/agency/ / 301',
        '/feed / 301',
        '/feed/ / 301',
        '',
    ])

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    for path, content in out.items():
        target = OUT / path.lstrip('/') / 'index.html' if path.endswith('/') else OUT / path.lstrip('/')
        if target.exists():
            raise SystemExit('Refusing to overwrite a static file: %s' % path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    n_files = sum(1 for _ in OUT.rglob('*') if _.is_file())
    print('built %d pages; %d files in public/' % (len(out), n_files))


if __name__ == '__main__':
    sys.exit(main())
