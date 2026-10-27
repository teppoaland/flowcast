#!/usr/bin/env python3
"""
Duplikaattitiedostojen etsintä- ja poistotyökalu.

Käyttää kaksivaiheista tunnistusta:
  1. Ryhmittele tiedostot koon mukaan (vain samankokoiset voivat olla duplikaatteja)
  2. Laske SHA256-tiiviste vain samankokoisille -> 100% varmat osumat

Soveltuu suurillekin (30 000+) tiedostokokoelmille.
"""

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Pakota UTF-8 Windows-terminaalissa (välttää cp1252-ongelmat)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Värikoodit / Unicode-merkit (ASCII-varalla)
# ---------------------------------------------------------------------------
try:
    import colorama
    colorama.init()
    RED = colorama.Fore.RED
    GREEN = colorama.Fore.GREEN
    YELLOW = colorama.Fore.YELLOW
    CYAN = colorama.Fore.CYAN
    RESET = colorama.Fore.RESET
except ImportError:
    RED = GREEN = YELLOW = CYAN = RESET = ""

# Border-merkit
BORDER_TL = "+"   # top-left
BORDER_TR = "+"   # top-right
BORDER_BL = "+"   # bottom-left
BORDER_BR = "+"   # bottom-right
BORDER_H = "-"    # horizontal
BORDER_V = "|"    # vertical
CHECK = "[OK]"
CROSS = "[X]"
STAR = "[K]"
WARN = "/!\\"
INFO = "[i]"


# ---------------------------------------------------------------------------
# Hash-funktiot
# ---------------------------------------------------------------------------
def hash_file(path: Path, algorithm: str = "sha256", chunk_size: int = 65536) -> str:
    """Laske tiedoston tiiviste puskuroituna – ei syö muistia isoilla tiedostoilla."""
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Tiedostojen skannaus
# ---------------------------------------------------------------------------
def scan_files(
    root: Path,
    extensions: Optional[set[str]] = None,
    exclude_dirs: Optional[set[str]] = None,
) -> list[Path]:
    """Palauta kaikki tiedostot hakemistopuusta, valinnaisella suodatuksella."""
    files: list[Path] = []
    exclude_dirs = exclude_dirs or set()

    for dirpath, dirnames, filenames in os.walk(root):
        # Estä skannaus tietyistä hakemistoista
        dirnames[:] = [d for d in dirnames if d.lower() not in exclude_dirs]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            try:
                if not fpath.is_file():
                    continue
                if extensions:
                    ext = fpath.suffix.lower()
                    if ext not in extensions:
                        continue
                files.append(fpath)
            except OSError:
                continue
    return files


# ---------------------------------------------------------------------------
# Duplikaattien etsintä (kaksivaiheinen)
# ---------------------------------------------------------------------------
def find_duplicates(
    files: list[Path],
    quick: bool = False,
) -> dict[str, list[Path]]:
    """
    Etsi duplikaatit kaksivaiheisesti:
      1. Ryhmittele tiedostokoon mukaan
      2. Laske hash vain ryhmille joissa useampi tiedosto
    Palauttaa dict: {hash: [polku1, polku2, ...]}
    """
    # Vaihe 1: ryhmittele koon mukaan
    print(f"\n{CYAN}[1/2] Ryhmitellään {len(files)} tiedostoa koon mukaan...{RESET}")
    size_map: dict[int, list[Path]] = defaultdict(list)
    for fpath in files:
        try:
            fsize = fpath.stat().st_size
            size_map[fsize].append(fpath)
        except OSError as e:
            print(f"{YELLOW}  {WARN} Ei paasy tiedostoon: {fpath} ({e}){RESET}")

    # Suodata pois uniikit koot
    candidates = {size: paths for size, paths in size_map.items() if len(paths) > 1}
    print(f"  -> {len(candidates)} kokoryhmaa joissa useampi tiedosto "
          f"(yht. {sum(len(v) for v in candidates.values())} tiedostoa)")

    if not candidates:
        print(f"\n{GREEN}{CHECK} Ei duplikaatteja loytynyt.{RESET}")
        return {}

    # Vaihe 2: hash vain epäillyille
    print(f"\n{CYAN}[2/2] Lasketaan tiivisteet epäillyille duplikaateille...{RESET}")
    hash_map: dict[str, list[Path]] = defaultdict(list)
    total = sum(len(v) for v in candidates.values())
    processed = 0

    for size, paths in candidates.items():
        for fpath in paths:
            try:
                if quick:
                    # Nopea "hybridi": lue vain alku + loppu (ei 100% varma)
                    # Tätä EI suositella tärkeille tiedostoille
                    h = _quick_hash(fpath)
                else:
                    h = hash_file(fpath)
                hash_map[h].append(fpath)
            except OSError as e:
                print(f"{YELLOW}  {WARN} Virhe luettaessa: {fpath} ({e}){RESET}")

            processed += 1
            if processed % 500 == 0:
                print(f"  ... {processed}/{total} tiedostoa käsitelty")

    print(f"  -> Valmis: {processed}/{total} tiedostoa kasitelty")

    # Suodata pois uniikit hashit
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return duplicates


def _quick_hash(path: Path) -> str:
    """Nopea hash: lue 4096 alusta + tiedostokoko + 4096 lopusta."""
    fsize = path.stat().st_size
    chunk = 4096
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        hasher.update(f.read(chunk))
        hasher.update(str(fsize).encode())
        if fsize > chunk * 2:
            f.seek(-chunk, os.SEEK_END)
            hasher.update(f.read(chunk))
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Poistologiikka
# ---------------------------------------------------------------------------
def delete_duplicates(
    duplicates: dict[str, list[Path]],
    keep: str = "first",
    dry_run: bool = True,
    log_file: Optional[Path] = None,
) -> tuple[int, int]:
    """
    Poista duplikaatit annetulla säilytyssäännöllä.
    Palauttaa (poistetut_tiedostot, vapautuneet_tavut).
    """
    deleted_count = 0
    freed_bytes = 0
    log_lines: list[str] = []

    for h, paths in duplicates.items():
        # Järjestä tiedostot säännön mukaan
        if keep == "newest":
            paths = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
        elif keep == "oldest":
            paths = sorted(paths, key=lambda p: p.stat().st_mtime)
        elif keep == "shortest_name":
            paths = sorted(paths, key=lambda p: len(p.name))
        elif keep == "longest_name":
            paths = sorted(paths, key=lambda p: len(p.name), reverse=True)
        # default "first": säilytä ensimmäinen, poista loput

        keep_path = paths[0]
        remove_paths = paths[1:]

        for rp in remove_paths:
            try:
                fsize = rp.stat().st_size
                if dry_run:
                    print(f"  [DRY-RUN] Poistettaisiin: {rp}")
                else:
                    rp.unlink()
                    print(f"  {RED}{CROSS} Poistettu:{RESET} {rp}")
                deleted_count += 1
                freed_bytes += fsize
                log_lines.append(f"{'[DRY-RUN] ' if dry_run else ''}POISTETTU {rp} "
                                 f"({fsize} tavua) – säilytetty {keep_path}")
            except OSError as e:
                print(f"{RED}  {CROSS} Virhe poistettaessa: {rp} ({e}){RESET}")
                log_lines.append(f"VIRHE {rp}: {e}")

    # Kirjoita loki
    if log_file and log_lines:
        with open(log_file, "w", encoding="utf-8") as lf:
            lf.write("\n".join(log_lines))
        print(f"\n  Loki kirjoitettu: {log_file}")

    return deleted_count, freed_bytes


# ---------------------------------------------------------------------------
# Raportointi
# ---------------------------------------------------------------------------
def print_summary(duplicates: dict[str, list[Path]]) -> None:
    """Tulosta yhteenveto löydetyistä duplikaateista."""
    if not duplicates:
        return

    total_dup_files = sum(len(v) - 1 for v in duplicates.values())
    total_wasted = 0
    for paths in duplicates.values():
        wasted = sum(p.stat().st_size for p in paths[1:])
        total_wasted += wasted

    print(f"\n{BORDER_H * 60}")
    print(f"{YELLOW}DUPLIKAATTIYHTEENVETO:{RESET}")
    print(f"  Uniikkeja tiedostoja (hash): {len(duplicates)}")
    print(f"  Ylimaaraisia kopioita:        {total_dup_files}")
    print(f"  Vapautuvaa tilaa:             {_format_bytes(total_wasted)}")
    print(f"{BORDER_H * 60}")

    # Näytä esimerkit
    print(f"\n{CYAN}Löydetyt duplikaattiryhmät (näytetään max 20):{RESET}")
    for i, (h, paths) in enumerate(duplicates.items()):
        if i >= 20:
            print(f"  ... ja {len(duplicates) - 20} muuta ryhmää")
            break
        print(f"\n  Hash: {h[:16]}...  ({len(paths)} kopiota, "
              f"{_format_bytes(sum(p.stat().st_size for p in paths[1:]))} vapautuu)")
        for j, p in enumerate(paths):
            marker = STAR if j == 0 else CROSS
            print(f"    {marker} {p}")


def _format_bytes(b: int) -> str:
    """Muotoile tavut ihmisluettavaan muotoon."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


# ---------------------------------------------------------------------------
# Pääohjelma
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Etsi ja poista duplikaattitiedostoja hakemistopuusta.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esimerkkejä:
  python duplicate_finder.py C:\\Kuvat
      Etsi duplikaatit hakemistosta (dry-run, ei poisteta)

  python duplicate_finder.py C:\\Kuvat --delete
      Etsi JA poista duplikaatit (säilytetään ensimmäinen löydetty)

  python duplicate_finder.py C:\\Kuvat --delete --keep newest
      Poista duplikaatit, säilytä uusin versio

  python duplicate_finder.py C:\\Kuvat --ext .jpg .png .mp4
      Etsi duplikaatteja vain tietyistä tiedostotyypeistä

  python duplicate_finder.py C:\\Kuvat --quick
      Nopea tila (hybridi-hash, hieman epävarmempi mutta 3-10x nopeampi)
        """,
    )

    parser.add_argument(
        "directory",
        type=str,
        help="Skannattava hakemisto",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Poista duplikaatit (oletus: dry-run, vain näyttää mitä poistettaisiin)",
    )
    parser.add_argument(
        "--keep",
        type=str,
        choices=("first", "newest", "oldest", "shortest_name", "longest_name"),
        default="first",
        help="Mikä tiedosto säilytetään? (oletus: first = ensimmäinen löydetty)",
    )
    parser.add_argument(
        "--ext",
        nargs="+",
        default=None,
        help="Käsittele vain tiedostot joilla on nämä päätteet "
             "(esim. --ext .jpg .png .mp4). Oletus: kaikki tiedostotyypit.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Nopea tila: käytä hybridi-hashia (alku+koko+loppu). "
             "Noin 3-10x nopeampi, mutta teoreettisesti epävarmempi.",
    )
    parser.add_argument(
        "--exclude-dir",
        nargs="+",
        default=None,
        help="Ohita nämä alihakemistot (esim. --exclude-dir thumbnails temp)",
    )
    parser.add_argument(
        "--log",
        type=str,
        default=None,
        help="Kirjoita poistoloki tiedostoon (oletus: duplicate_log.txt)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Ohita varmistuskysymys poistettaessa",
    )

    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"{RED}Virhe: '{root}' ei ole kelvollinen hakemisto.{RESET}")
        sys.exit(1)

    # Valmistele suodattimet
    extensions = None
    if args.ext:
        extensions = {e.lower() if e.startswith(".") else f".{e.lower()}"
                      for e in args.ext}

    exclude_dirs = set(d.lower() for d in (args.exclude_dir or []))

    print(f"{CYAN}{BORDER_H * 54}{RESET}")
    print(f"{CYAN}  DUPLIKAATTITIEDOSTOJEN ETSINTÄ{RESET}")
    print(f"{CYAN}{BORDER_H * 54}{RESET}")
    print(f"\n  Hakemisto:     {root}")
    print(f"  Tiedostopäätteet: {'kaikki' if extensions is None else ', '.join(sorted(extensions))}")
    print(f"  Tila:            {'NOPEA (hybridi)' if args.quick else 'TARKKA (SHA256)'}")
    print(f"  Poisto:          {'PÄÄLLÄ' if args.delete else 'DRY-RUN (ei poisteta)'}")
    if args.delete:
        print(f"  Säilytyssääntö:  {args.keep}")

    # Skannaa tiedostot
    print(f"\n{CYAN}Skannataan tiedostoja...{RESET}")
    files = scan_files(root, extensions=extensions, exclude_dirs=exclude_dirs)
    print(f"  -> Loydetiin {len(files)} tiedostoa")

    if len(files) < 2:
        print(f"{GREEN}{CHECK} Liian vahan tiedostoja - ei mahdollisia duplikaatteja.{RESET}")
        return

    # Etsi duplikaatit
    duplicates = find_duplicates(files, quick=args.quick)

    if not duplicates:
        print(f"\n{GREEN}{CHECK} Ei duplikaatteja loytynyt.{RESET}")
        return

    # Näytä yhteenveto
    print_summary(duplicates)

    # Poista jos pyydetty
    if args.delete:
        if not args.yes:
            print(f"\n{YELLOW}{BORDER_H * 54}{RESET}")
            print(f"{YELLOW}  {WARN} VAROITUS: Duplikaatit poistetaan pysyvasti!{RESET}")
            print(f"{YELLOW}{BORDER_H * 54}{RESET}")
            vastaus = input(f"\n  Jatketaanko poistoon? (k/e): ").strip().lower()
            if vastaus not in ("k", "kyllä", "y", "yes"):
                print(f"{GREEN}{CHECK} Peruutettu.{RESET}")
                return

        log_path = Path(args.log) if args.log else Path(root) / "duplicate_log.txt"
        deleted, freed = delete_duplicates(
            duplicates,
            keep=args.keep,
            dry_run=False,
            log_file=log_path,
        )
        print(f"\n{GREEN}{CHECK} Valmis! Poistettiin {deleted} tiedostoa, "
              f"vapautui {_format_bytes(freed)} tilaa.{RESET}")
    else:
        print(f"\n{CYAN}{INFO} Tama oli dry-run. Aja --delete poistaaksesi duplikaatit.{RESET}")


if __name__ == "__main__":
    main()
