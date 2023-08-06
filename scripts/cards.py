from __future__ import annotations

import configparser
import json
import logging
import os

from bs4 import BeautifulSoup
from io import StringIO
from PyQt6 import QtGui, QtWidgets

import english as lang

from app import AppWindow  # Just for type hinting
from constants import *

class TeaseCard(QtWidgets.QWidget):
    # creator: The object that created the widget. Its antithesis is self.windows.
    def __init__(self, creator: AppWindow, rootDir, defaultTeaseId, configOverride, SettingsPopupType: TeaseSettingsPopup):
        logging.debug(f"Creating tease card for {rootDir}.")
        super().__init__(creator)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), palette.color(QtGui.QPalette.ColorRole.Highlight))
        self.setPalette(palette)
        # self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        # https://stackoverflow.com/questions/44094293/pyqt-widget-seems-to-forget-its-parent
        self.creator = creator
        self.rootDir = rootDir
        self.config = self.loadConfig() if configOverride is None else configOverride
        if "tease_id" not in self.config["General"]:
            self.config["General"]["tease_id"] = defaultTeaseId

        self.settingsPopup = SettingsPopupType(self)
        
        layout = QtWidgets.QHBoxLayout()
        
        self.image = QtWidgets.QLabel(self)
        layout.addWidget(self.image)

        metaSubLayout = QtWidgets.QVBoxLayout()
        # metaSubLayoutDefaultMargins = metaSubLayout.getContentsMargins()
        # metaSubLayout.setContentsMargins(12, metaSubLayoutDefaultMargins[1], 24, metaSubLayoutDefaultMargins[3])

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
    
    def loadThumbnail(self, defaultThumb):
        thumbnail = thumb if (thumb := self.getThumbnail()) is not None else QtGui.QPixmap(defaultThumb)
        dim = min(thumbnail.width(), thumbnail.height())
        thumbnail = thumbnail.copy(
            (thumbnail.width() - dim) // 2,  # top left x
            (thumbnail.height() - dim) // 2,  # top left y
            dim, dim)  # width, height
        self.image.setPixmap(thumbnail.scaledToHeight(80))

    def refreshMetadata(self):
        self.titleMeta.setText(self.config["General"]["title"])
        self.authorMeta.setText(self.config["General"]["author"])
        self.teaseIdMeta.setText(f"ID: {self.config['General']['tease_id']}")
    
    def saveConfig(self):
        with StringIO() as iniHack:
            self.config.write(iniHack, False)
            configStr = iniHack.getvalue()
        configStr = configStr.replace("[General]\n", "")
        with open(os.path.join(self.rootDir, "config.ini"), "w") as iniFile:
            iniFile.write(configStr)
    
    def loadConfig(self):
        config = configparser.ConfigParser()
        # Hack because eos.outer.js can't handle sectioned files
        configStr = "[General]\n"
        with open(os.path.join(self.rootDir, "config.ini")) as iniFile:
            configStr += iniFile.read()
        config.read_string(configStr)
        return config
    
    def mousePressEvent(self, event):
        self.creator.setSelectedTease(self)
        return super().mousePressEvent(event)
    
    def showSettingsPopup(self):
        self.settingsPopup.refreshSettings()
        self.settingsPopup.show()
    
    def saveSettings(self):
        raise NotImplementedError
    
    def getThumbnail(self):
        raise NotImplementedError

class TeaseSettingsPopup(QtWidgets.QDialog):
    def __init__(self, creator: TeaseCard, layout: QtWidgets.QGridLayout):
        super().__init__(creator)
        self.setWindowTitle(f"{lang.teaseSettings}: {creator.config['General']['title']}")
        self.setMinimumWidth(4 * WINDOW_SIZE)
        self.setModal(True)
        self.creator = creator

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

        teaseIdTextBoxHint = QtWidgets.QLabel(self)
        teaseIdTextBoxHint.setText(lang.teaseIdTextBoxHint)
        layout.addWidget(teaseIdTextBoxHint, 2, 0)

        self.teaseIdTextBox = QtWidgets.QLineEdit(self)
        layout.addWidget(self.teaseIdTextBox, 2, 1)
    
    def refreshSettings(self):
        self.titleTextBox.setText(self.creator.config["General"]["title"])
        self.authorTextBox.setText(self.creator.config["General"]["author"])
        self.teaseIdTextBox.setText(self.creator.config["General"]["tease_id"])
        self._refreshSettings()
    
    def saveSettings(self):
        self.creator.config["General"]["title"] = self.titleTextBox.text()
        self.creator.config["General"]["author"] = self.authorTextBox.text()
        self.creator.config["General"]["tease_id"] = self.teaseIdTextBox.text()
        self._saveSettings()
        self.creator.saveSettings()
        self.hide()

    def _refreshSettings(self):
        raise NotImplementedError

    def _saveSettings(self):
        raise NotImplementedError

class EosTeaseCard(TeaseCard):
    def __init__(self, creator, rootDir, defaultTeaseId = "unset", defaultThumb = DEFAULT_THUMB, configOverride=None):
        super().__init__(creator, rootDir, defaultTeaseId, configOverride, EosTeaseSettingsPopup)
        if "unhide_timers" not in self.config["General"]:
            self.config["General"]["unhide_timers"] = "false"

        self.eosscript = self.loadEosscript()
        self.loadThumbnail(defaultThumb)
    
    def saveSettings(self):
        self.saveConfig()
        self.eosscript = self.loadEosscript()
        logging.debug(f"Reloaded eosscript for {self.rootDir} with {self.config['General']['unhide_timers']=}")
        self.refreshMetadata()
    
    def loadEosscript(self):
        with open(os.path.join(self.rootDir, "eosscript.json")) as jFile:
            eosscript = json.load(jFile)
        if self.config["General"]["unhide_timers"] == "true":
            self.unhideTimers(eosscript)
        return eosscript
    
    def getThumbnail(self):
        imgHash = None
        if (imgLocator := self.findFirstImage()) is not None:
            # Really wish we had streams right now
            if imgLocator.startswith("gallery:"):
                galId, imgId = imgLocator[len("gallery:"):].split("/", 1)
                for i in self.eosscript["galleries"][galId]["images"]:
                    # Using str() instead of int() to help prevent errors
                    if str(i["id"]) == imgId or imgId == "*":
                        imgHash = i["hash"]
                        break
                else:
                    logging.warning(f"Could not find thumbnail in eosscript galleries for {self.rootDir}")
            elif imgLocator.startswith("file:"):
                imgHash = self.eosscript["files"][imgLocator[len("file:"):]]["hash"]
        else:
            logging.warning(f"Could not find thumbnail in eosscript for {self.rootDir}")

        thumbnail = None
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
    
    def findFirstImage(self, eosFrag=None) -> str | None:
        if eosFrag is None:
            return self.findFirstImage(self.eosscript["pages"]["start"])
        
        if isinstance(eosFrag, list):
            for f in eosFrag:
                if (res := self.findFirstImage(f)) is not None:
                    return res
        elif isinstance(eosFrag, dict):
            if "image" in eosFrag:
                return eosFrag["image"]["locator"]
            elif "media" in eosFrag:
                return eosFrag["media"]["nyx.image"]
            else:
                for f in eosFrag.values():
                    if (res := self.findFirstImage(f)) is not None:
                        return res
        return None
    
    def unhideTimers(self, eosFrag):
        if isinstance(eosFrag, list):
            for f in eosFrag:
                self.unhideTimers(f)
        elif isinstance(eosFrag, dict):
            if "timer" in eosFrag and "style" in eosFrag["timer"]:
                del eosFrag["timer"]["style"]
            if "nyx.timer" in eosFrag and "style" in eosFrag["nyx.timer"]:
                del eosFrag["nyx.timer"]["style"]
            for f in eosFrag.values():
                self.unhideTimers(f)

class EosTeaseSettingsPopup(TeaseSettingsPopup):
    def __init__(self, creator: EosTeaseCard):
        layout = QtWidgets.QGridLayout()
        super().__init__(creator, layout)

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
    
    def _refreshSettings(self):
        self.unhideTimersButton.setChecked(self.creator.config["General"]["unhide_timers"] == "true")
        self.debugModeButton.setChecked(self.creator.config["General"]["preview"] == "true")
    
    def _saveSettings(self):
        self.creator.config["General"]["unhide_timers"] = str(self.unhideTimersButton.isChecked()).lower()
        self.creator.config["General"]["preview"] = str(self.debugModeButton.isChecked()).lower()

class RegularTeaseCard(TeaseCard):
    def __init__(self, creator, rootDir, defaultTeaseId = "unset", defaultThumb = DEFAULT_THUMB, configOverride=None):
        super().__init__(creator, rootDir, defaultTeaseId, configOverride, RegularTeaseSettingsPopup)
        self.loadThumbnail(defaultThumb)
    
    def saveSettings(self):
        self.saveConfig()
        self.refreshMetadata()
    
    def getThumbnail(self):
        with open(os.path.join(self.rootDir, "index.html")) as f:
            htmlTree = BeautifulSoup(f)
        for link in htmlTree.find_all("img", src=True):
            if "timg/tb_xl" in link["src"]:
                logging.debug(os.path.join(self.rootDir, link["src"]))
                return QtGui.QPixmap(os.path.join(self.rootDir, link["src"]))
        return None

class RegularTeaseSettingsPopup(TeaseSettingsPopup):
    def __init__(self, creator: EosTeaseCard):
        layout = QtWidgets.QGridLayout()
        super().__init__(creator, layout)
        
        saveButton = QtWidgets.QPushButton(self)
        saveButton.setText(lang.saveSettings)
        saveButton.clicked.connect(self.saveSettings)
        layout.addWidget(saveButton, 3, 0, 1, 2)

        self.setLayout(layout)
    
    def _refreshSettings(self):
        pass

    def _saveSettings(self):
        pass
