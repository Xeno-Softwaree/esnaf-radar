"""Esnaf Radar: Google Maps'ten isletme listesi toplar, data/ altina yazar.

Kullanim:  python -m radar.run            (queries.txt'deki tum aramalar)
           python -m radar.run "kuaför Tuzla"   (tek arama)
"""
import csv
import datetime as dt
import os
import random
import sys
import time
import urllib.parse
from pathlib import Path

from scrapling.fetchers import StealthySession

from radar import parse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "leads.csv"
MD_PATH = DATA / "LEADS.md"
BLOCK_PATH = ROOT / "hayir.txt"  # HAYIR diyen / istemeyen numaralar
SENDER = os.environ.get("SENDER", "Mami (OrwexAI)")
MAX_PER_QUERY = int(os.environ.get("MAX_PER_QUERY", "40"))
FIELDS = ["skor", "isim", "kategori", "telefon", "web", "puan", "yorum", "adres", "neden",
          "arama", "ilk_gorulme", "maps", "whatsapp", "mesaj", "key"]


def log(*a):
    print(*a, flush=True)


def accept_consent(page):
    for label in ("Tümünü kabul et", "Accept all", "Tümünü reddet", "Reject all"):
        try:
            btn = page.get_by_role("button", name=label)
            if btn.count():
                btn.first.click(timeout=3000)
                page.wait_for_timeout(1500)
                return
        except Exception:
            pass


def scroll_feed(page):
    accept_consent(page)
    try:
        page.wait_for_selector('div[role="feed"]', timeout=15000)
    except Exception:
        return page  # tek sonuc direkt yer sayfasi acilmis olabilir
    last = 0
    for _ in range(25):
        page.evaluate("""() => {const f=document.querySelector('div[role="feed"]'); if(f) f.scrollBy(0, 2500);}""")
        page.wait_for_timeout(random.randint(1200, 2000))
        n = page.locator("a.hfpxzc").count()
        ended = page.locator("text=Listenin sonuna ulaştınız").count() or page.locator("text=reached the end").count()
        if n >= MAX_PER_QUERY or ended or n == last:
            break
        last = n
    return page


def place_ready(page):
    accept_consent(page)
    try:
        page.wait_for_selector("h1", timeout=12000)
        page.wait_for_timeout(800)
    except Exception:
        pass
    return page


def load_existing():
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(encoding="utf-8-sig") as f:
        return {r["key"]: r for r in csv.DictReader(f) if r.get("key")}


def load_blocked():
    if not BLOCK_PATH.exists():
        return set()
    return {parse.normalize_phone(l) for l in BLOCK_PATH.read_text(encoding="utf-8").splitlines() if l.strip()}


def build_row(d, query, today):
    s, why = parse.score(d)
    msg = parse.message(d, SENDER)
    return {**{k: d.get(k, "") for k in ("isim", "kategori", "telefon", "web", "puan", "yorum", "adres", "maps", "key")},
            "puan": d.get("puan", ""), "yorum": d.get("yorum", ""),
            "skor": s, "neden": why, "arama": query, "ilk_gorulme": today,
            "whatsapp": parse.wa_link(d.get("telefon", ""), msg), "mesaj": msg}


def write_outputs(rows, today):
    DATA.mkdir(exist_ok=True)
    rows = sorted(rows, key=lambda r: (-int(r["skor"]), r["isim"]))
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    hot = [r for r in rows if int(r["skor"]) >= 5 and r["whatsapp"]]
    new = [r for r in hot if r["ilk_gorulme"] == today]
    lines = [f"# Esnaf Radar — {today}", "",
             f"Toplam {len(rows)} işletme · sıcak (skor 5+, WhatsApp'lı) {len(hot)} · bugün yeni {len(new)}", "",
             "Linke dokun, WhatsApp mesaj hazır açılır. Günde 20-30 tane, aralıklı gönder. HAYIR diyeni `hayir.txt`'ye ekle.", "",
             "| Skor | İşletme | Yorum | Neden | Yaz |", "|---:|---|---:|---|---|"]
    for r in hot:
        tag = " 🆕" if r["ilk_gorulme"] == today else ""
        name = parse.short_name(r["isim"]).replace("|", "/")
        lines.append(f"| {r['skor']} | [{name}]({r['maps']}){tag} | {r['yorum']} | {r['neden']} | [WhatsApp]({r['whatsapp']}) |")
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Yazildi: {len(rows)} satir, {len(hot)} sicak, {len(new)} yeni")


def main():
    today = dt.date.today().isoformat()
    queries = sys.argv[1:] or [q.strip() for q in (ROOT / "queries.txt").read_text(encoding="utf-8").splitlines()
                               if q.strip() and not q.startswith("#")]
    existing = load_existing()
    blocked = load_blocked()
    found = dict(existing)
    with StealthySession(headless=True, locale="tr-TR", timezone_id="Europe/Istanbul", timeout=45000) as s:
        for q in queries:
            url = "https://www.google.com/maps/search/" + urllib.parse.quote(q) + "?hl=tr"
            log(f"\n== {q}")
            try:
                page = s.fetch(url, page_action=scroll_feed)
            except Exception as e:
                log("  arama hatasi:", e)
                continue
            results = parse.parse_results(page)[:MAX_PER_QUERY]
            log(f"  {len(results)} sonuc")
            for r in results:
                if r["key"] in found:
                    continue
                time.sleep(random.uniform(1.5, 3.5))
                try:
                    p = s.fetch(r["maps"], page_action=place_ready)
                    d = parse.parse_place(p)
                except Exception as e:
                    log("  detay hatasi:", r["isim"], e)
                    continue
                d["isim"] = d["isim"] or r["isim"]
                d["maps"] = r["maps"]
                d["key"] = r["key"]
                if d["telefon"] and d["telefon"] in blocked:
                    continue
                row = build_row(d, q, today)
                found[r["key"]] = row
                log(f"  + {row['skor']:>3} {row['isim']} {row['telefon']} ({row['neden']})")
    rows = []
    for r in found.values():
        if r.get("telefon") and r["telefon"] in blocked:
            continue
        d = {**r, "yorum": parse.to_int(str(r.get("yorum", ""))), "puan": parse.to_float(str(r.get("puan", "")))}
        rows.append({**r, **build_row(d, r.get("arama", ""), r.get("ilk_gorulme") or today)})
    write_outputs(rows, today)


if __name__ == "__main__":
    main()
