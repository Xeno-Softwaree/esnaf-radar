"""Google Maps sayfalarindan isletme bilgisi cikarma + puanlama + mesaj taslagi."""
import re
import urllib.parse

BOOKING_HINTS = ("booksy", "fresha", "planity", "randevu", "setmore", "calendly", "simplybook", "treatwell", "kolayrandevu")


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def first(sel, query, attr=None):
    found = sel.css(query)
    if not found:
        return ""
    el = found[0]
    if attr:
        return clean(el.attrib.get(attr, ""))
    return clean(el.get_all_text() if hasattr(el, "get_all_text") else el.text)


def parse_results(page):
    """Arama sonuc listesinden (isim, link) ciftleri."""
    out, seen = [], set()
    for a in page.css("a.hfpxzc"):
        href = a.attrib.get("href", "")
        name = clean(a.attrib.get("aria-label", ""))
        if not href or "/maps/place/" not in href:
            continue
        key = place_key(href)
        if key in seen:
            continue
        seen.add(key)
        out.append({"isim": name, "maps": href.split("?")[0] if "!" not in href else href, "key": key})
    return out


def place_key(href):
    m = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", href)
    if m:
        return m.group(1)
    m = re.search(r"/maps/place/([^/]+)", href)
    return urllib.parse.unquote(m.group(1)) if m else href


def parse_place(page, html=""):
    """Isletme detay sayfasi."""
    html = html or str(getattr(page, "html_content", "") or "")
    d = {}
    d["isim"] = first(page, "h1.DUwDvf") or first(page, "h1")
    d["kategori"] = first(page, "button.DkEaL")
    adres = first(page, 'button[data-item-id="address"]', "aria-label")
    d["adres"] = re.sub(r"^Adres:\s*", "", adres)
    tel = ""
    for b in page.css('button[data-item-id^="phone:tel:"]'):
        tel = b.attrib.get("data-item-id", "").replace("phone:tel:", "")
        break
    if not tel:
        m = re.search(r'data-item-id="phone:tel:([+\d]+)"', html)
        tel = m.group(1) if m else ""
    d["telefon"] = normalize_phone(tel)
    d["web"] = first(page, 'a[data-item-id="authority"]', "href")
    # puan + yorum
    puan = first(page, 'div.F7nice span[aria-hidden="true"]')
    d["puan"] = to_float(puan)
    yorum = ""
    for s in page.css("div.F7nice span[aria-label]"):
        lab = s.attrib.get("aria-label", "")
        if "yorum" in lab.lower() or "review" in lab.lower():
            yorum = lab
            break
    if not yorum:
        m = re.search(r"\(([\d.,]+)\)", first(page, "div.F7nice"))
        yorum = m.group(1) if m else ""
    d["yorum"] = to_int(yorum)
    return d


def to_float(s):
    m = re.search(r"\d+[.,]\d+|\d+", s or "")
    return float(m.group(0).replace(",", ".")) if m else 0.0


def to_int(s):
    digits = re.sub(r"[^\d]", "", s or "")
    return int(digits) if digits else 0


def normalize_phone(raw):
    """+90 5XX XXX XX XX -> 905XXXXXXXXX. Turkiye disi/bos -> ''."""
    d = re.sub(r"\D", "", raw or "")
    if d.startswith("0090"):
        d = d[2:]
    if d.startswith("0") and len(d) == 11:
        d = "90" + d[1:]
    if len(d) == 10 and d[0] in "2345":
        d = "90" + d
    return d if d.startswith("90") and len(d) == 12 else ""


def is_mobile(phone):
    return phone.startswith("905")


def score(d):
    """Yuksek puan = sicak musteri. Nedenleri de doner."""
    s, why = 0, []
    web = (d.get("web") or "").lower()
    if is_mobile(d.get("telefon", "")):
        s += 3; why.append("cep no (WhatsApp)")
    elif d.get("telefon"):
        why.append("sabit hat")
    else:
        s -= 5; why.append("telefon yok")
    if any(h in web for h in BOOKING_HINTS):
        s -= 3; why.append("zaten randevu sistemi var")
    elif not web:
        s += 3; why.append("web sitesi yok")
    elif "instagram.com" in web or "facebook.com" in web:
        s += 2; why.append("sadece sosyal medya")
    if d.get("yorum", 0) >= 100:
        s += 3; why.append("100+ yorum")
    elif d.get("yorum", 0) >= 30:
        s += 2; why.append("30+ yorum")
    if d.get("puan", 0) >= 4.5:
        s += 1
    return s, ", ".join(why)


def short_name(name):
    """'Aleyna Beauty 🫶 Tuzla | Cilt Bakimi - Lazer' -> 'Aleyna Beauty'"""
    n = re.split(r"\s[|\-–(]\s?|\s\(|\||,", name or "")[0]
    n = re.sub(r"[^\w\s&'.]", "", n)
    n = re.sub(r"\b(Tuzla|Pendik|Kartal|İstanbul|Istanbul)\b", "", n, flags=re.I)
    words = clean(n).split()
    stop = {"güzellik", "merkezi", "salonu", "lazer", "epilasyon", "cilt", "bakımı"}
    out = []
    for w in words:
        if len(out) >= 2 and w.lower() in stop:
            break
        out.append(w)
        if len(out) == 4:
            break
    return " ".join(out) or clean(name)[:30]


def message(d, sender):
    isim = short_name(d.get("isim")) or "merhaba"
    yorum = d.get("yorum", 0)
    ovgu = f"Google'daki {yorum} yorumunuzu gördüm, tebrikler. " if yorum >= 20 else ""
    return (
        f"Merhaba {isim}, ben {sender}. {ovgu}"
        "Mesai dışında WhatsApp'a yazan müşterilerinize otomatik cevap verip randevu alan "
        "bir asistan kuruyorum. 1 dakikalık demo videosunu göndereyim mi? "
        "Mesaj almak istemezseniz HAYIR yazın, bir daha yazmam. "
        "(AjenVIO · ajenvio.com/ticari-ileti)"
    )


def wa_link(phone, text):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(text)}" if is_mobile(phone) else ""
