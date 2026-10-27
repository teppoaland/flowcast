# CLAUDE.md — FlowCast

> **Lue aina ensin `projekti.md`** — siellä on projektin arkkitehtuuri, asetukset, ja ajantasainen toiminnallisuuskuvaus.
> `docs/changelog.md` sisältää muutoshistorian.

## Käyttäytymissäännöt

- **Älä muuta koodia ilman lupaa.** Ehdota muutoksia ensin, toteuta vasta kun käyttäjä hyväksyy.
- **Älä poista tai muuta mitään olemassaolevaa.** Yksittäistä koodiriviä, toimintoa, UI-elementtiä, painiketta tai asetusta ei saa muuttaa, poistaa tai "siistiä" muiden muutosten yhteydessä. Jos jokin näyttää tarpeettomalta — kysy ensin.
- **Älä koske kommentteihin.** Kommentteja ei lisätä, muokata eikä poisteta ellei erikseen pyydetä.
- **Vastaa lyhyesti ja täsmällisesti.** Vältä turhia pohjustuksia ja yhteenvetoja.

## Projektin rakenne

```
mediaplayer.py      Flask-palvelin (portti 5010, oletus)
templates/
    display.html          Täysruutu-näyttö (selain fullscreen, ei kehyksiä)
    admin.html            Hallintapaneeli (lisää/poista/disable, esikatselu)
    admin_guest.html      Guest-latausnäkymä
playlist.json             Soittolistan pysyvä tallennus (syntyy automaattisesti)
docs/
    changelog.md          Muutosloki
requirements.txt          Python-riippuvuudet
mediaplayer.bat           Käynnistysskripti (Windows)
android/                  Android-sovellus (Flet)
tools/                    duplicate_finder.py (duplikaattien etsintä)
```

## Teknologiat

- **Python 3.12+** + **Flask** — ainoa pakollinen riippuvuus
- Ei Node.js, Java, Selenium, Newman tai muita ulkoisia työkaluja

## Asennusvaatimukset

Ainoastaan Python PATH:ssa. Kaikki muu hoituu `mediaplayer.bat`:lla automaattisesti.

## Tuetut sisältötyypit

- **Kuva:** JPEG, PNG — näytetään `<img>`-tagilla
- **Video:** MP4 — näytetään `<video autoplay muted loop>`-tagilla
- **URL:** mikä tahansa web-osoite — näytetään `<iframe>`-tagilla

## Flask-backend käytännöt

**Portit:**
- `5010` — mediaplayer (display + admin), oletus; `FLOWCAST_PORT` ohittaa

**Polkurakenne:**
- Media: `FLOWCAST_DATA_DIR` (oletus: projektikansion yläkansio) — `media_static/`, `media_general/`, `media_guest/`, `media_favorites/`, `media_converted/`, `android_upload/`, `Archive/`
- Soittolista: `playlist.json` projektikansiossa

**Serveririippumattomuus** — ei hardcodattuja palvelinpolkuja. IP näytetään dynaamisesti käynnistyksen yhteydessä.

## Testausmuistutus

Muistuta käyttäjää testauksesta kun:
- Uusi backend-endpoint on lisätty
- Display-logiikkaan on tehty muutoksia
- Useampi ominaisuus on toteutettu peräkkäin testaamatta
- ZIP-lataus tai videokonversio on kosketettu

Suositeltava testaussykli: **enintään 2-3 uutta toimintoa ennen testauskierrosta.**

## Muutosloki

Kun teet koodimuutoksia, kirjaa ne `docs/changelog.md`:hen käyttäjän hyväksynnän jälkeen.
Formaatti: `- [tiedosto] Lyhyt kuvaus muutoksesta` nykyisen päivämäärän alle.
Luo uusi päivämääräotsikko `## [Unreleased] - YYYY-MM-DD` jos sellaista ei vielä ole.
