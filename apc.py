import sys
import os
import winreg
import subprocess
from datetime import datetime, timedelta
import json
from PIL import Image
import win32gui
import win32ui
import webbrowser
import pefile
import urllib.request
import locale
from packaging.version import parse as parse_version
import base64
import win32com.client
from icon_data import ICON_BASE64
import ctypes
import shlex
import tempfile
from PySide6.QtGui import QPixmap, QIcon, QImage, QIntValidator, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QPushButton, QLineEdit,
    QLabel, QCheckBox, QProgressBar, QMessageBox, QHeaderView,
    QFrame, QFileDialog, QScrollArea, QMenu, QDialog, QTextEdit,
    QComboBox, QSystemTrayIcon, QDialogButtonBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, QSettings, QSharedMemory
APP_NAME_FOR_REGISTRY_UNINSTALL = "ApplicationToolkitPro_Uninstall"
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
def resolve_shortcut(path):
    if not path.lower().endswith('.lnk'):
        return path
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(path)
        return shortcut.TargetPath
    except Exception as e:
        print(f"Shortcut resolve error: {e}")
        return path
def manage_context_menu_entry(action, file_type, app_name_key, menu_text, command_verb):
    if not is_admin():
        return False, "Administrator privileges are required."
    try:
        executable_path = sys.executable.replace("python.exe", "pythonw.exe")
        script_path = os.path.abspath(sys.argv[0])
        command = f'"{executable_path}" "{script_path}" -{command_verb} "%1"'
        key_path = fr"Software\Classes\{file_type}\shell\{app_name_key}"
        if action == 'add':
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValue(key, '', winreg.REG_SZ, menu_text)
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{executable_path}",0')
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, f"{key_path}\\command") as key:
                winreg.SetValue(key, '', winreg.REG_SZ, command)
        elif action == 'remove':
            winreg.DeleteKeyEx(winreg.HKEY_LOCAL_MACHINE, f"{key_path}\\command")
            winreg.DeleteKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path)
        return True, "Operation successful."
    except FileNotFoundError:
        if action == 'remove':
            return True, "The entry does not exist anyway."
        return False, "Key not found."
    except Exception as e:
        return False, f"An error occurred: {e}"
CURRENT_VERSION = "1.0.1"
DARK_STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
    font-size: 10pt;
}
QMainWindow {
    background-color: #3c3c3c;
}
QTabWidget::pane {
    border: 1px solid #444;
    border-radius: 3px;
}
QTabBar::tab {
    background: #3c3c3c;
    border: 1px solid #444;
    padding: 8px 20px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #505050;
    margin-bottom: -1px;
}
QTreeWidget {
    background-color: #2b2b2b;
    border: 1px solid #444;
    border-radius: 3px;
}
QHeaderView::section {
    background-color: #4a4a4a;
    color: #f0f0f0;
    padding: 4px;
    border: 1px solid #3c3c3c;
}
QPushButton {
    background-color: #505050;
    border: 1px solid #666;
    padding: 5px;
    border-radius: 3px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #606060;
}
QPushButton:pressed {
    background-color: #404040;
}
QPushButton:disabled {
    background-color: #404040;
    color: #888;
}
QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #555;
    padding: 5px;
    border-radius: 3px;
}
QProgressBar {
    border: 1px solid #555;
    border-radius: 3px;
    text-align: center;
    height: 12px;
}
QProgressBar::chunk {
    background-color: #007acc;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
}
QMessageBox {
    background-color: #3c3c3c;
    min-width: 400px;
}
#DetailsPanel {
    background-color: #353535;
    border: 1px solid #444;
    border-radius: 3px;
}
#DetailsTitle {
    font-size: 12pt;
    font-weight: bold;
    margin-bottom: 10px;
}
#DetailsLabel {
    font-weight: bold;
}
#FilterPanel {
    background-color: #3c3c3c;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 5px;
    margin-bottom: 5px;
}
"""
class IconLoaderWorker(QObject):
    icon_loaded = Signal(QTreeWidgetItem, QIcon)
    def __init__(self, icon_cache):
        super().__init__()
        self.icon_cache = icon_cache
        self._is_running = True
        self.queue = []
    def stop(self):
        self._is_running = False
    def run(self):
        while self._is_running:
            if self.queue:
                item, program = self.queue.pop(0)
                icon_path = program.get("IconPath") or program.get("FullPath")
                if icon_path:
                    icon = get_icon(icon_path, self.icon_cache, size=16)
                    if icon:
                        self.icon_loaded.emit(item, icon)
            else:
                QThread.msleep(50)
    def add_to_queue(self, item, program):
        self.queue.append((item, program))
class Worker(QObject):
    finished = Signal(dict)
    progress_updated = Signal(int, int, str)
    def __init__(self, mode, show_system=False, favorites=None, scan_path_list=None):
        super().__init__()
        self.mode = mode
        self.show_system = show_system
        self.favorites = favorites if favorites is not None else []
        self.scan_path_list = scan_path_list if scan_path_list is not None else []
    def run(self):
        result = {}
        classification_lists = get_classification_lists()
        if self.mode == 'refresh' or self.mode == 'full_scan':
            all_programs = get_installed_programs(self.show_system)
            uwp_apps = get_uwp_apps()
            apps_list, games_list = [], []
            for prog in all_programs:
                if classify_program(prog, classification_lists):
                    games_list.append(prog)
                else:
                    apps_list.append(prog)
            favorites_list = [p for p in all_programs + uwp_apps if p['Name'] in self.favorites]
            result = {
                'apps': sorted(apps_list, key=lambda x: x.get('Name', '').lower()),
                'games': sorted(games_list, key=lambda x: x.get('Name', '').lower()),
                'uwp': sorted(uwp_apps, key=lambda x: x.get('Name', '').lower()),
                'fav': sorted(favorites_list, key=lambda x: x.get('Name', '').lower()),
            }
            if self.mode == 'full_scan':
                portable_apps = []
                for path in self.scan_path_list:
                    portable_apps.extend(self.find_portable_apps(path))
                result['portable'] = sorted(portable_apps, key=lambda x: x.get('Name', '').lower())
        elif self.mode == 'scan_portable':
            portable_apps = []
            for path in self.scan_path_list:
                portable_apps.extend(self.find_portable_apps(path))
            result = {'portable': sorted(portable_apps, key=lambda x: x.get('Name', '').lower())}
        self.finished.emit(result)
    def find_portable_apps(self, scan_path):
        apps = []
        ignored_dirs = {'$recycle.bin', 'windows', 'programdata', 'appdata', 'system32', 'syswow64'}
        ignored_exes = {
            'setup.exe', 'install.exe', 'installer.exe', 'unins000.exe',
            'uninstall.exe', 'updater.exe', 'crashreporter.exe', 'vcredist_x86.exe',
            'vcredist_x64.exe', 'dxsetup.exe', 'dotnetfx.exe', 'report.exe',
            'wow_helper.exe', 'python.exe', 'pip.exe'
        }
        total_files = 0
        self.progress_updated.emit(0, 0, f"Calculating: {os.path.basename(scan_path)}")
        for root, dirs, files in os.walk(scan_path, topdown=True):
            dirs[:] = [d for d in dirs if d.lower() not in ignored_dirs]
            for file in files:
                if file.lower().endswith(".exe"): total_files += 1
        scanned_files = 0
        for root, dirs, files in os.walk(scan_path, topdown=True):
            dirs[:] = [d for d in dirs if d.lower() not in ignored_dirs]
            for file in files:
                if file.lower().endswith(".exe"):
                    scanned_files += 1
                    if file.lower() in ignored_exes:
                        continue
                    if scanned_files % 10 == 0 or scanned_files == total_files: self.progress_updated.emit(scanned_files, total_files, root)
                    full_path = os.path.join(root, file)
                    try:
                        props = get_exe_properties(full_path)
                        if props and (props.get("FileDescription") or props.get("ProductName")):
                            app_name = props.get("FileDescription") or props.get("ProductName")
                            app = {"Name": app_name, "Publisher": props.get("CompanyName", "Unknown"), "Version": props.get("FileVersion", "N/A"), "InstallLocation": root, "Size": format_size(os.path.getsize(full_path) / 1024), "FullPath": full_path, "Type": "Portable"}
                            apps.append(app)
                    except Exception: continue
        return apps
class DetailsWorker(QObject):
    finished = Signal(dict)
    def __init__(self, program, icon_cache):
        super().__init__()
        self.program = program
        self.icon_cache = icon_cache
    def run(self):
        icon_path = self.program.get("IconPath") or self.program.get("FullPath")
        icon = get_icon(icon_path, self.icon_cache, size=64)
        props = None
        exe_path = self.program.get("FullPath")
        if exe_path and os.path.exists(exe_path) and exe_path.lower().endswith('.exe'):
            props = get_exe_properties(exe_path)
        result = {'program': self.program, 'icon': icon, 'properties': props}
        self.finished.emit(result)
class UninstallProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Uninstalling Programs...")
        self.setModal(True)
        self.setFixedSize(400, 120)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Starting...")
        self.current_program_label = QLabel("")
        self.progress_bar = QProgressBar()
        layout.addWidget(self.status_label)
        layout.addWidget(self.current_program_label)
        layout.addWidget(self.progress_bar)
    def update_progress(self, current, total, program_name):
        self.status_label.setText(f"Uninstalling program {current} of {total}...")
        self.current_program_label.setText(program_name)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
class UninstallReportDialog(QDialog):
    def __init__(self, succeeded_list, failed_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Uninstallation Report")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        layout = QVBoxLayout(self)
        summary_text = f"<b>{len(succeeded_list)}</b> program(s) were successfully uninstalled, <b>{len(failed_list)}</b> program(s) failed or still appear in the list."
        layout.addWidget(QLabel(summary_text))
        tab_widget = QTabWidget()
        if succeeded_list:
            succeeded_widget = QWidget()
            succeeded_layout = QVBoxLayout(succeeded_widget)
            succeeded_text_edit = QTextEdit()
            succeeded_text_edit.setReadOnly(True)
            succeeded_text_edit.setText("\n".join(succeeded_list))
            succeeded_layout.addWidget(succeeded_text_edit)
            tab_widget.addTab(succeeded_widget, f"Succeeded ({len(succeeded_list)})")
        if failed_list:
            failed_widget = QWidget()
            failed_layout = QVBoxLayout(failed_widget)
            failed_text_edit = QTextEdit()
            failed_text_edit.setReadOnly(True)
            failed_text_edit.setText("\n".join(failed_list))
            failed_layout.addWidget(failed_text_edit)
            tab_widget.addTab(failed_widget, f"Failed / No Change ({len(failed_list)})")
        if not succeeded_list and not failed_list:
            layout.addWidget(QLabel("Could not verify uninstallation status. Please check the list manually."))
        else:
            layout.addWidget(tab_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
class UninstallWorker(QObject):
    progress_updated = Signal(int, int, str)
    finished = Signal()
    uninstall_attempt_finished = Signal(list)
    def __init__(self, programs, is_silent):
        super().__init__()
        self.programs = programs
        self.is_silent = is_silent
        self._is_running = True
    def run(self):
        total = len(self.programs)
        for i, program in enumerate(self.programs):
            if not self._is_running:
                break
            self.progress_updated.emit(i + 1, total, program.get("Name", "Unknown"))
            uninstall_string = program.get("UninstallString")
            if not uninstall_string:
                continue
            cmd_str = uninstall_string
            try:
                if program.get('Type') == 'UWP':
                    cmd_list = ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', cmd_str]
                    subprocess.run(cmd_list, check=False, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    if self.is_silent:
                        if "msiexec.exe" in cmd_str.lower():
                            cmd_str = cmd_str.replace("/I", "/X").replace("/i", "/x") + " /qn"
                        else:
                            cmd_str += " /S /silent /quiet /verysilent"
                    cmd_list = shlex.split(cmd_str)
                    subprocess.run(cmd_list, check=False, timeout=300)
            except subprocess.TimeoutExpired:
                print(f"Timeout uninstalling {program.get('Name')}")
            except Exception as e:
                print(f"Error uninstalling {program.get('Name')}: {e}")
        self.uninstall_attempt_finished.emit(self.programs)
        self.finished.emit()
    def stop(self):
        self._is_running = False
class AppManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_admin_user = is_admin()
        admin_title = " (Administrator)" if self.is_admin_user else ""
        self.setWindowTitle(f"Application Toolkit Pro{admin_title}")
        self.tray_icon = None
        self.is_quitting_via_tray = False
        try:
            icon_data = base64.b64decode(ICON_BASE64)
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.app_icon = QIcon(pixmap)
            self.setWindowIcon(self.app_icon)
        except Exception as e:
            print(f"Could not load icon: {e}")
            self.app_icon = QIcon()
        self.setGeometry(100, 100, 1600, 800)
        self.settings = QSettings("ApplicationToolkitPro", "ApplicationToolkitPro")
        self.favorites = self.load_favorites()
        self.icon_cache = {}
        self.program_map = {}
        self.filtered_data = {}
        self.full_data = {}
        self.last_scanned_path = None
        self.is_user_scan = False
        self.pending_uninstall_check = []
        self.tab_configs = {
            "apps": {"title": "Applications"},
            "games": {"title": "Games"},
            "uwp": {"title": "Store Apps (UWP)"},
            "fav": {"title": "Favorites"},
            "portable": {"title": "Portables"}
        }
        self.tab_keys = list(self.tab_configs.keys())
        self.main_scan_thread = None
        self.main_scan_worker = None
        self.details_thread = None
        self.details_worker = None
        self.icon_loader_thread = None
        self.icon_loader_worker = None
        self.uninstall_thread = None
        self.uninstall_worker = None
        self.currently_loading_program = None
        self.currently_selected_program = None
        self.default_icon = self.create_default_icon()
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.filter_programs)
        self.initUI()
        self.create_actions()
        self.create_menus()
        self.create_tray_icon()
        self.load_settings()
        self.start_icon_loader()
        self.initial_load()
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        tray_menu = QMenu()
        self.toggle_visibility_action = QAction("Hide", self)
        self.toggle_visibility_action.triggered.connect(self.toggle_visibility)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.really_quit)
        tray_menu.addAction(self.toggle_visibility_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.handle_tray_activation)
        self.tray_icon.show()
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
    def handle_tray_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()
    def setVisible(self, visible):
        if visible:
            self.toggle_visibility_action.setText("Hide")
        else:
            self.toggle_visibility_action.setText("Show")
        super().setVisible(visible)
    def really_quit(self):
        self.is_quitting_via_tray = True
        self.close()
    def closeEvent(self, event):
        should_hide = self.settings.value("behavior/closeToTray", True, type=bool)
        if self.is_quitting_via_tray or not should_hide:
            threads_to_stop = [
                self.icon_loader_thread, self.main_scan_thread, self.details_thread,
                self.uninstall_thread
            ]
            workers_to_stop = [self.icon_loader_worker, self.uninstall_worker]
            for worker in workers_to_stop:
                if worker:
                    try:
                        worker.stop()
                    except: pass
            for thread in threads_to_stop:
                try:
                    if thread and thread.isRunning():
                        thread.quit()
                        thread.wait(2000)
                except RuntimeError:
                    pass
            self.tray_icon.hide()
            event.accept()
        else:
            event.ignore()
            self.hide()
    def restart_as_admin(self):
        try:
            executable = sys.executable.replace("python.exe", "pythonw.exe")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, " ".join(sys.argv), None, 1)
            self.really_quit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not restart as administrator: {e}")
    def uninstall_program(self):
        programs = self.get_selected_programs()
        if not programs:
            return
        if self.uninstall_thread and self.uninstall_thread.isRunning():
            QMessageBox.warning(self, "In Progress", "An uninstall process is already running.")
            return
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle("Uninstall Options")
        msg_box.setText(f"How would you like to uninstall the following {len(programs)} program(s)?")
        names = '\n'.join([f"- {p['Name']}" for p in programs])
        if len(programs) > 15:
            short_list = '\n'.join([f"- {p['Name']}" for p in programs[:10]])
            msg_box.setInformativeText(f"Selected programs:\n{short_list}\n...and {len(programs) - 10} more.")
        else:
            msg_box.setInformativeText(f"Selected programs:\n{names}")
        normal_button = msg_box.addButton("Normal Uninstall", QMessageBox.ButtonRole.AcceptRole)
        silent_button = msg_box.addButton("Try Silent Uninstall", QMessageBox.ButtonRole.ApplyRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()
        clicked_button = msg_box.clickedButton()
        if clicked_button == cancel_button:
            return
        is_silent = (clicked_button == silent_button)
        self.progress_dialog = UninstallProgressDialog(self)
        self.uninstall_thread = QThread()
        self.uninstall_worker = UninstallWorker(programs, is_silent)
        self.uninstall_worker.moveToThread(self.uninstall_thread)
        self.uninstall_worker.progress_updated.connect(self.progress_dialog.update_progress)
        self.uninstall_thread.started.connect(self.uninstall_worker.run)
        self.uninstall_worker.uninstall_attempt_finished.connect(self.on_uninstall_attempt_finished)
        self.uninstall_worker.finished.connect(self.uninstall_thread.quit)
        self.uninstall_worker.finished.connect(self.uninstall_worker.deleteLater)
        self.uninstall_thread.finished.connect(self.uninstall_thread.deleteLater)
        self.uninstall_thread.start()
        self.progress_dialog.show()
    def on_uninstall_attempt_finished(self, attempted_programs):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.information(self, "Process Finished", "The uninstall processes have been initiated. The list will now be refreshed to check the results.")
        self.pending_uninstall_check = attempted_programs
        self.start_loading_data(mode='refresh')
        self.uninstall_thread = None
        self.uninstall_worker = None
    def check_uninstall_results(self):
        if not self.pending_uninstall_check:
            return
        current_program_names = {p['Name'].lower() for p in self.full_data.get('apps', []) + self.full_data.get('games', []) + self.full_data.get('uwp', [])}
        succeeded = []
        failed = []
        for program in self.pending_uninstall_check:
            if program['Name'].lower() not in current_program_names:
                succeeded.append(program['Name'])
            else:
                failed.append(program['Name'])
        dialog = UninstallReportDialog(succeeded, failed, self)
        dialog.exec()
        self.pending_uninstall_check = []
    def start_icon_loader(self):
        self.icon_loader_thread = QThread()
        self.icon_loader_worker = IconLoaderWorker(self.icon_cache)
        self.icon_loader_worker.moveToThread(self.icon_loader_thread)
        self.icon_loader_worker.icon_loaded.connect(self.set_item_icon)
        self.icon_loader_thread.started.connect(self.icon_loader_worker.run)
        self.icon_loader_thread.start()
    def set_item_icon(self, item, icon):
        try:
            item.setIcon(0, icon)
        except RuntimeError:
            pass
    def initial_load(self):
        self.start_loading_data(mode='refresh')
        self.full_data['portable'] = self.load_portable_cache()
        self.filter_programs()
    def full_rescan(self):
        saved_paths = self.load_portable_paths()
        valid_paths, paths_changed = [], False
        for path in saved_paths:
            if os.path.isdir(path): valid_paths.append(path)
            else: paths_changed = True
        if paths_changed: self.save_portable_paths(valid_paths)
        self.start_loading_data(mode='full_scan', scan_path_list=valid_paths)
    def load_favorites(self): return self.settings.value("favorites", [], type=list)
    def save_favorites(self): self.settings.setValue("favorites", self.favorites)
    def load_portable_paths(self): return self.settings.value("portable_scan_paths", [], type=list)
    def save_portable_paths(self, paths): self.settings.setValue("portable_scan_paths", paths)
    def load_portable_cache(self):
        json_string = self.settings.value("portable_cache", "", type=str)
        if not json_string: return []
        try: return json.loads(json_string)
        except json.JSONDecodeError: return []
    def save_portable_cache(self, data):
        json_string = json.dumps(data, indent=2)
        self.settings.setValue("portable_cache", json_string)
    def create_actions(self):
        self.add_uninstall_action = QAction("Add 'Uninstall Program' Command (.lnk)", self)
        self.add_uninstall_action.triggered.connect(lambda: self.handle_uninstall_context_menu('add'))
        self.remove_uninstall_action = QAction("Remove 'Uninstall Program' Command", self)
        self.remove_uninstall_action.triggered.connect(lambda: self.handle_uninstall_context_menu('remove'))
        self.close_to_tray_action = QAction("Hide to Tray on Close", self, checkable=True)
        self.close_to_tray_action.triggered.connect(self.save_close_behavior_setting)
    def create_menus(self):
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("Settings")
        settings_menu.addAction(self.close_to_tray_action)
        tools_menu = menu_bar.addMenu("Tools")
        context_menu = tools_menu.addMenu("Context Menu Settings")
        context_menu.addAction(self.add_uninstall_action)
        context_menu.addAction(self.remove_uninstall_action)
    def handle_uninstall_context_menu(self, action):
        if not self.is_admin_user:
            QMessageBox.warning(self, "Privileges Required", "You need to restart the program as an administrator to perform this action.")
            return
        success, message = manage_context_menu_entry(action, 'lnkfile', APP_NAME_FOR_REGISTRY_UNINSTALL, 'Uninstall Program for this Shortcut', 'uninstall')
        if success:
            QMessageBox.information(self, "Success", f"Operation completed successfully.\n{message}")
        else:
            QMessageBox.critical(self, "Error", f"An error occurred during the operation.\n{message}")
    def load_settings(self):
        close_to_tray = self.settings.value("behavior/closeToTray", True, type=bool)
        self.close_to_tray_action.setChecked(close_to_tray)
    def save_close_behavior_setting(self):
        is_checked = self.close_to_tray_action.isChecked()
        self.settings.setValue("behavior/closeToTray", is_checked)
    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_h_layout = QHBoxLayout(main_widget)
        left_panel_widget = QWidget()
        left_layout = QVBoxLayout(left_panel_widget)
        top_layout = QHBoxLayout()
        title_label = QLabel("Application Toolkit Pro")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; border: none;")
        refresh_button = QPushButton("Refresh")
        refresh_button.setToolTip("Quickly refreshes the list of installed programs.")
        refresh_button.clicked.connect(lambda: self.start_loading_data(mode='refresh'))
        portable_scan_button = QPushButton("Scan Portable Folder")
        portable_scan_button.clicked.connect(self.scan_for_portables)
        top_layout.addWidget(title_label)
        top_layout.addStretch(1)
        top_layout.addWidget(refresh_button)
        top_layout.addWidget(portable_scan_button)
        if not self.is_admin_user:
            self.admin_button = QPushButton("Restart as Administrator")
            self.admin_button.setToolTip("Restart the application with administrator privileges.")
            self.admin_button.clicked.connect(self.restart_as_admin)
            top_layout.addWidget(self.admin_button)
        filter_panel = QWidget()
        filter_panel.setObjectName("FilterPanel")
        filter_layout = QVBoxLayout(filter_panel)
        filter_layout.setContentsMargins(10, 5, 10, 5)
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name or publisher...")
        self.search_box.textChanged.connect(self.schedule_filter)
        search_layout.addWidget(self.search_box)
        details_filter_layout = QHBoxLayout()
        self.date_filter_combo = QComboBox()
        self.date_filter_combo.addItems(["All Time", "Last 7 Days", "Last 30 Days", "Last Year"])
        self.date_filter_combo.currentIndexChanged.connect(self.schedule_filter)
        self.size_filter_input = QLineEdit()
        self.size_filter_input.setPlaceholderText("Size > (MB)")
        self.size_filter_input.setValidator(QIntValidator(0, 999999))
        self.size_filter_input.setFixedWidth(100)
        self.size_filter_input.textChanged.connect(self.schedule_filter)
        self.arch_filter_combo = QComboBox()
        self.arch_filter_combo.addItems(["All Architectures", "64-bit (x64)", "32-bit (x86)"])
        self.arch_filter_combo.currentIndexChanged.connect(self.schedule_filter)
        self.drive_filter_combo = QComboBox()
        self.drive_filter_combo.addItem("All Drives")
        available_drives = [f"{chr(drive)}:" for drive in range(65, 91) if os.path.exists(f"{chr(drive)}:")]
        self.drive_filter_combo.addItems(available_drives)
        self.drive_filter_combo.currentIndexChanged.connect(self.schedule_filter)
        details_filter_layout.addWidget(QLabel("Date:"))
        details_filter_layout.addWidget(self.date_filter_combo, 1)
        details_filter_layout.addWidget(QLabel("Size:"))
        details_filter_layout.addWidget(self.size_filter_input, 0)
        details_filter_layout.addWidget(QLabel("Arch:"))
        details_filter_layout.addWidget(self.arch_filter_combo, 1)
        details_filter_layout.addWidget(QLabel("Drive:"))
        details_filter_layout.addWidget(self.drive_filter_combo, 0)
        filter_layout.addLayout(search_layout)
        filter_layout.addLayout(details_filter_layout)
        options_layout = QHBoxLayout()
        self.system_checkbox = QCheckBox("Show System Components")
        self.system_checkbox.stateChanged.connect(lambda: self.start_loading_data(mode='refresh'))
        options_layout.addWidget(self.system_checkbox)
        options_layout.addStretch(1)
        self.tabs_widget = QTabWidget()
        self.tabs_widget.currentChanged.connect(self.update_active_tab_view)
        self.tabs = {}
        self.tabs_widget.blockSignals(True)
        for key, config in self.tab_configs.items():
            tab_widget, tree, buttons = self.create_tab(key)
            self.tabs_widget.addTab(tab_widget, config["title"])
            self.tabs[key] = {"widget": tab_widget, "tree": tree, "buttons": buttons, "title": config["title"]}
        self.tabs_widget.blockSignals(False)
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.addStretch(1)
        self.loading_status_label = QLabel("Loading data, please wait...")
        self.loading_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar()
        loading_layout.addWidget(self.loading_status_label)
        loading_layout.addWidget(self.progress_bar)
        loading_layout.addStretch(1)
        self.loading_widget.hide()
        left_layout.addLayout(top_layout)
        left_layout.addWidget(filter_panel)
        left_layout.addLayout(options_layout)
        left_layout.addWidget(self.tabs_widget)
        left_layout.addWidget(self.loading_widget)
        self.create_details_panel()
        self.main_h_layout.addWidget(left_panel_widget, 7)
        self.main_h_layout.addWidget(self.details_panel, 3)
        self.statusBar().showMessage(f"Version {CURRENT_VERSION}")
    def create_tab(self, key):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        tree = QTreeWidget()
        tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tree.setSortingEnabled(True)
        tree.setRootIsDecorated(False)
        headers = ["Name", "Publisher", "Version", "Date", "Size", "Location"]
        widths = [300, 180, 80, 120, 80, 450]
        tree.setColumnCount(len(headers))
        tree.setHeaderLabels(headers)
        tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        tree.header().setStretchLastSection(True)
        for i, width in enumerate(widths):
            tree.setColumnWidth(i, width)
        bottom_bar_layout, buttons = QHBoxLayout(), {}
        if key == 'portable':
            buttons["remove"] = QPushButton("Remove From List")
            buttons["remove"].clicked.connect(self.remove_portable_from_list)
            bottom_bar_layout.addWidget(buttons["remove"])
        buttons["uninstall"] = QPushButton("Uninstall Program")
        buttons["fav"] = QPushButton("Add/Remove Favorite")
        bottom_bar_layout.addWidget(buttons["uninstall"])
        bottom_bar_layout.addWidget(buttons["fav"])
        if key == 'portable':
            buttons["uninstall"].hide()
        bottom_bar_layout.addStretch(1)
        for btn in buttons.values(): btn.setEnabled(False)
        buttons["uninstall"].clicked.connect(self.uninstall_program)
        buttons["fav"].clicked.connect(self.toggle_favorite)
        tree.itemSelectionChanged.connect(lambda: self.on_item_select(tree, buttons))
        layout.addWidget(tree)
        layout.addLayout(bottom_bar_layout)
        return tab_widget, tree, buttons
    def create_details_panel(self):
        self.details_panel = QWidget()
        self.details_panel.setObjectName("DetailsPanel")
        self.details_layout = QVBoxLayout(self.details_panel)
        self.details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.detail_icon = QLabel()
        self.detail_icon.setFixedSize(64, 64)
        self.detail_icon.setScaledContents(True)
        self.detail_name = QLabel("No Program Selected")
        self.detail_name.setObjectName("DetailsTitle")
        self.detail_name.setWordWrap(True)
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.detail_icon)
        header_layout.addWidget(self.detail_name, 1)
        self.details_layout.addLayout(header_layout)
        self.details_progress_bar = QProgressBar()
        self.details_progress_bar.setRange(0, 0)
        self.details_progress_bar.setTextVisible(False)
        self.details_progress_bar.hide()
        self.details_layout.addWidget(self.details_progress_bar)
        self.details_layout.addSpacing(10)
        self.detail_buttons = {}
        self.detail_buttons["open_loc"] = QPushButton("Open File Location")
        self.detail_buttons["open_reg"] = QPushButton("Open in Registry")
        self.detail_buttons["search"] = QPushButton("Search Online")
        for btn in self.detail_buttons.values():
            btn.clicked.connect(self.handle_detail_button_click)
            self.details_layout.addWidget(btn)
        self.show_details_button = QPushButton("Show Detailed Information")
        self.show_details_button.clicked.connect(self.load_full_details)
        self.details_layout.addWidget(self.show_details_button)
        self.details_layout.addSpacing(15)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        self.details_info_layout = QVBoxLayout(scroll_widget)
        self.details_info_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(scroll_widget)
        self.details_layout.addWidget(self.scroll_area)
        self.clear_details_panel()
    def on_item_select(self, tree, buttons):
        is_selected = bool(tree.selectedItems())
        for btn in buttons.values(): btn.setEnabled(is_selected)
        selected_programs = self.get_selected_programs()
        if len(selected_programs) == 1:
            program = selected_programs[0]
            self.currently_selected_program = program
            self.clear_details_panel(is_clearing=False)
            self.detail_name.setText(program.get("Name", "N/A"))
            icon_path = program.get("IconPath") or program.get("FullPath")
            icon = get_icon(icon_path, self.icon_cache, size=64)
            if icon:
                self.detail_icon.setPixmap(icon.pixmap(64, 64))
            else:
                self.detail_icon.setPixmap(QPixmap())
            info = {
                "Publisher": program.get("Publisher"),
                "Version": program.get("Version"),
                "Install Date": program.get("InstallDate"),
                "Estimated Size": program.get("Size"),
                "Location": program.get("InstallLocation") or os.path.dirname(program.get("FullPath","")),
                "Registry Key": program.get("RegistryKey")
            }
            for label, value in info.items():
                if value: self.add_detail_info_row(label, value)
            self.detail_buttons["open_loc"].setEnabled(bool(info["Location"]))
            self.detail_buttons["open_reg"].setEnabled(bool(info["Registry Key"]))
            self.detail_buttons["search"].setEnabled(True)
            self.show_details_button.show()
        else:
            self.clear_details_panel()
            self.currently_selected_program = None
    def load_full_details(self):
        if not self.currently_selected_program:
            return
        try:
            if self.details_thread and self.details_thread.isRunning():
                return
        except RuntimeError:
            pass
        self.show_details_button.setEnabled(False)
        self.details_progress_bar.show()
        self.details_thread = QThread()
        self.details_worker = DetailsWorker(self.currently_selected_program, self.icon_cache)
        self.details_worker.moveToThread(self.details_thread)
        self.details_worker.finished.connect(self.on_details_loaded)
        self.details_thread.started.connect(self.details_worker.run)
        self.details_worker.finished.connect(self.details_thread.quit)
        self.details_worker.finished.connect(self.details_worker.deleteLater)
        self.details_thread.finished.connect(self.details_thread.deleteLater)
        self.details_thread.start()
    def on_details_loaded(self, result):
        program_from_worker = result['program']
        if not self.currently_selected_program or program_from_worker.get('FullPath') != self.currently_selected_program.get('FullPath'):
            return
        self.details_progress_bar.hide()
        self.show_details_button.hide()
        self.show_details_button.setEnabled(True)
        props = result['properties']
        if props:
            self.details_info_layout.addWidget(self.create_separator())
            self.add_detail_info_row("--- File Properties ---", "")
            for key, val in props.items():
                self.add_detail_info_row(key, val)
        elif program_from_worker.get("FullPath", "").lower().endswith('.exe'):
            self.details_info_layout.addWidget(self.create_separator())
            self.add_detail_info_row("File Properties", "Could not be read or is invalid.")
    def remove_portable_from_list(self):
        if self.get_active_tab_key() != 'portable': return
        selected_programs = self.get_selected_programs()
        if not selected_programs: return
        reply = QMessageBox.question(self, "Remove from List", f"Are you sure you want to permanently remove the {len(selected_programs)} selected application(s) from the list?\n\n(This does not delete the files, it only removes them from the list.)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            paths_to_remove = {app['FullPath'] for app in selected_programs}
            self.full_data['portable'] = [app for app in self.full_data.get('portable', []) if app['FullPath'] not in paths_to_remove]
            self.save_portable_cache(self.full_data['portable'])
            self.filter_programs()
            self.statusBar().showMessage(f"{len(selected_programs)} application(s) removed from the list.", 5000)
    def handle_detail_button_click(self):
        sender = self.sender()
        if sender == self.detail_buttons["open_loc"]: self.open_location()
        elif sender == self.detail_buttons["open_reg"]: self.open_in_registry()
        elif sender == self.detail_buttons["search"]: self.search_online()
    def start_loading_data(self, mode='refresh', scan_path_list=None):
        try:
            if self.main_scan_thread is not None and self.main_scan_thread.isRunning():
                self.statusBar().showMessage("An operation is already in progress...")
                return
        except RuntimeError:
            pass
        if mode in ['scan_portable', 'full_scan']:
            self.loading_status_label.setText("Scanning for portable applications...")
            self.progress_bar.setValue(0)
        else:
            self.loading_status_label.setText("Loading data, please wait...")
            self.progress_bar.setRange(0, 0)
        self.tabs_widget.hide()
        self.loading_widget.show()
        self.statusBar().showMessage("Loading data...")
        self.main_scan_thread = QThread()
        self.main_scan_worker = Worker(mode, self.system_checkbox.isChecked(), self.favorites, scan_path_list)
        self.main_scan_worker.moveToThread(self.main_scan_thread)
        self.main_scan_worker.progress_updated.connect(self.update_scan_progress)
        self.main_scan_thread.started.connect(self.main_scan_worker.run)
        self.main_scan_worker.finished.connect(self.on_data_loaded)
        self.main_scan_worker.finished.connect(self.main_scan_thread.quit)
        self.main_scan_worker.finished.connect(self.main_scan_worker.deleteLater)
        self.main_scan_thread.finished.connect(self.main_scan_thread.deleteLater)
        self.main_scan_thread.start()
    def update_scan_progress(self, current, total, path):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.loading_status_label.setText(f"Scanning: {current} / {total} files\n{path}")
        else:
            self.progress_bar.setRange(0, 0)
            self.loading_status_label.setText(path)
    def on_data_loaded(self, data):
        worker_mode = self.main_scan_worker.mode
        for key, value in data.items():
            if key == 'portable' and worker_mode == 'scan_portable':
                existing_paths = {p['FullPath'] for p in self.full_data.get('portable', [])}
                new_apps = [p for p in value if p['FullPath'] not in existing_paths]
                if 'portable' not in self.full_data: self.full_data['portable'] = []
                self.full_data['portable'].extend(new_apps)
                self.save_portable_cache(self.full_data['portable'])
            else: self.full_data[key] = value
        if worker_mode == 'full_scan': self.save_portable_cache(self.full_data.get('portable', []))
        self.loading_widget.hide()
        self.tabs_widget.show()
        self.statusBar().showMessage(f"Version {CURRENT_VERSION} | Data loaded.")
        self.filter_programs()
        self.clear_details_panel()
        if self.pending_uninstall_check:
            self.check_uninstall_results()
        if self.is_user_scan and self.last_scanned_path:
            reply = QMessageBox.question(self, "Save Scan Path?", f"Would you like to save the path '{self.last_scanned_path}' to automatically scan it during future 'Refresh' operations?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                saved_paths = self.load_portable_paths()
                if self.last_scanned_path not in saved_paths:
                    saved_paths.append(self.last_scanned_path)
                    self.save_portable_paths(saved_paths)
                    self.statusBar().showMessage(f"Path '{self.last_scanned_path}' saved.", 5000)
        self.is_user_scan = False
        self.last_scanned_path = None
    def schedule_filter(self):
        self.filter_timer.start(300)
    def filter_programs(self):
        query = self.search_box.text().lower()
        date_filter_index = self.date_filter_combo.currentIndex()
        arch_filter_index = self.arch_filter_combo.currentIndex()
        drive_filter_text = self.drive_filter_combo.currentText()
        days_limit = 0
        if date_filter_index == 1: days_limit = 7
        elif date_filter_index == 2: days_limit = 30
        elif date_filter_index == 3: days_limit = 365
        size_limit_mb_str = self.size_filter_input.text()
        size_limit_kb = int(size_limit_mb_str) * 1024 if size_limit_mb_str else 0
        for key, data_list in self.full_data.items():
            if not data_list:
                self.filtered_data[key] = []
                continue
            filtered_list = data_list
            if query:
                filtered_list = [p for p in filtered_list if query in p.get('Name', '').lower() or query in p.get('Publisher', '').lower()]
            if days_limit > 0:
                cutoff_date = datetime.now() - timedelta(days=days_limit)
                filtered_list = [
                    p for p in filtered_list
                    if p.get("InstallDate") != "Unknown" and
                    datetime.strptime(p.get("InstallDate"), "%Y-%m-%d") >= cutoff_date
                ]
            if size_limit_kb > 0:
                filtered_list = [p for p in filtered_list if parse_size_to_kb(p.get("Size", "N/A")) >= size_limit_kb]
            if arch_filter_index != 0:
                is_x86 = " (x86)" in os.environ.get("ProgramFiles(x86)", "")
                if is_x86:
                    program_files_x86 = os.environ.get("ProgramFiles(x86)", "").lower()
                    if arch_filter_index == 2:
                        filtered_list = [p for p in filtered_list if p.get("InstallLocation", "").lower().startswith(program_files_x86)]
                    elif arch_filter_index == 1:
                        filtered_list = [p for p in filtered_list if not p.get("InstallLocation", "").lower().startswith(program_files_x86)]
            if self.drive_filter_combo.currentIndex() != 0:
                filtered_list = [p for p in filtered_list if p.get("InstallLocation", "").lower().startswith(drive_filter_text.lower())]
            self.filtered_data[key] = filtered_list
        self.update_tab_counts()
        self.update_active_tab_view()
    def update_active_tab_view(self):
        active_key = self.get_active_tab_key()
        if not active_key: return
        tab_info, tree = self.tabs[active_key], self.tabs[active_key]["tree"]
        tree.clear()
        if self.icon_loader_worker:
            self.icon_loader_worker.queue.clear()
        data = self.filtered_data.get(active_key, [])
        for app in data:
            item = QTreeWidgetItem()
            item.setIcon(0, self.default_icon)
            item.setText(0, app.get("Name", "N/A"))
            item.setText(1, app.get("Publisher", "N/A"))
            item.setText(2, app.get("Version", "N/A"))
            item.setText(3, app.get("InstallDate", "N/A"))
            item.setText(4, app.get("Size", "N/A"))
            item.setText(5, app.get("InstallLocation", "N/A"))
            tree.addTopLevelItem(item)
            self.program_map[id(item)] = app
            if self.icon_loader_worker:
                self.icon_loader_worker.add_to_queue(item, app)
    def clear_details_panel(self, is_clearing=True):
        if is_clearing:
            self.detail_name.setText("No Program Selected")
            self.detail_icon.clear()
            self.currently_loading_program = None
        while self.details_info_layout.count():
            item = self.details_info_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.details_progress_bar.hide()
        self.scroll_area.show()
        self.show_details_button.hide()
        for btn in self.detail_buttons.values():
            btn.setEnabled(False)
    def add_detail_info_row(self, label_text, value_text):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(f"{label_text}:")
        label.setObjectName("DetailsLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        label.setFixedWidth(120)
        value = QLabel(str(value_text))
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if value_text:
            copy_button = QPushButton("Copy")
            copy_button.setFixedWidth(60)
            copy_button.setStyleSheet("font-size: 8pt; padding: 2px;")
            copy_button.clicked.connect(lambda: QApplication.clipboard().setText(str(value_text)))
            row_layout.addWidget(label)
            row_layout.addWidget(value, 1)
            row_layout.addWidget(copy_button)
        else:
            label.setFixedWidth(400)
            label.setStyleSheet("font-style: italic; color: #aaa;")
            row_layout.addWidget(label)
        self.details_info_layout.addWidget(row_widget)
    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #444;")
        return line
    def get_selected_programs(self):
        active_tree = self.get_active_tree()
        if not active_tree: return []
        selected_items = active_tree.selectedItems()
        return [self.program_map[id(item)] for item in selected_items if id(item) in self.program_map]
    def open_location(self):
        programs = self.get_selected_programs()
        if not programs: return
        path = programs[0].get("InstallLocation") or os.path.dirname(programs[0].get("FullPath",""))
        if path and os.path.isdir(path):
            try: os.startfile(path)
            except Exception as e: QMessageBox.critical(self, "Error", f"Could not open folder: {e}")
        else: QMessageBox.information(self, "Information", "An installation location for this program could not be found.")
    def toggle_favorite(self):
        programs = self.get_selected_programs()
        if not programs: return
        for program in programs:
            name = program["Name"]
            if name in self.favorites: self.favorites.remove(name)
            else: self.favorites.append(name)
        self.save_favorites()
        self.start_loading_data(mode='refresh')
    def create_default_icon(self):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        return QIcon(pixmap)
    def open_in_registry(self):
        if not self.is_admin_user:
            QMessageBox.warning(self, "Administrator Privileges Required",
                                "To use this feature, you need to run the application with administrator rights.\n\n"
                                "Please click the 'Restart as Administrator' button and try again.")
            return
        programs = self.get_selected_programs()
        if not programs: return
        reg_key = programs[0].get("RegistryKeyPath")
        if not reg_key:
            QMessageBox.warning(self, "Error", "A registry path for this program could not be found.")
        else:
            try:
                reg_edit_key_path = r'Software\Microsoft\Windows\CurrentVersion\Applets\Regedit'
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_edit_key_path) as key:
                    winreg.SetValueEx(key, 'LastKey', 0, winreg.REG_SZ, reg_key)
                subprocess.Popen(['regedit.exe'])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open the registry: {e}\nKey: {reg_key}")
    def search_online(self):
        programs = self.get_selected_programs()
        if not programs: return
        query = programs[0].get("Name")
        if query: webbrowser.open(f"https://www.google.com/search?q={query}")
    def scan_for_portables(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder to Scan", "")
        if path:
            self.last_scanned_path = path; self.is_user_scan = True
            self.start_loading_data(mode='scan_portable', scan_path_list=[path])
            self.tabs_widget.setCurrentIndex(self.tab_keys.index("portable"))
    def get_active_tab_key(self):
        idx = self.tabs_widget.currentIndex()
        if 0 <= idx < len(self.tab_keys): return self.tab_keys[idx]
        return None
    def get_active_tree(self):
        key = self.get_active_tab_key()
        if key and key in self.tabs: return self.tabs[key]["tree"]
        return None
    def update_tab_counts(self):
        for key, tab_info in self.tabs.items():
            count = len(self.filtered_data.get(key, []))
            self.tabs_widget.setTabText(self.tabs_widget.indexOf(tab_info["widget"]), f"{tab_info['title']} ({count})")
def get_classification_lists():
    return {"whitelist": [], "blacklist": []}
def pil_to_qicon(pil_img):
    if pil_img.mode != "RGBA": pil_img = pil_img.convert("RGBA")
    qimage = QImage(pil_img.tobytes("raw", "RGBA"), pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888)
    return QIcon(QPixmap.fromImage(qimage))
def get_icon(path, cache, size=16):
    if not path or not isinstance(path, str): return None
    cache_key = f"{path}_{size}"
    if cache_key in cache: return cache[cache_key]
    try:
        clean_path = os.path.expandvars(path).strip('"')
        if clean_path.lower().endswith('.ico') and os.path.isfile(clean_path):
            img = Image.open(clean_path).resize((size, size), Image.LANCZOS)
        else:
            large, small = win32gui.ExtractIconEx(clean_path, 0, 1)
            if not large and not small:
                cache[cache_key] = None
                return None
            icon_handle = (large + small)[0]
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            memdc = hdc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(hdc, 32, 32)
            memdc.SelectObject(bmp)
            memdc.DrawIcon((0, 0), icon_handle)
            bits = bmp.GetBitmapBits(True)
            img = Image.frombuffer('RGBA', (32, 32), bits, 'raw', 'BGRA', 0, 1).resize((size, size), Image.LANCZOS)
            for i in large + small: win32gui.DestroyIcon(i)
            memdc.DeleteDC()
            win32gui.DeleteObject(bmp.GetHandle())
            hdc.DeleteDC()
        icon = pil_to_qicon(img)
        cache[cache_key] = icon
        return icon
    except Exception as e:
        cache[cache_key] = None
        return None
def get_installed_programs(show_system_components=False):
    programs, unique_names = [], set()
    reg_roots = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    reg_paths_templates = [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]
    for root_name, hive in reg_roots.items():
        for path_template in reg_paths_templates:
            try:
                with winreg.OpenKey(hive, path_template) as reg_key:
                    for i in range(winreg.QueryInfoKey(reg_key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(reg_key, i)
                            full_key_path = f"{root_name}\\{path_template}\\{subkey_name}".replace("HKLM", "HKEY_LOCAL_MACHINE").replace("HKCU", "HKEY_CURRENT_USER")
                            with winreg.OpenKey(reg_key, subkey_name) as subkey:
                                values = {v[0]: v[1] for v in subkey_enum_values(subkey)}
                                name = values.get("DisplayName")
                                if not name or name.lower() in unique_names: continue
                                is_system = values.get("SystemComponent", 0)
                                if is_system == 1 and not show_system_components: continue
                                install_loc, display_icon = values.get("InstallLocation", ""), values.get("DisplayIcon", "")
                                icon_path = display_icon.split(',')[0].strip('"') if display_icon else ""
                                full_path = ""
                                if install_loc and not icon_path:
                                    potential_path = os.path.join(install_loc, name.replace(" ", "") + ".exe")
                                    if os.path.exists(potential_path): full_path = potential_path
                                app_data = {"Name": name, "Publisher": values.get("Publisher", ""), "Version": values.get("DisplayVersion", ""), "InstallLocation": install_loc, "UninstallString": values.get("UninstallString", ""), "InstallDate": format_date(values.get("InstallDate", "")), "Size": format_size(values.get("EstimatedSize", 0)), "Type": "Win32", "IconPath": icon_path, "FullPath": full_path or icon_path, "RegistryKey": subkey_name, "RegistryKeyPath": full_key_path}
                                programs.append(app_data); unique_names.add(name.lower())
                        except OSError: continue
            except FileNotFoundError: continue
    return programs
def subkey_enum_values(subkey):
    values, i = [], 0
    while True:
        try:
            values.append(winreg.EnumValue(subkey, i))
            i += 1
        except OSError:
            break
    return values
def get_uwp_apps():
    apps = []
    try:
        cmd = 'powershell -ExecutionPolicy Bypass -NoProfile "Get-AppxPackage | Where-Object {$_.IsFramework -eq $false -and $_.NonRemovable -eq $false} | Select-Object Name, Publisher, Version, InstallLocation, PackageFullName | ConvertTo-Json -Compress"'
        system_encoding = locale.getpreferredencoding()
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding=system_encoding, errors='replace',
                                shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode == 0 and result.stdout:
            json_data = json.loads(result.stdout)
            if isinstance(json_data, dict):
                json_data = [json_data]
            for item in json_data:
                app = {
                    "Name": item.get('Name'),
                    "Publisher": item.get('Publisher'),
                    "Version": item.get('Version'),
                    "InstallLocation": item.get('InstallLocation'),
                    "UninstallString": f"Get-AppxPackage -Package '{item.get('PackageFullName')}' | Remove-AppxPackage",
                    "Type": "UWP"
                }
                apps.append(app)
    except Exception as e:
        print(f"A general error occurred while getting UWP apps: {e}")
    return apps
def get_exe_properties(filepath):
    try:
        pe = pefile.PE(filepath)
        if not hasattr(pe, 'VS_VERSIONINFO') or not hasattr(pe, 'FileInfo') or len(pe.FileInfo) == 0:
            return None
        string_info = {}
        for entry in pe.FileInfo[0]:
            if hasattr(entry, 'StringTable'):
                for st_entry in entry.StringTable:
                    for key, value in st_entry.entries.items():
                        string_info[key.decode('utf-8', 'ignore')] = value.decode('utf-8', 'ignore')
        return string_info
    except Exception:
        return None
def classify_program(program, lists):
    name = program.get("Name", "")
    if lists and name:
        if any(item in name for item in lists.get('whitelist', [])):
            return True
        if any(item in name for item in lists.get('blacklist', [])):
            return False
    name_lower = name.lower()
    publisher = program.get("Publisher", "").lower()
    install_loc = program.get("InstallLocation", "").lower().replace("/", "\\")
    if any(keyword in name_lower for keyword in ["launcher", "client", "sdk", "redistributable", "driver", "runtime"]):
        return False
    if any(path in install_loc for path in [r"steam\steamapps\common", r"epic games", r"riot games", r"gog galaxy\games"]):
        return True
    game_publishers = ["valve", "electronic arts", "ea", "ubisoft", "activision", "blizzard", "riot games", "rockstar games", "bethesda", "2k", "epic games", "steam", "scs software", "paradox interactive", "cd projekt red"]
    if any(p in publisher for p in game_publishers):
        return True
    if any(keyword in name_lower for keyword in ["game", "simulator"]):
        return True
    return False
def format_date(date_str):
    if not date_str or len(str(date_str)) != 8:
        return "Unknown"
    try:
        return datetime.strptime(str(date_str), "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return "Unknown"
def format_size(size_kb):
    if not isinstance(size_kb, (int, float)) or size_kb <= 0:
        return "N/A"
    if size_kb < 1024:
        return f"{size_kb:.0f} KB"
    if size_kb < 1024*1024:
        return f"{size_kb/1024:.1f} MB"
    return f"{size_kb/(1024*1024):.2f} GB"
def parse_size_to_kb(size_str):
    if not isinstance(size_str, str) or size_str == "N/A":
        return 0
    try:
        size_str = size_str.lower()
        if "gb" in size_str:
            return float(size_str.replace("gb", "").strip()) * 1024 * 1024
        elif "mb" in size_str:
            return float(size_str.replace("mb", "").strip()) * 1024
        elif "kb" in size_str:
            return float(size_str.replace("kb", "").strip())
        return 0
    except (ValueError, TypeError):
        return 0
def headless_uninstall(file_path):
    app = QApplication(sys.argv)
    target_path = resolve_shortcut(file_path)
    if not target_path or not os.path.exists(target_path):
        QMessageBox.critical(None, "Error", f"Target file not found:\n{target_path}")
        return
    installed_programs = get_installed_programs(True) + get_uwp_apps()
    found_program = None
    target_path_lower = os.path.normpath(target_path.lower())
    for prog in installed_programs:
        prog_path = prog.get("FullPath")
        install_loc = prog.get("InstallLocation")
        match = False
        if prog_path and os.path.normpath(prog_path.lower()) == target_path_lower:
            match = True
        elif install_loc and target_path_lower.startswith(os.path.normpath(install_loc.lower())):
            match = True
        if match:
            found_program = prog
            break
    if not found_program:
        QMessageBox.warning(None, "Not Found", "No installed program associated with this file could be found.")
        return
    uninstall_string = found_program.get("UninstallString")
    if not uninstall_string:
        QMessageBox.critical(None, "Error", "An uninstall command for this program could not be found.")
        return
    msg_box = QMessageBox(None)
    msg_box.setWindowTitle("Uninstall Confirmation")
    msg_box.setIcon(QMessageBox.Icon.Question)
    msg_box.setText("Are you sure you want to uninstall the following program?")
    msg_box.setInformativeText(f"<b>{found_program.get('Name')}</b><br><small>Publisher: {found_program.get('Publisher')}</small>")
    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg_box.setDefaultButton(QMessageBox.StandardButton.No)
    reply = msg_box.exec()
    if reply == QMessageBox.StandardButton.Yes:
        try:
            if found_program.get('Type') == 'UWP':
                cmd_list = ['powershell', '-Command', uninstall_string]
                subprocess.run(cmd_list, check=False)
            else:
                cmd_list = shlex.split(uninstall_string)
                subprocess.run(cmd_list, check=False)
            QMessageBox.information(None, "Process Started", "The uninstallation process has been started. Please follow the on-screen instructions.")
        except Exception as e:
            QMessageBox.critical(None, "Uninstallation Error", f"An error occurred while uninstalling the program:\n{e}")
if __name__ == '__main__':
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'UTF-8'
    if len(sys.argv) > 2 and sys.argv[1].lower() == "-uninstall":
        headless_uninstall(sys.argv[2])
        sys.exit(0)
    app = QApplication(sys.argv)
    shared_memory = QSharedMemory("ApplicationToolkitPro_SingleInstance_Key_1A2B3C")
    if not shared_memory.create(1):
        QMessageBox.warning(None, "Already Running", "Application Toolkit Pro is already running. Please check the system tray or task manager.")
        sys.exit(1)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    ex = AppManager()
    ex.shared_memory = shared_memory
    ex.show()
    sys.exit(app.exec())