# Third Party Notices — FlowCast

FlowCast käyttää seuraavia kolmannen osapuolen komponentteja erillisinä
riippuvuuksina. Ne eivät ole tämän projektin lisensoimaa koodia.

## Palvelin (`requirements.txt`)

| Komponentti | Versio | Lisenssi |
|-------------|--------|----------|
| Flask | 3.1.3 | BSD-3-Clause |
| Werkzeug | 3.1.6 | BSD-3-Clause |

## Videokonversio (valinnainen, ei mukana repossa)

| Komponentti | Lisenssi |
|-------------|----------|
| FFmpeg | LGPL-2.1+ tai GPL, käytetystä buildista riippuen |

FFmpeg:iä ei toimiteta tässä repositoriossa eikä `ffmpeg.exe` ole mukana.
Käyttäjä asentaa sen itse (esim. `winget install Gyan.FFmpeg`) ja vastaa
asennetun buildin lisenssiehtojen noudattamisesta.

## Android-sovellus (`android/requirements.txt`)

| Komponentti | Versio | Lisenssi |
|-------------|--------|----------|
| Flet | >= 0.85.1 | Apache-2.0 |
| httpx | >= 0.28.1 | BSD-3-Clause |

## Selain

Näyttö- ja admin-näkymät käyttävät vain selaimen omia web-standardeja
(HTML, CSS, JavaScript). Mukana ei ole kolmannen osapuolen
JavaScript-kirjastoja eikä fontteja.

Lisenssitekstit löytyvät kunkin paketin mukana toimitettavasta
LICENSE-tiedostosta.
