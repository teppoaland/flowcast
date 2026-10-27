# CHANGELOG - FlowCast

## [Unreleased] - 2026-10-27

### Geneerinen julkaisu: riippumaton asennushakemistosta ja verkko-osoitteesta (v2.2.0)
- [mediaplayer.py] Uusi `DATA_ROOT` (`FLOWCAST_DATA_DIR`, oletus projektikansion yläkansio): kaikki mediakansiot johdetaan siitä — `MEDIA_FAVORITES_DIR` ja `ANDROID_UPLOAD_DIR` eivät enää käytä absoluuttista `D:/MediaPlayer`-polkua
- [mediaplayer.py] `PORT` (`FLOWCAST_PORT`, oletus 5010) ja `HOST` (`FLOWCAST_HOST`, oletus 0.0.0.0) ympäristömuuttujista; `app.run()` ja startup-banneri käyttävät niitä
- [mediaplayer.py] `adminpanel()` ja `guest()`: näyttö-URLit rakennetaan `request.host_url`-arvosta — IP ja portti tulevat aina pyynnöstä, ei kiinteinä
- [mediaplayer.py] `api_android_ping()`: portti `PORT`-muuttujasta
- [mediaplayer.py] `get_local_ip()`: UDP-kikan lisäksi `gethostbyname`-fallback, ei enää pelkkä 127.0.0.1 offline-verkossa
- [mediaplayer.bat] `FLOWCAST_PORT` huomioidaan porttitarkistuksessa, tulosteissa ja selaimen avauksessa
- [android/main.py] `DEFAULT_HOST` = `127.0.0.1` kiinteän Tailscale-IP:n sijaan; asetusteksti ei viittaa kiinteään levykirjaimeen
- [docs/changelog.md] Henkilökohtaiset hakemistoviittaukset yleistetty
- [.gitignore] Media, `playlist.json`, `ffmpeg.exe`, `venv/` ja Android-buildit pois repositoriosta
- [.gitattributes] Rivinvaihdot: `*.bat` CRLF, `*.sh` LF
- [LICENSE] All rights reserved -lisenssi (Copyright 2026 Teppo Ålander)
- [THIRD_PARTY_NOTICES.md] Kolmannen osapuolen komponenttiluettelo
- [VERSION] 2.2.0
- [README.md] Uudelleenkirjoitettu geneerisillä asennus- ja asetusohjeilla

## [Unreleased] - 2026-06-03

### Per-source shuffle -korjaus: sekoitus kunnioittaa osiokohtaisia asetuksia (taso 2/10)
- [templates/display.html] `rebuildPlaylist()` uudelleenkirjoitettu: jokainen lähde (general, external, guest, favorites) kerätään omaan taulukkoonsa ja shuffle-ajetaan vain jos kyseisen osion `*_shuffle_enabled`-asetus on päällä — ei enää ehdotonta globaalia shufflea
- [templates/display.html] Osioiden 2–5 limitäminen round-robin-periaatteella: kun useampi osio on aktiivinen, niiden sisältö limitetään vuorotellen (yksi kustakin) jotta eri lähteiden kuvat/videot sekoittuvat keskenään
- [templates/display.html] Kun shuffle on pois päältä, tiedostot näytetään hakemistojärjestyksessä (aakkosjärjestys)
- [playlist.json] Vahvistettu: `external_shuffle_enabled: false` toimii nyt oikein — ulkoisen hakemiston kuvat näkyvät hakemistojärjestyksessä

### Dokumentaation päivitys (taso 1/10)
- [projekti.md] Päivitetty Näyttö-osio: kaikki 4 URL:ä (`/display`, `/img`, `/vid`, `/fav`), 5 lähdettä, round-robin-limitäminen, per-source shuffle
- [projekti.md] Päivitetty Admin UI -osio: Guest ja Suosikit -osiot, niiden asetukset
- [projekti.md] Päivitetty Asetukset-taulukko: `guest_enabled`, `guest_shuffle_enabled`, `favorites_enabled`, `favorites_shuffle_enabled`, `favorites_playback_buttons`, `favorites_show_filename`

## [Unreleased] - 2026-05-22

### Android-sovellus — Taildrop File Manager & Uploader (taso 8/10)
- [android/main.py] Uusi Flet-pohjainen Android-sovellus: 5 välilehden navigaatio (Taildrop, Lataa, Palvelin, Tiedostot, Asetukset)
- [android/main.py] Taildrop-välilehti: pikasiirto Lataukset-kansiosta, valitse kaikki/yksittäin, kohdekansion valinta, poisto puhelimesta
- [android/main.py] Lataa-välilehti: täysi tiedostoselain koko puhelimen tiedostojärjestelmälle, navigointi, monivalinta
- [android/main.py] Palvelin-välilehti: yhteyden tila, kansioiden luonti ja poisto
- [android/main.py] Tiedostot-välilehti: palvelimen tiedostonhallinta, kansioittain ryhmittely, poisto
- [android/main.py] Asetukset-välilehti: palvelimen IP/portti, pysyvä tallennus client_storageen
- [android/main.py] Async-arkkitehtuuri: httpx.AsyncClient + page.run_task(), timeoutit per operaatio (5-180s)
- [android/main.py] Tumma teema: FlowCast-yhteensopiva värimaailma (12 väriä), File Manager+ -tyylinen UI
- [android/main.py] Tiedostokokojen ja aikaleimojen näyttö, emoji-kuvakkeet tiedostotyypeille
- [android/main.py] Maksimikoko 2000 MB, tuetut muodot: jpg, jpeg, png, mp4, avi, wmv, mov, mkv
- [android/main.py] Automaattinen Android- ja Taildrop-polun tunnistus (Downloads, DCIM/Camera)
- [android/requirements.txt] Riippuvuudet: flet>=0.85.1, httpx>=0.28.1
- [android/run.bat] Desktop-testausskripti: tarkistaa flet-asennuksen, käynnistää sovelluksen
- [android/build_apk.bat] APK-buildausskripti: tarkistaa Flutter/Android SDK, ajaa `flet build apk`
- [android/README.md] Täydellinen dokumentaatio: arkkitehtuuri, asennus, käyttöohje, vianmääritys
- [android/API_REFERENCE.md] API-dokumentaatio: 7 endpointia, pyyntö/vastaus-esimerkit, curl-testit
- [mediaplayer.py] Uusi `ANDROID_UPLOAD_DIR` = `android_upload` — oletus-latauskansio
- [mediaplayer.py] `GET /api/android/ping` — kevyt health-check, palauttaa serverin IP:n
- [mediaplayer.py] `GET /api/android/folders` — listaa android_uploadin alikansiot
- [mediaplayer.py] `GET /api/android/list` — listaa kaikki mediatiedostot (kuvat + videot + koot)
- [mediaplayer.py] `POST /api/android/upload` — vastaanottaa tiedostoja multipart/form-data, tukee kohdekansiota ja delete_after-lippua
- [mediaplayer.py] `POST /api/android/delete-file` — poistaa tiedoston polkuturvalla
- [mediaplayer.py] `POST /api/android/create-folder` — luo alikansion (nimen validointi)
- [mediaplayer.py] `GET /media_android/<path>` — staattisten tiedostojen tarjoilu android_uploadista
- [mediaplayer.py] Videokonversio uploadissa: AVI/WMV/MOV/MKV → MP4 FFmpegillä
- [mediaplayer.py] Duplikaattien esto: samanniminen tiedosto ohitetaan
- [mediaplayer.py] Tietoturva: polkuturva (directory traversal esto), tiedostotyyppirajaus, kansionnimen validointi

## [Unreleased] - 2026-05-16

### /fav — Mediapainikkeet + tiedostopolku -asetukset (taso 3/10)
- [playlist.json] Uudet asetukset: `favorites_playback_buttons` ("täysin"|"minimi"|"off", default "minimi") ja `favorites_show_filename` (bool, default false)
- [mediaplayer.py] `load_playlist()` ja `api_save_settings()`: tuki uusille favorites-asetuksille
- [templates/admin.html] Osio 4: 3-asentoinen Mediapainikkeet-valinta (Täysin/Minimi/Off) + Näytä tiedostopolku -toggle, tooltipit
- [templates/display.html] `updatePlaybackControls()`: FAVORITES_ONLY-tilassa käyttää `favorites_playback_buttons` — minimillä vain << pause >>, offilla piilotettu
- [templates/display.html] `updateInfoOverlay()`: FAVORITES_ONLY-tilassa käyttää `favorites_show_filename` tiedostonimen näyttöön
- [templates/display.html] `pollSettings()`: FAVORITES_ONLY-pollaus huomioi uudet asetukset

## [Unreleased] - 2026-05-14

### /fav — Suosikit feed (taso 2/10)
- [mediaplayer.py] Uusi route `/fav`: oma display-feed joka näyttää vain `media_favorites`-hakemiston kuvat ja videot default-asetuksilla
- [mediaplayer.py] `/fav` käyttää samaa `display.html`-templatea `favorites_only=True`-yliajolla — ei hallintaa tai UI:ta
- [mediaplayer.py] `adminpanel()`: lisätty `fav_url` muuttuja templateen, `/fav`-URL lisätty admin-paneelin yläpalkkiin guest-linkin tilalle
- [mediaplayer.py] Startup-banneriin lisätty `Suosikit: http://...:5010/fav`
- [templates/display.html] Uusi `FAVORITES_ONLY` template-muuttuja: kun `true`, kaikki muut sisältölähteet ohitetaan ja vain favorites-tiedostot näytetään
- [templates/display.html] `fetchPlaylist()`: favorites-only -tilassa haetaan vain `/api/playlist` ja `/api/favorites/list` (muut API-kutsut ohitetaan)
- [templates/display.html] `rebuildPlaylist()`: favorites-only -tilassa playlist-itemit, general, external ja guest ohitetaan kokonaan
- [templates/display.html] `next()`, `pollSettings()`, `deleteCurrentItem()`, `addToFavorites()`: kaikki mukautettu `FAVORITES_ONLY`-tilaan
- [templates/display.html] Sivun otsikko: "FlowCast – Suosikit" `/fav`-feedissä
- [templates/admin.html] Yläpalkin guest-linkki (`(Guest upload UI)`) korvattu fav-linkillä (`(Suosikit feed)`)
- [templates/admin.html] Guest-linkki (`(Guest upload UI)`) siirretty osion 5 (Guest sisältö) alareunaan `guest-info`-divin alle
- [docs/changelog.md] Tämä changelog päivitetty

### Globaali shuffle — korjaa "random ei toimi" (taso 6/10)
- [templates/display.html] `rebuildPlaylist()` uudelleenkirjoitettu: kaikki bulk-lähteet (general, external, guest, favorites) yhdistetään yhteen pottiin ja sekoitetaan globaalisti Fisher-Yatesilla — ei enää lohkokohtaista sekoitusta
- [templates/display.html] Poistettu `shuffle()`-apufunktio — shuffle nyt inline rebuildPlaylistissa (vähemmän taulukon kopiointia)
- [templates/display.html] Poistettu 2h `location.reload()` — turha, `pollSettings()` hoitaa asetuspäivitykset, reload rikkoi random-syklin
- [templates/display.html] Yksinkertaistettu `pollSettings()` ja `next()`: poistettu per-section shuffle -muuttujat (lastShuffleEnabled, lastExternalShuffleEnabled, jne.) — globaalissa shufflessa tarpeettomia
- [templates/display.html] `rebuildPlaylist()`-lokitus näyttää nyt osiokohtaiset luvut + "bulk X globally shuffled"

### Shuffle-debuggaus & korjaukset (taso 2/10)
- [playlist.json] Lisätty puuttuvat avaimet: `general_shuffle_enabled`, `favorites_enabled`, `favorites_shuffle_enabled` — tiedosto nyt konsistentti
- [templates/display.html] Parannettu `rebuildPlaylist()`-lokitus: näyttää nyt osiokohtaiset tiedostomäärät + shuffle-tilat + 3 ekaa tiedostonimeä
- [templates/admin.html] Settings-linkin fonttikoko periytyy nyt h2-otsikosta, ei boldia (poistettu `font-size:0.8rem`)
- [templates/admin.html] Korjattu section 2 Tiedostot-painikkeen `btn-small1` → `btn-small`

### Settings-sivu & Admin-näkymän hallinta (taso 5/10)
- [templates/settings.html] Uusi sivu `/adminsettings`: Admin-näkymän asetukset — kenttien ja osioiden näkyvyyden hallinta
- [templates/settings.html] "Admin asetukset — näytettävät kentät": 10 togglea default-asetuskentille (näyttöaika, fade, siirtymät, jne.)
- [templates/settings.html] "Sisällön hallinta — näytettävät osiot": 5 osiota, jokaiselle Näytä ON/OFF + Auki/Kiinni -tila
- [mediaplayer.py] Uusi `admin_ui`-rakenne playlist.json:ssa: `show_fields` (kenttäkohtaiset togglet) + `sections` (osiokohtaiset togglet)
- [mediaplayer.py] `GET/POST /api/admin-ui` endpointit admin-näkymän asetusten lukuun ja tallennukseen
- [mediaplayer.py] `/adminsettings` route: renderöi `templates/settings.html`
- [templates/admin.html] ⚙ Settings-linkki Default asetukset -paneelin oikeassa laidassa
- [templates/admin.html] `applyAdminUIVisibility()`: piilottaa/näyttää kentät ja osiot `ADMIN_UI`-asetusten mukaan, asettaa auki/kiinni-tilan
- [templates/admin.html] Korjattu: section 2 Tiedostot-painikkeen `btn-small1` → `btn-small`

### Sydän-painike & Parhaat sisältö (taso 7/10)
- [mediaplayer.py] Uusi `MEDIA_FAVORITES_DIR` (`media_favorites`): suosikkikuvien hakemisto
- [mediaplayer.py] Uudet API-endpointit: `GET /api/favorites/list`, `POST /api/favorites/add` (kopioi tiedoston), `POST /api/favorites/delete-file`, `POST /api/favorites/rename-file`
- [mediaplayer.py] `POST /api/favorites/add`: tukee kaikkia lähdetyyppejä (`/media/`, `/media_general/`, `/media_guest/`, `/api/external/file`), automaattinen nimitörmäysten käsittely
- [mediaplayer.py] `GET /media_favorites/<path>`: staattisten suosikkitiedostojen tarjoilu
- [mediaplayer.py] Uudet asetukset `favorites_enabled` ja `favorites_shuffle_enabled` (default: `True`)
- [mediaplayer.py] `adminpanel`: vie `favorites_dir`, `general_dir`, `guest_dir` templateen (backslashit korvattu `/`)
- [templates/display.html] ❤️ Sydän-painike toistopainikkeisiin — kopioi nykyisen median suosikkeihin, visuaalinen palaute (punahehku + skaalaus)
- [templates/display.html] `favoritesFiles` fetch + rebuildPlaylist: suosikit viidentenä osiona (playlist → general → external → guest → favorites)
- [templates/display.html] Suosikit tuettu shufflessa, pollauksessa, poistossa ja content_filter:ssä
- [templates/admin.html] Osio 4 "Parhaat sisältö": toggle-kytkimet, tiedostolaskuri, Tiedostot-modali (polku, puunäkymä, uudelleennimeäminen, poisto)
- [templates/admin.html] CSS `#favorites-files-modal`: täysi modal-tyylitys mobiilioptimoinnilla
- [templates/admin.html] Korjattu: border-bottom pois kaikista Tiedostot-modaleista (general, guest, favorites), padding 4px→2px
- [templates/admin.html] Modaalien h3-margin pienennetty 16px→4px, lisätty `.fav-path`-tyyli polkunäytölle
- [templates/admin.html] Lisätty base-hakemistopolut general- ja guest-modaleihin
- [templates/admin.html] Auto-refresh 10s välein: guest- ja favorites-listat päivittyvät automaattisesti

- [templates/admin.html] Favicon: favicon.svg (neliö) korvaa favicon.ico:n — kaikissa templateissa <link> ja Flask-routessa
- [mediaplayer.py] `/favicon.ico`-route säilytetty aliaksena, `/favicon.svg` uusi route (mimetype: image/svg+xml)
- [templates/admin.html] Logo: flowcast.svg (250x60) upotettu inline h1-tekstin tilalle vasempaan ylänurkkaan
- [templates/admin.html] Brändäys: MediaPlayer → FlowCast (title, h1), "MediaPlayerin näyttö URL" → "Stream näyttö URL"
- [templates/admin_guest.html] Brändäys: MediaPlayer → FlowCast (title, h1), "MediaPlayerin näyttö URL" → "Stream näyttö URL"
- [templates/display.html] Brändäys: MediaPlayer → FlowCast (title)
- [templates/loading.html] Brändäys: MediaPlayer → FlowCast (title, h1)
- [mediaplayer.bat] Brändäys: MediaPlayer → FlowCast (title, tilaviestit, banneri)
- [CLAUDE.md] Brändäys: MediaPlayer → FlowCast (otsikko)
- [docs/changelog.md] Brändäys: MediaPlayer → FlowCast (otsikko)
- [projekti.md] Brändäys: MediaPlayer → FlowCast (otsikko)
- [README.md] Brändäys: MediaPlayer → FlowCast (otsikko)
- [templates/display.html] Tiedostonimi nyt klikattavissa: kopioi suoran linkin leikepöydälle (clipboard API + textarea/execCommand-fallback HTTP:lle)
- [templates/admin.html] Globaali `#loading-overlay` (z-index: 9999) — näkyy aina sivun yläreunassa, pulssi-animaatio, ei riipu modaleista
- [templates/admin.html] `showLoading(msg)` / `hideLoading()` — kaikki pitkät operaatiot (deleteGeneralFile, deleteGuestFile, deleteExternalDir, refreshExternalDirs) käyttävät näitä
- [templates/display.html] Uusi roskakori-painike (🗑️) toistopainikkeiden oikealla puolella — poistaa näytössä olevan kuvan/videon pysyvästi (varmistuksella)
- [templates/display.html] Roskakori tukee kaikkia lähteitä: kustomoitu sisältö, mediakirjasto, guest-media ja ulkoiset hakemistot
- [mediaplayer.py] Hakemistokohtainen `allow_delete`-kenttä `external_dirs`-entryissä (default: `False`) — korvaa kiinteän `ALLOWED_DELETE_ROOT`-polun
- [mediaplayer.py] Uusi route `POST /api/external/delete-file`: ulkoisen tiedoston poisto polkutarkistuksella, tarkistaa `allow_delete`-lipun, poistaa myös konvertoidun MP4-välimuistitiedoston
- [mediaplayer.py] `POST /api/external/add`: uusiin hakemistoihin `allow_delete: False` oletuksena
- [mediaplayer.py] `PATCH /api/external/<id>`: tuki `allow_delete`-kentän päivitykselle
- [templates/admin.html] Jokaisella ulkoisella hakemistorivillä nyt "Salli tiedoston poisto" -toggle
- [mediaplayer.py] `scan_external_dirs()` siirretty taustasäikeeseen (`threading.Thread(daemon=True)`) — palvelin alkaa kuunnella heti, ei jumita startupissa suurilla tiedostomäärillä
- [mediaplayer.py] `_SCAN_LOCK`: globaali lukko joka estää samanaikaiset päällekkäiset skannaukset (`acquire(blocking=False)`)
- [mediaplayer.py] `_SCANNING_EXTERNAL`: lippu joka kertoo onko ulkoisten hakemistojen skannaus kesken
- [mediaplayer.py] `/api/external/list` palauttaa nyt `"scanning": true/false` — admin UI pollaa kunnes skannaus valmis
- [templates/admin.html] `loadExternalDirs()`: jos `scanning === true`, näyttää "Skannataan hakemistoja... (X tiedostoa laskettu)" ja pollaa 2s välein
- [templates/loading.html] Uusi välilataussivu: aukeaa heti, näyttää "Palvelu käynnistyy" -animaation, pollaa `/api/ping` ja siirtyy `/adminpanel`-sivulle kun palvelin vastaa (1,5s miniminäyttöaika)
- [mediaplayer.py] `/adminloginhere` näyttää nyt `loading.html` (kevyt, aukeaa heti)
- [mediaplayer.py] Uusi route `/adminpanel`: varsinainen admin-näkymä (`admin.html`)
- [mediaplayer.py] Uusi route `/api/ping`: kevyt health-check endpoint (ei levy-I/O:ta)
- [mediaplayer.py] Uusi `MEDIA_GUEST_DIR` (`media_guest/`): guest-käyttäjien mediatiedostojen hakemisto
- [mediaplayer.py] Uusi route `GET /guest`: guest-käyttöliittymä (`admin_guest.html`)
- [mediaplayer.py] Uusi route `GET /api/guest/list`: listaa media_guest-hakemiston tiedostot
- [mediaplayer.py] Uusi route `POST /api/guest/upload`: tiedostojen ja ZIP-pakettien lataus media_guest-hakemistoon
- [mediaplayer.py] Uusi route `POST /api/guest/delete-file`: tiedoston poisto media_guest-hakemistosta polkuturvalla
- [mediaplayer.py] Uusi route `POST /api/guest/rename-file`: tiedoston uudelleennimeäminen media_guest-hakemistossa polkuturvalla
- [mediaplayer.py] Uusi route `GET /media_guest/<filename>`: staattisten tiedostojen tarjoilu media_guest-hakemistosta
- [mediaplayer.py] Uudet asetukset `guest_enabled` ja `guest_shuffle_enabled` (default: `True`) — guest-median näyttö ja sekoitus feedissä
- [mediaplayer.py] `api_save_settings()`: tuki `guest_enabled` ja `guest_shuffle_enabled` -asetuksille
- [templates/admin_guest.html] Uusi guest-käyttöliittymä: ladattujen tiedostojen selaus ja poisto, kuva/videomäärät
- [templates/admin.html] Guest-URL lisätty yläosan osoiteriville muiden näyttö-URL:ien jatkoksi
- [templates/admin.html] Uusi osio 4 "Guest sisältö" omilla "Guest-media näkyvissä" ja "Sekoita guest-media" -toggleilla, tiedostolaskurilla (Kuvat/Videot) ja Tiedostot-modali (muokkaus/poisto)
- [templates/display.html] `fetchPlaylist()`: lisätty `/api/guest/list`-haku guest-tiedostoille
- [templates/display.html] `rebuildPlaylist()`: guest-media neljäntenä osiona (playlist → general → external → guest), deduplikointi, shuffle
- [templates/display.html] `pollSettings()` ja `next()`: guest-asetusmuutosten tunnistus

## [Unreleased] - 2026-05-12
- [mediaplayer.py] Uusi asetus `general_shuffle_enabled` (default: `True`) — osion 2 oma sekoitustoggle
- [mediaplayer.py] `api_save_settings()`: tuki `general_shuffle_enabled`-asetuksen tallennukselle
- [templates/admin.html] Osion 2 "Sekoita näytettäessä osion sisältö"-toggle ohjaa nyt `general_shuffle_enabled` (aiemmin ohjasi virheellisesti globaalia `shuffle_enabled`)
- [templates/display.html] `rebuildPlaylist()`: uusi keskitetty funktio soittolistan rakennukseen — osiokohtaiset shufflet, deduplikointi `src`-kentän mukaan, osion 1 järjestys säilyy aina käyttäjän määrittämänä
- [templates/display.html] `rebuildPlaylist()`: osio 2 sekoitetaan `general_shuffle_enabled` mukaan, osio 3 `external_shuffle_enabled` mukaan — ei enää globaalia shufflea joka rikkoi osion 1 järjestyksen
- [templates/display.html] `fetchPlaylist(force)`: promise-cache — data haetaan vain kerran, ei 3 HTTP-kutsua per medianvaihto
- [templates/display.html] `pollSettings()`: kevyt 10s pollaus asetusmuutoksille (vain `/api/playlist`), triggeröi täyden refetchin + rebuildin vain kun asetukset muuttuvat
- [templates/display.html] Poistettu `shuffle_enabled` globaali shuffle — osio 1 pysyy aina käyttäjän järjestyksessä, osiot 2 ja 3 shufflataan omien asetustensa mukaan
- [templates/display.html] Korjattu startup double-rebuild (rebuildPlaylist + next molemmat rebuildasivat)
- [templates/display.html] Korjattu epäyhtenäiset totuusarvotarkistukset: `shuffle_enabled`/`external_shuffle_enabled` molemmat `!== false`

## [Unreleased] - 2026-05-11
- [mediaplayer.py] Uusi: `convert_external_to_mp4()` — ulkoisten AVI/WMV/MOV/MKV-tiedostojen automaattikonversio MP4:ksi, originaaleja ei muokata
- [mediaplayer.py] `CONVERTED_CACHE_DIR` (`media_converted/`): konvertoidut tiedostot välimuistissa, uudelleenkonversio vain jos lähdetiedosto muuttunut
- [mediaplayer.py] `CONVERTED_CACHE_MAP` (`media_converted/_cache_map.json`): JSON-kartta lähdetiedosto → välimuistitiedosto, mahdollistaa alkuperäiset tiedostonimet
- [mediaplayer.py] Konvertoidut MP4-tiedostot säilyttävät alkuperäisen nimen (esim. MVI_4915.mp4), vain nimikollisioissa lisätään lyhyt hash-pääte
- [mediaplayer.py] `_load_cache_map()` / `_save_cache_map()`: apufunktiot konversiokartan hallintaan
- [mediaplayer.py] `scan_external_dirs()`: skannaa nyt myös CONVERT_EXTENSIONS-tiedostot, konvertoi ne automaattisesti ja lisää feediin videoina
- [mediaplayer.py] Uusi route `GET /media_converted/<filename>`: tarjoilee konvertoidut MP4-tiedostot
- [mediaplayer.py] `_ffmpeg_cmd()` apufunktio: ffmpeg-polun resolvointi keskitetysti

## [Unreleased] - 2026-05-10
- [templates/admin.html] Tiedostot-modaali (Osio 2): hakemistopuunäkymä kansioittain, avattavat/suljettavat kansiot, tiedostomäärät
- [templates/admin.html] Tiedostoriveille Poista (🗑️) ja Nimeä uudelleen (✏️) -painikkeet, `confirm()`/`prompt()`-varmistukset
- [mediaplayer.py] `POST /api/general/delete-file`: tiedoston poisto polkuturvalla + playlist.json-päivitys
- [mediaplayer.py] `POST /api/general/rename-file`: tiedoston uudelleennimeäminen polkuturvalla + playlist.json-päivitys
- [templates/admin.html] Tiedostot-modaalin mobiilioptimointi: inline-tyylit, kapea 500px max-width, 48px rivikorkeus, flex-palstaus
- [templates/admin.html] Poista tiedostot UI-painike poistettu ja sitä tukeva JS-funktio.
- [mediaplayer.py] `api_general_upload()`: alikansiotuki — `folder`-parametri pakollinen, tiedostot menevät `media_general/{kansio}/`-alle
- [mediaplayer.py] `api_general_upload()`: alkuperäiset tiedostonimet säilyvät (ei enää MD5-tiivistettä), duplikaatit ohitetaan tiedostonimen perusteella
- [mediaplayer.py] `api_general_upload()`: videokonversio (AVI/WMV/MOV/MKV → MP4) säilyttää alkuperäisen nimen, vain pääte vaihtuu
- [mediaplayer.py] `api_general_delete()`: `<path:filename>` tuki alihakemistopolulle, polkupakotusestot (..-traversal, resolve-tarkistus)
- [templates/admin.html] Mediakirjasto-paneeliin "Kansion nimi" -tekstikenttä ennen tiedostovalitsinta
- [templates/admin.html] `uploadGeneralFiles()`: tarkistaa kansion nimen, lähettää `folder`-parametrin FormData:ssa

## [Unreleased] - 2026-05-09
- [templates/admin.html] `formatDuration()`: kestojen formaattimuunnos — alle 60 min näyttää minuutteina ("45 min"), 60+ min näyttää tunteina ja minuutteina ("1.15h", "28.57h")
- [templates/admin.html] Kolme kestoyhteenvetoa (kustomoitu sisältö, mediakirjasto, liitetyt hakemistot) käyttävät nyt `formatDuration()`
- [templates/admin.html] Sivun uudelleenlataus (`location.reload()`) toimintojen jälkeen: Tallenna-asetukset, +Lataa, Lisää hakemisto, Päivitä-hakemistot — varmistaa että kestolaskelmat päivittyvät aina

## [Unreleased] - 2026-05-08
- [templates/display.html] "Napauta aloittaaksesi" -overlay häviää automaattisesti 5s jälkeen fade-out-animaatiolla (TV-käyttö)
- [mediaplayer.py] Lyhennetyt URL-polut: `/images` → `/img`, `/videos` → `/vid` (helpompi kirjoittaa televisiolla)
- [templates/display.html] Kuva/video-virheenkäsittely: `error`-tapahtuma skipaa rikkinäisen median heti seuraavaan kohteeseen
- [templates/display.html] Automaattinen sivun uudelleenlataus 2 tunnin välein (selaimen jäätymisen varalta)

## [Unreleased] - 2026-05-06
- [mediaplayer.py] Uusi ominaisuus: "Liitetyt hakemistot" — ulkoisten levyhakemistojen tuki (esim. USB-levyt)
- [mediaplayer.py] `scan_external_dirs()`: startup-skannaus rekisteröidyille hakemistoille, puuttuvat polut ohitetaan varoituksella
- [mediaplayer.py] `EXTERNAL_CACHE`: startupissa cachettu tiedostolista, ei uudelleenskannausta feedin aikana
- [mediaplayer.py] Uudet API-reitit: `/api/external/list`, `/api/external/add`, `/api/external/<id>` (PATCH/DELETE), `/api/external/refresh`, `/api/external/file`
- [mediaplayer.py] `/api/external/file`: tarjoilee tiedostoja suoraan levyltä `send_file`-funktiolla, polkuvalidointi rekisteröityjä hakemistoja vasten
- [mediaplayer.py] `playlist.json` laajennettu: `external_dirs`-taulukko (id, path, label, enabled)
- [templates/admin.html] Uusi "Liitetyt hakemistot" -paneeli: polun ja nimikkeen syöttö, lista hallittavista hakemistoista, enable/disable, poisto, päivitys
- [templates/display.html] `fetchPlaylist()` hakee nyt myös `/api/external/list` — ulkoiset tiedostot yhdistetään feediin
- [templates/display.html] Ulkoiset tiedostot sekoittuvat `generalFiles`-tiedostojen kanssa samaan massaan shuffle-tilan mukaan

## [Unreleased] - 2026-05-01
- [templates/display.html] Korjattu: Sekoita-togglen muutos astuu voimaan heti seuraavalla sisällönvaihdolla, ei vasta koko listan kierrettyä
- [mediaplayer.py] Sekoita-asetus (shuffle_enabled, default true) /api/settings:iin
- [templates/admin.html] Sekoita-toggle "Sisältö joka näytetään default asetuksilla" -otsikon alle
- [templates/display.html] Sekoita-logiikka: custom-itemit aina ensin järjestyksessä, general-itemit sekoitetaan vain shuffle_enabled=true
- [mediaplayer.py] Lista2 (media_general): uudet endpointit list, upload, delete, clear, archive
- [mediaplayer.py] ZIP-tuki: purkaa tiedostot suoraan media_general-kansioon, tukee alihakemistoja
- [mediaplayer.py] FFmpeg-konversio: AVI/WMV/MOV/MKV → MP4 automaattisesti latauksen yhteydessä
- [mediaplayer.py] Paikallinen ffmpeg.exe: etsitään ensin projektin juuresta, sitten PATH:sta
- [mediaplayer.py] Duplikaattiesto: MD5-hash tiedostonimeksi, sama tiedosto ohitetaan
- [mediaplayer.py] MAX_CONTENT_LENGTH nostettu 2000MB (ZIP-tuki)
- [mediaplayer.py] Arkistoi-endpoint: siirtää media_general-tiedostot Archive_YYYY-MM-DD_HH-MM -kansioon
- [mediaplayer.py] Default-asetukset: video_audio (bool) ja video_duration (full/default)
- [mediaplayer.bat] FFmpeg-autoasennus: kutsuu PowerShell + winget CMD-ikkunasta
- [templates/display.html] Lista2-sekoitus: Fisher-Yates shuffle kun media_general ei tyhjä
- [templates/display.html] video_duration=full: video pyörii loppuun, ended-event käynnistää seuraavan
- [templates/display.html] Android autoplay-korjaus: play().catch() mykistää ja yrittää uudelleen
- [templates/admin.html] Lista2-paneeli: lataus, tiedostolaskuri, Arkistoi, Tyhjennä kaikki
- [templates/admin.html] Uudet default-asetukset: Äänet (video), Videot näyttöaika
- [templates/admin.html] Latausstatus näyttää ladattu/ohitettu/virheitä erikseen
- [mediaplayer.py] Uusi default-asetus playback_buttons (default true) /api/settings:iin
- [templates/admin.html] Toistopainikkeet-asetus (Kyllä/Ei) default-asetuspaneliin "Videot näyttöaika" -kentän jälkeen
- [templates/display.html] Toistopainikkeet: << Play/Pause >> -painikkeet oikeassa alakulmassa, kun playback_buttons=true
- [templates/display.html] Toistopainikkeiden pause/resume: pysäyttää ajastimen ja videon, jatkaa jäljellä olevasta ajasta
- [templates/display.html] Toistopainikkeet näkyvät/piiloutuvat ilman fadea (teknisesti vakaampi, ei ristiriitoja siirtymien kanssa)

## [Unreleased] - 2026-04-29
- [projekti.md] Projektisuunnitelma ja spesifikaatio luotu
- [CLAUDE.md] Projektin käyttäytymissäännöt ja rakennekuvaus
- [requirements.txt] Minimaaliset riippuvuudet: Flask + Werkzeug
- [mediaplayer.bat] Käynnistysskripti: venv-luonti, asennus, palvelimen käynnistys, porttitarkistus
- [mediaplayer.py] Flask-backend: kaikki API-reitit, tiedostolataus, soittolistan hallinta
- [mediaplayer.py] Tietoturvakovennukset: tiedostokoko 50MB, URL-validointi, id-tarkistus, fade_type-whitelist, HTTP-otsikot
- [mediaplayer.py] Admin-reitti muutettu /admin → /adminloginhere
- [templates/display.html] Täysruutu-soitin: 5 siirtymätyyppiä + satunnainen, URL-saavutettavuustarkistus, cache-busting
- [templates/display.html] Korjattu puuttuva </script>-tagi (aiheutti tyhjän sivun)
- [templates/admin.html] Hallintapaneeli: soittolistan hallinta, drag-and-drop järjestys, esikatselu, asetukset
- [README.md] Asennusohje ja vianmääritys luotu
