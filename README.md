# Esnaf Radar

Google Maps'ten güzellik merkezi / salon listesi toplar, sıcak müşterileri puanlar ve her biri için hazır WhatsApp mesaj linki üretir. Her gece 23:00'te GitHub Actions'ta kendi kendine çalışır, senin bilgisayarında hiçbir şey çalışmaz.

## Sonuçlar
- **`data/LEADS.md`**: telefondan aç, satırdaki **WhatsApp** linkine dokun, mesaj hazır açılır, gönder.
- `data/leads.csv`: tüm liste (Excel/Sheets ile açılır).

## Puanlama
| Durum | Puan |
|---|---:|
| Cep numarası (WhatsApp'a yazılabilir) | +3 |
| Web sitesi yok | +3 |
| Sadece Instagram/Facebook | +2 |
| 100+ yorum / 30+ yorum | +3 / +2 |
| Puan 4.5+ | +1 |
| Zaten randevu sistemi var (Booksy, Fresha vb.) | -3 |
| Telefon yok | -5 |

`LEADS.md` dosyasında sadece skoru 5 ve üzeri olan, cep numaralı işletmeler var.

## Ayarlar
- **Aramalar:** `queries.txt` (her satır bir arama).
- **Elle çalıştırma:** Actions → Esnaf Radar → Run workflow (istersen tek arama yaz).
- **HAYIR diyenler:** numarayı `hayir.txt`'ye bir satır olarak ekle, bir daha listeye girmez.
- Repo Settings → Variables: `SENDER` (mesajdaki isim), `MAX_PER_QUERY` (arama başına en fazla sonuç, varsayılan 40).

## Kurallar (ban ve şikâyet yememek için)
- Günde 20-30 mesaj, aralarında 1-2 dakika. Toplu gönderim yapma.
- Ayrı bir numara kullan.
- İlk mesajda link yok, cevap gelirse demo videosunu at.
- Esnafa onaysız ticari ileti atılabilir ama HAYIR diyene bir daha yazılmaz (6563 sayılı kanun).
