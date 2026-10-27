# FlowCast Android — Taildrop File Manager & Uploader

Android-sovellus FlowCast-palvelimen etäkäyttöön Tailscale-verkon yli. Mahdollistaa mediatiedostojen siirron Android-puhelimesta FlowCast-palvelimelle, kohdekansion valinnan, paikallisten tiedostojen automaattisen poiston duplikaattien välttämiseksi sekä palvelimen tiedostonhallinnan.

---

## Sisällys

1. [Ominaisuudet](#ominaisuudet)
2. [Arkkitehtuuri](#arkkitehtuuri)
3. [Kansiorakenne](#kansiorakenne)
4. [Vaatimukset](#vaatimukset)
5. [Asennus](#asennus)
6. [Käyttöohje](#käyttöohje)
7. [API-referenssi](#api-referenssi)
8. [Sovelluksen rakenne](#sovelluksen-rakenne)
9. [Väriteema](#väriteema)
10. [APK:n rakennus](#apkn-rakennus)
11. [Vianmääritys](#vianmääritys)
12. [Kehitys](#kehitys)

---

## Ominaisuudet

| Ominaisuus | Kuvaus |
|-----------|--------|
| **Taildrop-pikasiirto** | Näyttää Lataukset-kansion (Taildrop) sisällön. Valitse yksittäin tai kaikki kerralla. Yhden napin lähetys palvelimelle. |
| **Tiedostoselain** | Selaa koko puhelimen tiedostojärjestelmää. Navigoi kansioissa, näkee tiedostokoot ja aikaleimat. Vain mediatiedostot näytetään. |
| **Kohdekansion valinta** | Valitse palvelimelta mihin kansioon tiedostot tallennetaan. Lista haetaan reaaliajassa palvelimelta. |
| **Poisto latauksen jälkeen** | Automaattinen paikallisen tiedoston poisto onnistuneen latauksen jälkeen. Estää duplikaatit puhelimessa. |
| **Palvelimen tiedostonhallinta** | Selaa palvelimella olevia tiedostoja kansioittain. Poista yksittäisiä tiedostoja tai kokonaisia kansioita. |
| **Kansioiden hallinta** | Luo uusia kansioita palvelimelle suoraan sovelluksesta. |
| **Moderni UI** | Tumma teema (FlowCast-yhteensopiva). 5 välilehden navigaatio. Responsiivinen mobiilikäyttöön optimoitu käyttöliittymä. |
| **Pysyvät asetukset** | Palvelimen IP, portti, kohdekansio ja muut asetukset tallentuvat laitteelle. |

---

## Arkkitehtuuri

```
┌──────────────────────────────┐          Tailscale VPN           ┌─────────────────────────────┐
│     ANDROID PUHELIN           │ ═══════════════════════════════ │     PC (FLOWCAST-SERVER)     │
│                               │         HTTP :5010              │                              │
│  ┌─────────────────────────┐  │                                 │  ┌─────────────────────────┐ │
│  │  FlowCast Android (Flet) │  │  GET  /api/android/ping        │  │  mediaplayer.py          │ │
│  │                          │──│────────────────────────────────▶│  │  Flask 3.1.3             │ │
│  │  Välilehdet:             │  │  GET  /api/android/folders     │  │  Port: 5010              │ │
│  │  0. Taildrop             │  │  GET  /api/android/list        │  └───────────┬─────────────┘ │
│  │  1. Lataa                │  │  POST /api/android/upload      │              │               │
│  │  2. Palvelin             │  │  POST /api/android/delete-file │              ▼               │
│  │  3. Tiedostot            │  │  POST /api/android/create-folder│  ┌─────────────────────────┐ │
│  │  4. Asetukset            │  │  GET  /media_android/<path>    │  │  <data-juuri>/           │ │
│  └─────────────────────────┘  │                                 │  │    android_upload/       │ │
│                               │                                 │  │    ├── kuvat/             │ │
│  Taildrop (.apk/.zip/kuvat)   │                                 │  │    ├── videot/            │ │
│       │                       │                                 │  │    ├── IMG_001.jpg       │ │
│       ▼                       │                                 │  │    └── VID_001.mp4       │ │
│  /storage/emulated/0/        │                                 │  └─────────────────────────┘ │
│    Download/                  │                                 │                              │
└──────────────────────────────┘                                 └─────────────────────────────┘
```

### Tietovuo

```
1. Käyttäjä valitsee tiedostot → Sovellus lukee tiedostopolut
2. HTTP POST → Palvelimen /api/android/upload
3. Palvelin tallentaa → android_upload/[kansio]/ (FLOWCAST_DATA_DIR)
4. Palvelin vastaa {saved, skipped, errors}
5. Sovellus näyttää tulokset
6. Jos delete_after=true → Sovellus poistaa paikallisen tiedoston
```

### Tietoturva

- **Tailscale VPN** — Kaikki liikenne kulkee salatun Tailscale-verkon yli
- **Ei autentikointia** — Sisäverkko-oletus, Tailscale hoitaa pääsynhallinnan
- **Polkuturva** — Palvelin estää directory traversal -hyökkäykset (`..`, absoluuttiset polut)
- **Tiedostotyyppirajaus** — Vain sallitut mediatiedostomuodot hyväksytään

---

## Kansiorakenne

```
<projektikansio>\
├── MediaPlayer\                     # FlowCast-palvelin
│   ├── mediaplayer.py               # Flask-backend (+ Android API)
│   ├── mediaplayer.bat              # Palvelimen käynnistys
│   ├── playlist.json                # Soittolista + asetukset
│   ├── templates\                   # HTML-template (admin, display, guest)
│   └── ...
│
├── android\                         # ANDROID-SOVELLUS
│   ├── main.py                      # Flet-sovelluksen pääkoodi
│   ├── requirements.txt             # Python-riippuvuudet (flet, httpx)
│   ├── run.bat                      # Desktop-testaus
│   ├── build_apk.bat                # APK-buildaus
│   ├── README.md                    # Tämä dokumentaatio
│   └── API_REFERENCE.md             # API-dokumentaatio
│
└── android_upload\                  # OLETUS-LATAUSKANSIO
    ├── (ladatut tiedostot)
    └── (alikansiot)
```

---

## Vaatimukset

### Palvelin (PC)

| Komponentti | Vaatimus |
|-------------|----------|
| Python | 3.11+ |
| Flask | 3.1.3 (asennettu automaattisesti) |
| Verkko | Tailscale VPN |
| Levy | android_upload\ |

### Android (puhelin)

| Komponentti | Vaatimus |
|-------------|----------|
| Android-versio | 8.0 (API 26) tai uudempi |
| Verkko | Tailscale VPN -sovellus asennettuna |
| Oikeudet | Tiedostojen luku, Internet |
| Tila | ~100 MB vapaata tilaa APK:lle |

### Kehitys (APK-buildaus)

| Komponentti | Vaatimus |
|-------------|----------|
| Python | 3.12+ |
| Flet | 0.85.1+ |
| Flutter SDK | 3.x |
| Android SDK | API 34+ |
| JDK | 17+ |

---

## Asennus

### 1. Palvelinpuolen valmistelu (PC)

Varmista, että FlowCast-palvelin on käynnissä:

```batch
cd <projektikansio>
mediaplayer.bat
```

Palvelin käynnistyy porttiin 5010. Uudet Android API -päätteet ovat automaattisesti käytettävissä.

Tarkista, että `android_upload\` on luotu:

```batch
dir android_upload
```

### 2. Tailscale-yhteyden varmistus

- PC:llä Tailscale päällä, IP esim. `100.123.45.67`
- Puhelimella Tailscale päällä, yhdistetty samaan verkkoon
- Testaa yhteys puhelimen selaimella: `http://100.123.45.67:5010/api/android/ping`
- Vastauksen pitäisi olla: `{"ok": true, "server_ip": "100.123.45.67", "port": 5010}`

### 3. Android-sovelluksen asennus

#### Vaihtoehto A: Asenna valmis APK

1. Siirrä APK puhelimeen Taildropilla
2. Avaa APK-tiedosto puhelimella
3. Salli asennus tuntemattomista lähteistä (jos kysyy)
4. Asenna ja käynnistä

#### Vaihtoehto B: Testaa desktopilla

```batch
cd <projektikansio>\android
pip install -r requirements.txt
python main.py
```

### 4. Ensiyhteys

1. Käynnistä FlowCast-sovellus
2. Siirry **Asetukset**-välilehdelle
3. Syötä FlowCast-palvelimen **Tailscale IP-osoite** (esim. `100.123.45.67`)
4. Portti on oletuksena `5010`
5. Paina **Testaa yhteys**
6. Vihreä "✅ Yhdistetty" vahvistaa yhteyden
7. Paina **Tallenna** tallentaaksesi asetukset

---

## Käyttöohje

### Taildrop-välilehti (etusivu)

Tämä on pääasiallinen työkalu Taildrop-tiedostojen siirtoon.

1. Sovellus näyttää automaattisesti **Lataukset-kansion** sisällön
2. Kansion voi vaihtaa painamalla 📁-kuvaketta
3. **Valitse tiedostot** napauttamalla (pitkä painallus mobiilissa)
4. **Valitse kaikki** — käytä "Valitse kaikki" -valintaruutua
5. Valitse **kohdekansio** palvelimelta ("Valitse..."-painike)
6. Halutessasi ota käyttöön **"Poista puhelimesta latauksen jälkeen"**
7. Paina **"Lataa valitut"** (vain valitut) tai **"Lataa KAIKKI"** (kaikki kansion tiedostot)
8. Edistymispalkki näyttää jokaisen tiedoston tilan:
   - ✅ Vihreä = onnistui
   - ⏭️ Harmaa = ohitettiin (oli jo palvelimella)
   - ❌ Punainen = epäonnistui

### Lataa-välilehti

Täysi tiedostoselain koko puhelimen tiedostojärjestelmälle.

- **Navigointi:** Nuolinäppäimet (← takaisin, 🏠 kotiin, ↻ päivitä)
- **Polkunäyttö:** Yläpalkissa näkyy nykyinen polku
- **Valinta:** Napauta tiedostoa valitaksesi sen (korostuu sinisellä)
- **Monivalinta:** Valitse useita tiedostoja peräkkäin
- **Kohdekansio:** Sama kuin Taildrop-välilehdellä (jaettu tila)
- **Lataa palvelimelle:** Painike näyttää valittujen tiedostojen määrän ja koon

### Palvelin-välilehti

Palvelimen tilan seuranta ja kansioiden hallinta.

- **Yhteyden tila:** ✅/🔌 -ilmaisin
- **Yhdistä-painike:** Testaa yhteyden manuaalisesti
- **Luo kansio:** Kirjoita nimi ja paina 📁-kuvaketta tai Enter
- **Kansiolista:** Näyttää kaikki android_upload-kansion alikansiot
- **Poista kansio:** Roskakori-kuvake poistaa kansion ja kaikki sen tiedostot

### Tiedostot-välilehti

Palvelimen tiedostonhallinta.

- **Kansiot:** Näkyvät 📁-kuvakkeella ja tiedostomäärillä
- **Tiedostot:** 🖼️ kuva / 🎬 video -kuvake, koko, poistopainike
- **Poista tiedosto:** Roskakori-kuvake → vahvistus → poisto
- **Poista kansio:** Poistaa kaikki kansion tiedostot kerralla
- **Tilastot:** Yläpalkissa näkyy tiedostojen kokonaismäärä ja koko

### Asetukset-välilehti

Pysyvät asetukset (tallentuvat laitteen muistiin).

| Asetus | Kuvaus | Oletus |
|--------|--------|--------|
| Palvelimen IP | FlowCast-palvelimen Tailscale-osoite | `192.168.1.x` |
| Portti | Palvelimen HTTP-portti | `5010` |
| Testaa yhteys | Tarkistaa yhteyden palvelimeen | — |
| Tallenna | Tallentaa asetukset pysyvästi | — |

---

## API-referenssi

Kaikki API-kutsut tehdään FlowCast-palvelimelle porttiin 5010.

### `GET /api/android/ping`

Yhteyden testaus. Palauttaa myös palvelimen IP:n.

**Vastaus (200):**
```json
{
  "ok": true,
  "server_ip": "192.168.1.100",
  "port": 5010
}
```

### `GET /api/android/folders`

Listaa kaikki alikansiot `android_upload\` -hakemistossa.

**Vastaus (200):**
```json
{
  "folders": ["kuvat", "videot", "lomakuvat-2025"],
  "root": "D:\\MediaPlayer\\android_upload"
}
```

### `GET /api/android/list`

Listaa kaikki mediatiedostot android_upload-hakemistossa ja sen alikansioissa.

**Vastaus (200):**
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

### `POST /api/android/upload`

Vastaanottaa tiedostoja Android-sovellukselta.

**Parametrit (multipart/form-data):**

| Kenttä | Tyyppi | Pakollinen | Kuvaus |
|--------|--------|-----------|--------|
| `files` | file(s) | kyllä | Ladattavat tiedostot (yksi tai useampi) |
| `folder` | text | ei | Kohdekansio android_uploadin alla (tyhjä = juuri) |
| `delete_after` | text | ei | `"true"` jos sovelluksen tulee poistaa paikallinen tiedosto |

**Tuotetut tiedostomuodot:** `.jpg`, `.jpeg`, `.png`, `.mp4`, `.avi`, `.wmv`, `.mov`, `.mkv`

**Videokonversio:** `.avi`, `.wmv`, `.mov`, `.mkv` konvertoidaan automaattisesti MP4:ksi FFmpegillä.

**Vastaus (200):**
```json
{
  "saved": 3,
  "skipped": 1,
  "errors": ["corrupt_file.avi: Konversio epaonnistui"],
  "folder": "kuvat",
  "delete_requested": true
}
```

### `POST /api/android/delete-file`

Poistaa yksittäisen tiedoston android_upload-hakemistosta.

**Pyyntö (JSON):**
```json
{
  "filename": "kuvat/IMG_001.jpg"
}
```

**Vastaus (200):**
```json
{
  "ok": true
}
```

**Virhe (404):**
```json
{
  "error": "Tiedostoa ei loydy"
}
```

### `POST /api/android/create-folder`

Luo uuden alikansion android_upload-hakemiston alle.

**Pyyntö (JSON):**
```json
{
  "folder": "uudet-kuvat"
}
```

**Vastaus (200):**
```json
{
  "ok": true,
  "folder": "uudet-kuvat"
}
```

**Virhe (400):**
```json
{
  "error": "Kansio on jo olemassa"
}
```

### `GET /media_android/<path:filename>`

Tarjoilee ladatun tiedoston palvelimelta. Käytetään tiedostojen selailuun palvelimen tiedostonhallinnassa.

**Esimerkki:** `GET /media_android/kuvat/IMG_001.jpg`

---

## Sovelluksen rakenne

### Luokkakaavio

```
FlowCastApp (main.py)
├── C: väriteema-dict
├── Tila:
│   ├── server_host, server_port, server_online
│   ├── local_files, local_current_dir
│   ├── selected_files: Set[str]
│   ├── delete_after_upload: bool
│   ├── dest_folder: str
│   ├── remote_folders: list, remote_files: list
│   └── taildrop_dir: str
├── UI-komponentit (5 välilehteä):
│   ├── tab_taildrop    → _build_taildrop_tab()
│   ├── tab_upload      → _build_upload_tab()
│   ├── tab_server      → _build_server_tab()
│   ├── tab_files       → _build_files_tab()
│   └── tab_settings    → _build_settings_tab()
└── Metodit:
    ├── Yhteys: _test_connection(), _auto_connect()
    ├── Paikalliset tiedostot: _load_local_dir(), _toggle_local_select()
    ├── Taildrop: _refresh_taildrop_files(), _quick_upload_taildrop()
    ├── Lataus: _perform_upload()
    ├── Palvelin: _refresh_server_files(), _delete_server_file()
    ├── Kansiot: _refresh_server_folders(), _create_folder()
    └── Asetukset: _load_settings(), _save_settings()
```

### Riippuvuudet

```
main.py
├── flet (UI-framework, Flutter-pohjainen)
│   ├── ft.Page          — Ikkuna/sovellus
│   ├── ft.NavigationBar — Alapalkin navigaatio
│   ├── ft.ListView      — Vieritettävät listat
│   ├── ft.AlertDialog   — Vahvistusdialogit
│   ├── ft.SnackBar      — Ilmoitukset
│   └── ft.AnimatedSwitcher — Välilehtien vaihto
├── httpx (async HTTP)
│   └── httpx.AsyncClient — HTTP-kutsut palvelimelle
├── asyncio (async/await)
├── pathlib.Path — Tiedostopolkujen käsittely
└── datetime — Aikaleimojen muotoilu
```

### Async-mallit

Sovellus käyttää Fletin `page.run_task()` -metodia kaikkiin asynkronisiin operaatioihin:

```python
# Sync-event → Async-task
def handler(e):
    self.page.run_task(self._some_async_method, arg1)

async def _some_async_method(self, arg1):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
```

---

## Väriteema

Sovellus käyttää FlowCastin kanssa yhteensopivaa tummaa väriteemaa:

| Muuttuja | Väri | Käyttökohde |
|----------|------|-------------|
| `bg` | `#1a1a2e` | Tausta |
| `panel` | `#16213e` | Paneelit, ylä-/alapalkit |
| `accent` | `#0f3460` | Syöttökentät, korostukset |
| `highlight` | `#e94560` | Tärkeät korostukset (poisto) |
| `text` | `#eeeeee` | Pääteksti |
| `muted` | `#888888` | Toissijainen teksti |
| `border` | `#2a2a4a` | Reunat |
| `green` | `#2ecc71` | Onnistumiset |
| `red` | `#e74c3c` | Virheet |
| `blue` | `#2980b9` | Painikkeet, linkit |
| `orange` | `#f39c12` | Kansioiden kuvakkeet |
| `yellow` | `#f1c40f` | Varoitukset |

---

## APK:n rakennus

### Vaatimukset APK-buildaukseen

Ennen buildausta on asennettava:

1. **Flutter SDK**
   ```batch
   winget install Google.Flutter
   ```

2. **Android SDK** (asennetaan Flutterin kautta)
   ```batch
   flutter doctor
   flutter doctor --android-licenses
   ```

3. **JDK 17+**
   ```batch
   winget install EclipseAdoptium.Temurin.17.JDK
   ```

### Build-komento

**Automaattinen:**
```batch
cd <projektikansio>\android
build_apk.bat
```

**Manuaalinen:**
```batch
cd <projektikansio>\android
flet build apk ^
    --org com.flowcast.android ^
    --project "FlowCast Android" ^
    --product "FlowCast" ^
    --description "FlowCast Android - Taildrop File Manager" ^
    --android-permissions "android.permission.INTERNET" ^
    --android-permissions "android.permission.ACCESS_NETWORK_STATE" ^
    --android-permissions "android.permission.READ_EXTERNAL_STORAGE" ^
    --android-permissions "android.permission.WRITE_EXTERNAL_STORAGE" ^
    --android-permissions "android.permission.READ_MEDIA_IMAGES" ^
    --android-permissions "android.permission.READ_MEDIA_VIDEO" ^
    --android-features "android.hardware.camera=false" ^
    --android-features "android.hardware.camera.autofocus=false" ^
    --no-android-splash
```

### Build-tulos

Onnistuneen buildin jälkeen APK löytyy:
```
android\build\apk\debug\app-debug.apk
```

### Android-oikeudet (AndroidManifest.xml)

Sovellus pyytää seuraavat oikeudet:

| Oikeus | Syy |
|--------|-----|
| `INTERNET` | HTTP-yhteys palvelimeen |
| `ACCESS_NETWORK_STATE` | Verkon tilan tarkistus |
| `READ_EXTERNAL_STORAGE` | Tiedostojen luku laitteelta |
| `WRITE_EXTERNAL_STORAGE` | Tiedostojen poisto latauksen jälkeen |
| `READ_MEDIA_IMAGES` | Kuvien luku (Android 13+) |
| `READ_MEDIA_VIDEO` | Videoiden luku (Android 13+) |

---

## Vianmääritys

### Yhteysongelmat

| Ongelma | Todennäköinen syy | Ratkaisu |
|---------|------------------|----------|
| "🔌 Ei yhteyttä" | Tailscale ei päällä | Käynnistä Tailscale puhelimessa ja PC:llä |
| "🔌 Ei yhteyttä" | Väärä IP | Tarkista PC:n Tailscale IP (`tailscale status`) |
| Yhteys katkeilee | Heikko verkkoyhteys | Varmista molemmat laitteet samassa verkossa |
| HTTP 500 | Palvelin ei käynnissä | Käynnistä `mediaplayer.bat` PC:llä |

### Tiedosto-ongelmat

| Ongelma | Todennäköinen syy | Ratkaisu |
|---------|------------------|----------|
| "Ei lukuoikeutta" | Android-oikeudet puuttuvat | Anna sovellukselle tiedostojen käyttöoikeudet |
| "Ei tiedostoja" kansiossa | Tyhjä kansio | Varmista, että Taildrop on ladannut tiedostot |
| Tiedostoja ei näy | Ei-tuettu tiedostomuoto | Vain .jpg, .png, .mp4, .avi, .wmv, .mov, .mkv |
| Lataus epäonnistuu | Tiedosto liian suuri | Maksimikoko 2000 MB per tiedosto |
| Konversiovirhe | FFmpeg puuttuu palvelimelta | Varmista `ffmpeg.exe` MediaPlayer-kansiossa |

### Build-ongelmat

| Ongelma | Ratkaisu |
|---------|----------|
| `flet: command not found` | `pip install flet` |
| `flutter: command not found` | Asenna Flutter: `winget install Google.Flutter` |
| Android SDK ei löydy | `flutter doctor` ja seuraa ohjeita |
| `JAVA_HOME` ei asetettu | Asenna JDK 17: `winget install EclipseAdoptium.Temurin.17.JDK` |

---

## Kehitys

### Testaus desktopilla

```batch
cd <projektikansio>\android
python main.py
```

Tämä avaa sovelluksen työpöytäikkunassa. Voit testata kaikkia toimintoja paikallisesti. Asetukset tallentuvat `%LOCALAPPDATA%\flet\client_storage\`.

### Koodin rakenne

- [`android/main.py`](main.py) — Kaikki sovelluslogiikka yhdessä tiedostossa (~750 riviä)
- Luokka `FlowCastApp` sisältää kaiken tilan ja metodit
- 5 × `_build_*_tab()` -metodia rakentavat välilehtien UI-komponentit
- Async-metodit käyttävät `async/await` + `httpx.AsyncClient`

### Palvelimen API:n testaus

```batch
# Testaa ping
curl http://localhost:5010/api/android/ping

# Listaa kansiot
curl http://localhost:5010/api/android/folders

# Listaa tiedostot
curl http://localhost:5010/api/android/list

# Luo kansio
curl -X POST http://localhost:5010/api/android/create-folder ^
  -H "Content-Type: application/json" ^
  -d "{\"folder\":\"testi\"}"
```

### Muutosten teko

1. Muokkaa [`android/main.py`](main.py)
2. Testaa desktopilla: `python main.py`
3. Buildaa APK: `build_apk.bat`
4. Asenna puhelimeen ja testaa

---

## Muutosloki

Katso [`../docs/changelog.md`](../docs/changelog.md) — Android-osio lisätty 2026-05-22.
