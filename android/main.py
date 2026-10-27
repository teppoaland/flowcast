"""
FlowCast Android — File Manager & Uploader
Flet-based Android app for transferring files to PC via Tailscale.
Supports: Taildrop upload, file browsing, remote folder management.
Android 13 compatible.
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime
import flet as ft
import httpx

APP_NAME = "FlowCast Pro"
APP_VERSION = "10.02"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5010
DEFAULT_TARGET = "android_upload"

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".mp4", ".avi", ".wmv", ".mov", ".mkv",
                ".gif", ".webp", ".bmp", ".zip", ".pdf", ".apk"}

# Quick-access Android paths
ANDROID_DOWNLOAD = "/storage/emulated/0/Download"
ANDROID_CAMERA = "/storage/emulated/0/DCIM/Camera"
ANDROID_SCREENSHOTS = "/storage/emulated/0/DCIM/Screenshots"
ANDROID_PICTURES = "/storage/emulated/0/Pictures"


def fmt_size(sz: int) -> str:
    if sz < 1024: return f"{sz} B"
    elif sz < 1048576: return f"{sz/1024:.1f} KB"
    elif sz < 1073741824: return f"{sz/1048576:.1f} MB"
    return f"{sz/1073741824:.2f} GB"


def fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def ext_icon(ext: str) -> str:
    e = ext.lower()
    if e in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}: return "🖼️"
    if e in {".mp4", ".avi", ".wmv", ".mov", ".mkv"}: return "🎬"
    if e == ".zip": return "📦"
    if e == ".apk": return "📱"
    if e == ".pdf": return "📄"
    return "📎"


def server_url(host: str, port: int, path: str = "") -> str:
    h = host.strip().rstrip("/")
    if not h.startswith("http"): h = f"http://{h}"
    if port and port != 80: h = f"{h}:{port}"
    return f"{h}{path}" if path else h


def _is_android() -> bool:
    try:
        import android  # noqa
        return True
    except ImportError:
        pass
    import sys
    return hasattr(sys, "getandroidapilevel")


class FlowCastApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = APP_NAME
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.bgcolor = "#0f172a"

        self.C = {
            "bg": "#0f172a", "panel": "#1e293b", "card": "#334155",
            "accent": "#3b82f6", "accent2": "#2563eb",
            "green": "#10b981", "red": "#ef4444", "orange": "#f59e0b",
            "yellow": "#eab308", "text": "#f1f5f9", "muted": "#94a3b8",
            "border": "#334155",
        }

        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.server_online = False
        self.selected_files: set = set()
        self.delete_after = False
        self.dest_folder = DEFAULT_TARGET
        self.uploading = False
        self.local_current_dir = ANDROID_DOWNLOAD
        self.taildrop_dir = ANDROID_DOWNLOAD
        self.remote_folders: list = []
        self.remote_files: list = []
        self._td_tiles = {}
        self.is_android = _is_android()

        self._detect_paths()

        try:
            self._build_ui()
        except Exception as e:
            page.add(ft.SafeArea(ft.Text(f"Kriittinen UI-virhe: {e}", color="red", size=16)))
            return

        self.page.run_task(self._init_app)

    def _detect_paths(self):
        if self.is_android:
            for p in [ANDROID_DOWNLOAD, ANDROID_CAMERA]:
                if os.path.isdir(p):
                    self.taildrop_dir = p
                    self.local_current_dir = p
                    break
        else:
            self.taildrop_dir = str(Path.home() / "Downloads")
            self.local_current_dir = self.taildrop_dir

    def _build_ui(self):
        self.status_icon = ft.Icon(ft.Icons.CIRCLE, color=self.C["red"], size=10)
        self.status_text = ft.Text("Offline", size=11, color=self.C["muted"])

        # NATIVE OS-LEVEL NAVIGATION BAR
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self._on_nav,
            bgcolor=self.C["panel"],
            indicator_color=self.C["card"],
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Pika"),
                ft.NavigationBarDestination(icon=ft.Icons.FOLDER_OPEN, label="Selaa"),
                ft.NavigationBarDestination(icon=ft.Icons.DNS, label="Serveri"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Asetukset"),
            ],
        )

        # NATIVE OS-LEVEL FAB
        self.page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.CLOUD_UPLOAD,
            bgcolor=self.C["accent"],
            on_click=self._fab_upload,
        )

        self.tab_taildrop = self._build_taildrop_tab()
        self.tab_browse = self._build_browse_tab()
        self.tab_server = self._build_server_tab()
        self.tab_settings = self._build_settings_tab()
        self.all_tabs = [self.tab_taildrop, self.tab_browse, self.tab_server, self.tab_settings]

        self.content_container = ft.Container(expand=True, padding=ft.Padding(12, 8, 12, 8))
        self.dest_label = ft.Text(DEFAULT_TARGET, size=12, color=self.C["accent"], weight="bold")

        self.page.add(
            ft.SafeArea(
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Text("FlowCast", size=20, weight="bold", color=self.C["text"]),
                                ft.Text(APP_VERSION, size=11, color=self.C["muted"]),
                            ], spacing=6),
                            ft.Container(expand=True),
                            ft.Row([self.status_icon, self.status_text], spacing=4),
                        ]),
                        padding=ft.Padding(20, 12, 20, 12),
                        bgcolor=self.C["panel"],
                    ),
                    self.content_container,
                ], expand=True, spacing=0)
            )
        )

        self.content_container.content = self.tab_taildrop

    def _on_nav(self, e):
        idx = int(e.data)
        self.content_container.content = self.all_tabs[idx]
        self.content_container.update()
        if idx == 0: self.page.run_task(self._refresh_taildrop)
        elif idx == 1: self.page.run_task(self._load_local, self.local_current_dir)
        elif idx == 2: self.page.run_task(self._refresh_server_tab)

    # ── TAB: Taildrop (Quick Upload) ────────────────────────────────────

    def _build_taildrop_tab(self):
        self.td_info = ft.Text("", size=11, color=self.C["muted"])
        self.td_list = ft.ListView(expand=True, spacing=2)

        self.td_quick_paths = ft.Row([
            self._quick_btn("📥 Lataukset", ANDROID_DOWNLOAD),
            self._quick_btn("📸 Kamera", ANDROID_CAMERA),
            self._quick_btn("🖼️ Kuvat", ANDROID_SCREENSHOTS),
        ], scroll="auto", spacing=6)

        self.td_select_all_cb = ft.Checkbox(
            label="Valitse kaikki", value=False,
            fill_color=self.C["accent"],
            on_change=lambda e: self.page.run_task(self._td_select_all, e),
        )

        return ft.Column([
            ft.Text("Taildrop-pikasiirto", size=16, weight="bold", color=self.C["text"]),
            ft.Text("Valitse tiedostoja ja lataa palvelimelle yhdellä napilla.", size=12, color=self.C["muted"]),
            ft.Divider(color=self.C["border"]),

            ft.Container(
                content=ft.Column([
                    ft.Text("Pikavalinta:", size=11, color=self.C["muted"]),
                    self.td_quick_paths,
                ], spacing=4),
                padding=ft.Padding(0, 0, 0, 8),
            ),

            ft.Container(
                content=ft.Column([
                    ft.Row([self.td_info, ft.Container(expand=True), self.td_select_all_cb]),
                    ft.Row([
                        ft.Text("Poista puhelimesta siirron jälkeen:", size=11, color=self.C["muted"]),
                        ft.Switch(value=False, active_color=self.C["red"],
                                  on_change=lambda e: setattr(self, "delete_after", e.control.value)),
                    ]),
                ], spacing=4),
                padding=ft.Padding(0, 4, 0, 8),
            ),

            # KRIITTINEN KORJAUS: Ei ylimääräistä Containeria! Lista on suoraan kiinni Columnissa.
            self.td_list,
            
        ], spacing=2, expand=True)

    def _quick_btn(self, label, path):
        return ft.TextButton(
            content=ft.Text(label, size=12, color=self.C["accent"]),
            style=ft.ButtonStyle(padding=ft.Padding(8, 4, 8, 4)),
            on_click=lambda e, p=path: self.page.run_task(self._td_set_path, p),
        )

    async def _td_set_path(self, path):
        if os.path.isdir(path):
            self.taildrop_dir = path
            self.local_current_dir = path
            await self._refresh_taildrop()

    async def _refresh_taildrop(self):
        if not self.taildrop_dir: return
        self.td_list.controls.clear()
        self.td_info.value = self.taildrop_dir.replace("/storage/emulated/0", "📱")
        try:
            entries = sorted(Path(self.taildrop_dir).iterdir(), key=lambda x: (not x.is_file(), x.stat().st_mtime), reverse=True)
        except Exception:
            self.td_list.controls.append(ft.Text("Ei lukuoikeutta — tarkista Android-oikeudet", color=self.C["red"], size=13))
            self.td_list.update()
            return

        self._td_tiles = {}
        found = 0
        for entry in entries:
            if not entry.is_file(): continue
            ext = entry.suffix.lower()
            if ext not in ALLOWED_EXTS: continue

            p = str(entry)
            st = entry.stat()
            sel = p in self.selected_files

            tile = ft.ListTile(
                leading=ft.Text(ext_icon(ext), size=22),
                title=ft.Text(entry.name, size=13, color=self.C["text"], overflow="ellipsis"),
                subtitle=ft.Text(f"{fmt_size(st.st_size)} • {fmt_time(st.st_mtime)}", size=11, color=self.C["muted"]),
                dense=True, selected=sel, selected_color=self.C["accent"],
                on_click=lambda e, pp=p: self._td_toggle(pp),
            )
            container = ft.Container(
                content=tile, border_radius=8, bgcolor=self.C["card"] if sel else None,
                padding=ft.Padding(4, 0, 4, 0), margin=ft.Padding(0, 1, 0, 1),
            )
            self.td_list.controls.append(container)
            self._td_tiles[p] = (container, tile)
            found += 1

        if found == 0:
            self.td_list.controls.append(ft.Text("Ei mediatiedostoja tässä kansiossa", color=self.C["muted"], size=14))
        self.td_info.update(); self.td_list.update()

    def _td_toggle(self, path):
        if path in self.selected_files:
            self.selected_files.discard(path); new_sel = False
        else:
            self.selected_files.add(path); new_sel = True
        
        if hasattr(self, '_td_tiles') and path in self._td_tiles:
            container, tile = self._td_tiles[path]
            tile.selected = new_sel
            container.bgcolor = self.C["card"] if new_sel else None
            tile.update(); container.update()

    async def _td_select_all(self, e):
        val = e.control.value
        if hasattr(self, '_td_tiles'):
            for ps, (cont, tile) in self._td_tiles.items():
                if val: self.selected_files.add(ps)
                else: self.selected_files.discard(ps)
                tile.selected = val
                cont.bgcolor = self.C["card"] if val else None
                tile.update(); cont.update()

    # ── TAB: Browse ─────────────────────────────────────────────────────

    def _build_browse_tab(self):
        self.br_crumb = ft.Text("", size=11, color=self.C["accent"])
        self.br_list = ft.ListView(expand=True, spacing=2)
        self.br_quick_paths = ft.Row([
            self._quick_btn("📥 Download", ANDROID_DOWNLOAD),
            self._quick_btn("📸 Camera", ANDROID_CAMERA),
            self._quick_btn("🏠 Home", "/storage/emulated/0"),
        ], scroll="auto", spacing=6)

        return ft.Column([
            ft.Text("Tiedostoselain", size=16, weight="bold", color=self.C["text"]),
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=self.C["text"], on_click=self._loc_back),
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=self.C["accent"], on_click=self._loc_refresh),
                ft.Container(expand=True),
                self.br_crumb,
            ]),
            self.br_quick_paths,
            
            # KRIITTINEN KORJAUS: Listaus on suoraan Columnissa ilman expand Containeria
            self.br_list,
            
        ], spacing=4, expand=True)

    async def _load_local(self, path):
        self.br_list.controls.clear()
        try:
            if not os.path.exists(path): path = "/storage/emulated/0" if self.is_android else str(Path.home())
            p = Path(path).resolve()
            self.local_current_dir = str(p)
            self.br_crumb.value = str(p).replace("/storage/emulated/0", "📱")
            self.br_crumb.update()

            try: items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                self.br_list.controls.append(ft.Text("Ei lukuoikeutta", color=self.C["red"], size=14))
                self.br_list.update(); return

            if self.local_current_dir not in ("/", "", "."):
                parent = str(p.parent)
                self.br_list.controls.append(
                    ft.ListTile(leading=ft.Icon(ft.Icons.ARROW_UPWARD, color=self.C["accent"]),
                                title=ft.Text(".. (ylös)", color=self.C["accent"], size=14),
                                dense=True, on_click=lambda e: self.page.run_task(self._load_local, parent))
                )

            for entry in items:
                if entry.name.startswith('.'): continue
                try:
                    if entry.is_dir():
                        self.br_list.controls.append(ft.ListTile(
                            leading=ft.Text("📁", size=22), title=ft.Text(entry.name, size=13, color=self.C["text"], overflow="ellipsis"),
                            subtitle=ft.Text("Kansio", size=11, color=self.C["muted"]), dense=True,
                            on_click=lambda e, ep=str(entry): self.page.run_task(self._load_local, ep)
                        ))
                    elif entry.is_file() and entry.suffix.lower() in ALLOWED_EXTS:
                        ep = str(entry); sel = ep in self.selected_files; st = entry.stat()
                        self.br_list.controls.append(ft.Container(
                            content=ft.ListTile(
                                leading=ft.Text(ext_icon(entry.suffix), size=22),
                                title=ft.Text(entry.name, size=13, color=self.C["text"], overflow="ellipsis"),
                                subtitle=ft.Text(f"{fmt_size(st.st_size)} • {fmt_time(st.st_mtime)}", size=11, color=self.C["muted"]),
                                dense=True, selected=sel, selected_color=self.C["accent"],
                                on_click=lambda e, ep2=ep: self._loc_toggle(ep2)
                            ),
                            border_radius=8, bgcolor=self.C["card"] if sel else None,
                            padding=ft.Padding(4, 0, 4, 0), margin=ft.Padding(0, 1, 0, 1),
                        ))
                except: continue
        except Exception as ex:
            self.br_list.controls.append(ft.Text(f"Virhe: {ex}", color=self.C["red"]))
        self.br_list.update()

    def _loc_toggle(self, path):
        if path in self.selected_files: self.selected_files.discard(path)
        else: self.selected_files.add(path)
        self.br_list.update()

    async def _loc_back(self, e=None):
        p = Path(self.local_current_dir)
        for _ in range(10):
            parent = str(p.parent)
            if os.path.exists(parent): await self._load_local(parent); return
            p = p.parent
        await self._load_local("/storage/emulated/0" if self.is_android else str(Path.home()))

    async def _loc_refresh(self, e=None):
        await self._load_local(self.local_current_dir)

    # ── TAB: Server ─────────────────────────────────────────────────────

    def _build_server_tab(self):
        self.srv_status = ft.Text("🔌 Ei yhteyttä", size=14, color=self.C["muted"])
        self.srv_folder_input = ft.TextField(
            hint_text="Uusi kansio...", dense=True, border_color=self.C["border"],
            color=self.C["text"], bgcolor=self.C["panel"], on_submit=self._create_folder,
        )
        self.srv_folder_list = ft.ListView(expand=True, spacing=2)
        self.srv_files_list = ft.ListView(expand=True, spacing=2)

        return ft.Column([
            ft.Text("Serverin hallinta", size=16, weight="bold", color=self.C["text"]),
            ft.Container(
                content=ft.Row([
                    self.srv_status, ft.Container(expand=True),
                    ft.TextButton(content=ft.Text("Testaa yhteys", color=self.C["accent"]),
                                  icon=ft.Icons.NETWORK_CHECK, on_click=lambda e: self.page.run_task(self._test_conn)),
                ]),
                padding=ft.Padding(12, 8, 12, 8), bgcolor=self.C["panel"], border_radius=10,
            ),
            ft.Divider(color=self.C["border"]),
            ft.Text("Kansiot palvelimella", size=13, weight="bold", color=self.C["text"]),
            ft.Row([
                self.srv_folder_input,
                ft.IconButton(icon=ft.Icons.CREATE_NEW_FOLDER, icon_color=self.C["accent"], on_click=self._create_folder),
            ]),
            ft.Container(content=self.srv_folder_list, height=150, border_radius=10, bgcolor=self.C["panel"], padding=ft.Padding(8, 4, 8, 4)),
            ft.Divider(color=self.C["border"]),
            ft.Row([
                ft.Text("Tiedostot palvelimella", size=13, weight="bold", color=self.C["text"]),
                ft.Container(expand=True),
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=self.C["accent"], on_click=lambda e: self.page.run_task(self._refresh_server_files)),
            ]),
            
            # KRIITTINEN KORJAUS: Ei expand Containeria täälläkään
            self.srv_files_list,
            
        ], spacing=4, expand=True)

    async def _refresh_server_tab(self):
        await self._refresh_folders()
        await self._refresh_server_files()

    # ── TAB: Settings ───────────────────────────────────────────────────

    def _build_settings_tab(self):
        self.set_host = ft.TextField(label="Palvelimen IP (Tailscale)", value=DEFAULT_HOST, border_color=self.C["border"], color=self.C["text"], bgcolor=self.C["panel"], prefix_icon=ft.Icons.COMPUTER)
        self.set_port = ft.TextField(label="Portti", value=str(DEFAULT_PORT), border_color=self.C["border"], color=self.C["text"], bgcolor=self.C["panel"], keyboard_type="number")
        self.set_target = ft.TextField(label="Kohdekansio palvelimella", value=DEFAULT_TARGET, border_color=self.C["border"], color=self.C["text"], bgcolor=self.C["panel"])

        return ft.Column([
            ft.Text("Asetukset", size=16, weight="bold", color=self.C["text"]),
            ft.Divider(color=self.C["border"]),
            ft.Text("Palvelinyhteys", size=13, weight="bold", color=self.C["muted"]),
            ft.Text("Kayta Tailscale-verkon IP-osoitetta (100.x.x.x).", size=11, color=self.C["muted"]),
            self.set_host, self.set_port,
            ft.Divider(color=self.C["border"]),
            ft.Text("Oletuskohde", size=13, weight="bold", color=self.C["muted"]),
            ft.Text("Tiedostot ladataan PC:llä palvelimen latauskansioon (oletus: android_upload)", size=11, color=self.C["muted"]),
            self.set_target,
            ft.Row([
                ft.FilledButton(content=ft.Text("Testaa yhteys"), icon=ft.Icons.NETWORK_CHECK, on_click=lambda e: self.page.run_task(self._test_conn), style=ft.ButtonStyle(bgcolor=self.C["accent"], color=self.C["text"])),
                ft.FilledButton(content=ft.Text("Tallenna"), icon=ft.Icons.SAVE, on_click=lambda e: self.page.run_task(self._save_settings), style=ft.ButtonStyle(bgcolor=self.C["green"], color=self.C["text"])),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ], spacing=8, expand=True, scroll="auto")

    # ── FAB Upload ──────────────────────────────────────────────────────

    async def _fab_upload(self, e=None):
        if not self.server_online: self._snack("Yhdista ensin palvelimeen!", self.C["red"]); return
        if not self.selected_files: self._snack("Valitse tiedostoja ensin", self.C["orange"]); return
        await self._do_upload(list(self.selected_files))

    async def _do_upload(self, paths):
        if not self.server_online or not paths: return
        self.uploading = True
        url = server_url(self.host, self.port, "/api/android/upload")
        total = len(paths)
        ok, fail, skip = 0, 0, 0
        self._snack(f"Ladataan {total} tiedostoa...", self.C["accent"])

        for idx, fp in enumerate(paths):
            if not os.path.isfile(fp): fail += 1; continue
            fn = os.path.basename(fp)
            try:
                async with httpx.AsyncClient(timeout=180) as c:
                    with open(fp, "rb") as f:
                        r = await c.post(url, files={"files": (fn, f, "application/octet-stream")}, data={"folder": self.dest_folder, "delete_after": str(self.delete_after).lower()})
                    if r.status_code == 200:
                        d = r.json()
                        if d.get("saved", 0) > 0:
                            ok += 1
                            if self.delete_after:
                                try: os.remove(fp)
                                except: pass
                        elif d.get("skipped", 0) > 0: skip += 1
                        else: fail += 1
                    else: fail += 1
            except: fail += 1
            await asyncio.sleep(0.05)

        msg = f"Valmis: {ok} ladattu"
        if skip: msg += f", {skip} ohitettu"
        if fail: msg += f", {fail} epaonnistui"
        self._snack(msg, self.C["green"] if fail == 0 else self.C["orange"])
        self.selected_files.clear(); self.uploading = False
        await self._refresh_taildrop(); await self._load_local(self.local_current_dir)
        if self.server_online: await self._refresh_server_files()

    # ── Logic ───────────────────────────────────────────────────────────

    async def _test_conn(self) -> bool:
        url = server_url(self.host, self.port, "/api/android/ping")
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(url)
                if r.status_code == 200 and r.json().get("ok"):
                    self.server_online = True
                    self.status_icon.color = self.C["green"]
                    self.status_text.value = "Online"
                    self.srv_status.value = f"Yhdistetty: {self.host}:{self.port}"
                    self.srv_status.color = self.C["green"]
                    self.status_text.update(); self.srv_status.update()
                    await self._refresh_folders(); await self._refresh_server_files()
                    self._snack("Yhdistetty palvelimeen", self.C["green"])
                    return True
        except: pass
        self.server_online = False
        self.status_icon.color = self.C["red"]
        self.status_text.value = "Offline"
        self.srv_status.value = "Ei yhteyttä"
        self.srv_status.color = self.C["red"]
        self.status_text.update(); self.srv_status.update()
        return False

    async def _init_app(self):
        await asyncio.sleep(0.5)
        try:
            h = await self.page.client_storage.get_async("host")
            p = await self.page.client_storage.get_async("port")
            da = await self.page.client_storage.get_async("delete_after")
            df = await self.page.client_storage.get_async("dest_folder")
            if h: self.host = h; self.set_host.value = h
            if p: self.port = p; self.set_port.value = str(p)
            if da is not None: self.delete_after = da
            if df: self.dest_folder = df; self.set_target.value = df
            self.set_host.update(); self.set_port.update(); self.set_target.update()
        except: pass
        for _ in range(3):
            if await self._test_conn(): break
            await asyncio.sleep(1.0)
        await self._refresh_taildrop()

    async def _save_settings(self):
        self.host = self.set_host.value.strip()
        try: self.port = int(self.set_port.value)
        except: self.port = DEFAULT_PORT
        self.dest_folder = self.set_target.value.strip() or DEFAULT_TARGET
        try:
            await self.page.client_storage.set_async("host", self.host)
            await self.page.client_storage.set_async("port", self.port)
            await self.page.client_storage.set_async("delete_after", self.delete_after)
            await self.page.client_storage.set_async("dest_folder", self.dest_folder)
            self._snack("Asetukset tallennettu", self.C["green"])
        except Exception as e: self._snack(str(e), self.C["red"])
        await self._test_conn()

    async def _refresh_folders(self):
        if not self.server_online: return
        url = server_url(self.host, self.port, "/api/android/folders")
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    self.remote_folders = r.json().get("folders", [])
                    self.srv_folder_list.controls.clear()
                    if not self.remote_folders: self.srv_folder_list.controls.append(ft.Text("Ei kansioita", color=self.C["muted"], size=12))
                    for f in sorted(self.remote_folders):
                        self.srv_folder_list.controls.append(
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.FOLDER, color=self.C["orange"]),
                                title=ft.Text(f, size=13, color=self.C["text"], overflow="ellipsis"),
                                dense=True,
                                trailing=ft.Row([
                                    ft.IconButton(icon=ft.Icons.CHECK, icon_color=self.C["accent"], icon_size=16, on_click=lambda e, ff=f: self._set_target_folder(ff), tooltip="Aseta kohteeksi"),
                                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=self.C["red"], icon_size=16, on_click=lambda e, ff=f: self.page.run_task(self._del_folder, ff)),
                                ], spacing=0, main_axis_size="min"),
                            ))
                    self.srv_folder_list.update()
        except: pass

    def _set_target_folder(self, folder):
        self.dest_folder = folder
        if hasattr(self, 'set_target'): self.set_target.value = folder; self.set_target.update()
        self._snack(f"Kohde: {folder}", self.C["accent"])

    async def _create_folder(self, e=None):
        name = self.srv_folder_input.value.strip()
        if not name: self._snack("Anna kansion nimi", self.C["red"]); return
        url = server_url(self.host, self.port, "/api/android/create-folder")
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(url, json={"folder": name})
                if r.status_code == 200:
                    self._snack(f"Kansio '{name}' luotu", self.C["green"])
                    self.srv_folder_input.value = ""; self.srv_folder_input.update()
                    await self._refresh_folders()
                else: self._snack(r.json().get("error", "Virhe"), self.C["red"])
        except Exception as e: self._snack(str(e), self.C["red"])

    async def _del_folder(self, folder):
        if not await self._confirm(f"Poista KAIKKI tiedostot kansiosta '{folder}'?"): return
        targets = [f for f in self.remote_files if f.get("filename", "").startswith(folder + "/")]
        ok, fail = 0, 0
        for f in targets:
            url = server_url(self.host, self.port, "/api/android/delete-file")
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.post(url, json={"filename": f["filename"]})
                    if r.status_code == 200: ok += 1
                    else: fail += 1
            except: fail += 1
        self._snack(f"Poistettu {ok}" + (f", {fail} epaonnistui" if fail else ""), self.C["green"])
        await self._refresh_server_files()

    async def _refresh_server_files(self):
        if not self.server_online: return
        self.srv_files_list.controls.clear()
        try:
            url = server_url(self.host, self.port, "/api/android/list")
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    files = r.json()
                    self.remote_files = files
                    if not files: self.srv_files_list.controls.append(ft.Text("Ei tiedostoja palvelimella", color=self.C["muted"], size=12))
                    else:
                        groups = {}; roots = []
                        for f in files:
                            nm = f.get("filename", "")
                            if "/" in nm: groups.setdefault(nm.split("/")[0], []).append(f)
                            else: roots.append(f)

                        for g in sorted(groups):
                            fs = groups[g]
                            img = sum(1 for x in fs if x.get("type") == "image")
                            vid = sum(1 for x in fs if x.get("type") == "video")
                            self.srv_files_list.controls.append(
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.FOLDER, color=self.C["orange"]),
                                    title=ft.Text(f"📁 {g}", size=13, color=self.C["text"]),
                                    subtitle=ft.Text(f"{len(fs)} tiedostoa · 🖼{img} 🎬{vid}", size=11, color=self.C["muted"]),
                                    dense=True, trailing=ft.IconButton(icon=ft.Icons.DELETE, icon_color=self.C["red"], icon_size=16, on_click=lambda e, gg=g: self.page.run_task(self._del_folder, gg))
                                ))

                        for f in sorted(roots, key=lambda x: x.get("filename", "")):
                            nm = f.get("filename", "")
                            icon = "🎬" if f.get("type") == "video" else "🖼️"
                            self.srv_files_list.controls.append(
                                ft.ListTile(
                                    leading=ft.Text(icon, size=18),
                                    title=ft.Text(nm, size=13, color=self.C["text"], overflow="ellipsis"),
                                    subtitle=ft.Text(fmt_size(f.get("size", 0)), size=11, color=self.C["muted"]),
                                    dense=True, trailing=ft.IconButton(icon=ft.Icons.DELETE, icon_color=self.C["red"], icon_size=16, on_click=lambda e, nn=nm: self.page.run_task(self._del_file, nn))
                                ))

                        total_sz = sum(f.get("size", 0) for f in files)
                        self.srv_files_list.controls.insert(0, ft.Text(f"{len(files)} tiedostoa ({fmt_size(total_sz)})", size=11, color=self.C["muted"]))
        except: pass
        self.srv_files_list.update()

    async def _del_file(self, fn):
        if not await self._confirm(f"Poista '{fn}' palvelimelta?"): return
        url = server_url(self.host, self.port, "/api/android/delete-file")
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(url, json={"filename": fn})
                if r.status_code == 200: self._snack("Poistettu", self.C["green"]); await self._refresh_server_files()
                else: self._snack(r.json().get("error", "Virhe"), self.C["red"])
        except Exception as e: self._snack(str(e), self.C["red"])

    async def _confirm(self, msg: str) -> bool:
        result = [False]
        def set_res(v): result[0] = v; dlg.open = False; self.page.update()
        dlg = ft.AlertDialog(title=ft.Text("Vahvista"), content=ft.Text(msg), actions=[ft.TextButton(content=ft.Text("Kyllä"), on_click=lambda _: set_res(True)), ft.TextButton(content=ft.Text("Peruuta"), on_click=lambda _: set_res(False))])
        self.page.overlay.append(dlg); dlg.open = True; self.page.update()
        while dlg.open: await asyncio.sleep(0.1)
        return result[0]

    def _snack(self, msg, color=None):
        self.page.snack_bar = ft.SnackBar(content=ft.Text(msg, color=color or self.C["text"]), bgcolor=self.C["panel"], duration=3000)
        self.page.snack_bar.open = True; self.page.update()

def main(page: ft.Page): FlowCastApp(page)

if __name__ == "__main__": ft.app(target=main)