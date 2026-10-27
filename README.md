# FlowCast <small>10.01</small>

Itse ylläpidettävä 24/7 info-TV ja mediasoitin sisäverkkoon. FlowCast pyörittää
kuva-, video- ja URL-sisältöä missä tahansa selaimellisessa laitteessa —
televisiossa, tabletissa tai puhelimessa — ja tarjoaa selainpohjaisen
hallintapaneelin sisällön ohjaamiseen.

Käyttötapaus: näyttö, joka pyörii jatkuvasti omalla materiaalilla. FlowCast
kokoaa useat lähteet (omat kansiot, liitetyt levyt, guest-lataukset, suosikit)
yhdeksi feediksi, josta voi valita kuvat, videot tai molemmat — tai vain
parhaat pätkät. Skaalautuu kymmeniintuhansiin kuviin ja kymmeniin tunteihin
videota.

> Repositorio sisältää vain lähdekoodin — ei kuvia, videoita eikä muuta
> sisältöä. Lisenssi: ks. [LICENSE](LICENSE).

## Ominaisuudet

- Neljä näkymää: `/display` (mix), `/img` (kuvat), `/vid` (videot), `/fav` (suosikit)
- Viisi sisältölähdettä: kustomoidut itemit, general-kansio, liitetyt hakemistot, guest-lataukset, suosikit
- Lähdekohtainen sekoitus (shuffle), fade-siirtymät ja näyttöajat
- Kuvat (JPEG/PNG), videot (MP4), URL-sisältö (iframe)
- AVI/WMV/MOV/MKV → MP4 -automaattikonversio FFmpegillä
- Guest-latausnäkymä ja suosikkikuvat
- Erillinen Android-sovellus tiedostojen siirtoon (Flet)

## Vaatimukset

- Python 3.11+ (testattu 3.11.9)
- Windows `.bat`-käynnistystä varten — käsin käynnistys toimii myös muilla alustoilla
- FFmpeg PATH:ssa vain jos tarvitset AVI/WMV/MOV/MKV-konversiota

## Asennus

Kaksoisklikkaa `mediaplayer.bat`. Skripti luo virtuaaliympäristön (`venv\`),
asentaa riippuvuudet, käynnistää palvelimen ja avaa admin-sivun selaimeen.

### Käsin

```bat
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python mediaplayer.py
```

## Osoitteet

| Sivu | URL |
|------|-----|
| Näyttö (mix) | `http://<palvelin>:5010/display` |
| Vain kuvat | `http://<palvelin>:5010/img` |
| Vain videot | `http://<palvelin>:5010/vid` |
| Suosikit | `http://<palvelin>:5010/fav` |
| Admin | `http://<palvelin>:5010/adminloginhere` |
| Guest-lataus | `http://<palvelin>:5010/guest` |

Palvelimen sisäverkon IP tulostuu konsoliin käynnistyksen yhteydessä.
Admin-paneeli näyttää näyttö-URLit aina sillä osoitteella, jolla sivu
avattiin, joten kiinteitä IP-osoitteita ei tarvita.

## Asetukset (ympäristömuuttujat)

| Muuttuja | Oletus | Kuvaus |
|----------|--------|--------|
| `FLOWCAST_PORT` | `5010` | Kuunneltava portti |
| `FLOWCAST_HOST` | `0.0.0.0` | Kuunneltava osoite |
| `FLOWCAST_DATA_DIR` | projektikansion yläkansio | Mediakansioiden juurihakemisto |

```bat
set FLOWCAST_PORT=8080
set FLOWCAST_DATA_DIR=D:\FlowCastData
mediaplayer.bat
```

## Hakemistorakenne

```
mediaplayer.py          Flask-palvelin
mediaplayer.bat         Käynnistysskripti (Windows)
VERSION                 Tuoteversio (10.01)
templates/              Näyttö- ja admin-näkymät
tools/                  duplicate_finder.py — duplikaattien etsintä
docs/changelog.md       Muutosloki
android/                Android-sovellus (Flet)
playlist.json           Soittolista ja asetukset (syntyy automaattisesti)
```

Mediakansiot syntyvät automaattisesti `FLOWCAST_DATA_DIR`-hakemistoon:
`media_static/`, `media_general/`, `media_guest/`, `media_favorites/`,
`media_converted/`, `android_upload/`. `Archive/` syntyy general-sisällön
arkistoinnin yhteydessä.

`playlist.json` ja kaikki mediakansiot on gitignoressa — ne eivät koskaan
päädy repositorioon.

## Android-sovellus

`android/` sisältää Flet-pohjaisen sovelluksen, jolla tiedostoja siirretään
puhelimesta palvelimelle. Asennus ja buildaus: [`android/README.md`](android/README.md).
API-kuvaus: [`android/API_REFERENCE.md`](android/API_REFERENCE.md).

## Tietoturva

- Admin-paneelissa **ei ole autentikointia** — palvelu on tarkoitettu suljettuun
  sisäverkkoon, ei julkiseen internetiin.
- Liitettyjen hakemistojen tiedostojen tarjoilu validoidaan rekisteröityjä
  hakemistopolkuja vasten (directory traversal esto).
- Latauskoko on rajoitettu 2000 MB:iin.

## Vianmääritys

- **Portti varattu** — lopeta aiempi ajo: `Get-Process python | Stop-Process`
- **Näyttö on tyhjä** — kova päivitys `Ctrl+Shift+R`, tarkista että soittolistalla
  on aktiivisia kohteita
- **URL-kohde ei näy** — kohdesivusto estää iframe-upotuksen (`X-Frame-Options`)
- **Palvelin kaatuu käynnistyksessä** — poista vioittunut `playlist.json`,
  ohjelma luo uuden oletussoittolistan

## Lisenssi

All rights reserved. Ks. [LICENSE](LICENSE). Repositorio on julkinen
katselua ja tutustumista varten.

Kolmannen osapuolen komponentit: ks. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
