# FlowCast — Projektisuunnitelma

## Tarkoitus

Selainpohjainen digitaalinen mainosnäyttöpalvelu kahvihuoneen 100" näytölle.
Korvaa ohjelma-x:n, joka ei tue URL-sisältöä. Pyörii sisäverkossa ilman sertifikaattia.

---

## Ympäristö

- **Hakemisto:** projektikansio (esim. `D:\FlowCast\`) — ei riippuvuuksia muihin projekteihin
- **Portti:** `5010` (oletus, ohitettavissa `FLOWCAST_PORT`-ympäristömuuttujalla)
- **Palvelin:** voi pyöriä millä tahansa sisäverkon koneella
- **FFmpeg:** PATH:ssa tai `ffmpeg.exe` projektikansiossa — tarvitaan AVI/WMV/MOV/MKV → MP4 konversioon
- **Verkko:** sisäverkko, VPN-suojattu, sertifikaattia ei tarvita
- **Datajuuri:** `FLOWCAST_DATA_DIR` (oletus: projektikansion yläkansio)

---

## Arkkitehtuuri

```
mediaplayer.py       Flask-palvelin (portti 5010)
templates/
    display.html           Täysruutu-näyttö (ei kehyksiä, selain fullscreen)
    admin.html             Hallintapaneeli
    admin_guest.html       Guest-käyttöliittymä
    settings.html          Admin-näkymän asetukset
    loading.html           Välilataussivu
mediaplayer.bat            Palvelimen käynnistys
playlist.json              Soittolistan pysyvä tallennus (sis. external_dirs, asetukset)
ffmpeg.exe                 Paikallinen FFmpeg video-konversioon (valinnainen, ei repossa)
docs/
    changelog.md           Muutosloki

android/                   ANDROID-SOVELLUS (Flet)
    main.py                Pääsovellus (~750 riviä, 5 välilehteä)
    requirements.txt       Python-riippuvuudet (flet, httpx)
    run.bat                Desktop-testaus
    build_apk.bat          APK-buildaus
    README.md              Dokumentaatio
    API_REFERENCE.md       API-dokumentaatio

# Mediakansiot (sijaitsevat FLOWCAST_DATA_DIR-juuressa)
media_static/              Ladatut kuvat ja videot (JPEG, PNG, MP4)
media_general/             Default-asetuksilla näytettävä bulk-sisältö
media_converted/           Ulkoisten AVI/WMV/MOV/MKV-tiedostojen automaattikonversioiden MP4-välimuisti
media_guest/               Guest-käyttäjien lataama sisältö
media_favorites/           Suosikkikuvat ja -videot
android_upload/            Android-sovelluksen oletus-latauskansio
```

---

## Toiminnallisuus

### Näyttö

Kaikki neljä näkymää käyttävät samaa `display.html`-pohjaa eri parametreilla:

| URL | Polku | Kuvaus |
|-----|-------|--------|
| `/display` | `display.html` | Mix-näkymä — kaikki aktiiviset osiot sekoitettuna |
| `/img` | `display.html?content_filter_override=images` | Vain kuvat kaikista osioista |
| `/vid` | `display.html?content_filter_override=videos` | Vain videot kaikista osioista |
| `/fav` | `display.html?favorites_only=true` | Vain suosikit-osio |

- Täysruutu ilman selaimen kehyksiä (F11 / kiosk-tila)
- Pyörittää yhdistettyä soittolistaa viidestä lähteestä:
  1. **Kustomoidut itemit** (playlist.json) — käyttäjän määrittämässä järjestyksessä, ei shufflea (vain `/display`, `/img`, `/vid`)
  2. **General-sisältö** (`media_general/`) — sekoitetaan jos `general_shuffle_enabled=true`
  3. **Ulkoiset hakemistot** — sekoitetaan jos `external_shuffle_enabled=true`
  4. **Guest-sisältö** (`media_guest/`) — sekoitetaan jos `guest_shuffle_enabled=true`
  5. **Favorites-sisältö** (`media_favorites/`) — sekoitetaan jos `favorites_shuffle_enabled=true`
- Yhdistetyn listan järjestys:
  - **Kustomoidut itemit** tulevat aina ensin, käyttäjän määrittämässä järjestyksessä
  - **Osiot 2–5** limitetään round-robin-periaatteella (yksi kustakin lähteestä vuorotellen), jotta eri osioiden kuvat/videot sekoittuvat keskenään
  - Kunkin osion sisäinen järjestys: hakemistojärjestys jos shuffle pois päältä, satunnainen jos shuffle päällä
- Deduplikointi `src`-kentän mukaan — sama tiedostopolku ei voi esiintyä kahdesti
- Vain aktiiviset (ei-disabled) kohteet näytetään
- Default näyttöaika: **60 sekuntia** per kohde
- Master fade in/out: On/Off -valinta + dropdown (esim. 0.5s / 1s / 2s / 3s)
- Asetusmuutokset havaitaan 10s pollauksella — ei vaadi sivun uudelleenlatausta
- Tukee:
  - Kuva (JPEG, PNG) — näytetään `<img>`-tagilla
  - Video (MP4) — näytetään `<video>`-tagilla, autoplay, muted
  - URL — näytetään `<iframe>`-tagilla (esim. radiaattori, maisemakamera)

### Admin UI (`/adminloginhere`)
- Soittolistan hallintalista
  - Lisää uusi kohde (upload kuva/video tai syötä URL)
  - Poista kohde
  - Disable/Enable — jättää kohteen listaan mutta ohittaa näytössä
  - Per-kohde: näyttöaika (override default)
  - Per-kohde: fade override (override master)
  - Esikatselu — avaa kohteen uudessa välilehdessä tai modal-ikkunassa
- Master-asetukset (fade, default-aika)
- Osio 2 "Sisältö default asetuksilla":
  - Näytä On/Off (`general_enabled`)
  - Sekoita näytettäessä osion sisältö On/Off (`general_shuffle_enabled`)
  - Bulk-sisällön lataus ja hallinta (ZIP-tuki, arkistointi)
- Osio 3 "Liitetyt hakemistot":
  - Sekoita näytettäessä osion sisältö On/Off (`external_shuffle_enabled`)
  - Ulkoisten levyhakemistojen (esim. USB-levyt) lisäys ja hallinta
  - Per-hakemisto enable/disable
- Osio 4 "Guest-sisältö":
  - Näytä On/Off (`guest_enabled`)
  - Sekoita näytettäessä osion sisältö On/Off (`guest_shuffle_enabled`)
- Osio 5 "Suosikit":
  - Näytä On/Off (`favorites_enabled`)
  - Sekoita näytettäessä osion sisältö On/Off (`favorites_shuffle_enabled`)
  - Toistopainikkeet: täysin / minimi / off (`favorites_playback_buttons`)
  - Näytä tiedostonimi (`favorites_show_filename`)
- Näyttää selkeästi palvelun URL:t: `http://<ip>:5010/display`, `/img`, `/vid`, `/fav`

---

## Asetukset (playlist.json)

| Asetus | Tyyppi | Default | Kuvaus |
|--------|--------|---------|--------|
| `default_duration` | int | 60 | Oletusnäyttöaika sekunteina |
| `fade_enabled` | bool | true | Fade-siirtymät päällä/pois |
| `fade_duration` | float | 1.0 | Fade-siirtymän kesto sekunteina |
| `fade_type` | str | "normaali" | Siirtymätyyppi |
| `video_audio` | bool | false | Videoäänet päällä/pois |
| `video_duration` | str | "default" | "default" tai "full" (koko video) |
| `shuffle_enabled` | bool | true | (Vanhentunut — ei enää käytössä näytössä) |
| `playback_buttons` | bool | true | Toistopainikkeet näkyvissä (mix-näkymä) |
| `general_enabled` | bool | true | Osion 2 sisältö näkyy feedissä |
| `general_shuffle_enabled` | bool | true | Osion 2 sisällön sekoitus |
| `guest_enabled` | bool | true | Osion 4 (guest) sisältö näkyy feedissä |
| `guest_shuffle_enabled` | bool | true | Osion 4 (guest) sisällön sekoitus |
| `favorites_enabled` | bool | true | Osion 5 (suosikit) sisältö näkyy feedissä |
| `favorites_shuffle_enabled` | bool | true | Osion 5 (suosikit) sisällön sekoitus |
| `favorites_playback_buttons` | str | "minimi" | Suosikit-näkymän painikkeet: "täysin" / "minimi" / "off" |
| `favorites_show_filename` | bool | false | Tiedostonimi näkyvissä suosikit-näkymässä |
| `content_filter` | str | "all" | "all", "images", tai "videos" |
| `external_shuffle_enabled` | bool | true | Osion 3 sisällön sekoitus |
| `show_video_timer` | bool | true | Videoajastin näkyvissä |
| `show_filename` | bool | true | Tiedostonimi näkyvissä (mix-näkymä) |

---

## Käyttäytymissäännöt (samat kuin Repo-projektissa)

- **Älä muuta koodia ilman lupaa.** Ehdota muutoksia ensin, toteuta vasta kun käyttäjä hyväksyy.
- **Älä poista tai muuta mitään olemassaolevaa** ilman erillistä pyyntöä.
- **Älä koske kommentteihin** ellei erikseen pyydetä.
- **Vastaa lyhyesti ja täsmällisesti.**
- Kun teet koodimuutoksia, kirjaa ne `docs/changelog.md`:hen käyttäjän hyväksynnän jälkeen.

---

## Liitetyt hakemistot

Ulkoisten levyhakemistojen (esim. USB-levyt) tuki:

- Hakemistot rekisteröidään admin-paneelissa polun ja valinnaisen nimikkeen kera
- Palvelun startissa skannataan kaikki aktivoidut hakemistot ja cachetaan tiedostolista
- **Puuttuvat polut ohitetaan varoituksella** — ei kaada palvelinta
- Tiedostoja ei kopioida palvelimelle, vaan ne tarjoillaan suoraan levyltä
- Feedissä ulkoiset tiedostot näkyvät default-asetusten mukaan, limittyen muiden osioiden kanssa
- Tietoturva: tiedostojen tarjoilu validoidaan rekisteröityjä hakemistopolkuja vasten

---

## Android-sovellus (Taildrop File Manager)

Flet-pohjainen Android-sovellus tiedostojen siirtoon puhelimesta FlowCast-palvelimelle Tailscale-verkon yli.

### Yleiskuva

- **Hakemisto:** `android/` — sovelluksen lähdekoodi
- **Framework:** Flet 0.85.1 (Python → Flutter)
- **APK:** `flet build apk` — vaatii Flutter SDK + Android SDK
- **Latauskansio:** `android_upload/` (`FLOWCAST_DATA_DIR`-juuressa)

### Välilehdet

| Välilehti | Kuvaus |
|-----------|--------|
| **Taildrop** | Pikasiirto Lataukset-kansiosta. Valitse tiedostot, valitse kohdekansio, poisto puhelimesta. |
| **Lataa** | Täysi tiedostoselain. Navigoi koko puhelimen tiedostojärjestelmässä. Monivalinta. |
| **Palvelin** | Yhteyden tila, kansioiden luonti ja poisto palvelimella. |
| **Tiedostot** | Palvelimen tiedostonhallinta. Tiedostojen ja kansioiden selaus ja poisto. |
| **Asetukset** | Palvelimen IP/portti, pysyvä tallennus. |

### API-päätteet (palvelin)

| Pääte | Kuvaus |
|--------|--------|
| `GET /api/android/ping` | Yhteyden testaus |
| `GET /api/android/folders` | Kansiolistaus |
| `GET /api/android/list` | Tiedostolistaus |
| `POST /api/android/upload` | Tiedostojen vastaanotto |
| `POST /api/android/delete-file` | Tiedoston poisto |
| `POST /api/android/create-folder` | Kansion luonti |
| `GET /media_android/<path>` | Tiedostojen tarjoilu |

### Taildrop-integraatio

- Sovellus tunnistaa automaattisesti Androidin Lataukset-kansion (`/storage/emulated/0/Download`)
- Kansion voi vaihtaa (DCIM/Camera, Screenshots, jne.)
- "Lataa KAIKKI" — yhden napin koko kansion lähetys
- "Poista puhelimesta latauksen jälkeen" — estää duplikaatit

### Buildaus

```batch
cd android
build_apk.bat
```

Vaatii: Flutter SDK, Android SDK, JDK 17+

Katso tarkemmat ohjeet: [`android/README.md`](android/README.md)

---

## Muutosloki

Katso `docs/changelog.md`.
