from __future__ import annotations

import json
import logging
import os
import typing

from bs4 import BeautifulSoup
from configparser import ConfigParser
from io import StringIO
from PyQt6 import QtGui, QtWidgets

import english as lang

from app import AppWindow
from constants import *

class TeaseCard(QtWidgets.QWidget):
    MY_FANCY_NAME = "Generic Tease Card"
    DEFAULT_THUMB = DEFAULT_THUMB_PATH

    def __init__(self, creator: AppWindow, rootDir: os.PathLike):
        logging.debug(f"Creating tease card of type {type(self)} with {rootDir=}")
        super().__init__(creator)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), palette.color(QtGui.QPalette.ColorRole.Highlight))
        self.setPalette(palette)
        self.creator = creator
        self.rootDir = rootDir
        self.config: ConfigParser = self._loadConfig()
        if "tease_id" not in self.config["General"]:
            self.config["General"]["tease_id"] = "unset"

        self.settingsPopup: TeaseSettingsPopup = None

        self.thumbnail = QtWidgets.QLabel(self)
        self.thumbnail.setPixmap(self.getDefaultThumbnail())

        self.teaseTitle = QtWidgets.QLabel(self)
        titleFont = self.teaseTitle.font()
        titleFont.setPointSize(14)
        self.teaseTitle.setFont(titleFont)

        self.teaseAuthor = QtWidgets.QLabel(self)
        authorFont = self.teaseAuthor.font()
        authorFont.setPointSize(11)
        self.teaseAuthor.setFont(authorFont)

        self.extraInfo = QtWidgets.QLabel(self)
        extraInfoFont = self.extraInfo.font()
        extraInfoFont.setPointSize(9)
        extraInfoFont.setItalic(True)
        self.extraInfo.setFont(extraInfoFont)

        metadataSubLayout = QtWidgets.QVBoxLayout()
        metadataSubLayout.addWidget(self.teaseTitle)
        metadataSubLayout.addWidget(self.teaseAuthor)
        metadataSubLayout.addWidget(self.extraInfo)
        metadataSubLayout.addStretch(1)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.thumbnail)
        layout.addLayout(metadataSubLayout)
        layout.addStretch()

        self.refreshMetadata()

        self.setLayout(layout)
    
    def saveSettings(self):
        self._saveConfig()
        self.refreshMetadata()
    
    def refreshMetadata(self):
        self.teaseTitle.setText(self.config["General"]["title"])
        self.teaseAuthor.setText(self.config["General"]["author"])
        self.extraInfo.setText(" | ".join([self.config["General"]["tease_id"], self.MY_FANCY_NAME]))
    
    def getThumbnail(self) -> QtGui.QPixmap | None:
        return self.getDefaultThumbnail()
    
    def mousePressEvent(self, event):
        self.creator.setSelectedTease(self)
        return super().mousePressEvent(event)
    
    def _saveConfig(self):
        with open(os.path.join(self.rootDir, "config.ini"), "w") as f:
            self.saveConfig(self.config, f)
    
    def _loadConfig(self) -> ConfigParser:
        with open(os.path.join(self.rootDir, "config.ini")) as f:
            return self.loadConfig(f)
    
    # Workaround for "QPixmap: Must construct a QGuiApplication before a QPixmap"
    @classmethod
    def getDefaultThumbnail(cls) -> QtGui.QPixmap:
        if type(cls.DEFAULT_THUMB) is not QtGui.QPixmap:
            logging.debug("Creating default thumbnail")
            cls.DEFAULT_THUMB = cls.cropThumbnail(QtGui.QPixmap(cls.DEFAULT_THUMB))
        return cls.DEFAULT_THUMB

    @staticmethod
    def cropThumbnail(thumbnail: QtGui.QPixmap) -> QtGui.QPixmap:
        dim = min(thumbnail.width(), thumbnail.height())
        if dim == 0:
            return thumbnail
        return thumbnail.copy(
            (thumbnail.width() - dim) // 2,  # top left x
            (thumbnail.height() - dim) // 2,  # top left y
            dim, dim  # width, height
        ).scaledToHeight(80)

    @staticmethod
    def saveConfig(config: ConfigParser, file: typing.TextIO):
        # eos.outer.js doesn't support .ini files with sections
        with StringIO() as configgy:
            config.write(configgy, False)
            config = configgy.getvalue()
        config = config.lstrip("[General]\n")
        file.write(config)
    
    @staticmethod
    def loadConfig(file: typing.TextIO) -> ConfigParser:
        # eos.outer.js doesn't support .ini files with sections
        configgy = file.read()
        configgy = "[General]\n" + configgy
        config = ConfigParser()
        config.read_string(configgy)
        return config
    
class TeaseSettingsPopup(QtWidgets.QDialog):
    def __init__(self, creator: TeaseCard):
        super().__init__(creator)
        self.setMinimumWidth(4 * WINDOW_SIZE)
        self.setModal(True)
        self.creator = creator

        self.layout_ = QtWidgets.QGridLayout(self)
        self.setLayout(self.layout_)
        
        teaseTitleHint = QtWidgets.QLabel(lang.titleTextBoxHint, self)
        self.teaseTitleEdit = QtWidgets.QLineEdit(self)

        teaseAuthorHint = QtWidgets.QLabel(lang.authorTextBoxHint, self)
        self.teaseAuthorEdit = QtWidgets.QLineEdit(self)

        teaseIdHint = QtWidgets.QLabel(lang.teaseIdTextBoxHint, self)
        self.teaseIdEdit = QtWidgets.QLineEdit(self)

        saveSettingsButton = QtWidgets.QPushButton(lang.saveSettings, self)
        saveSettingsButton.clicked.connect(self.saveSettings)
        self.layout_.addWidget(teaseTitleHint, 0, 0)
        self.layout_.addWidget(self.teaseTitleEdit, 0, 1)
        self.layout_.addWidget(teaseAuthorHint, 1, 0)
        self.layout_.addWidget(self.teaseAuthorEdit, 1, 1)
        self.layout_.addWidget(teaseIdHint, 2, 0)
        self.layout_.addWidget(self.teaseIdEdit, 2, 1)
        # Hack
        self.layout_.addWidget(saveSettingsButton, 10, 0, 1, 2)
    
    def saveSettings(self):
        self.creator.config["General"]["title"] = self.teaseTitleEdit.text()
        self.creator.config["General"]["author"] = self.teaseAuthorEdit.text()
        self.creator.config["General"]["tease_id"] = self.teaseIdEdit.text()
        self.creator.saveSettings()
        self.hide()

    def refreshSettings(self):
        self.teaseTitleEdit.setText(self.creator.config["General"]["title"])
        self.teaseAuthorEdit.setText(self.creator.config["General"]["author"])
        self.teaseIdEdit.setText(self.creator.config["General"]["tease_id"])
        self.setWindowTitle(f"{lang.teaseSettings}: {self.creator.config['General']['title']}")

class EosTeaseCard(TeaseCard):
    MY_FANCY_NAME = "EOS Tease Card"

    def __init__(self, creator: AppWindow, rootDir: os.PathLike):
        super().__init__(creator, rootDir)
        if "unhide_timers" not in self.config["General"]:
            self.config["General"]["unhide_timers"] = "false"

        self.settingsPopup = EosTeaseSettingsPopup(self)
        self.eosscript = self.loadEosscript()
        if (thumbnail := self.getThumbnail()) is not None:
            self.thumbnail.setPixmap(thumbnail)
    
    def saveSettings(self):
        super().saveSettings()
        self.eosscript = self.loadEosscript()
        logging.debug(f"Reloaded eosscript for {self.rootDir} with {self.config['General']['unhide_timers']=}")
    
    def loadEosscript(self) -> typing.Any:
        with open(os.path.join(self.rootDir, "eosscript.json")) as f:
            eosscript = json.load(f)
        if self.config["General"].getboolean("unhide_timers"):
            logging.debug(f"Hiding timers for {self.rootDir}")
            self.removeTags(("nyx.timer/style", "timer/style"), eosscript)
        return eosscript
    
    def getThumbnail(self) -> QtGui.QPixmap | None:
        imgHash = None
        if (imgLocator := self.findFirstImage(self.eosscript["pages"]["start"])) is not None:
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
        
        if imgHash is None:
            logging.warning(f"Unknown image locator: {imgLocator}")
            return None

        for img in os.listdir(imgDir := os.path.join(self.rootDir, "timg", "tb_xl")):
            if img.startswith(imgHash):
                return self.cropThumbnail(QtGui.QPixmap(os.path.join(imgDir, img)))

        logging.warning(f"Could not find thumbnail in media for {self.rootDir}")
        return None
    
    @classmethod
    def findFirstImage(cls, eosFrag) -> str | None:
        if isinstance(eosFrag, dict):
            if "image" in eosFrag:
                return eosFrag["image"]["locator"]
            elif "media" in eosFrag and "nyx.image" in eosFrag["media"]:
                return eosFrag["media"]["nyx.image"]
            for frag in eosFrag.values():
                if (res := cls.findFirstImage(frag)) is not None:
                    return res
        elif isinstance(eosFrag, list):
            for frag in eosFrag:
                if (res := cls.findFirstImage(frag)) is not None:
                    return res
        return None

    @classmethod
    def removeTags(cls, tags: tuple[str], eosFrag):
        if isinstance(eosFrag, dict):
            for tag in tags:
                path = tag.split("/")
                tmp = eosFrag
                for key in path[:-1]:
                    if key in tmp:
                        tmp = tmp[key]
                    else:
                        break
                else:
                    if path[-1] in tmp:
                        del tmp[path[-1]]
            for frag in eosFrag.values():
                cls.removeTags(tags, frag)
        elif isinstance(eosFrag, list):
            for frag in eosFrag:
                cls.removeTags(tags, frag)

class EosTeaseSettingsPopup(TeaseSettingsPopup):
    def __init__(self, creator: EosTeaseCard):
        super().__init__(creator)

        self.unhideTimersButton = QtWidgets.QCheckBox(lang.unhideTimers, self)
        self.layout_.addWidget(self.unhideTimersButton, 3, 0, 1, 2)

        self.debugModeButton = QtWidgets.QCheckBox(lang.debugMode, self)
        self.layout_.addWidget(self.debugModeButton, 4, 0, 1, 2)
    
    def saveSettings(self):
        super().saveSettings()
        # Need to use .lower() so that eos.outer.js can read it properly
        self.creator.config["General"]["unhide_timers"] = str(self.unhideTimersButton.isChecked()).lower()
        self.creator.config["General"]["preview"] = str(self.debugModeButton.isChecked()).lower()
    
    def refreshSettings(self):
        super().saveSettings()
        self.unhideTimersButton.setChecked(self.creator.config["General"].getboolean("unhide_timers"))
        self.debugModeButton.setChecked(self.creator.config["General"].getboolean("preview"))

class RegularTeaseCard(TeaseCard):
    MY_FANCY_NAME = "Regular Tease Card"

    def __init__(self, creator, rootDir):
        super().__init__(creator, rootDir)
        self.settingsPopup = RegularTeaseSettingsPopup(self)
        if (thumbnail := self.getThumbnail()) is not None:
            self.thumbnail.setPixmap(thumbnail)
    
    def getThumbnail(self) -> QtGui.QPixmap | None:
        with open(os.path.join(self.rootDir, "index.html")) as f:
            htmlTree = BeautifulSoup(f, "html.parser")
        # If I cannot chain far too many methods (in multiple lines) at once, this happens.
        htmlTree = htmlTree.find("html", recursive=False)
        htmlTree = htmlTree.find("body", recursive=False)
        htmlTree = htmlTree.find("div", {"id": "cm_wide"})
        for link in htmlTree.find_all("img", src=True):
            if "timg/tb_xl" in link["src"]:
                return self.cropThumbnail(QtGui.QPixmap(os.path.join(self.rootDir, link["src"])))
        return None

class RegularTeaseSettingsPopup(TeaseSettingsPopup):
    pass
