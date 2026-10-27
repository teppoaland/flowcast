# FlowCast Android — Changelog

## v10.02 (2026-10-27) — Versiot yhdenmukaisiksi

- `APP_VERSION` = `10.02`, sama numero kuin palvelimen `VERSION`-tiedostossa
- Ei toiminnallisia muutoksia; palvelimen käynnistysbattia (`mediaplayer.bat`) parannettu (ajokansio + datakansion tiedotus)

---

## v10.01 (2026-10-27) — Tuoteversio käyttöön

### Muutettu
- `APP_VERSION` = `10.01` — sama numero kuin palvelimen `VERSION`-tiedostossa (`android/VERSION` päivitetty)
- Yläpalkissa pieni versiotunnus `FlowCast`-otsikon vieressä
- Palvelimen `GET /api/android/ping` palauttaa nyt myös `version`-kentän

---

## v2.1.3 (2026-05-28) — Native Navigation Bar

### Muutettu
- `self.page.navigation_bar` (natiivi OS-tason alapalkki) — nav ei enää taistele Column-layoutin kanssa
- `self.page.floating_action_button` — FAB natiivina

### Tunnettu ongelma
- **ListView-skrollaus ei toimi** — Fletin Android-moottori (Samsung One UI) ei rajoita sisäkkäisten expand-ketjujen läpi olevan ListView'n korkeutta. Ainoa tunnettu ratkaisu: koko UI yhdeksi ListViewksi. Katso [BUILDING.md](BUILDING.md).

---

## v2.1.0 (2026-05-28)

- ScrollMode.AUTO poistettu, main_axis_size="min", overflow="ellipsis" merkkijonona

## v2.0.8 (2026-05-28)

- Nav suoraan Column-lapsena, ListView ilman Container-wrapperia

## v2.0.5—v2.0.6 (2026-05-28)

- Tile-kartta, inline toggle, auto-connect retry, Select All -visualisointi

## v2.0.0 (2026-05-28)

- Täysi uudelleenkirjoitus: 4 välilehteä

## v1.0.x (2026-05-26—28)

- Ensimmäiset Android-versiot
