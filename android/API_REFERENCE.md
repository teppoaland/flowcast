# FlowCast Android — API Reference

Täydellinen API-dokumentaatio Android-sovelluksen ja FlowCast-palvelimen väliseen kommunikaatioon.

---

## Yhteenveto

| Metodi | Pääte | Kuvaus |
|--------|-------|--------|
| `GET` | `/api/android/ping` | Yhteyden testaus |
| `GET` | `/api/android/folders` | Kansiolistaus |
| `GET` | `/api/android/list` | Tiedostolistaus |
| `POST` | `/api/android/upload` | Tiedostojen lataus |
| `POST` | `/api/android/delete-file` | Tiedoston poisto |
| `POST` | `/api/android/create-folder` | Kansion luonti |
| `GET` | `/media_android/<path>` | Tiedoston tarjoilu |

Palvelimen URL: `http://<tailscale-ip>:5010`

---

## 1. `GET /api/android/ping`

Kevyt health-check endpoint. Palauttaa myös palvelimen IP:n ja portin.

### Pyyntö

```http
GET /api/android/ping HTTP/1.1
Host: 100.123.45.67:5010
```

### Vastaus — 200 OK

```json
{
  "ok": true,
  "server_ip": "192.168.1.100",
  "port": 5010
}
```

### Sovelluksen käyttö

```python
async with httpx.AsyncClient(timeout=5) as client:
    resp = await client.get(f"{base_url}/api/android/ping")
    if resp.status_code == 200 and resp.json().get("ok"):
        print("Yhteys OK")
```

### Virhetilanteet

| Status | Syy |
|--------|-----|
| Yhteysvirhe | Palvelin ei käynnissä, Tailscale ei päällä, väärä IP |
| Timeout | Verkko-ongelma |

---

## 2. `GET /api/android/folders`

Palauttaa kaikki alikansiot `android_upload\` -hakemistossa.

### Pyyntö

```http
GET /api/android/folders HTTP/1.1
Host: 100.123.45.67:5010
```

### Vastaus — 200 OK

```json
{
  "folders": [
    "kuvat",
    "videot",
    "lomakuvat-2025"
  ],
  "root": "D:\\MediaPlayer\\android_upload"
}
```

- `folders` — Alikansioiden nimet suhteellisina polkuina
- `root` — Hakemiston absoluuttinen polku palvelimella

### Sovelluksen käyttö

```python
# Kansion valintaan
async with httpx.AsyncClient(timeout=10) as client:
    resp = await client.get(f"{base_url}/api/android/folders")
    data = resp.json()
    for folder in data["folders"]:
        print(f"📁 {folder}")
```

---

## 3. `GET /api/android/list`

Palauttaa kaikki mediatiedostot android_upload-hakemistossa ja sen alikansioissa.

### Pyyntö

```http
GET /api/android/list HTTP/1.1
Host: 100.123.45.67:5010
Cache-Control: no-store
```

### Vastaus — 200 OK

```json
[
  {
    "filename": "IMG_001.jpg",
    "src": "/media_android/IMG_001.jpg",
    "type": "image",
    "name": "IMG_001.jpg",
    "size": 2456789
  },
  {
    "filename": "kuvat/IMG_002.jpg",
    "src": "/media_android/kuvat/IMG_002.jpg",
    "type": "image",
    "name": "kuvat/IMG_002.jpg",
    "size": 3124567
  },
  {
    "filename": "videot/VID_001.mp4",
    "src": "/media_android/videot/VID_001.mp4",
    "type": "video",
    "name": "videot/VID_001.mp4",
    "size": 52456789,
    "duration": 45.5
  }
]
```

### Kentät

| Kenttä | Tyyppi | Kuvaus |
|--------|--------|--------|
| `filename` | string | Tiedoston suhteellinen polku android_uploadista |
| `src` | string | URL-polku tiedoston tarjoiluun (`/media_android/...`) |
| `type` | string | `"image"` tai `"video"` |
| `name` | string | Näyttönimi (sama kuin filename) |
| `size` | integer | Tiedoston koko tavuina |
| `duration` | float | Videon kesto sekunteina (vain videoille) |

### Suodatus

Vain seuraavat tiedostopäätteet sisällytetään:
- Kuvat: `.jpg`, `.jpeg`, `.png`
- Videot: `.mp4`

### Sovelluksen käyttö

```python
async with httpx.AsyncClient(timeout=10) as client:
    resp = await client.get(f"{base_url}/api/android/list")
    files = resp.json()

    # Ryhmittele kansioittain
    groups = {}
    roots = []
    for f in files:
        name = f["filename"]
        if "/" in name:
            folder = name.split("/")[0]
            groups.setdefault(folder, []).append(f)
        else:
            roots.append(f)
```

---

## 4. `POST /api/android/upload`

Vastaanottaa yhden tai useamman tiedoston Android-sovellukselta.

### Pyyntö

```http
POST /api/android/upload HTTP/1.1
Host: 100.123.45.67:5010
Content-Type: multipart/form-data; boundary=----Boundary
Content-Length: 5245678

------Boundary
Content-Disposition: form-data; name="folder"

kuvat
------Boundary
Content-Disposition: form-data; name="delete_after"

true
------Boundary
Content-Disposition: form-data; name="files"; filename="IMG_001.jpg"
Content-Type: application/octet-stream

[binary data]
------Boundary--
```

### Parametrit

| Kenttä | Tyyppi | Pakollinen | Oletus | Kuvaus |
|--------|--------|-----------|--------|--------|
| `files` | file(s) | ✅ Kyllä | — | Yksi tai useampi tiedosto |
| `folder` | string | ❌ Ei | `""` (juuri) | Kohdekansio android_uploadin alla |
| `delete_after` | string | ❌ Ei | `"false"` | `"true"` jos paikallinen tiedosto poistetaan |

### Tuetut tiedostomuodot

| Pääte | Tyyppi | Käsittely |
|-------|--------|----------|
| `.jpg`, `.jpeg`, `.png` | Kuva | Tallennetaan suoraan |
| `.mp4` | Video | Tallennetaan suoraan |
| `.avi`, `.wmv`, `.mov`, `.mkv` | Video | Konvertoidaan MP4:ksi FFmpegillä |

### Kansion nimen validointi

Kansion nimestä poistetaan kaikki muut paitsi:
- Kirjaimet (a-z, A-Z, ä, ö, å)
- Numerot (0-9)
- Välilyönnit
- Viivat, alleviivaukset, pisteet, sulut

Maksimipituus: 100 merkkiä.

### Vastaus — 200 OK

```json
{
  "saved": 3,
  "skipped": 1,
  "errors": [
    "corrupt_file.avi: Konversio epaonnistui"
  ],
  "folder": "kuvat",
  "delete_requested": true
}
```

### Kentät

| Kenttä | Tyyppi | Kuvaus |
|--------|--------|--------|
| `saved` | integer | Onnistuneesti tallennettujen tiedostojen määrä |
| `skipped` | integer | Ohitettujen duplikaattien määrä |
| `errors` | string[] | Virheilmoitukset epäonnistuneille tiedostoille |
| `folder` | string | Kohdekansio (tyhjä = juuri) |
| `delete_requested` | boolean | Tosi jos sovellus pyysi paikallista poistoa |

### Virhevastaus — 400 Bad Request

```json
{
  "error": "Ei tiedostoja"
}
```

```json
{
  "error": "Kansion nimi ei kelpaa"
}
```

### Sovelluksen käyttö

```python
async with httpx.AsyncClient(timeout=180) as client:
    with open(filepath, "rb") as f:
        files = {"files": (filename, f, "application/octet-stream")}
        data = {"folder": "kuvat", "delete_after": "true"}
        resp = await client.post(
            f"{base_url}/api/android/upload",
            files=files,
            data=data
        )

    result = resp.json()
    if result["saved"] > 0:
        print(f"Ladattu {result['saved']} tiedostoa")
    if result["skipped"] > 0:
        print(f"Ohitettu {result['skipped']} duplikaattia")
    for err in result["errors"]:
        print(f"Virhe: {err}")
```

### Duplikaattien käsittely

- Tiedosto ohitetaan (`skipped`++) jos samanniminen tiedosto on jo kohdekansiossa
- Vertailu tehdään pelkän tiedostonimen perusteella
- Konvertoiduille videoille vertaillaan `.mp4`-päätteistä nimeä

---

## 5. `POST /api/android/delete-file`

Poistaa yksittäisen tiedoston android_upload-hakemistosta.

### Pyyntö

```http
POST /api/android/delete-file HTTP/1.1
Host: 100.123.45.67:5010
Content-Type: application/json

{
  "filename": "kuvat/IMG_001.jpg"
}
```

### Vastaus — 200 OK

```json
{
  "ok": true
}
```

### Virhevastaukset

| Status | Vastaus | Syy |
|--------|---------|-----|
| 400 | `{"error": "Tiedostonimi puuttuu"}` | Tyhjä filename |
| 400 | `{"error": "Virheellinen tiedostonimi"}` | Sisältää `..` tai `/` alussa |
| 404 | `{"error": "Tiedostoa ei loydy"}` | Tiedostoa ei ole |

### Tietoturva

- `..` estetty — directory traversal -hyökkäys torjuttu
- `/` alussa estetty — absoluuttiset polut estetty
- `resolve().relative_to()` — Varmistetaan, että polku on android_uploadin sisällä

### Sovelluksen käyttö

```python
async with httpx.AsyncClient(timeout=10) as client:
    resp = await client.post(
        f"{base_url}/api/android/delete-file",
        json={"filename": "kuvat/old_photo.jpg"}
    )
    if resp.status_code == 200:
        print("Poistettu")
```

---

## 6. `POST /api/android/create-folder`

Luo uuden alikansion android_upload-hakemiston alle.

### Pyyntö

```http
POST /api/android/create-folder HTTP/1.1
Host: 100.123.45.67:5010
Content-Type: application/json

{
  "folder": "uudet-kuvat"
}
```

### Validointi

Samat säännöt kuin uploadin kansion nimelle:
- Sallitut merkit: `a-zA-Z0-9äöåÄÖÅ\s\-_.()`
- Maksimipituus: 100 merkkiä

### Vastaus — 200 OK

```json
{
  "ok": true,
  "folder": "uudet-kuvat"
}
```

### Virhevastaukset

| Status | Vastaus | Syy |
|--------|---------|-----|
| 400 | `{"error": "Kansion nimi puuttuu"}` | Tyhjä nimi |
| 400 | `{"error": "Kansion nimi ei kelpaa"}` | Virheelliset merkit |
| 400 | `{"error": "Kansio on jo olemassa"}` | Duplikaatti |

---

## 7. `GET /media_android/<path:filename>`

Tarjoilee ladatun tiedoston suoraan levyltä.

### Pyyntö

```http
GET /media_android/kuvat/IMG_001.jpg HTTP/1.1
Host: 100.123.45.67:5010
```

### Vastaus — 200 OK

```
Content-Type: image/jpeg
Content-Length: 2456789

[binary data]
```

### Käyttö

Tätä endpointia käytetään lähinnä palvelimen tiedostonhallinnassa tiedostojen esikatseluun. Android-sovellus ei tällä hetkellä lataa tiedostoja takaisin puhelimeen.

---

## Virhekoodit

| Koodi | Kuvaus |
|-------|--------|
| 200 | OK — Pyyntö onnistui |
| 400 | Bad Request — Puuttuvat tai virheelliset parametrit |
| 404 | Not Found — Tiedostoa tai kansiota ei löydy |
| 500 | Internal Server Error — Palvelinvirhe (esim. FFmpeg ei asennettu) |

---

## Aikakatkaisut

| Operaatio | Timeout | Syy |
|-----------|---------|-----|
| Ping | 5 s | Nopea tarkistus |
| Listaus | 10 s | Voi olla paljon tiedostoja |
| Upload (per tiedosto) | 180 s | Suuret videotiedostot |
| Delete | 10 s | Nopea operaatio |
| Create folder | 10 s | Nopea operaatio |

---

## Esimerkkisovellus (curl)

### Windows (cmd.exe)

```batch
REM Testaa yhteys
curl http://100.123.45.67:5010/api/android/ping

REM Listaa kansiot
curl http://100.123.45.67:5010/api/android/folders

REM Listaa tiedostot
curl http://100.123.45.67:5010/api/android/list

REM Luo kansio
curl -X POST http://100.123.45.67:5010/api/android/create-folder ^
  -H "Content-Type: application/json" ^
  -d "{\"folder\":\"testi\"}"

REM Lataa tiedosto
curl -X POST http://100.123.45.67:5010/api/android/upload ^
  -F "files=@C:\kuva.jpg" ^
  -F "folder=testi"

REM Poista tiedosto
curl -X POST http://100.123.45.67:5010/api/android/delete-file ^
  -H "Content-Type: application/json" ^
  -d "{\"filename\":\"testi/kuva.jpg\"}"
```

### Linux/macOS (bash)

```bash
# Testaa yhteys
curl http://100.123.45.67:5010/api/android/ping

# Listaa kansiot
curl http://100.123.45.67:5010/api/android/folders

# Listaa tiedostot
curl http://100.123.45.67:5010/api/android/list

# Luo kansio
curl -X POST http://100.123.45.67:5010/api/android/create-folder \
  -H "Content-Type: application/json" \
  -d '{"folder":"testi"}'

# Lataa tiedosto
curl -X POST http://100.123.45.67:5010/api/android/upload \
  -F "files=@/path/to/photo.jpg" \
  -F "folder=testi"

# Poista tiedosto
curl -X POST http://100.123.45.67:5010/api/android/delete-file \
  -H "Content-Type: application/json" \
  -d '{"filename":"testi/photo.jpg"}'
```
