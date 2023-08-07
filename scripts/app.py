from __future__ import annotations

import configparser
import functools
import json
import logging
import multiprocessing.dummy as threadiprocessing
import os
import platform
import pyperclip
import requests
import shutil
import subprocess
import threading
import urllib.parse
import uuid
import webbrowser

from bs4 import BeautifulSoup
from http import HTTPStatus
from http.server import HTTPServer
from PyQt6 import QtCore, QtGui, QtWidgets

import english as lang

from cards import *
from constants import *
from eosHttpServer import MiloHTTPRequestHandler
from stoppableThread import StoppableThread
            
def copyAll(src, dest, *files) -> list[str]:
    failedFiles = list()
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

def getNewRootDir() -> os.PathLike:
    return os.path.join(TEASES_DIR, str(uuid.uuid4()))

def startHttpServer(appWindow) -> HTTPServer:
    httpd = HTTPServer((appWindow.config["General"]["ip"], int(appWindow.config["General"]["port"])), 
                       functools.partial(MiloHTTPRequestHandler, directory=TEASES_DIR, commonDir=COMMON_DIR, appWindow=appWindow))
    threading.Thread(target = httpd.serve_forever).start()
    logging.info(f"Serving files on http://{appWindow.config['General']['ip']}:{appWindow.config['General']['port']}")
    return httpd

def stopHttpServer(httpd: HTTPServer):
    httpd.shutdown()
    # Frees the socket
    httpd.server_close()

class AppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(lang.windowTitle % VERSION)
        self.setMinimumSize(QtCore.QSize(4, 3) * WINDOW_SIZE)
        self.resize(QtCore.QSize(8, 5) * WINDOW_SIZE)
        self.teases: dict[str, TeaseCard] = dict()
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
        searchIcon = QtGui.QIcon.fromTheme("system-search-symbolic", QtGui.QIcon(SEARCH_ICON_PATH))
        searchImage = QtWidgets.QLabel(self)
        searchImage.setPixmap(searchIcon.pixmap(QtCore.QSize(16, 16)))
        searchSubLayout.addWidget(searchImage)

        searchBox = QtWidgets.QLineEdit(self)
        searchBox.textChanged.connect(self.filterTeases)
        searchSubLayout.addWidget(searchBox)

        cardsSubLayout.addLayout(searchSubLayout)

        self.teaseListSubLayout = QtWidgets.QVBoxLayout()

        for teaseTup in self.loadTeases(TEASES_DIR):
            self.addTeaseToList(*teaseTup)

        # Need to specify a stretch factor or else it'll try to "share" 
        # with all the other widgets' default stretch factors of 0.
        self.teaseListSubLayout.addStretch(1)

        teaseListWidget = QtWidgets.QWidget(self)
        teaseListWidget.setLayout(self.teaseListSubLayout)

        teaseScroll = QtWidgets.QScrollArea(self)
        teaseScroll.setWidget(teaseListWidget)
        teaseScroll.setWidgetResizable(True)  # Default is False
        cardsSubLayout.addWidget(teaseScroll)

        layout.addLayout(cardsSubLayout)

        buttonsSubLayout = QtWidgets.QVBoxLayout()

        globalSettingsButton = QtWidgets.QPushButton(lang.globalSettings, self)
        globalSettingsButton.pressed.connect(self.showGlobalSettingsPopup)
        buttonsSubLayout.addWidget(globalSettingsButton)

        settingsButton = QtWidgets.QPushButton(lang.teaseSettings, self)
        settingsButton.pressed.connect(self.showTeaseSettingsPopup)
        buttonsSubLayout.addWidget(settingsButton)

        openTeaseButton = QtWidgets.QPushButton(lang.openTease, self)
        openTeaseButton.pressed.connect(self.openTeaseInBrowser)
        buttonsSubLayout.addWidget(openTeaseButton)

        copyTeaseUrlButton = QtWidgets.QPushButton(lang.copyTeaseUrl, self)
        copyTeaseUrlButton.pressed.connect(self.copyTeaseUrl)
        buttonsSubLayout.addWidget(copyTeaseUrlButton)

        openTeaseFolderButton = QtWidgets.QPushButton(lang.openTeaseFolder, self)
        openTeaseFolderButton.pressed.connect(self.openTeaseFolder)
        buttonsSubLayout.addWidget(openTeaseFolderButton)

        buttonsSubLayout.addStretch()

        importEOSTeaseButton = QtWidgets.QPushButton(lang.importTease, self)
        importEOSTeaseButton.pressed.connect(self.importEOSTease)
        buttonsSubLayout.addWidget(importEOSTeaseButton)

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

    def addTeaseToList(self, rootDir, tease: TeaseCard):
        self.teases[rootDir] = tease
        # Place the card before the stretch.
        self.teaseListSubLayout.insertWidget(len(self.teaseListSubLayout) - 1, tease)

    def removeTeaseFromList(self, tease: TeaseCard):
        del self.teases[tease.rootDir]
        self.teaseListSubLayout.removeWidget(tease)
        tease.close()
    
    def setSelectedTease(self, tease: TeaseCard):
        if self.selectedTease is not None:
            self.selectedTease.setAutoFillBackground(False)
        self.selectedTease = tease
        self.selectedTease.setAutoFillBackground(True)
        logging.debug(f"Set selected tease to {tease} with rootDir {tease.rootDir}")
    
    def filterTeases(self, text: str):
        for tease in self.teases.values():
            tease.setVisible(text.lower() in tease.config["General"]["title"].lower() or \
                             text.lower() in tease.config["General"]["author"].lower())

    def showGlobalSettingsPopup(self):
        self.globalSettingsPopup.refreshSettings()
        self.globalSettingsPopup.show()
    
    def showTeaseSettingsPopup(self):
        if self.selectedTease is not None:
            self.selectedTease.settingsPopup.refreshSettings()
            self.selectedTease.settingsPopup.show()
    
    def openTeaseInBrowser(self):
        if self.selectedTease is not None:
            webbrowser.open_new_tab(self.getTeaseUrl())
    
    def copyTeaseUrl(self):
        if self.selectedTease is not None:
            pyperclip.copy(self.getTeaseUrl())
    
    def getTeaseUrl(self):
        # Sorry not sorry
        return f"http://{self.config['General']['ip']}:{self.config['General']['port']}/{self.selectedTease.rootDir.removeprefix(TEASES_DIR).replace(os.path.sep, '/').lstrip('/')}"

    def openTeaseFolder(self):
        fileManagerMap = {
            "Windows": "explorer.exe",
            "Darwin": "open",
            "Linux": "xdg-open"
        }
        if self.selectedTease is not None:
            subprocess.Popen([fileManagerMap[platform.system()], self.selectedTease.rootDir])
    
    def importEOSTease(self):
        rootDir = QtWidgets.QFileDialog.getExistingDirectory(self, lang.fileSelectTease)
        if rootDir == "":
            logging.debug("Canceled when importing tease from EOS at file picker.")
            return
        newRootDir = getNewRootDir()
        logging.info(f"Importing Tease from {rootDir} to {newRootDir}")
        os.mkdir(newRootDir)
        copyAll(rootDir, newRootDir, "tease", "timg", "config.ini", "eosscript.json")
        teaseCard = EosTeaseCard(self, newRootDir)
        if (teaseId := os.path.basename(rootDir)).isdigit():
            teaseCard.config["General"]["tease_id"] = teaseId
        logging.debug(teaseId)
        teaseCard.saveSettings()
        self.addTeaseToList(newRootDir, teaseCard)
    
    def showDownloadPopup(self):
        self.downloadTeasePopup.refreshSettings()
        self.downloadTeasePopup.show()

    def deleteTease(self):
        if self.selectedTease is not None:
            logging.debug(f"Deleting {self.selectedTease.rootDir}")
            shutil.rmtree(self.selectedTease.rootDir)
            self.removeTeaseFromList(self.selectedTease)
            self.selectedTease = None
    
    def loadTeases(self, searchDir) -> list(tuple):
        if not os.path.exists(searchDir):
            os.makedirs(searchDir)
            return []
        
        teases = list()
        for folder in os.listdir(searchDir):
            rootDir = os.path.join(searchDir, folder)
            if not os.path.isdir(rootDir):
                continue
            if "config.ini" not in (ld := os.listdir(rootDir)):
                continue
            try:
                if "eosscript.json" in ld:
                    teases.append((rootDir, EosTeaseCard(self, rootDir)))
                else:
                    teases.append((rootDir, RegularTeaseCard(self, rootDir)))
            except Exception as e:
                logging.error(e)
        return teases
    
    def saveSettings(self):
        with open("config.ini", "w") as inifile:
            self.config.write(inifile)
        self.refreshIcon()
        global httpd
        if (self.config["General"]["ip"], int(self.config["General"]["port"])) != httpd.server_address:
            logging.debug("Restarting HTTP Server")
            stopHttpServer(httpd)
            httpd = startHttpServer(self)
    
    def refreshIcon(self):
        self.setWindowIcon(QtGui.QIcon(self.config["General"]["icon_path"]))

class GlobalSettingsPopup(QtWidgets.QDialog):
    def __init__(self, creator: AppWindow):
        super().__init__(creator)
        self.setWindowTitle(f"{lang.windowTitle % VERSION}: {lang.globalSettings}")
        self.setMinimumWidth(4 * WINDOW_SIZE)
        self.setModal(True)
        self.creator = creator
        self.iconPath = None

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

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
        self.toAdd: list[TeaseCard] = list()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        idTextBoxSubLayout = QtWidgets.QHBoxLayout()
        
        idTextBoxHint = QtWidgets.QLabel(self)
        idTextBoxHint.setText(lang.teaseIdTextBoxHint)
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
    
    def refreshSettings(self):
        self.idTextBox.setText("")
        self.downloadStatus.setText(lang.downloadInfo)
    
    def beginDownload(self):
        # TODO make the download button into a progress bar?
        if self.downloadThread is None:
            self.idTextBox.setEnabled(False)
            self.downloadButton.setEnabled(False)
            self.downloadThread = StoppableThread(target=self.downloadTease)
            self.downloadThread.start()
    
    def closeEvent(self, event):
        if self.downloadThread is not None:
            self.downloadThread.stop()
        for rootDir in self.toAdd:
            # Copied from AppWindow.loadTeases()
            if "config.ini" not in (ld := os.listdir(rootDir)):
                continue
            try:
                if "eosscript.json" in ld:
                    self.creator.addTeaseToList(rootDir, EosTeaseCard(self.creator, rootDir))
                else:
                    self.creator.addTeaseToList(rootDir, RegularTeaseCard(self.creator, rootDir))
            except Exception as e:
                logging.error(e)
        return super().closeEvent(event)
    
    def downloadTease(self):
        try:
            rootDir = getNewRootDir()
            logging.debug(f"Creating folder {rootDir} for downloading tease id {self.idTextBox.text()}.")
            os.makedirs(os.path.join(rootDir, "timg", "tb_xl"))

            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            logging.debug(f"Downloading metadata for {self.idTextBox.text()}.")
            self.downloadStatus.setText(lang.downloadingMeta)
            metaReq = requests.get(f"https://milovana.com/webteases/showtease.php?id={self.idTextBox.text()}")
            if metaReq.status_code != HTTPStatus.OK:
                self.downloadStatus.setText(lang.downloadUnknownError)
                logging.error(f"Error downloading metadata: {metaReq.status_code=}, {metaReq.reason=}")
                return
            
            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            metaHtmlTree = BeautifulSoup(metaReq.content.decode(), "html.parser")

            # Can't use status codes since the site always seems to return 200 if it's not down.
            if (titleElem := metaHtmlTree.find("head").find("title").string) is not None:
                if titleElem == "Milovana.com - This tease is invisible.":
                    self.downloadStatus.setText(lang.downloadInvisibleTease)
                    logging.error(f"Tease ID {self.idTextBox.text()} is invisible.")
                    return
                elif titleElem == "Milovana.com - Tease not found.":
                    self.downloadStatus.setText(lang.downloadInvalidId)
                    logging.error(f"Tease ID {self.idTextBox.text()} is invalid.")
                    return

            if (eosTopBody := metaHtmlTree.find("body", {"class": "eosTopBody"})) is not None:
                if self.idTextBox.text() != eosTopBody.attrs["data-tease-id"]:
                    raise ValueError("Metadata ID does not match entered ID")
                medias = self.downloadEosTease(rootDir, self.idTextBox.text(), eosTopBody.attrs)
            else:
                if self.idTextBox.text() not in metaHtmlTree.find("head").find("title").contents[0]:
                    raise ValueError("Metadata ID does not match entered ID")
                medias = self.downloadRegularTease(rootDir, self.idTextBox.text(), metaHtmlTree)

            self.downloadStatus.setText(lang.downloadingMedia)
            with threadiprocessing.Pool(MEDIA_THREADS) as threadPool:
                res = threadPool.starmap_async(self.downloadMedia, medias)
                while not res.ready():
                    res.wait(1)
                    if self.downloadThread.stopped():
                        logging.debug("Download Thread Stopping!")
                        return
                    
            self.toAdd.append(rootDir)
            self.downloadStatus.setText(lang.downloadComplete)
        except (OSError, IOError):
            self.downloadStatus.setText(lang.downloadWriteError)
            raise
        except Exception:
            self.downloadStatus.setText(lang.downloadUnknownError)
            raise
        finally:
            self.idTextBox.setEnabled(True)
            self.downloadButton.setEnabled(True)
            self.downloadThread = None

    def downloadMedia(self, file, url):
        mediaReq = requests.get(url)
        if mediaReq.status_code == HTTPStatus.FORBIDDEN:
            logging.warning(f"Received HTTP 403 Forbidden for file {url}")
        elif mediaReq.status_code != HTTPStatus.OK:
            logging.warning(f"Error downloading media: {mediaReq.status_code=}, {mediaReq.reason=}")
        else:
            logging.debug(f"Writing file {file}")
            try:
                with open(os.path.normpath(file), "wb") as media:
                    media.write(mediaReq.content)
            except (OSError, IOError) as e:
                logging.warning(f"Error writing file {file}: {e}")
    
    def downloadRegularTease(self, rootDir, teaseId, fpHtmlTree):
        metaElem = fpHtmlTree.find("h1", {"id": "tease_title"})
        title = metaElem.contents[0].strip()
        author = metaElem.find("a").contents[0].strip()
        config = configparser.ConfigParser()
        config["General"] = {
            "title": title,
            "author": author,
            "tease_id": teaseId
        }

        with open(os.path.join(rootDir, "config.ini"), "w") as f:
            RegularTeaseCard.saveConfig(config, f)

        if self.downloadThread.stopped():
            logging.debug("Download Thread Stopping!")
            return
        
        nextLinks, medias = self.saveHtml(rootDir, teaseId, fpHtmlTree, os.path.join(rootDir, "index.html"))
        
        self.downloadStatus.setText(lang.downloadingHtml)
        seenLinks = set()
        while nextLinks:
            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            nextLink = nextLinks.pop()
            if nextLink in seenLinks:
                logging.debug(f"Skipping {nextLink} because it was already downloaded.")
                continue
            else:
                seenLinks.add(nextLink)

            logging.debug(f"Downloading {nextLink}")
            pageReq = requests.get(nextLink[1])
            if pageReq.status_code != HTTPStatus.OK:
                logging.warning(f"Error downloading html: {pageReq.status_code=}, {pageReq.reason=}")
                continue

            pageHtmlTree = BeautifulSoup(pageReq.content.decode(), "html.parser")
            try:
                nextLinks_, medias_ = self.saveHtml(rootDir, teaseId, pageHtmlTree, nextLink[0])
                nextLinks.update(nextLinks_)
                medias.update(medias_)
            except (OSError, IOError) as e:
                logging.warning(f"Error writing file {os.path.join(rootDir, nextLink[0])}: {e}")

        return medias
    
    def saveHtml(self, rootDir, teaseId, htmlTree: BeautifulSoup, meFile):
        def getPageFilename(page):
            return f"{'page'+page if page else 'index'}.html"
        
        def stripRemoteComponent(url):
            return urllib.parse.urlunparse(url._replace(netloc="", scheme=""))
        
        while (newRoot := htmlTree.find("html", recursive=False)) is not None:
            htmlTree = newRoot

        # local filepath, remote url
        nextLinks: set[tuple[str, str]] = set()
        medias: set[tuple[str, str]] = set()
        
        if (htmlHead := htmlTree.find("head", recursive=False)) is not None:
            if (cur := htmlHead.find("base", href=True, recursive=False)) is not None:
                cur.decompose()
            else:
                logging.debug("Couldn't find <base> tag")
            
            if (cur := htmlHead.find("script", {"type": "text/javascript"}, src=True, recursive=False)) is not None and \
                  cur["src"].endswith("jquery.min.js"):
                cur["src"] = "script/jquery.min.js"
            else:
                logging.debug("Couldn't find jquery")
        else:
            logging.warning("Could not find html <head>!")

        if (htmlBody := htmlTree.find("body", recursive=False)) is not None:
            for cur in htmlBody.find_all("script", recursive=False):
                if "googletagmanager.com/gtag/js" in cur.get("src", "") or \
                      cur.string is not None and "function gtag()" in cur.string:
                    cur.decompose()
                
            if (cur := htmlBody.find("div", {"id": "tease_content"})) is not None and \
                  (cur := cur.find("script", {"type": "text/javascript"})) is not None:
                search_begin = "var link='"
                search_end = "';"

                slice_begin = cur.string.find(search_begin) + len(search_begin)
                slice_end = cur.string.find(search_end, slice_begin)

                url = urllib.parse.urlparse(cur.string[slice_begin:slice_end])
                qs = urllib.parse.parse_qs(url.query)
                if url.hostname.endswith("milovana.com") and url.path == "/webteases/showtease.php":
                    if qs.get("id") and qs.get("id")[0] == teaseId and qs.get("p"):
                        if (page := qs.get("p")[0]).isdigit():
                            filename = getPageFilename(page)
                            cur.string = cur.string[:slice_begin] + filename + "#t" + cur.string[slice_end:]
                            nextLinks.add((
                                os.path.join(rootDir, filename),
                                f"https://milovana.com/webteases/showtease.php?id={teaseId}&p={page}#t"
                            ))
                        else:
                            logging.warning(f"Found non-numeric page {page} for url {url}")
                    else:
                        logging.debug(f"{url} didn't contain an id or p tag in spacebar script")
                else:
                    logging.debug(f"{url} didn't match hostname or path in spacebar script")
            else:
                logging.debug(f"Couldn't find spacebar script")
        else:
            logging.debug("Could not find html <body>!")

        for link in htmlTree.find_all(("a", "link"), href=True):
            url = urllib.parse.urlparse(link["href"])
            qs = urllib.parse.parse_qs(url.query)
            if not (url.hostname is None or url.hostname.endswith("milovana.com")):
                logging.debug(f"No hostname match for url {url} with hostname {url.hostname}")
                continue

            if url.path == "/webteases/showtease.php":
                if qs.get("id") and qs.get("id")[0] == teaseId and qs.get("p"):
                    if (page := qs.get("p")[0]).isdigit():
                        filename = getPageFilename(page)
                        link["href"] = filename + "#t"
                        nextLinks.add((
                            os.path.join(rootDir, filename),
                            f"https://milovana.com/webteases/showtease.php?id={teaseId}&p={page}#t"
                        ))
                    else:
                        logging.debug(f"Non-numeric page: {page}")
                else:
                    logging.debug(f"No id match for {url}")
            elif url.path.startswith(("/style/", "/gx/")):
                link["href"] = stripRemoteComponent(url._replace(path=url.path[1:]))
            elif url.path == "favicon.ico":
                link["href"] = stripRemoteComponent(url)
            elif url.path not in ("/id/", "webteases/", "urge/", "forum/", "chat/", "", 
                                  "pages/impressum.php", "pages/contact.php", "pages/about.php",
                                  "pages/privacy.php", "pages/tos.php", "pages/whyfree.php"):
                logging.warning(f"Uncaptured url: {url}")

        for link in htmlTree.find_all("img", src=True):
            url = urllib.parse.urlparse(link["src"])
            if not (url.hostname is None or url.hostname.endswith("milovana.com")):
                logging.debug(f"No hostname match for img {url} with hostname {url.hostname}")
                continue

            if url.path.startswith("/timg/"):
                img, ext = os.path.splitext(url.path[url.path.rfind("/")+1:])
                ext = ext[1:]
                if img.isalnum() and ext.isalnum():
                    filename = f"timg/tb_xl/{img}.{ext}"
                    link["src"] = filename
                    medias.add((
                        os.path.join(rootDir, filename),
                        f"https://media.milovana.com/{filename}"
                    ))
                else:
                    logging.debug(f"Image isn't valid hash or ext: {img=}, {ext=}")
            elif url.path.startswith("/gx/"):
                link["src"] = stripRemoteComponent(url._replace(path=url.path[1:]))
            else:
                logging.debug(f"Uncaptured img: {url}")
        
        with open(meFile, "w") as p:
            p.write(str(htmlTree))
        
        return (nextLinks, medias)

    def downloadEosTease(self, rootDir, teaseId, metadata):
        try:
            config = configparser.ConfigParser()
            config["General"] = {
                "title": metadata["data-title"],
                "author": metadata["data-author"],
                "preview": metadata["data-preview"],
                "tease_id": metadata["data-tease-id"],
                "author_id": metadata["data-author-id"]
            }

            with open(os.path.join(rootDir, "config.ini"), "w") as f:
                EosTeaseCard.saveConfig(config, f)

            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            logging.debug(f"Downloading eosscript for {teaseId}.")
            self.downloadStatus.setText(lang.downloadingScript)
            eosscriptReq = requests.get(f"https://milovana.com/webteases/geteosscript.php?id={teaseId}")
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
            
            logging.debug(f"Finding media for {teaseId}.")
            mime2PathMap = {
                "audio/mpeg": "timg/%s.mp3",
                "image/jpeg": "timg/tb_xl/%s.jpg"
            }
            medias: set[tuple[str, str]] = set()
            if "galleries" in eosscript:
                medias.update({
                    (os.path.join(rootDir, (file := mime2PathMap["image/jpeg"] % image["hash"])),
                     f"https://media.milovana.com/{file}")
                    for gallery in eosscript["galleries"].values()
                    for image in gallery["images"]
                })
            if "files" in eosscript:
                for f in eosscript["files"].values():
                    medias.add((os.path.join(rootDir, (file := mime2PathMap[f["type"]] % f["hash"])),
                                f"https://media.milovana.com/{file}"))
                    
            if self.downloadThread.stopped():
                logging.debug("Download Thread Stopping!")
                return
            
            return medias
        except requests.exceptions.JSONDecodeError:
            self.downloadStatus.setText(lang.downloadJsonError)
            logging.error(f"An error occurred when decoding eosscript.json.")
            raise


if __name__ == "__main__":
    logging.getLogger().setLevel("DEBUG")

    app = QtWidgets.QApplication([])
    appWindow = AppWindow()

    httpd = startHttpServer(appWindow)
    appWindow.show()
    app.exec()

    logging.debug("Shutting down HTTP Server")
    stopHttpServer(httpd)
    logging.debug("Successfully shut down HTTP Server")
