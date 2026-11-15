"""Render a private, meal-grouped cart PDF from a verified retailer snapshot."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen
from xml.sax.saxutils import escape

from PIL import Image, ImageChops, PngImagePlugin
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as Photo, Paragraph, SimpleDocTemplate, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'src'))
from shopping_agent.private import PROFILE, private_dir

GREEN = '#174937'
INK = '#172C26'
MUTED = '#475C52'
PALE = '#F0F4EE'
MARGIN = 24
WIDTH = A4[0] - 2 * MARGIN
GENERAL = 'General'


def cents(value):
    amount = Decimal(str(value)) * 100
    if not amount.is_finite() or amount != amount.to_integral_value():
        raise ValueError(f'Expected a cent-exact CAD value, got {value}')
    return int(amount)


def money(value):
    return f"${Decimal(value) / 100:,.2f}"


def allocate(item, line_cents):
    """Conserve both purchased quantity and price, breaking penny ties in input order."""
    if 'shares' not in item:
        return [(item['group'], item['amount'], line_cents)]
    if 'group' in item:
        raise ValueError(f"Choose one allocation method for {item['name']}")
    shares = {group: Fraction(str(q)) for group, q in item['shares'].items()}
    total = Fraction(str(item['total_amount']))
    if not shares or min(shares.values()) <= 0 or sum(shares.values()) != total:
        raise ValueError(f"Shares must account for the entire purchase of {item['name']}")
    exact = {group: abs(line_cents) * q / total for group, q in shares.items()}
    amounts = {group: int(value) for group, value in exact.items()}
    pennies = abs(line_cents) - sum(amounts.values())
    for group in sorted(shares, key=lambda g: exact[g] - amounts[g], reverse=True)[:pennies]:
        amounts[group] += 1
    sign = -1 if line_cents < 0 else 1
    purchase = ' '.join(item['amount'].splitlines())
    return [(g, f"{item['shares'][g]} {item['unit']}\nfrom {purchase}", sign * amounts[g])
            for g in shares]


def read_cart(path):
    data = json.loads(path.read_text())
    if 'content' in data:
        if data.get('isError'):
            raise ValueError('Supply a successful cart readback')
        data = data.get('structuredContent') or json.loads(data['content'][0]['text'])
    orders = data['orders']
    entries = [entry for order in orders for entry in order['entries'] if entry['quantity'] > 0]
    totals = orders[0]['totals'] if len(orders) == 1 else data['orderAggregations']['open']['totals']
    by_code = {e['offer']['id']: e for e in entries}
    if len(by_code) != len(entries):
        raise ValueError('Multiple cart lines have the same code. Reconcile them before export.')
    return by_code, totals


def thumbnail(data, source_hash):
    with Image.open(BytesIO(data)) as original:
        rgba = original.convert('RGBA')
        white = Image.new('RGB', rgba.size, 'white')
        white.paste(rgba, mask=rgba.getchannel('A'))
    mask = ImageChops.difference(white, Image.new('RGB', white.size, 'white')).convert('L')
    box = mask.point(lambda pixel: 255 if pixel > 20 else 0).getbbox()
    if not box:
        raise ValueError('Product photo is blank')
    thumb = white.crop(box)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('source', source_hash)
    stream = BytesIO()
    thumb.save(stream, format='PNG', pnginfo=metadata)
    return stream.getvalue()


def cached_photo(entry, local_path, cache, refresh):
    offer = entry['offer']
    key = sha256(offer['id'].encode()).hexdigest()
    target = cache / (key + '.png')
    if local_path is None:
        url = offer['product']['primaryImage']
        parts = urlsplit(url)
        if (parts.scheme, parts.hostname) != ('https', 'digital.loblaws.ca'):
            raise ValueError('Supply the exact product photo locally for this retailer URL')
        source_hash = 'url-' + sha256(url.encode()).hexdigest()
    else:
        data = local_path.read_bytes()
        source_hash = 'file-' + sha256(data).hexdigest()

    if not refresh:
        try:
            saved = target.read_bytes()
            with Image.open(BytesIO(saved)) as image:
                if image.format == 'PNG' and image.info.get('source') == source_hash:
                    image.verify()
                    return saved, True
        except (FileNotFoundError, OSError, SyntaxError, ValueError):
            pass  # Missing or damaged thumbnails are rebuilt from the verified source.
    if local_path is None:
        with urlopen(url, timeout=18) as response:
            data = response.read()
    prepared = thumbnail(data, source_hash)
    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        temporary.write_bytes(prepared)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return prepared, False


def font_names():
    family = Path('/System/Library/Fonts/Avenir Next.ttc')
    if family.exists():
        for name, index in [('CartRegular', 5), ('CartBold', 2)]:
            pdfmetrics.registerFont(TTFont(name, str(family), subfontIndex=index))
        return 'CartRegular', 'CartBold'
    return 'Helvetica', 'Helvetica-Bold'


def render(layout, entries, totals, folder, output, *, refresh_photos=False):
    regular, bold = font_names()
    def para(text, size=11, color=INK, strong=False, align=0):
        style = ParagraphStyle('cell', fontName=bold if strong else regular,
                               fontSize=size, leading=size*1.16, textColor=colors.HexColor(color),
                               alignment=align, splitLongWords=1)
        return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)

    sections = {name: [] for name in layout['groups']}
    sections.setdefault(GENERAL, [])
    if set(entries) != set(layout['items']):
        raise ValueError('The layout must include every verified cart code exactly once')
    cache = private_dir(private_dir(PROFILE / 'cache') / 'cart-pdf-photos')
    def load_photo(code):
        item = layout['items'][code]
        source = None
        if item.get('photo'):
            source = (folder / item['photo']).resolve()
            if not source.is_relative_to(folder):
                raise ValueError('Local photos must be in the private layout directory')
        return cached_photo(entries[code], source, cache, refresh_photos)

    with ThreadPoolExecutor(max_workers=4) as pool:
        photos = dict(zip(entries, pool.map(load_photo, entries)))
    group_totals = Counter()
    for code, item in layout['items'].items():
        entry = entries[code]
        if Fraction(str(item['packs'])) != Fraction(str(entry['quantity'])):
            raise ValueError(f'Cart quantity changed for {code}')
        offer = entry['offer']
        brand = offer['product'].get('brand') or 'Not listed'
        brand = {'Scale Label-Div': 'Not listed', 'Un-Branded': 'Unbranded'}.get(brand, brand)
        photo = Photo(BytesIO(photos[code][0]), width=40, height=30, kind='proportional', hAlign='CENTER')
        estimated = 'WEIGHT' in str(offer.get('sellingType', '')) or offer['product'].get('weighted')
        for group, amount, price in allocate(item, cents(entry['prices']['totalSalePrice'])):
            if group not in sections:
                raise ValueError(f'Unknown meal section {group}')
            group_totals[group] += price
            product_cell = [para(item['name'], 11.7, strong=True), para(brand, 9.5, MUTED)]
            quantity_cell = [para(line, 10.8 if i == 0 else 9.5, INK if i == 0 else MUTED)
                             for i, line in enumerate(amount.splitlines())]
            price_cell = para(money(price) + ('*' if estimated else ''), 12, strong=True, align=2)
            sections[group].append([photo, product_cell, quantity_cell, price_cell])

    adjustment = cents(layout.get('subtotal_adjustment', 0))
    subtotal = cents(totals['subTotal'])
    final = cents(totals['estimatedTotal'])
    if sum(group_totals.values()) + adjustment != subtotal:
        raise ValueError('Allocated line totals and confirmed adjustment must reconcile to the subtotal')
    rows = [['', para('ITEM / BRAND', 9, MUTED, True), para('QUANTITY', 9, MUTED, True),
             para('PRICE (CAD)', 9, MUTED, True, 2)]]
    styles = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
              ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PALE)),
              ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
              ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]
    for group, lines in sections.items():
        if not lines:
            continue
        i = len(rows)
        rows.append([para(group, 14.5, GREEN, True), '', '', para(money(group_totals[group]), 13, GREEN, True, 2)])
        styles.extend([('SPAN', (0, i), (2, i)), ('NOSPLIT', (0, i), (-1, i+1)),
                       ('TOPPADDING', (0, i), (-1, i), 7),
                       ('LINEBELOW', (0, i), (-1, i), 0.8, colors.HexColor(GREEN))])
        rows.extend(lines)
        for j in range(i+1, len(rows)):
            styles.append(('LINEBELOW', (0, j), (-1, j), 0.35, colors.HexColor('#DCE4DD')))
    footer = len(rows)
    rows.append([para('Estimated total', 16, GREEN, True), '', '',
                 para(money(final), 18, GREEN, True, 2)])
    styles.extend([('SPAN', (0, footer), (2, footer)), ('BACKGROUND', (0, footer), (-1, footer), colors.HexColor(PALE)),
                   ('TOPPADDING', (0, footer), (-1, footer), 9), ('BOTTOMPADDING', (0, footer), (-1, footer), 9)])
    tax = cents(totals.get('totalTax') or 0)
    summary = [f'Subtotal {money(subtotal)}', f'Tax {money(tax)}', f'Fees and other charges {money(final-subtotal-tax)}']
    if adjustment:
        summary.insert(0, f'Basket adjustment {money(adjustment)}')
    notes = ['   ·   '.join(summary)]
    if any('WEIGHT' in str(e['offer'].get('sellingType', '')) or e['offer']['product'].get('weighted') for e in entries.values()):
        notes.append('* Final price depends on weight.')
    if layout.get('note'):
        notes.append(layout['note'])
    rows.append([[para(note, 9, MUTED) for note in notes], '', '', ''])
    styles.extend([('SPAN', (0, -1), (-1, -1)), ('NOSPLIT', (0, footer-1), (-1, -1))])
    widths = [51, WIDTH*0.44, WIDTH*0.56-51-88, 88]
    table = Table(rows, colWidths=widths, repeatRows=1, style=TableStyle(styles))
    def header(canvas, doc):
        canvas.setFillColor(colors.HexColor(GREEN))
        canvas.rect(0, A4[1]-68, A4[0], 68, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#D7E8A8'))
        canvas.setFont(bold, 10.5)
        canvas.drawString(MARGIN+6, A4[1]-21, 'PROVIGO')
        canvas.setFillColor(colors.white)
        canvas.drawRightString(A4[0]-MARGIN-6, A4[1]-21, layout['period'].upper())
        canvas.setFont(bold, 29)
        canvas.drawString(MARGIN+6, A4[1]-55, 'Weekly grocery cart')
        canvas.setFont(regular, 8)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawRightString(A4[0]-MARGIN-6, 12, str(doc.page))
    doc = SimpleDocTemplate(str(output), pagesize=A4, title='Weekly grocery cart', author='',
                            leftMargin=MARGIN-6, rightMargin=MARGIN-6, topMargin=70, bottomMargin=19)
    doc.build([table], onFirstPage=header, onLaterPages=header)
    reused = sum(hit for _, hit in photos.values())
    print(f'Product photos: {reused} reused, {len(photos) - reused} refreshed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('layout', 'cart', 'output'):
        parser.add_argument(arg, type=Path)
    parser.add_argument('--refresh-photos', action='store_true',
                        help='Replace the cached photos used in this export, including unchanged image URLs')
    args = parser.parse_args()
    folder = args.layout.resolve().parent
    if not all(p.resolve().is_relative_to(PROFILE) for p in (args.layout, args.cart, args.output)):
        parser.error('Keep cart inputs and output under the project’s .profile directory')
    if args.output.suffix.lower() != '.pdf':
        parser.error('The output must be a PDF')
    layout = json.loads(args.layout.read_text())
    entries, totals = read_cart(args.cart)
    os.umask(0o077)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, suffix='.pdf', delete=False) as tmp:
        path = Path(tmp.name)
    try:
        render(layout, entries, totals, folder, path, refresh_photos=args.refresh_photos)
        path.replace(args.output)
    finally:
        path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
