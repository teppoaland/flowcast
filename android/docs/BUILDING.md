# FlowCast Android — Build Guide

## Vaatimukset (Prerequisites)

| Komponentti | Versio | Tarkistus |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Flet CLI | 0.85+ | `pip show flet` |
| Flutter SDK | 3.x | `flutter --version` |
| Android SDK | API 34 | `%ANDROID_HOME%` |
| JDK | 17+ | `java --version` |

---

## Quick Build (Windows)

### 1. Aseta ympäristö

```cmd
cd <projektikansio>\android
pip install flet httpx
```

### 2. Buildaa APK

```cmd
set PYTHONIOENCODING=utf-8 && flet build apk ^
    --org com.flowcast.android ^
    --project "FlowCast Android" ^
    --product "FlowCast" ^
    --description "FlowCast Android - Taildrop File Manager" ^
    --android-permissions "android.permission.INTERNET=true" ^
    --android-permissions "android.permission.ACCESS_NETWORK_STATE=true" ^
    --android-permissions "android.permission.ACCESS_WIFI_STATE=true" ^
    --android-permissions "android.permission.READ_EXTERNAL_STORAGE=true" ^
    --android-permissions "android.permission.WRITE_EXTERNAL_STORAGE=true" ^
    --android-permissions "android.permission.MANAGE_EXTERNAL_STORAGE=true" ^
    --android-permissions "android.permission.READ_MEDIA_IMAGES=true" ^
    --android-permissions "android.permission.READ_MEDIA_VIDEO=true" ^
    --android-permissions "android.permission.READ_MEDIA_AUDIO=true" ^
    --android-features "android.hardware.camera=false" ^
    --android-features "android.hardware.camera.autofocus=false" ^
    --no-android-splash ^
    --no-rich-output ^
    --skip-flutter-doctor
```

> **HUOM!** `set PYTHONIOENCODING=utf-8 &&` on **pakollinen** Windowsissa. Ilman tätä Fletin build-työkalun Rich-kirjasto kaatuu `UnicodeEncodeError`-virheeseen.

### 3. Valmis APK

```
build\apk\FlowCast Android.apk
```

---

## APK-yhteensopivuussäännöt

Näitä ei saa käyttää — APK:n Flet-versio ei tue:

| Shorthand (älä käytä) | Korvaava raaka muoto (käytä) |
|---|---|
| `ft.alignment.center` / `.CENTER` | `ft.Alignment(0, 0)` |
| `ft.padding.only(top=6)` | `ft.Padding(0, 6, 0, 0)` |
| `ft.padding.symmetric(horizontal=16, vertical=8)` | `ft.Padding(16, 8, 16, 8)` |
| `ft.TextButton("teksti")` / `ft.FilledButton("teksti")` | `ft.TextButton(content=ft.Text("teksti"))` |
| `ft.TextOverflow.ELLIPSIS` (enum) | `"ellipsis"` (merkkijono) |
| `ft.ScrollMode.AUTO` missään Columnissa jossa on `ListView(expand=True)` | Poista scroll kokonaan |
| `NavigationBar` `Container`-wrapperin sisällä | `self.page.navigation_bar = ...` (natiivi) |

---

## Tunnettu ongelma: ListView-skrollaus Androidilla

**Status:** Ei ratkaistu (v2.1.3). Navigaatio ja FAB toimivat, mutta tiedostolistat eivät skrollaa.

**Juurisyy:** Fletin Android-moottori (erityisesti Samsung One UI -laitteilla) ei rajoita ListView'n korkeutta oikein kun se on sisäkkäisten `SafeArea → Column(expand=True) → Container(expand=True) → Column(expand=True) → ListView(expand=True)` ketjussa. Androidin asettelumoottori "luovuttaa" korkeuden rajoittamisen ja piirtää listan yhtenä äärettömänä pötkönä.

**Kokeillut ratkaisut (eivät toimineet):**
- `AnimatedSwitcher` → suora `Container.content` swap
- `ListView` suoraan `Column(expand=True)` lapsena ilman Container-wrappereita
- `self.page.navigation_bar` (natiivi OS-tason alapalkki) — nav näkyy muttei korjaa listan skrollausta
- Kaikkien `scroll=ScrollMode.AUTO` poisto Columneista

**Ainoa tunnettu 100% varma ratkaisu Flet-Androidilla:**
```
Page → ListView (sisältää headerit + pikanapit EDELLÄ tiedostorivejä)
```
Eli koko UI on yksi iso `ListView` — ei sisäkkäisiä Column/Container rakenteita ollenkaan. Tämä vaatii koko UI-puun uudelleenkirjoituksen.

---

## Virhetaulukko

- **`UnicodeEncodeError: 'charmap' codec can't encode character`** — lisää `set PYTHONIOENCODING=utf-8 &&`
- **`module 'flet.controls.alignment' has no attribute 'center'` / `'CENTER'`** — käytä `ft.Alignment(0, 0)`
- **`module 'flet.controls.padding' has no attribute 'only'` / `'symmetric'`** — käytä `ft.Padding(L, T, R, B)`
- **`TextButton init() unexpected arg 'text'`** — käytä `content=ft.Text("Teksti")`
- **`flutter: command not found`** — `winget install Google.Flutter`
- **`ANDROID_HOME not set`** — asenna Android Studio tai SDK

---

## Versiohistoria

Katso [CHANGELOG.md](CHANGELOG.md)
