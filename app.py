import configparser
import english as lang
import io
import json
import logging
import multiprocessing.dummy as threadiprocessing  # IT'S A GOOD NAME AND YOU KNOW IT OKAY
import os
import platform
import pyperclip
import requests
import shutil
import subprocess
import threading
import uuid
import webbrowser

from bs4 import BeautifulSoup
from constants import *
from http import HTTPStatus
from PyQt6 import QtCore, QtGui, QtWidgets

class AppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(lang.windowTitle % VERSION)
        self.setMinimumSize(QtCore.QSize(4, 3) * WINDOW_SIZE)
        self.teases: dict[str, TeaseCard] = self.loadTeases(TEASES_DIR)
        self.selectedTease: TeaseCard = None
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        if "icon_path" not in self.config["General"]:
            self.config["General"]["icon_path"] = "icons/icon.png"
        
        self.globalSettingsPopup = GlobalSettingsPopup(self)
        self.downloadTeasePopup = DownloadTeasePopup(self)
        
        self.refreshIcon()

        layout = QtWidgets.QHBoxLayout()

        # Holds the search box as well
        cardsSubLayout = QtWidgets.QVBoxLayout()

        searchSubLayout = QtWidgets.QHBoxLayout()

        # TODO icon doesn't invert colors properly
        searchIcon = QtGui.QIcon.fromTheme("system-search-symbolic", QtGui.QIcon(SEARCH_ICON))
        searchImage = QtWidgets.QLabel(self)
        searchImage.setPixmap(searchIcon.pixmap(QtCore.QSize(16, 16)))
        searchSubLayout.addWidget(searchImage)

        searchBox = QtWidgets.QLineEdit(self)
        searchBox.textChanged.connect(self.filterTeases)
        searchSubLayout.addWidget(searchBox)

        cardsSubLayout.addLayout(searchSubLayout)

        # Need a second sublayout and widget so the cards don't expand vertically when
        # the window is too big and don't get crushed when the window is too small.
        teaseListScrollHackSubLayout = QtWidgets.QVBoxLayout()

        self.teaseListSubLayout = QtWidgets.QVBoxLayout()
        # TODO make it not look weird when there's only one item left in the filter (Linux only)

        for tease in self.teases.values():
            self.teaseListSubLayout.addWidget(tease)

        teaseListWidget = QtWidgets.QWidget(self)
        teaseListWidget.setLayout(self.teaseListSubLayout)

        teaseListScrollHackSubLayout.addWidget(teaseListWidget)

        teaseListScrollHackSubLayout.addStretch()

        teaseListScrollHackWidget = QtWidgets.QWidget(self)
        teaseListScrollHackWidget.setLayout(teaseListScrollHackSubLayout)

        teaseScroll = QtWidgets.QScrollArea(self)
        teaseScroll.setWidget(teaseListScrollHackWidget)
        teaseScroll.setWidgetResizable(True)  # Default is False
        # teaseScroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cardsSubLayout.addWidget(teaseScroll)

        layout.addLayout(cardsSubLayout)

        buttonsSubLayout = QtWidgets.QVBoxLayout()

        globalSettingsButton = QtWidgets.QPushButton(lang.globalSettings, self)
        globalSettingsButton.pressed.connect(self.showGlobalSettingsPopup)
        buttonsSubLayout.addWidget(globalSettingsButton)

        settingsButton = QtWidgets.QPushButton(lang.teaseSettings, self)
        settingsButton.pressed.connect(self.showSettingsPopup)
        buttonsSubLayout.addWidget(settingsButton)

        openTeaseButton = QtWidgets.QPushButton(lang.openTease, self)
        openTeaseButton.pressed.connect(self.openTeaseInBrowser)
        buttonsSubLayout.addWidget(openTeaseButton)

        copyTeaseUrlButton = QtWidgets.QPushButton(lang.copyTeaseUrl, self)
        copyTeaseUrlButton.pressed.connect(self.copyTeaseUrl)
        buttonsSubLayout.addWidget(copyTeaseUrlButton)

        openFolderButton = QtWidgets.QPushButton(lang.openFolder, self)
        openFolderButton.pressed.connect(self.openFolder)
        buttonsSubLayout.addWidget(openFolderButton)

        buttonsSubLayout.addStretch()

        importTeaseButton = QtWidgets.QPushButton(lang.importTease, self)
        importTeaseButton.pressed.connect(self.importTease)
        buttonsSubLayout.addWidget(importTeaseButton)

        downloadTeaseButton = QtWidgets.QPushButton(lang.downloadTease, self)
        downloadTeaseButton.pressed.connect(self.showDownloadPopup)
        buttonsSubLayout.addWidget(downloadTeaseButton)

        buttonsSubLayout.addStretch()

        deleteTeaseButton = QtWidgets.QPushButton(lang.deleteTease, self)
        deleteTeaseButton.pressed.connect(self.deleteTease)
        buttonsSubLayout.addWidget(deleteTeaseButton)

        layout.addLayout(buttonsSubLayout)

        mainWidget = QtWidgets.QWidget(self)
        mainWidget.setLayout(layout)
        self.setCentralWidget(mainWidget)
    
    def setSelectedTease(self, tease):
        if self.selectedTease is not None:
            self.selectedTease.setAutoFillBackground(False)
        self.selectedTease: TeaseCard = tease
        self.selectedTease.setAutoFillBackground(True)
        logging.debug(f"Set selected tease to {tease} with rootDir {tease.rootDir}")
    
    def showSettingsPopup(self):
        # Need a constant handle for PyQt
        if self.selectedTease is not None:
            self.selectedTease.showSettingsPopup()
    
    def importTease(self):
        rootDir = QtWidgets.QFileDialog.getExistingDirectory(self, lang.fileSelectTease)
        if rootDir == "":
            logging.debug("Canceled when importing tease from EOS at file picker.")
        else:
            newRootDir = getNewRootDir()
            logging.info(f"Importing Tease from {rootDir} to {newRootDir}")
            os.mkdir(newRootDir)
            copyAll(rootDir, newRootDir, "tease", "timg", "config.ini", "eosscript.json")
            if (teaseId := os.path.basename(rootDir)).isdigit():
                teaseCard = TeaseCard(self, newRootDir, defaultTeaseId=teaseId)
                teaseCard.saveSettings()
                self.addTeaseToList(newRootDir, teaseCard)
            else:
                self.addTeaseToList(newRootDir, TeaseCard(self, newRootDir))
            logging.debug(teaseId)

    def addTeaseToList(self, rootDir, tease):
        self.teases[rootDir] = tease
        self.teaseListSubLayout.addWidget(tease)
    
    def deleteTease(self):
        if self.selectedTease is not None:
            shutil.rmtree(self.selectedTease.rootDir)
            self.removeTeaseFromList(self.selectedTease)
            self.selectedTease = None

    def removeTeaseFromList(self, tease):
        del self.teases[tease.rootDir]
        self.teaseListSubLayout.removeWidget(tease)
        tease.close()
    
    def filterTeases(self, text: str):
        for tease in self.teases.values():
            if text.lower() in tease.config["General"]["title"].lower() or \
                 text.lower() in tease.config["General"]["author"].lower():
                tease.show()
            else:
                tease.hide()

    def showGlobalSettingsPopup(self):
        self.globalSettingsPopup.refreshSettings()
        self.globalSettingsPopup.show()
    
    def saveSettings(self):
        with open("config.ini", "w") as inifile:
            self.config.write(inifile)
        self.refreshIcon()
        global httpd
        if (self.config["General"]["ip"], int(self.config["General"]["port"])) != httpd.server_address:
            logging.debug("Restarting HTTP Server")
            httpd = restartHttpServer(httpd)
    
    def openTeaseInBrowser(self):
        if self.selectedTease is not None:
            webbrowser.open_new_tab(self.getTeaseUrl())
    
    def copyTeaseUrl(self):
        if self.selectedTease is not None:
            pyperclip.copy(self.getTeaseUrl())
    
    def getTeaseUrl(self):
        # Sorry not sorry
        return f"http://{self.config['General']['ip']}:{self.config['General']['port']}/{self.selectedTease.rootDir.removeprefix(TEASES_DIR).replace(os.path.sep, '/').lstrip('/')}"

    def showDownloadPopup(self):
        self.downloadTeasePopup.refreshSettings()
        self.downloadTeasePopup.show()

    def loadTeases(self, searchDir, testFile = "config.ini") -> dict:
        teases = dict()
        for file in os.listdir(searchDir):
            if os.path.isdir(rootDir := os.path.join(searchDir, file)) and testFile in os.listdir(rootDir):
                teases[rootDir] = TeaseCard(self, rootDir)
        return teases
    
    def openFolder(self):
        fileManagerMap = {
            "Windows": "explorer.exe",
            "Darwin": "open",
            "Linux": "xdg-open"
        }
        if self.selectedTease is not None:
            subprocess.Popen([fileManagerMap[platform.system()], self.selectedTease.rootDir])
    
    def refreshIcon(self):
        self.setWindowIcon(QtGui.QIcon(self.config["General"]["icon_path"]))

class TeaseCard(QtWidgets.QWidget):
    def __init__(self, creator, rootDir, defaultTeaseId="unset", defaultThumb = DEFAULT_THUMB, configOverride=None):
        super().__init__(creator)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), palette.color(QtGui.QPalette.ColorRole.Highlight))
        self.setPalette(palette)
        # self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.creator = creator
        self.rootDir = rootDir
        self.config = self.loadConfig() if configOverride is None else configOverride
        if "tease_id" not in self.config["General"]:
            self.config["General"]["tease_id"] = defaultTeaseId
        if "unhide_timers" not in self.config["General"]:
            self.config["General"]["unhide_timers"] = "false"

        self.eosscript = self.loadEosscript()
        self.settingsPopup = None
        
        layout = QtWidgets.QHBoxLayout()
        
        thumbnail = self.loadThumbnail(defaultThumb)
        dim = min(thumbnail.width(), thumbnail.height())
        thumbnail = thumbnail.copy(
            (thumbnail.width() - dim) // 2,  # top left x
            (thumbnail.height() - dim) // 2,  # top left y
            dim, dim)  # width, height
        image = QtWidgets.QLabel(self)
        image.setPixmap(thumbnail.scaledToHeight(80))
        layout.addWidget(image)

        metaSubLayout = QtWidgets.QVBoxLayout()
        metaSubLayoutDefaultMargins = metaSubLayout.getContentsMargins()
        metaSubLayout.setContentsMargins(12, metaSubLayoutDefaultMargins[1], 24, metaSubLayoutDefaultMargins[3])

        metaSubLayout.addStretch()

        self.titleMeta = QtWidgets.QLabel(self)
        titleFont = self.titleMeta.font()
        titleFont.setPointSize(14)
        self.titleMeta.setFont(titleFont)
        metaSubLayout.addWidget(self.titleMeta)

        self.authorMeta = QtWidgets.QLabel(self)
        authorFont = self.authorMeta.font()
        authorFont.setPointSize(11)
        self.authorMeta.setFont(authorFont)
        metaSubLayout.addWidget(self.authorMeta)

        self.teaseIdMeta = QtWidgets.QLabel(self)
        teaseIdFont = self.teaseIdMeta.font()
        teaseIdFont.setPointSize(8)
        teaseIdFont.setItalic(True)
        self.teaseIdMeta.setFont(teaseIdFont)
        metaSubLayout.addWidget(self.teaseIdMeta)

        metaSubLayout.addStretch()

        layout.addLayout(metaSubLayout)

        layout.addStretch()

        self.refreshMetadata()
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        # https://stackoverflow.com/questions/44094293/pyqt-widget-seems-to-forget-its-parent
        self.creator.setSelectedTease(self)
        return super().mousePressEvent(event)
    
    def showSettingsPopup(self):
        if self.settingsPopup is None:
            self.settingsPopup = TeaseSettingsPopup(self)
        self.settingsPopup.refreshSettings()
        self.settingsPopup.show()
    
    def saveSettings(self):
        with io.StringIO() as configIo:
            self.config.write(configIo, False)
            iniHack = configIo.getvalue()
        iniHack = iniHack.replace("[General]\n", "")
        with open(os.path.join(self.rootDir, "config.ini"), "w") as iniFile:
            iniFile.write(iniHack)
        self.eosscript = self.loadEosscript()
        logging.debug(f"Reloaded eosscript for {self.rootDir} with {self.config['General']['unhide_timers']=}")
        self.refreshMetadata()

    def refreshMetadata(self):
        self.titleMeta.setText(self.config["General"]["title"])
        self.authorMeta.setText(self.config["General"]["author"])
        self.teaseIdMeta.setText(f"ID: {self.config['General']['tease_id']}")
    
    def loadEosscript(self):
        with open(os.path.join(self.rootDir, "eosscript.json")) as jFile:
            eosscript = json.load(jFile)
        if self.config["General"]["unhide_timers"] == "true":
            unhideTimers(eosscript)
        return eosscript
    
    def loadConfig(self):
        config = configparser.ConfigParser()
        # Hack because eos.outer.js can't handle sectioned files
        iniHack = "[General]\n"
        with open(os.path.join(self.rootDir, "config.ini")) as iniFile:
            iniHack += iniFile.read()
        config.read_string(iniHack)
        return config
    
    def loadThumbnail(self, defaultThumb):
        imgHash = None
        if (imgLocator := findFirstImage(self.eosscript["pages"]["start"])) is not None:
            # Really wish we had streams right now
            if imgLocator.startswith("gallery:"):
                galId, imgId = imgLocator[len("gallery:"):].split("/", 1)
                imgId = int(imgId)
                for i in self.eosscript["galleries"][galId]["images"]:
                    if i["id"] == imgId:
                        imgHash = i["hash"]
                        break
                else:
                    logging.warning(f"Could not find thumbnail in eosscript galleries for {self.rootDir}")
            elif imgLocator.startswith("file:"):
                imgHash = self.eosscript["files"][imgLocator[len("file:"):]]["hash"]
        else:
            logging.warning(f"Could not find thumbnail in eosscript for {self.rootDir}")

        thumbnail = QtGui.QPixmap(defaultThumb)
        if imgHash is not None:
            for img in os.listdir(imgDir := os.path.join(self.rootDir, "timg", "tb_xl")):
                if img.startswith(imgHash):
                    thumbnail = QtGui.QPixmap(os.path.join(imgDir, img))
                    logging.debug(os.path.join(imgDir, img))
                    break
            else:
                logging.warning(f"Could not find thumbnail in media for {self.rootDir}")
        else:
            logging.warning(f"No image extractor for image locator {imgLocator}")
        
        return thumbnail

class TeaseSettingsPopup(QtWidgets.QDialog):
    # creator: The object that created the widget. Its antithesis is self.windows.
    def __init__(self, creator: TeaseCard):
        super().__init__(creator)
        self.setWindowTitle(f"{lang.teaseSettings}: {creator.config['General']['title']}")
        self.setMinimumWidth(4 * WINDOW_SIZE)
        self.setModal(True)
        self.creator = creator

        layout = QtWidgets.QGridLayout()

        titleTextBoxHint = QtWidgets.QLabel(self)
        titleTextBoxHint.setText(lang.titleTextBoxHint)
        layout.addWidget(titleTextBoxHint, 0, 0)

        self.titleTextBox = QtWidgets.QLineEdit(self)
        layout.addWidget(self.titleTextBox, 0, 1)

        authorTextBoxHint = QtWidgets.QLabel(self)
        authorTextBoxHint.setText(lang.authorTextBoxHint)
        layout.addWidget(authorTextBoxHint, 1, 0)

        self.authorTextBox = QtWidgets.QLineEdit(self)
        layout.addWidget(self.authorTextBox, 1, 1)

        idTextBoxHint = QtWidgets.QLabel(self)
        idTextBoxHint.setText(lang.idTextBoxHint)
        layout.addWidget(idTextBoxHint, 2, 0)

        self.teaseIdTextBox = QtWidgets.QLineEdit(self)
        layout.addWidget(self.teaseIdTextBox, 2, 1)

        self.unhideTimersButton = QtWidgets.QCheckBox(self)
        self.unhideTimersButton.setText(lang.unhideTimers)
        layout.addWidget(self.unhideTimersButton, 3, 0, 1, 2)

        self.debugModeButton = QtWidgets.QCheckBox(self)
        self.debugModeButton.setText(lang.debugMode)
        layout.addWidget(self.debugModeButton, 4, 0, 1, 2)
        
        saveButton = QtWidgets.QPushButton(self)
        saveButton.setText(lang.saveSettings)
        saveButton.clicked.connect(self.saveSettings)
        layout.addWidget(saveButton, 5, 0, 1, 2)

        self.setLayout(layout)
    
    def refreshSettings(self):
        self.titleTextBox.setText(self.creator.config["General"]["title"])
        self.authorTextBox.setText(self.creator.config["General"]["author"])
        self.teaseIdTextBox.setText(self.creator.config["General"]["tease_id"])
        self.unhideTimersButton.setChecked(self.creator.config["General"]["unhide_timers"] == "true")
        self.debugModeButton.setChecked(self.creator.config["General"]["preview"] == "true")
    
    def saveSettings(self):
        self.creator.config["General"]["title"] = self.titleTextBox.text()
        self.creator.config["General"]["author"] = self.authorTextBox.text()
        self.creator.config["General"]["tease_id"] = self.teaseIdTextBox.text()
        self.creator.config["General"]["unhide_timers"] = str(self.unhideTimersButton.isChecked()).lower()
        self.creator.config["General"]["preview"] = str(self.debugModeButton.isChecked()).lower()
        self.creator.saveSettings()
        self.hide()

class GlobalSettingsPopup(QtWidgets.QDialog):
    def __init__(self, creator: AppWindow):
        super().__init__(creator)
        self.setWindowTitle(f"{lang.windowTitle % VERSION}: {lang.globalSettings}")
        self.setMinimumWidth(4 * WINDOW_SIZE)
        self.setModal(True)
        self.creator = creator
        self.iconPath = None

        layout = QtWidgets.QGridLayout()

        ipTextBoxHint = QtWidgets.QLabel(self)
        ipTextBoxHint.setText(lang.ipTextBoxHint)
        layout.addWidget(ipTextBoxHint, 0, 0)

        self.ipTextBox = QtWidgets.QLineEdit(self)
        layout.addWidget(self.ipTextBox, 0, 1)

        portTextBoxHint = QtWidgets.QLabel(self)
        portTextBoxHint.setText(lang.portTextBoxHint)
        layout.addWidget(portTextBoxHint, 1, 0)

        self.portTextBox = QtWidgets.QLineEdit(self)
        layout.addWidget(self.portTextBox, 1, 1)

        changeIconButton = QtWidgets.QPushButton(lang.changeIcon, self)
        changeIconButton.pressed.connect(self.changeIcon)
        layout.addWidget(changeIconButton, 2, 0)
        
        self.currentIconPath = QtWidgets.QLabel(self)
        layout.addWidget(self.currentIconPath, 2, 1)
        
        saveButton = QtWidgets.QPushButton(self)
        saveButton.setText(lang.saveSettings)
        saveButton.clicked.connect(self.saveSettings)
        layout.addWidget(saveButton, 3, 0, 1, 2)

        self.setLayout(layout)
    
    def refreshSettings(self):
        self.ipTextBox.setText(self.creator.config["General"]["ip"])
        self.portTextBox.setText(self.creator.config["General"]["port"])
        self.setIconPath(self.creator.config["General"]["icon_path"])
    
    def saveSettings(self):
        self.creator.config["General"]["ip"] = self.ipTextBox.text()
        self.creator.config["General"]["port"] = self.portTextBox.text()
        self.creator.config["General"]["icon_path"] = self.iconPath
        self.creator.saveSettings()
        self.hide()
    
    def changeIcon(self):
        iconPath = QtWidgets.QFileDialog.getOpenFileName(self, lang.fileSelectIcon, filter="Image files (*.jpg *.jpeg *.png *.ico *.gif *.icns)")[0]
        if iconPath != "":
            self.setIconPath(iconPath)
            logging.debug(f"Set icon to {self.iconPath}")
    
    def setIconPath(self, iconPath):
        self.iconPath = iconPath
        # Again, sorry not sorry
        self.currentIconPath.setText(f"{self.iconPath[:16]}...{self.iconPath[len(self.iconPath)-21:]}" if len(self.iconPath) > 40 else self.iconPath)

class DownloadTeasePopup(QtWidgets.QDialog):
    def __init__(self, creator: AppWindow):
        super().__init__(creator)
        self.setWindowTitle(f"{lang.windowTitle % VERSION}: {lang.downloadTease}")
        self.setMinimumWidth(4 * WINDOW_SIZE)
        self.setModal(True)
        self.creator = creator
        self.downloadThread = None
        self.downloadedTeases: list[tuple] = list()

        layout = QtWidgets.QVBoxLayout()

        idTextBoxSubLayout = QtWidgets.QHBoxLayout()
        
        idTextBoxHint = QtWidgets.QLabel(self)
        idTextBoxHint.setText(lang.idTextBoxHint)
        idTextBoxSubLayout.addWidget(idTextBoxHint)

        idTextBoxValidator = QtGui.QIntValidator(self)

        self.idTextBox = QtWidgets.QLineEdit(self)
        self.idTextBox.setValidator(idTextBoxValidator)
        idTextBoxSubLayout.addWidget(self.idTextBox)
        
        layout.addLayout(idTextBoxSubLayout)
        
        self.downloadButton = QtWidgets.QPushButton(self)
        self.downloadButton.setText(lang.downloadButton)
        self.downloadButton.clicked.connect(self.beginDownload)
        layout.addWidget(self.downloadButton)
        
        self.downloadStatus = QtWidgets.QLabel(self)
        layout.addWidget(self.downloadStatus)

        self.setLayout(layout)
    
    def refreshSettings(self):
        self.idTextBox.setText("")
        self.downloadStatus.setText(lang.downloadInfo)
    
    def beginDownload(self):
        if self.downloadThread is None:
            self.idTextBox.setEnabled(False)
            # TODO make the button into a progress bar?
            self.downloadButton.setEnabled(False)
            self.downloadThread = StoppableThread(target=self.downloadTease)
            self.downloadThread.start()
    
    def closeEvent(self, event):
        if self.downloadThread is not None:
            self.downloadThread.stop()
        for rootDir, config in self.downloadedTeases:
            logging.debug(f"Creating tease card for {rootDir}.")
            teaseCard = TeaseCard(self.creator, rootDir, configOverride = config)
            teaseCard.saveSettings()
            self.creator.addTeaseToList(rootDir, teaseCard)
        self.downloadedTeases.clear()
        return super().closeEvent(event)
    
    def downloadTease(self):
        try:
            rootDir = getNewRootDir()
            logging.debug(f"Creating folder {rootDir} for downloading tease id {self.idTextBox.text()}.")
            os.makedirs(os.path.join(rootDir, "timg", "tb_xl"))
            os.mkdir(os.path.join(rootDir, "tease"))
            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            logging.debug(f"Downloading metadata for {self.idTextBox.text()}.")
            self.downloadStatus.setText(lang.downloadingMeta)
            teaseReq = requests.get(f"https://milovana.com/webteases/showtease.php?id={self.idTextBox.text()}")
            if teaseReq.status_code != HTTPStatus.OK:
                self.downloadStatus.setText(lang.downloadUnknownError)
                logging.error(f"Network error {teaseReq.status_code} occurred when downloading the tease:")
                logging.error(f"{teaseReq.content=}")
                logging.error(f"{teaseReq.reason=}")
                return
            # Can't use status codes since milovana always seems to return 200.
            elif b"<title>Milovana.com - Tease not found.</title>" in teaseReq.content:
                self.downloadStatus.setText(lang.downloadInvalidId)
                logging.error(f"Tease ID {self.idTextBox.text()} was not found on the remote server.")
                return
            metadata = BeautifulSoup(teaseReq.content.decode(), "html.parser").find("body", {"class": "eosTopBody"}).attrs
            config = configparser.ConfigParser()
            config["General"] = {
                "title": metadata["data-title"],
                "author": metadata["data-author"],
                "preview": metadata["data-preview"],
                "tease_id": metadata["data-tease-id"],
                "author_id": metadata["data-author-id"]
            }
            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return

            logging.debug(f"Downloading eosscript for {self.idTextBox.text()}.")
            self.downloadStatus.setText(lang.downloadingScript)
            eosscriptReq = requests.get(f"https://milovana.com/webteases/geteosscript.php?id={self.idTextBox.text()}")
            if eosscriptReq.status_code != HTTPStatus.OK:
                self.downloadStatus.setText(lang.downloadUnknownError)
                logging.error(f"Network error {eosscriptReq.status_code} occurred when downloading eosscript.json:")
                logging.error(f"{eosscriptReq.content=}")
                logging.error(f"{eosscriptReq.reason=}")
                return
            eosscript = eosscriptReq.json()
            with open(os.path.join(rootDir, "eosscript.json"), "w") as jFile:
                json.dump(eosscript, jFile)
            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            logging.debug(f"Finding media for {self.idTextBox.text()}.")
            toDownload: dict[str, set[str]] = {"image/jpeg": set()}
            if "galleries" in eosscript:
                toDownload["image/jpeg"].update({image["hash"] for gallery in eosscript["galleries"].values() for image in gallery["images"]})
            if "files" in eosscript:
                for file in eosscript["files"].values():
                    if file["type"] not in toDownload:
                        toDownload[file["type"]] = set()
                    toDownload[file["type"]].add(file["hash"])
            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            filePathMap = {
                "audio/mpeg": "timg/%s.mp3",
                "image/jpeg": "timg/tb_xl/%s.jpg"
            }
            with threadiprocessing.Pool(MEDIA_THREADS) as threadPool:
                for mimetype, fileHashes in toDownload.items():
                    if mimetype not in filePathMap:
                        logging.warning(f"Unrecognized mimetype {mimetype} for files {fileHashes}")
                        continue
                    urlTemplate = "https://media.milovana.com/" + filePathMap[mimetype]
                    fileTemplate = os.path.normpath(os.path.join(rootDir, filePathMap[mimetype]))
                    logging.debug(f"Downloading mimetype {mimetype} for {self.idTextBox.text()} using")
                    logging.debug(f"url template {urlTemplate} and file template {fileTemplate}.")
                    self.downloadStatus.setText(lang.downloadingMedia % mimetype)
                    res = threadPool.starmap_async(self.downloadMedia, map(lambda h: (fileTemplate % h, urlTemplate % h), fileHashes))
                    while not res.ready():
                        res.wait(1)
                        if self.downloadThread.stopped():
                            logging.debug("Download Thread Stopping!")
                            # Called automatically when using a context manager
                            # threadPool.terminate()
                            return

            self.downloadedTeases.append((rootDir, config))
            self.downloadStatus.setText(lang.downloadComplete)
        except (FileExistsError, FileNotFoundError) as e:
            self.downloadStatus.setText(lang.downloadWriteError)
            logging.error(f"An error occurred while creating a new tease directory {rootDir}:")
            logging.error(e)
        except requests.exceptions.JSONDecodeError as e:
            self.downloadStatus.setText(lang.downloadJsonError)
            logging.error(f"An error occurred when decoding eosscript.json.")
            logging.error(e)
        except Exception as e:
            self.downloadStatus.setText(lang.downloadUnknownError)
            raise
        finally:
            self.idTextBox.setEnabled(True)
            self.downloadButton.setEnabled(True)
            self.downloadThread = None

    def downloadMedia(self, file, url):
        req = requests.get(url)
        if req.status_code == HTTPStatus.FORBIDDEN:
            logging.warning(f"Received HTTP 403 Forbidden for file {url}")
        elif req.status_code != HTTPStatus.OK:
            logging.warning(f"Network error {req.status_code} occurred when downloading {url}:")
            logging.warning(f"{req.content=}")
            logging.warning(f"{req.reason=}")
        else:
            logging.debug(f"Writing file {file}")
            with open(os.path.normpath(file), "wb") as media:
                media.write(req.content)

def findFirstImage(eosscript) -> str | None:
    if isinstance(eosscript, list):
        for i in eosscript:
            if (res := findFirstImage(i)) is not None:
                return res
    elif isinstance(eosscript, dict):
        if "image" in eosscript:
            return eosscript["image"]["locator"]
        elif "media" in eosscript:
            return eosscript["media"]["nyx.image"]
        else:
            for i in eosscript.values():
                if (res := findFirstImage(i)) is not None:
                    return res
    return None
            
def unhideTimers(eosscript):
    if isinstance(eosscript, list):
        for i in eosscript:
            unhideTimers(i)
    elif isinstance(eosscript, dict):
        if "timer" in eosscript and "style" in eosscript["timer"]:
            del eosscript["timer"]["style"]
        for i in eosscript.values():
            unhideTimers(i)

def copyAll(src, dest, *files) -> list[str]:
    failedFiles = []
    for file in files:
        try:
            if os.path.isdir(os.path.join(src, file)):
                shutil.copytree(os.path.join(src, file), os.path.join(dest, file))
            else:
                shutil.copyfile(os.path.join(src, file), os.path.join(dest, file))
        except Exception as e:
            logging.error(e)
            failedFiles.append(file)
    return failedFiles

def getNewRootDir():
    return os.path.join(TEASES_DIR, str(uuid.uuid4()))


import datetime
import email.utils
import urllib.parse

from http.server import HTTPServer, SimpleHTTPRequestHandler

class MiloHTTPRequestHandler(SimpleHTTPRequestHandler):
    server_version = "MiloHTTP/0.6"
    # Copied from http.server.SimpleHTTPRequestHandler
    index_pages = ("index.html", "index.htm")

    def __init__(self, *args, directory=None, commonDir=None, commonFilesMap={None: ()}, **kwargs):
        self.commonDir = commonDir
        # Needed because http.server makes a new handler every time a file is fetched
        if commonDir not in commonFilesMap:
            logging.debug(f"Initializing common files for {commonDir}")
            commonFilesMap[commonDir] = tuple(os.listdir(commonDir))
            logging.debug(commonFilesMap)
        else:
            logging.debug(f"Skipping init of common files for {commonDir}")
        self.commonFiles = commonFilesMap[commonDir]
        super().__init__(*args, **kwargs, directory=directory)

    # Serves most files from commonfiles to deduplicate data
    # and fix the font issue.
    def translate_path(self, path):
        path = super().translate_path(path)
        logging.debug(f"{self.directory=}")
        logging.debug(f"{path=}")

        # Skip the prefix directory (self.directory).
        if path.startswith(self.directory):
            i = len(self.directory)
        else:
            return path
        # This should always skip a separator. If it doesn't,
        # the prefix is the full path. (See below on Apache)
        if i < len(path) and path[i] == os.path.sep:
            i += 1
        else:
            return path
        
        # Some fonts call an absolute path (/static/media/[...])
        # instead of a relative path (../../[...]).
        if path.startswith((os.path.join("static", "media", "fontsans"),
                            os.path.join("static", "media", "fontserif"),
                            os.path.join("static", "media", "noto-sans-latin")), i):
            logging.debug(f"Font workaround: Returning {os.path.join(self.commonDir, path[i:])}")
            return os.path.join(self.commonDir, path[i:])
        
        # Skip a UUID or fail
        try:
            # If accessing the base dir of the tease, it'll be a
            # forward slash even on windows (blame Apache lmao)
            nextSep = path.find(os.path.sep, i)
            if -1 < (pf := path.find("/", i)) < nextSep or nextSep == -1:
                nextSep = pf
            if nextSep == -1:
                raise ValueError
            uuid.UUID(path[i:nextSep])
            # Skip the last slash too.
            i = nextSep + 1
        except ValueError:
            return path
        
        if i == len(path):
            # Normally we would serve "index.html" by default if the
            # path was the folder, but it was moved to commonfiles.
            logging.debug(f"Returning index.html for {path}")
            return os.path.sep.join([self.commonDir, "index.html"])
        if path.startswith(self.commonFiles, i):
            path = os.path.sep.join([self.commonDir, path[i:]])
            logging.debug(f"New path is {path}")
        return path
    
    # Mostly copied from http.server.SimpleHTTPRequestHandler
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            for index in self.index_pages:
                index = os.path.join(path, index)
                if os.path.isfile(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        # check for trailing "/" which should return 404. See Issue17324
        # The test for this was added in test_httpserver.py
        # However, some OS platforms accept a trailingSlash as a filename
        # See discussion on python-dev and Issue34711 regarding
        # parsing and rejection of filenames with a trailing slash
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            # Here's the extra part that wasn't in the original
            if path.endswith(f"{os.path.sep}eosscript.json"):
                global appWindow
                if (teaseKey := path.removesuffix(f"{os.path.sep}eosscript.json")) in appWindow.teases:
                    logging.debug(f"Serving in-memory eosscript for {path}")
                    eosscript = json.dumps(appWindow.teases[teaseKey].eosscript).encode()
                    f = io.BytesIO(eosscript)

                    # Copied from below
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-type", ctype)
                    self.send_header("Content-Length", len(eosscript))
                    # Make sure this copy is never cached.
                    self.send_header("Last-Modified",
                        self.date_time_string(int(datetime.datetime.utcnow().timestamp())))
                    self.end_headers()
                    return f
                else:
                    logging.debug(f"{teaseKey} was not in {appWindow.teases=} or has no eosscript.")
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers
                    and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"])
                except (TypeError, IndexError, OverflowError, ValueError):
                    # ignore ill-formed values
                    pass
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc)
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified",
                self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

def startHttpServer():
    httpd = HTTPServer((appWindow.config["General"]["ip"], int(appWindow.config["General"]["port"])), 
                    functools.partial(MiloHTTPRequestHandler, directory=TEASES_DIR, commonDir=COMMON_DIR))
    threading.Thread(target = httpd.serve_forever).start()
    logging.info(f"Serving files on http://{appWindow.config['General']['ip']}:{appWindow.config['General']['port']}")
    return httpd

def stopHttpServer(httpd):
    httpd.shutdown()
    # Frees the socket
    httpd.server_close()

def restartHttpServer(httpd):
    stopHttpServer(httpd)
    return startHttpServer()


class StoppableThread(threading.Thread):
    # Copied from https://stackoverflow.com/questions/24843193/stopping-a-python-thread-running-an-infinite-loop
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.is_set()


import functools

logging.getLogger().setLevel("DEBUG")

app = QtWidgets.QApplication([])
appWindow = AppWindow()

httpd = startHttpServer()
appWindow.show()
app.exec()

logging.debug("Shutting down HTTP Server")
stopHttpServer(httpd)
logging.debug("Successfully shut down HTTP Server")
