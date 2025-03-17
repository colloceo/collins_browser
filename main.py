import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                            QPushButton, QLineEdit, QHBoxLayout, QAction, QFileDialog, 
                            QListWidget, QTabWidget, QMenuBar, QMenu, QMessageBox,
                            QCheckBox, QLabel, QToolTip, QColorDialog)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineScript
from PyQt5.QtCore import QUrl, Qt, QSize, QPoint, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
import json
import uuid

# Custom New Tab Page HTML
NEW_TAB_HTML = """
<html>
<head>
    <style>
        body { background: #121212; color: white; font-family: Arial, sans-serif; text-align: center; }
        .search { margin: 100px auto; width: 50%; }
        input { width: 100%; padding: 10px; background: #222; color: white; border: 1px solid #555; border-radius: 5px; }
        .links { margin-top: 20px; }
        a { color: #1a73e8; text-decoration: none; margin: 0 10px; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="search">
        <input type="text" id="search" placeholder="Search Google or type a URL" onkeypress="if(event.keyCode==13) window.location.href='https://www.google.com/search?q='+this.value;">
    </div>
    <div class="links">
        <a href="https://www.google.com">Google</a>
        <a href="https://www.youtube.com">YouTube</a>
        <a href="https://www.github.com">GitHub</a>
    </div>
</body>
</html>
"""

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        layout = QVBoxLayout()
        self.dark_mode = QCheckBox("Dark Mode (Restart Required)")
        self.dark_mode.setChecked(True)
        layout.addWidget(QLabel("Browser Settings"))
        layout.addWidget(self.dark_mode)
        self.setLayout(layout)

class Browser(QMainWindow):
    instances = []

    def __init__(self, incognito=False):
        super().__init__()
        self.instances.append(self)
        self.incognito = incognito
        self.extensions = {}
        self.tab_groups = {}
        self.new_tab_url = "collins://newtab"  # Custom identifier for new tab
        
        self.profile = QWebEngineProfile("Incognito" if incognito else "Default", self)
        if incognito:
            self.profile.setHttpCacheType(QWebEngineProfile.NoCache)
            self.profile.clearHttpCache()
        
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
                color: white;
            }
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QLineEdit {
                background-color: #222;
                color: white;
                padding: 5px;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QTabWidget::pane {
                border: 0;
            }
            QTabBar::tab {
                background: #333;
                color: white;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background: #555;
            }
        """)
        
        self.setup_menu_bar()
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.tabs.setTabBarAutoHide(False)
        self.tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self.tab_context_menu)
        
        self.back_button = QPushButton("◀")
        self.forward_button = QPushButton("▶")
        self.reload_button = QPushButton("⟳")
        self.new_tab_button = QPushButton("+")
        self.url_bar = QLineEdit()
        self.bookmark_button = QPushButton("⭐")
        
        self.back_button.clicked.connect(self.go_back)
        self.forward_button.clicked.connect(self.go_forward)
        self.reload_button.clicked.connect(self.reload_page)
        self.new_tab_button.clicked.connect(self.add_new_tab)
        self.bookmark_button.clicked.connect(self.add_bookmark)
        self.url_bar.returnPressed.connect(self.load_url)
        
        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.reload_button)
        nav_layout.addWidget(self.new_tab_button)
        nav_layout.addWidget(self.url_bar, stretch=1)
        nav_layout.addWidget(self.bookmark_button)
        
        layout = QVBoxLayout()
        layout.addLayout(nav_layout)
        layout.addWidget(self.tabs)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        self.bookmarks = self.load_data("bookmarks.json") if not self.incognito else []
        self.history = self.load_data("history.json") if not self.incognito else []
        
        self.profile.downloadRequested.connect(self.handle_download)
        
        self.add_new_tab()
        self.setWindowTitle("Collins Browser" + (" (Incognito)" if self.incognito else ""))
        self.setGeometry(100, 100, 1200, 800)
        
        icon = QIcon()
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#1a73e8"))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setBrush(Qt.white)
        painter.drawEllipse(10, 10, 12, 12)
        painter.end()
        icon.addPixmap(pixmap)
        self.setWindowIcon(icon)
        
        self.settings = SettingsWindow()
    
    def setup_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        new_tab_action = QAction("New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self.add_new_tab)
        file_menu.addAction(new_tab_action)
        
        new_window_action = QAction("New Window", self)
        new_window_action.setShortcut("Ctrl+N")
        new_window_action.triggered.connect(lambda: Browser())
        file_menu.addAction(new_window_action)
        
        new_incognito_action = QAction("New Incognito Window", self)
        new_incognito_action.setShortcut("Ctrl+Shift+N")
        new_incognito_action.triggered.connect(lambda: Browser(incognito=True))
        file_menu.addAction(new_incognito_action)
        
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        file_menu.addAction(close_tab_action)
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close_all)
        file_menu.addAction(exit_action)
        
        view_menu = menubar.addMenu("View")
        fullscreen_action = QAction("Full Screen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        bookmarks_menu = menubar.addMenu("Bookmarks")
        show_bookmarks_action = QAction("Show Bookmarks", self)
        show_bookmarks_action.triggered.connect(self.show_bookmarks)
        bookmarks_menu.addAction(show_bookmarks_action)
        
        history_menu = menubar.addMenu("History")
        show_history_action = QAction("Show History", self)
        show_history_action.triggered.connect(self.show_history)
        history_menu.addAction(show_history_action)
        
        tools_menu = menubar.addMenu("Tools")
        extensions_action = QAction("Extensions", self)
        extensions_action.triggered.connect(self.manage_extensions)
        tools_menu.addAction(extensions_action)
        
        devtools_action = QAction("Developer Tools", self)
        devtools_action.setShortcut("Ctrl+Shift+I")
        devtools_action.triggered.connect(self.open_devtools)
        tools_menu.addAction(devtools_action)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
    
    def tab_context_menu(self, position):
        tab_bar = self.tabs.tabBar()
        tab_index = tab_bar.tabAt(position)
        if tab_index >= 0:
            menu = QMenu(self)
            close_action = menu.addAction("Close Tab")
            close_action.triggered.connect(lambda: self.close_tab(tab_index))
            close_others_action = menu.addAction("Close Other Tabs")
            close_others_action.triggered.connect(lambda: self.close_other_tabs(tab_index))
            group_action = menu.addAction("Add to Group")
            group_action.triggered.connect(lambda: self.add_to_group(tab_index))
            menu.exec_(tab_bar.mapToGlobal(position))
    
    def add_new_tab(self, qurl=None, label="New Tab"):
        if not isinstance(qurl, QUrl):
            browser = QWebEngineView()
            page = QWebEnginePage(self.profile, browser)
            browser.setPage(page)
            browser.setHtml(NEW_TAB_HTML)
            browser.setProperty("is_new_tab", True)  # Flag to identify new tab page
        else:
            browser = QWebEngineView()
            page = QWebEnginePage(self.profile, browser)
            browser.setPage(page)
            browser.setUrl(qurl)
            browser.setProperty("is_new_tab", False)
        
        browser.urlChanged.connect(lambda url: self.update_url_bar(url, browser))
        browser.loadFinished.connect(lambda ok: self.update_tab_title(browser))
        browser.page().fullScreenRequested.connect(self.handle_fullscreen_request)
        browser.setContextMenuPolicy(Qt.CustomContextMenu)
        browser.customContextMenuRequested.connect(lambda pos: self.page_context_menu(browser, pos))
        
        browser.renderProcessTerminated.connect(lambda: self.update_tab_preview(browser))
        browser.loadFinished.connect(lambda ok: self.update_tab_preview(browser))
        
        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)
    
    def page_context_menu(self, browser, position):
        menu = QMenu(self)
        back_action = menu.addAction("Back")
        forward_action = menu.addAction("Forward")
        reload_action = menu.addAction("Reload")
        menu.addSeparator()
        new_tab_action = menu.addAction("New Tab")
        devtools_action = menu.addAction("Inspect")
        
        action = menu.exec_(browser.mapToGlobal(position))
        if action == back_action:
            browser.back()
        elif action == forward_action:
            browser.forward()
        elif action == reload_action:
            browser.reload()
        elif action == new_tab_action:
            self.add_new_tab()
        elif action == devtools_action:
            self.open_devtools()
    
    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.close()
    
    def close_other_tabs(self, keep_index):
        for i in range(self.tabs.count() - 1, -1, -1):
            if i != keep_index:
                self.tabs.removeTab(i)
    
    def add_to_group(self, index):
        color = QColorDialog.getColor()
        if color.isValid():
            self.tab_groups[index] = color
            self.tabs.tabBar().setTabTextColor(index, color)
    
    def tab_changed(self, index):
        if index >= 0:
            browser = self.tabs.widget(index)
            if browser:
                self.update_url_bar(browser.url(), browser)
    
    def load_url(self):
        url = self.url_bar.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            if "." not in url:
                url = f"https://www.google.com/search?q={url}"
            else:
                url = "https://" + url
        self.current_browser().setUrl(QUrl(url))
        self.current_browser().setFocus()
    
    def go_back(self):
        self.current_browser().back()
    
    def go_forward(self):
        self.current_browser().forward()
    
    def reload_page(self):
        self.current_browser().reload()
    
    def add_bookmark(self):
        if self.incognito:
            QMessageBox.warning(self, "Incognito", "Bookmarks are disabled in Incognito mode")
            return
        url = self.current_browser().url().toString()
        if url and url not in self.bookmarks and not url.startswith("data:"):
            self.bookmarks.append(url)
            self.save_data("bookmarks.json", self.bookmarks)
            QMessageBox.information(self, "Bookmark", "Page bookmarked!")
    
    def show_bookmarks(self):
        window = QWidget()
        window.setWindowTitle("Bookmarks")
        layout = QVBoxLayout()
        list_widget = QListWidget()
        list_widget.addItems(self.bookmarks)
        list_widget.itemDoubleClicked.connect(self.load_bookmark)
        layout.addWidget(list_widget)
        window.setLayout(layout)
        window.resize(400, 300)
        window.show()
    
    def load_bookmark(self, item):
        self.current_browser().setUrl(QUrl(item.text()))
    
    def show_history(self):
        window = QWidget()
        window.setWindowTitle("History")
        layout = QVBoxLayout()
        list_widget = QListWidget()
        list_widget.addItems(self.history)
        list_widget.itemDoubleClicked.connect(self.load_bookmark)
        layout.addWidget(list_widget)
        window.setLayout(layout)
        window.resize(400, 300)
        window.show()
    
    def handle_download(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", download.suggestedFileName())
        if path:
            download.setPath(path)
            download.accept()
    
    def current_browser(self):
        return self.tabs.currentWidget()
    
    def update_url_bar(self, qurl, browser):
        if browser == self.current_browser():
            url_str = qurl.toString()
            is_new_tab = browser.property("is_new_tab") or url_str.startswith("data:text/html")
            if is_new_tab:
                self.url_bar.clear()  # Clear URL bar for new tab page
            else:
                self.url_bar.setText(url_str)
            if url_str and not self.incognito and not is_new_tab:
                self.history.append(url_str)
                self.save_data("history.json", self.history)
    
    def update_tab_title(self, browser):
        index = self.tabs.indexOf(browser)
        if index >= 0:
            title = browser.page().title()
            if title:
                self.tabs.setTabText(index, title[:20] + "..." if len(title) > 20 else title)
                self.tabs.setTabToolTip(index, title)
    
    def update_tab_preview(self, browser):
        index = self.tabs.indexOf(browser)
        if index >= 0:
            pixmap = QPixmap(QSize(200, 150))
            browser.render(pixmap)
            self.tabs.tabBar().setTabData(index, pixmap)
            self.tabs.tabBar().setToolTipDuration(5000)
    
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def handle_fullscreen_request(self, request):
        request.accept()
        if request.toggleOn():
            self.showFullScreen()
        else:
            self.showNormal()
    
    def open_devtools(self):
        browser = self.current_browser()
        if browser:
            dev_view = QWebEngineView()
            browser.page().setDevToolsPage(dev_view.page())
            dev_window = QWidget()
            dev_layout = QVBoxLayout()
            dev_layout.addWidget(dev_view)
            dev_window.setLayout(dev_layout)
            dev_window.setWindowTitle("Developer Tools")
            dev_window.resize(800, 600)
            dev_window.show()
    
    def manage_extensions(self):
        window = QWidget()
        window.setWindowTitle("Extensions")
        layout = QVBoxLayout()
        load_button = QPushButton("Load Extension")
        load_button.clicked.connect(self.load_extension)
        layout.addWidget(QLabel("Extensions (JavaScript files)"))
        layout.addWidget(load_button)
        for ext_id, ext_file in self.extensions.items():
            layout.addWidget(QLabel(f"Loaded: {ext_file}"))
        window.setLayout(layout)
        window.resize(400, 300)
        window.show()
    
    def load_extension(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Extension", "", "JavaScript Files (*.js)")
        if file_path:
            with open(file_path, 'r') as f:
                script_content = f.read()
            script = QWebEngineScript()
            script.setName(str(uuid.uuid4()))
            script.setSourceCode(script_content)
            script.setInjectionPoint(QWebEngineScript.DocumentReady)
            script.setRunsOnSubFrames(True)
            self.profile.scripts().insert(script)
            self.extensions[script.name()] = os.path.basename(file_path)
            QMessageBox.information(self, "Extension", f"Loaded: {file_path}")
    
    def show_settings(self):
        self.settings.show()
    
    def close_all(self):
        for instance in self.instances[:]:
            instance.close()
        self.instances.clear()
    
    def load_data(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return []
    
    def save_data(self, filename, data):
        if not self.incognito:
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = Browser()
    window.show()
    sys.exit(app.exec_())