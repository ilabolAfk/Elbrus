#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Эльбрус Emergency Toolkit v3.0
Профессиональный инструмент восстановления Windows
"""

import sys
import os
import subprocess
import winreg
import ctypes
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import psutil

# =====================================================================
# КЛАСС ДЛЯ РАБОТЫ С РЕЕСТРОМ (расширенный)
# =====================================================================

class RegistryManager:
    REG_PATH = {
        'Run': r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        'RunOnce': r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
        'Winlogon': r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
        'AppInit_DLLs': r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows",
        'CmdLine': r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
    }
    
    HIVES = {
        'HKEY_CLASSES_ROOT': winreg.HKEY_CLASSES_ROOT,
        'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
        'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
        'HKEY_USERS': winreg.HKEY_USERS,
        'HKEY_CURRENT_CONFIG': winreg.HKEY_CURRENT_CONFIG
    }
    
    @staticmethod
    def get_hive(name):
        return RegistryManager.HIVES.get(name)
    
    @staticmethod
    def read_value(hive, subkey, value_name):
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            return value
        except:
            return None
    
    @staticmethod
    def write_value(hive, subkey, value_name, data, reg_type=winreg.REG_SZ):
        try:
            key = winreg.CreateKey(hive, subkey)
            winreg.SetValueEx(key, value_name, 0, reg_type, data)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def delete_value(hive, subkey, value_name):
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, value_name)
            winreg.CloseKey(key)
            return True
        except:
            return False
    
    @staticmethod
    def delete_key(hive, subkey):
        try:
            winreg.DeleteKey(hive, subkey)
            return True
        except:
            return False
    
    @staticmethod
    def create_key(hive, subkey):
        try:
            winreg.CreateKey(hive, subkey)
            return True
        except:
            return False
    
    @staticmethod
    def get_all_values(hive, subkey):
        results = []
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
            index = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, index)
                    if name.lower() not in ['default', '(default)']:
                        results.append((name, value))
                    index += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except:
            pass
        return results
    
    @staticmethod
    def get_subkeys(hive, subkey):
        """Возвращает список подразделов."""
        results = []
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(key, index)
                    results.append(name)
                    index += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except:
            pass
        return results
    
    @staticmethod
    def get_value_type(hive, subkey, value_name):
        """Возвращает тип данных параметра."""
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
            _, reg_type = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            return reg_type
        except:
            return None

# =====================================================================
# ПОТОК ДЛЯ ОБНОВЛЕНИЯ ПРОЦЕССОВ
# =====================================================================

class ProcessUpdateThread(QThread):
    data_ready = pyqtSignal(list)
    
    def run(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                pinfo = proc.info
                mem_mb = pinfo['memory_info'].rss / (1024 * 1024)
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu': pinfo['cpu_percent'],
                    'memory': mem_mb,
                    'status': pinfo['status']
                })
            except:
                pass
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        self.data_ready.emit(processes[:50])

# =====================================================================
# ГЛАВНОЕ ОКНО
# =====================================================================

class ElbrusWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Эльбрус - Административный инструментарий v3.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # Загружаем иконку из файла
        self.load_app_icon()
        
        # Проверка прав
        self.is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not self.is_admin:
            self.show_admin_warning()
        
        self.setup_ui()
        self.load_autorun_data()
        self.refresh_processes()
    
    def load_app_icon(self):
        """Загружает иконку из файла icon.ico."""
        icon_paths = [
            os.path.join(os.path.dirname(sys.argv[0]), "icon.ico"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
            "icon.ico"
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                try:
                    icon = QIcon(path)
                    self.setWindowIcon(icon)
                    return
                except:
                    pass
        
        self.setWindowIcon(self.create_default_icon())
    
    def create_default_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 80, 180)))
        painter.setPen(QPen(QColor(0, 60, 140), 2))
        painter.drawEllipse(4, 4, 56, 56)
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        painter.setPen(QPen(QColor(255, 255, 255, 230), 2))
        path = QPainterPath()
        path.moveTo(32, 10)
        path.lineTo(50, 16)
        path.lineTo(50, 30)
        path.arcTo(30, 28, 40, 40, 0, 180)
        path.lineTo(14, 30)
        path.lineTo(32, 10)
        painter.drawPath(path)
        painter.setPen(QPen(QColor(0, 80, 180), 3))
        painter.drawLine(32, 22, 32, 44)
        painter.drawLine(22, 33, 42, 33)
        painter.end()
        return QIcon(pixmap)
    
    def create_icon(self, icon_type):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        
        if icon_type == "process":
            painter.drawRect(2, 2, 12, 12)
            painter.drawPoint(6, 6)
            painter.drawPoint(10, 6)
            painter.drawPoint(6, 10)
            painter.drawPoint(10, 10)
        elif icon_type == "autorun":
            painter.drawEllipse(4, 4, 8, 8)
            painter.drawLine(8, 2, 8, 14)
            painter.drawLine(2, 8, 14, 8)
        elif icon_type == "recovery":
            painter.drawEllipse(3, 3, 10, 10)
            painter.drawLine(5, 8, 7, 11)
            painter.drawLine(7, 11, 12, 5)
        elif icon_type == "cmdline":
            painter.drawRect(2, 2, 12, 10)
            painter.drawLine(4, 5, 7, 7)
            painter.drawLine(7, 7, 4, 9)
        elif icon_type == "registry":
            painter.drawRect(2, 2, 12, 12)
            painter.drawLine(4, 6, 8, 8)
            painter.drawLine(8, 8, 12, 6)
            painter.drawLine(4, 10, 8, 12)
            painter.drawLine(8, 12, 12, 10)
        elif icon_type == "refresh":
            painter.drawArc(3, 3, 10, 10, 0, 300 * 16)
            painter.drawLine(10, 2, 13, 6)
            painter.drawLine(13, 6, 9, 8)
        elif icon_type == "terminate":
            painter.setPen(QPen(QColor(200, 50, 50), 2))
            painter.drawLine(3, 3, 13, 13)
            painter.drawLine(13, 3, 3, 13)
        elif icon_type == "repair":
            painter.setPen(QPen(QColor(255, 200, 50), 2))
            painter.drawRect(4, 2, 8, 4)
            painter.drawLine(6, 6, 6, 12)
            painter.drawLine(10, 6, 10, 12)
            painter.drawLine(6, 12, 10, 12)
        elif icon_type == "clean":
            painter.drawRect(4, 4, 8, 10)
            painter.drawLine(3, 4, 13, 4)
            painter.drawLine(6, 2, 10, 2)
            painter.drawLine(6, 6, 6, 11)
            painter.drawLine(10, 6, 10, 11)
        elif icon_type == "remove":
            painter.setPen(QPen(QColor(200, 50, 50), 2))
            painter.drawLine(3, 8, 13, 8)
        elif icon_type == "scan":
            painter.drawEllipse(4, 4, 8, 8)
            painter.drawLine(10, 10, 14, 14)
        elif icon_type == "add":
            painter.setPen(QPen(QColor(100, 200, 100), 2))
            painter.drawLine(3, 8, 13, 8)
            painter.drawLine(8, 3, 8, 13)
        elif icon_type == "edit":
            painter.drawLine(3, 12, 10, 5)
            painter.drawLine(10, 5, 13, 8)
            painter.drawLine(13, 8, 6, 15)
            painter.drawLine(6, 15, 3, 12)
        
        painter.end()
        return QIcon(pixmap)
    
    def show_admin_warning(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Требуются права администратора")
        msg.setText("Программа запущена без прав администратора!\n"
                   "Некоторые функции (работа с реестром, завершение процессов) будут недоступны.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Retry)
        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Retry:
            self.restart_as_admin()
    
    def restart_as_admin(self):
        script = os.path.abspath(sys.argv[0])
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}"', None, 1
            )
        except:
            pass
        sys.exit(0)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)
        
        # === Верхняя панель ===
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
                border-bottom: 2px solid #1a4a7a;
            }
            QLabel {
                color: #e0e0e0;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 0, 20, 0)
        header.setLayout(header_layout)
        
        icon_label = QLabel()
        icon_label.setPixmap(self.windowIcon().pixmap(32, 32))
        header_layout.addWidget(icon_label)
        
        title = QLabel("ЭЛЬБРУС")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #4a9eff; letter-spacing: 3px;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Административный инструментарий")
        subtitle.setStyleSheet("font-size: 12px; color: #666666; font-weight: 300; margin-left: 8px;")
        header_layout.addWidget(subtitle)
        
        header_layout.addStretch()
        
        version_label = QLabel("Версия 3.0")
        version_label.setStyleSheet("color: #444444; font-size: 11px; font-weight: 300;")
        header_layout.addWidget(version_label)
        
        header_layout.addSpacing(15)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #333333;")
        header_layout.addWidget(sep)
        header_layout.addSpacing(15)
        
        status_color = "#4CAF50" if self.is_admin else "#FF9800"
        status_text = "АДМИНИСТРАТОР" if self.is_admin else "ОГРАНИЧЕННЫЙ ДОСТУП"
        status_label = QLabel(f"● {status_text}")
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {status_color};
                font-weight: 600;
                font-size: 11px;
                padding: 4px 14px;
                border: 1px solid {status_color};
                border-radius: 12px;
                letter-spacing: 0.5px;
            }}
        """)
        header_layout.addWidget(status_label)
        
        header_layout.addSpacing(10)
        
        refresh_btn = QPushButton(self.create_icon("refresh"), " Обновить")
        refresh_btn.setFixedSize(120, 34)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a2a3a;
                color: #8ab4f8;
                border: 1px solid #2a4a6a;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2a3a5a;
                border-color: #4a7aaa;
            }
            QPushButton:pressed {
                background-color: #0a1a2a;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_all)
        header_layout.addWidget(refresh_btn)
        
        main_layout.addWidget(header)
        
        # === Вкладки ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #888888;
                padding: 14px 28px;
                margin-right: 1px;
                border: none;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.5px;
            }
            QTabBar::tab:selected {
                background-color: #1a1a1a;
                color: #4a9eff;
                border-bottom: 2px solid #4a9eff;
            }
            QTabBar::tab:hover {
                background-color: #2a2a2a;
                color: #cccccc;
            }
        """)
        main_layout.addWidget(self.tabs)
        
        # Вкладка 1: Процессы
        self.task_tab = QWidget()
        self.tabs.addTab(self.task_tab, self.create_icon("process"), "ПРОЦЕССЫ")
        self.init_task_tab()
        
        # Вкладка 2: Автозагрузка
        self.autorun_tab = QWidget()
        self.tabs.addTab(self.autorun_tab, self.create_icon("autorun"), "АВТОЗАГРУЗКА")
        self.init_autorun_tab()
        
        # Вкладка 3: Реестр (НОВАЯ!)
        self.registry_tab = QWidget()
        self.tabs.addTab(self.registry_tab, self.create_icon("registry"), "РЕЕСТР")
        self.init_registry_tab()
        
        # Вкладка 4: Восстановление
        self.restore_tab = QWidget()
        self.tabs.addTab(self.restore_tab, self.create_icon("recovery"), "ВОССТАНОВЛЕНИЕ")
        self.init_restore_tab()
        
        # Вкладка 5: CmdLine
        self.cmdline_tab = QWidget()
        self.tabs.addTab(self.cmdline_tab, self.create_icon("cmdline"), "CMDLINE")
        self.init_cmdline_tab()
    
    # ВКЛАДКА 1: ПРОЦЕССЫ (без изменений)
    
    def init_task_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        self.task_tab.setLayout(layout)
        self.task_tab.setStyleSheet("background-color: #1a1a1a;")
        
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(5)
        self.process_table.setHorizontalHeaderLabels([
            "Идентификатор", "Имя процесса", "Загрузка ЦП, %", "Память, МБ", "Состояние"
        ])
        self.process_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                gridline-color: #2a2a2a;
                border: 1px solid #2a2a2a;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background-color: #1a3a5c; color: #ffffff; }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: #888888;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #2a2a2a;
                font-weight: 600;
                font-size: 11px;
                letter-spacing: 0.5px;
            }
        """)
        self.process_table.horizontalHeader().setStretchLastSection(True)
        self.process_table.setAlternatingRowColors(False)
        self.process_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.process_table)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        kill_btn = QPushButton(self.create_icon("terminate"), " Завершить процесс")
        kill_btn.setFixedSize(180, 34)
        kill_btn.setStyleSheet("""
            QPushButton {
                background-color: #c62828; color: #ffffff; border: none;
                border-radius: 4px; font-size: 12px; font-weight: 600;
                padding: 5px 12px; letter-spacing: 0.5px;
            }
            QPushButton:hover { background-color: #b71c1c; }
        """)
        kill_btn.clicked.connect(self.kill_selected_process)
        btn_layout.addWidget(kill_btn)
        
        refresh_btn = QPushButton(self.create_icon("refresh"), " Обновить список")
        refresh_btn.setFixedSize(160, 34)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #252525; color: #cccccc;
                border: 1px solid #3a3a3a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 12px;
            }
            QPushButton:hover { background-color: #353535; border-color: #5a5a5a; }
        """)
        refresh_btn.clicked.connect(self.refresh_processes)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def refresh_processes(self):
        self.process_table.setRowCount(0)
        self.thread = ProcessUpdateThread()
        self.thread.data_ready.connect(self.update_process_table)
        self.thread.start()
    
    def update_process_table(self, processes):
        self.process_table.setRowCount(len(processes))
        for row, proc in enumerate(processes):
            self.process_table.setItem(row, 0, QTableWidgetItem(str(proc['pid'])))
            self.process_table.setItem(row, 1, QTableWidgetItem(proc['name']))
            cpu_item = QTableWidgetItem(f"{proc['cpu']:.1f}")
            if proc['cpu'] > 50:
                cpu_item.setBackground(QColor(200, 50, 50, 80))
            self.process_table.setItem(row, 2, cpu_item)
            self.process_table.setItem(row, 3, QTableWidgetItem(f"{proc['memory']:.1f}"))
            self.process_table.setItem(row, 4, QTableWidgetItem(proc['status']))
        self.process_table.resizeColumnsToContents()
    
    def kill_selected_process(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        selected = self.process_table.currentRow()
        if selected < 0:
            QMessageBox.information(self, "Информация", "Выберите процесс в таблице")
            return
        pid_item = self.process_table.item(selected, 0)
        if not pid_item:
            return
        pid = int(pid_item.text())
        name = self.process_table.item(selected, 1).text()
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Завершить процесс '{name}' (Идентификатор: {pid})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                gone, alive = psutil.wait_procs([proc], timeout=3)
                if proc in alive:
                    proc.kill()
                QMessageBox.information(self, "Успех", f"Процесс '{name}' завершён")
                self.refresh_processes()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось завершить процесс: {e}")
    
    # ВКЛАДКА 2: АВТОЗАГРУЗКА (без изменений)
    
    def init_autorun_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        self.autorun_tab.setLayout(layout)
        self.autorun_tab.setStyleSheet("background-color: #1a1a1a;")
        
        self.autorun_tree = QTreeWidget()
        self.autorun_tree.setHeaderLabels(["Раздел реестра / Параметр", "Значение"])
        self.autorun_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e1e; color: #d4d4d4;
                border: 1px solid #2a2a2a; font-size: 12px;
                font-family: 'Segoe UI';
            }
            QTreeWidget::item { padding: 6px; }
            QTreeWidget::item:selected { background-color: #1a3a5c; color: #ffffff; }
            QHeaderView::section {
                background-color: #1a1a1a; color: #888888; padding: 8px;
                border: none; border-bottom: 2px solid #2a2a2a;
                font-weight: 600; font-size: 11px; letter-spacing: 0.5px;
            }
        """)
        self.autorun_tree.setAlternatingRowColors(False)
        layout.addWidget(self.autorun_tree)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        scan_btn = QPushButton(self.create_icon("scan"), " Сканировать реестр")
        scan_btn.setFixedSize(170, 34)
        scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #252525; color: #cccccc;
                border: 1px solid #3a3a3a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 12px;
            }
            QPushButton:hover { background-color: #353535; border-color: #5a5a5a; }
        """)
        scan_btn.clicked.connect(self.load_autorun_data)
        btn_layout.addWidget(scan_btn)
        
        fix_btn = QPushButton(self.create_icon("repair"), " Восстановить Winlogon")
        fix_btn.setFixedSize(200, 34)
        fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #c62828; color: #ffffff; border: none;
                border-radius: 4px; font-size: 12px; font-weight: 600;
                padding: 5px 12px;
            }
            QPushButton:hover { background-color: #b71c1c; }
        """)
        fix_btn.clicked.connect(self.fix_winlogon)
        btn_layout.addWidget(fix_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def load_autorun_data(self):
        self.autorun_tree.clear()
        for section, path in RegistryManager.REG_PATH.items():
            section_item = QTreeWidgetItem(self.autorun_tree)
            section_item.setText(0, f"[{section}]")
            section_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
            section_item.setForeground(0, QColor(74, 158, 255))
            
            if section in ['Winlogon', 'AppInit_DLLs', 'CmdLine']:
                values = self.get_critical_values(section)
                for name, value in values:
                    child = QTreeWidgetItem(section_item)
                    child.setText(0, name)
                    child.setText(1, str(value) if value is not None else "Не найден")
                    if self.is_threat(section, name, value):
                        child.setBackground(0, QColor(200, 50, 50, 80))
                        child.setBackground(1, QColor(200, 50, 50, 80))
                        child.setText(0, "⚠ " + name)
            else:
                values = RegistryManager.get_all_values(winreg.HKEY_LOCAL_MACHINE, path)
                if not values:
                    child = QTreeWidgetItem(section_item)
                    child.setText(0, "✓ Пусто")
                    child.setForeground(0, QColor(100, 200, 100))
                else:
                    for name, value in values:
                        child = QTreeWidgetItem(section_item)
                        child.setText(0, name)
                        child.setText(1, str(value))
            section_item.setExpanded(True)
        self.autorun_tree.resizeColumnToContents(0)
        self.autorun_tree.resizeColumnToContents(1)
    
    def get_critical_values(self, section):
        if section == 'Winlogon':
            shell = RegistryManager.read_value(winreg.HKEY_LOCAL_MACHINE, 
                                              RegistryManager.REG_PATH['Winlogon'], 'Shell')
            userinit = RegistryManager.read_value(winreg.HKEY_LOCAL_MACHINE,
                                                 RegistryManager.REG_PATH['Winlogon'], 'Userinit')
            return [('Shell', shell), ('Userinit', userinit)]
        elif section == 'AppInit_DLLs':
            load = RegistryManager.read_value(winreg.HKEY_LOCAL_MACHINE,
                                             RegistryManager.REG_PATH['AppInit_DLLs'], 'LoadAppInit_DLLs')
            dlls = RegistryManager.read_value(winreg.HKEY_LOCAL_MACHINE,
                                             RegistryManager.REG_PATH['AppInit_DLLs'], 'AppInit_DLLs')
            return [('LoadAppInit_DLLs', load), ('AppInit_DLLs', dlls)]
        elif section == 'CmdLine':
            cmd = RegistryManager.read_value(winreg.HKEY_LOCAL_MACHINE,
                                            RegistryManager.REG_PATH['CmdLine'], 'CmdLine')
            return [('CmdLine', cmd)]
        return []
    
    def is_threat(self, section, name, value):
        if section == 'Winlogon':
            if name == 'Shell' and value != 'explorer.exe':
                return True
            if name == 'Userinit' and value != r'C:\Windows\System32\userinit.exe':
                return True
        elif section == 'AppInit_DLLs':
            if name == 'AppInit_DLLs' and value and value != '':
                return True
        elif section == 'CmdLine':
            if name == 'CmdLine' and value and 'cmd.exe' not in str(value).lower() and 'powershell' not in str(value).lower():
                return True
        return False
    
    def fix_winlogon(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Восстановить параметры Winlogon до стандартных?\nShell = explorer.exe\nUserinit = C:\\Windows\\System32\\userinit.exe",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = True
            success &= RegistryManager.write_value(
                winreg.HKEY_LOCAL_MACHINE, RegistryManager.REG_PATH['Winlogon'], 'Shell', 'explorer.exe')
            success &= RegistryManager.write_value(
                winreg.HKEY_LOCAL_MACHINE, RegistryManager.REG_PATH['Winlogon'], 'Userinit', r'C:\Windows\System32\userinit.exe')
            if success:
                QMessageBox.information(self, "Успех", "Winlogon восстановлен! Перезагрузите компьютер.")
                self.load_autorun_data()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось записать в реестр")
    
    # ВКЛАДКА 3: РЕЕСТР (НОВАЯ!)
    
    def init_registry_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        self.registry_tab.setLayout(layout)
        self.registry_tab.setStyleSheet("background-color: #1a1a1a;")
        
        # Верхняя панель с выбором куста
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        top_layout.addWidget(QLabel("Куст:"))
        
        self.hive_combo = QComboBox()
        self.hive_combo.addItems(list(RegistryManager.HIVES.keys()))
        self.hive_combo.setStyleSheet("""
            QComboBox {
                background-color: #252525; color: #d4d4d4;
                border: 1px solid #3a3a3a; border-radius: 4px;
                padding: 5px; min-width: 200px;
            }
            QComboBox:hover { background-color: #353535; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #252525; color: #d4d4d4;
                selection-background-color: #1a3a5c;
            }
        """)
        self.hive_combo.currentTextChanged.connect(self.load_registry_branch)
        top_layout.addWidget(self.hive_combo)
        
        top_layout.addSpacing(20)
        
        top_layout.addWidget(QLabel("Путь:"))
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Введите путь к разделу (например: SOFTWARE\\Microsoft\\Windows")
        self.path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252525; color: #d4d4d4;
                border: 1px solid #3a3a3a; border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus { border-color: #4a9eff; }
        """)
        self.path_edit.returnPressed.connect(self.load_registry_branch)
        top_layout.addWidget(self.path_edit)
        
        go_btn = QPushButton(self.create_icon("scan"), " Перейти")
        go_btn.setFixedSize(100, 32)
        go_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3a5a; color: #8ab4f8;
                border: 1px solid #2a4a6a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 10px;
            }
            QPushButton:hover { background-color: #2a4a6a; }
        """)
        go_btn.clicked.connect(self.load_registry_branch)
        top_layout.addWidget(go_btn)
        
        layout.addLayout(top_layout)
        
        # Основной виджет с деревом
        self.registry_tree = QTreeWidget()
        self.registry_tree.setHeaderLabels(["Имя", "Тип", "Значение"])
        self.registry_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e1e; color: #d4d4d4;
                border: 1px solid #2a2a2a; font-size: 12px;
                font-family: 'Segoe UI';
            }
            QTreeWidget::item { padding: 6px; }
            QTreeWidget::item:selected { background-color: #1a3a5c; color: #ffffff; }
            QHeaderView::section {
                background-color: #1a1a1a; color: #888888; padding: 8px;
                border: none; border-bottom: 2px solid #2a2a2a;
                font-weight: 600; font-size: 11px; letter-spacing: 0.5px;
            }
        """)
        self.registry_tree.setAlternatingRowColors(False)
        self.registry_tree.setIndentation(20)
        layout.addWidget(self.registry_tree)
        
        # Нижняя панель с кнопками
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        add_key_btn = QPushButton(self.create_icon("add"), " Создать раздел")
        add_key_btn.setFixedSize(150, 34)
        add_key_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a5a3a; color: #8af8b4;
                border: 1px solid #2a6a4a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 10px;
            }
            QPushButton:hover { background-color: #2a6a4a; }
        """)
        add_key_btn.clicked.connect(self.add_registry_key)
        btn_layout.addWidget(add_key_btn)
        
        add_value_btn = QPushButton(self.create_icon("add"), " Создать параметр")
        add_value_btn.setFixedSize(170, 34)
        add_value_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a5a3a; color: #8af8b4;
                border: 1px solid #2a6a4a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 10px;
            }
            QPushButton:hover { background-color: #2a6a4a; }
        """)
        add_value_btn.clicked.connect(self.add_registry_value)
        btn_layout.addWidget(add_value_btn)
        
        edit_btn = QPushButton(self.create_icon("edit"), " Редактировать")
        edit_btn.setFixedSize(150, 34)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3a5a; color: #8ab4f8;
                border: 1px solid #2a4a6a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 10px;
            }
            QPushButton:hover { background-color: #2a4a6a; }
        """)
        edit_btn.clicked.connect(self.edit_registry_value)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton(self.create_icon("remove"), " Удалить")
        delete_btn.setFixedSize(120, 34)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a1a1a; color: #f88a8a;
                border: 1px solid #6a2a2a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 10px;
            }
            QPushButton:hover { background-color: #6a2a2a; }
        """)
        delete_btn.clicked.connect(self.delete_registry_item)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Загружаем корневой раздел
        self.current_hive = winreg.HKEY_LOCAL_MACHINE
        self.current_path = ""
        self.load_registry_branch()
    
    def load_registry_branch(self):
        """Загружает содержимое раздела реестра."""
        self.registry_tree.clear()
        
        hive_name = self.hive_combo.currentText()
        self.current_hive = RegistryManager.get_hive(hive_name)
        if self.current_hive is None:
            return
        
        self.current_path = self.path_edit.text().strip()
        
        try:
            key = winreg.OpenKey(self.current_hive, self.current_path, 0, winreg.KEY_READ)
        except:
            # Если путь не существует, попробуем открыть корень
            if self.current_path:
                QMessageBox.warning(self, "Ошибка", f"Раздел '{self.current_path}' не найден!")
                self.path_edit.clear()
                try:
                    key = winreg.OpenKey(self.current_hive, "", 0, winreg.KEY_READ)
                    self.current_path = ""
                except:
                    return
            else:
                try:
                    key = winreg.OpenKey(self.current_hive, "", 0, winreg.KEY_READ)
                except:
                    return
        
        # Добавляем подразделы
        index = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, index)
                item = QTreeWidgetItem(self.registry_tree)
                item.setText(0, f"📁 {subkey_name}")
                item.setForeground(0, QColor(255, 200, 100))
                item.setData(0, Qt.ItemDataRole.UserRole, f"key|{subkey_name}")
                index += 1
            except OSError:
                break
        
        # Добавляем параметры
        index = 0
        while True:
            try:
                value_name, value_data, value_type = winreg.EnumValue(key, index)
                item = QTreeWidgetItem(self.registry_tree)
                
                # Имя параметра
                display_name = "(По умолчанию)" if value_name == "" else value_name
                item.setText(0, display_name)
                
                # Тип параметра
                type_names = {
                    winreg.REG_SZ: "REG_SZ",
                    winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
                    winreg.REG_BINARY: "REG_BINARY",
                    winreg.REG_DWORD: "REG_DWORD",
                    winreg.REG_DWORD_BIG_ENDIAN: "REG_DWORD_BIG_ENDIAN",
                    winreg.REG_LINK: "REG_LINK",
                    winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
                    winreg.REG_RESOURCE_LIST: "REG_RESOURCE_LIST",
                    winreg.REG_FULL_RESOURCE_DESCRIPTOR: "REG_FULL_RESOURCE_DESCRIPTOR",
                    winreg.REG_RESOURCE_REQUIREMENTS_LIST: "REG_RESOURCE_REQUIREMENTS_LIST",
                }
                type_name = type_names.get(value_type, f"Тип {value_type}")
                item.setText(1, type_name)
                
                # Значение параметра
                if value_type == winreg.REG_BINARY:
                    if isinstance(value_data, bytes):
                        display_value = " ".join(f"{b:02X}" for b in value_data[:16])
                        if len(value_data) > 16:
                            display_value += "..."
                    else:
                        display_value = str(value_data)
                elif value_type == winreg.REG_DWORD:
                    display_value = str(value_data)
                elif value_type in (winreg.REG_MULTI_SZ,):
                    if isinstance(value_data, (list, tuple)):
                        display_value = " | ".join(str(v) for v in value_data[:3])
                        if len(value_data) > 3:
                            display_value += "..."
                    else:
                        display_value = str(value_data)
                else:
                    display_value = str(value_data)
                item.setText(2, display_value)
                item.setData(0, Qt.ItemDataRole.UserRole, f"value|{value_name}|{value_type}")
                
                # Подсветка подозрительных значений
                if value_name.lower() in ['shell', 'userinit'] and self.current_path.lower().find('winlogon') != -1:
                    if value_data != 'explorer.exe' and value_name.lower() == 'shell':
                        item.setBackground(0, QColor(200, 50, 50, 80))
                    if value_data != r'C:\Windows\System32\userinit.exe' and value_name.lower() == 'userinit':
                        item.setBackground(0, QColor(200, 50, 50, 80))
                
                index += 1
            except OSError:
                break
        
        winreg.CloseKey(key)
        self.registry_tree.resizeColumnToContents(0)
        self.registry_tree.resizeColumnToContents(1)
        self.registry_tree.resizeColumnToContents(2)
        
        # Информация в строке состояния
        count = self.registry_tree.topLevelItemCount()
        status_text = f"Загружено: {count} элементов"
        self.statusBar().showMessage(status_text)
    
    def add_registry_key(self):
        """Создаёт новый раздел в реестре."""
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        
        name, ok = QInputDialog.getText(self, "Создать раздел", "Введите имя нового раздела:")
        if not ok or not name.strip():
            return
        
        new_path = f"{self.current_path}\\{name.strip()}" if self.current_path else name.strip()
        success = RegistryManager.create_key(self.current_hive, new_path)
        
        if success:
            QMessageBox.information(self, "Успех", f"Раздел '{name}' создан!")
            self.load_registry_branch()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать раздел '{name}'")
    
    def add_registry_value(self):
        """Создаёт новый параметр в реестре."""
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        
        # Диалог создания параметра
        dialog = QDialog(self)
        dialog.setWindowTitle("Создать параметр")
        dialog.setFixedSize(400, 250)
        dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #d4d4d4; }
            QLineEdit {
                background-color: #252525; color: #d4d4d4;
                border: 1px solid #3a3a3a; border-radius: 4px; padding: 5px;
            }
            QComboBox {
                background-color: #252525; color: #d4d4d4;
                border: 1px solid #3a3a3a; border-radius: 4px; padding: 5px;
            }
            QPushButton {
                background-color: #1a3a5a; color: #8ab4f8;
                border: 1px solid #2a4a6a; border-radius: 4px;
                padding: 8px 20px; font-weight: 500;
            }
            QPushButton:hover { background-color: #2a4a6a; }
        """)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        layout.addWidget(QLabel("Имя параметра:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("(оставьте пустым для значения по умолчанию)")
        layout.addWidget(name_edit)
        
        layout.addWidget(QLabel("Тип данных:"))
        type_combo = QComboBox()
        type_combo.addItems(["REG_SZ (Строка)", "REG_DWORD (Число)", "REG_BINARY (Бинарный)", "REG_EXPAND_SZ (Расширяемая строка)"])
        layout.addWidget(type_combo)
        
        layout.addWidget(QLabel("Значение:"))
        value_edit = QLineEdit()
        value_edit.setPlaceholderText("Введите значение")
        layout.addWidget(value_edit)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Создать")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        name = name_edit.text()
        value = value_edit.text()
        type_map = {
            0: winreg.REG_SZ,
            1: winreg.REG_DWORD,
            2: winreg.REG_BINARY,
            3: winreg.REG_EXPAND_SZ
        }
        reg_type = type_map.get(type_combo.currentIndex(), winreg.REG_SZ)
        
        # Преобразование значения
        if reg_type == winreg.REG_DWORD:
            try:
                value = int(value)
            except:
                QMessageBox.critical(self, "Ошибка", "Для типа REG_DWORD введите число!")
                return
        elif reg_type == winreg.REG_BINARY:
            # Пока поддерживаем только текстовый ввод
            value = value.encode('utf-8')
        
        success = RegistryManager.write_value(self.current_hive, self.current_path, name, value, reg_type)
        
        if success:
            QMessageBox.information(self, "Успех", f"Параметр '{name or '(По умолчанию)'}' создан!")
            self.load_registry_branch()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось создать параметр")
    
    def edit_registry_value(self):
        """Редактирует выбранный параметр."""
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        
        item = self.registry_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Информация", "Выберите параметр для редактирования")
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or not data.startswith("value|"):
            QMessageBox.information(self, "Информация", "Выберите параметр, а не раздел")
            return
        
        parts = data.split("|")
        if len(parts) < 3:
            return
        
        value_name = parts[1] if parts[1] != "(По умолчанию)" else ""
        value_type = int(parts[2])
        
        # Получаем текущее значение
        current_value = RegistryManager.read_value(self.current_hive, self.current_path, value_name)
        if current_value is None:
            QMessageBox.critical(self, "Ошибка", "Не удалось прочитать текущее значение")
            return
        
        # Простой диалог редактирования
        new_value, ok = QInputDialog.getText(
            self,
            "Редактировать параметр",
            f"Изменить значение для '{value_name or '(По умолчанию)'}':",
            QLineEdit.EchoMode.Normal,
            str(current_value)
        )
        
        if ok:
            success = RegistryManager.write_value(self.current_hive, self.current_path, value_name, new_value, value_type)
            if success:
                QMessageBox.information(self, "Успех", "Значение обновлено!")
                self.load_registry_branch()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить значение")
    
    def delete_registry_item(self):
        """Удаляет выбранный элемент (раздел или параметр)."""
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        
        item = self.registry_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Информация", "Выберите элемент для удаления")
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        name = item.text(0)
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if data.startswith("key|"):
            # Удаление раздела
            key_name = data.split("|")[1]
            full_path = f"{self.current_path}\\{key_name}" if self.current_path else key_name
            success = RegistryManager.delete_key(self.current_hive, full_path)
            if success:
                QMessageBox.information(self, "Успех", f"Раздел '{key_name}' удалён!")
                self.load_registry_branch()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить раздел. Возможно, он не пуст.")
        
        elif data.startswith("value|"):
            # Удаление параметра
            parts = data.split("|")
            value_name = parts[1] if parts[1] != "(По умолчанию)" else ""
            success = RegistryManager.delete_value(self.current_hive, self.current_path, value_name)
            if success:
                QMessageBox.information(self, "Успех", f"Параметр удалён!")
                self.load_registry_branch()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить параметр")
    
    # ВКЛАДКА 4: ВОССТАНОВЛЕНИЕ (без изменений)
    
    def init_restore_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        self.restore_tab.setLayout(layout)
        self.restore_tab.setStyleSheet("background-color: #1a1a1a;")
        
        title = QLabel("Инструменты восстановления системы")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600; padding: 10px 0; letter-spacing: 0.5px;")
        layout.addWidget(title)
        
        card_layout = QGridLayout()
        card_layout.setSpacing(15)
        
        card1 = self.create_tool_card(
            "Ассоциации файлов",
            "Восстановить стандартные ассоциации для .exe, .lnk, .bat, .cmd",
            "Восстановить", "repair"
        )
        card1.clicked.connect(self.restore_associations)
        card_layout.addWidget(card1, 0, 0)
        
        card2 = self.create_tool_card(
            "Восстановление Winlogon",
            "Восстановить параметры Shell и Userinit до стандартных значений",
            "Восстановить", "repair"
        )
        card2.clicked.connect(self.fix_winlogon)
        card_layout.addWidget(card2, 0, 1)
        
        card3 = self.create_tool_card(
            "Очистка временных файлов",
            "Удалить временные файлы и данные Prefetch для освобождения места",
            "Очистить", "clean"
        )
        card3.clicked.connect(self.clean_temp_files)
        card_layout.addWidget(card3, 1, 0)
        
        card4 = self.create_tool_card(
            "Удаление CmdLine",
            "Удалить подозрительные команды, запускающиеся до входа в систему",
            "Удалить", "remove"
        )
        card4.clicked.connect(self.clear_cmdline)
        card_layout.addWidget(card4, 1, 1)
        
        layout.addLayout(card_layout)
        layout.addStretch()
    
    def create_tool_card(self, title, description, button_text, icon_type):
        card = QPushButton()
        card.setFixedHeight(150)
        card.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e; border: 1px solid #2a2a2a;
                border-radius: 8px; text-align: left; padding: 15px;
            }
            QPushButton:hover { background-color: #2a2a2a; border-color: #4a7aaa; }
            QPushButton:pressed { background-color: #151515; }
        """)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        card.setLayout(layout)
        
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self.create_icon(icon_type).pixmap(20, 20))
        header_layout.addWidget(icon_label)
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; margin-left: 8px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #888888; font-size: 11px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        layout.addStretch()
        
        btn = QLabel(f"▸ {button_text}")
        btn.setStyleSheet("""
            QLabel {
                color: #4a9eff; font-size: 12px; font-weight: 500;
                padding: 4px 14px; border: 1px solid #4a9eff; border-radius: 4px;
            }
        """)
        layout.addWidget(btn)
        return card
    
    def restore_associations(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        try:
            subprocess.run(["assoc", ".exe=exefile"], shell=True, check=True)
            subprocess.run(["assoc", ".lnk=lnkfile"], shell=True, check=True)
            subprocess.run(["assoc", ".bat=batfile"], shell=True, check=True)
            subprocess.run(["assoc", ".cmd=cmdfile"], shell=True, check=True)
            QMessageBox.information(self, "Успех", "Ассоциации файлов восстановлены!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось восстановить: {e}")
    
    def clean_temp_files(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Очистить временные папки и Prefetch?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            temp_folders = [
                os.environ.get('TEMP', ''),
                os.environ.get('TMP', ''),
                r"C:\Windows\Prefetch"
            ]
            deleted = 0
            for folder in temp_folders:
                if folder and os.path.exists(folder):
                    try:
                        for file in os.listdir(folder):
                            file_path = os.path.join(folder, file)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                                deleted += 1
                    except:
                        pass
            QMessageBox.information(self, "Успех", f"Удалено {deleted} временных файлов")
    
    def clear_cmdline(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Ошибка", "Требуются права администратора!")
            return
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить параметр CmdLine из реестра?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = RegistryManager.delete_value(
                winreg.HKEY_LOCAL_MACHINE,
                RegistryManager.REG_PATH['CmdLine'],
                'CmdLine'
            )
            if success:
                QMessageBox.information(self, "Успех", "CmdLine удалён!")
                self.load_autorun_data()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить CmdLine")
    
    # ВКЛАДКА 5: CMDLINE (без изменений)
    
    def init_cmdline_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        self.cmdline_tab.setLayout(layout)
        self.cmdline_tab.setStyleSheet("background-color: #1a1a1a;")
        
        title = QLabel("Анализ команд, запускаемых до входа в систему")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600; padding: 5px 0; letter-spacing: 0.5px;")
        layout.addWidget(title)
        
        self.cmdline_text = QTextEdit()
        self.cmdline_text.setReadOnly(True)
        self.cmdline_text.setFont(QFont("Consolas", 10))
        self.cmdline_text.setStyleSheet("""
            QTextEdit {
                background-color: #151515; color: #d4d4d4;
                border: 1px solid #2a2a2a; border-radius: 4px; padding: 12px;
            }
        """)
        layout.addWidget(self.cmdline_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        scan_btn = QPushButton(self.create_icon("scan"), " Сканировать")
        scan_btn.setFixedSize(140, 34)
        scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #252525; color: #cccccc;
                border: 1px solid #3a3a3a; border-radius: 4px;
                font-size: 12px; font-weight: 500; padding: 5px 12px;
            }
            QPushButton:hover { background-color: #353535; border-color: #5a5a5a; }
        """)
        scan_btn.clicked.connect(self.check_cmdline)
        btn_layout.addWidget(scan_btn)
        
        remove_btn = QPushButton(self.create_icon("remove"), " Удалить угрозу")
        remove_btn.setFixedSize(170, 34)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #c62828; color: #ffffff; border: none;
                border-radius: 4px; font-size: 12px; font-weight: 600;
                padding: 5px 12px;
            }
            QPushButton:hover { background-color: #b71c1c; }
        """)
        remove_btn.clicked.connect(self.clear_cmdline)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.check_cmdline()
    
    def check_cmdline(self):
        self.cmdline_text.clear()
        cmdline = RegistryManager.read_value(
            winreg.HKEY_LOCAL_MACHINE,
            RegistryManager.REG_PATH['CmdLine'],
            'CmdLine'
        )
        self.cmdline_text.append("═" * 75)
        self.cmdline_text.append("  АНАЛИЗ CMDLINE")
        self.cmdline_text.append("═" * 75)
        self.cmdline_text.append(f"  Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if cmdline is None:
            self.cmdline_text.append("  СТАТУС: БЕЗОПАСНО")
            self.cmdline_text.append("  Подозрительных команд, запускаемых до входа, не обнаружено.")
        else:
            self.cmdline_text.append("  СТАТУС: ОБНАРУЖЕНА УГРОЗА")
            self.cmdline_text.append(f"  Значение: {cmdline}\n")
            if 'cmd.exe' in str(cmdline).lower() or 'powershell' in str(cmdline).lower():
                self.cmdline_text.append("  Информация: Команда использует консоль (cmd/powershell).")
            if 'explorer.exe' in str(cmdline).lower():
                self.cmdline_text.append("  Информация: Команда запускает explorer.exe.")
            suspicious = ['virus', 'malware', 'trojan', 'hack', 'crypt', '.bat', '.ps1']
            if any(word in str(cmdline).lower() for word in suspicious):
                self.cmdline_text.append("\n  ВНИМАНИЕ: ОБНАРУЖЕНА ПОДОЗРИТЕЛЬНАЯ КОМАНДА!")
                self.cmdline_text.append("  Рекомендуется удалить её с помощью кнопки 'Удалить угрозу'.")
        self.cmdline_text.append("\n" + "═" * 75)
        self.cmdline_text.append("  Примечание: CmdLine используется программами-вымогателями")
        self.cmdline_text.append("  для запуска до появления экрана входа в Windows.")
    
    # ОБНОВЛЕНИЕ ВСЕХ ДАННЫХ
    
    def refresh_all(self):
        self.refresh_processes()
        self.load_autorun_data()
        self.load_registry_branch()
        self.check_cmdline()
        QMessageBox.information(self, "Успех", "Все данные обновлены!")

# ЗАПУСК

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Text, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(26, 58, 92))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = ElbrusWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()