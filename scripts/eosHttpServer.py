import datetime
import email.utils
import io
import json
import logging
import os
import urllib.parse

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
import uuid

class MiloHTTPRequestHandler(SimpleHTTPRequestHandler):
    server_version = "MiloHTTP/0.6"
    # Copied from http.server.SimpleHTTPRequestHandler
    index_pages = ("index.html", "index.htm")

    def __init__(self, *args, directory=None, commonDir=None, appWindow, **kwargs):
        self.commonDir = commonDir
        self.appWindow = appWindow
        super().__init__(*args, **kwargs, directory=directory)

    # Serves most files from commonfiles to deduplicate data
    # and fix the font issue.
    def translate_path(self, path):
        path = super().translate_path(path)
        logging.debug(f"{self.directory=}")
        logging.debug(f"{path=}")

        if self.commonDir is None:
            return path

        # TODO learn match and replace below as 
        #  well as most of the rest of the script
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
        # This test also includes navy.70005832.png but it's fine.
        if path.startswith((sm := os.path.join("static", "media")), i) and \
              path[i+len(sm)+1:] in os.listdir(os.path.join(self.commonDir, sm)):
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
        
        # TODO make this more precise, maybe..?
        if i == len(path) and os.path.isdir(path) and \
              not set(self.index_pages).intersection(os.listdir(path)):
            # Normally we would serve "index.html" by default if the
            # path was the folder, but it was moved to commonfiles.
            logging.debug(f"Returning eos index.html for {path}")
            return os.path.join(self.commonDir, "index.html")
        if path.startswith(tuple(os.listdir(self.commonDir)), i):
            logging.debug(f"New path is {os.path.join(self.commonDir, path[i:])}")
            return os.path.join(self.commonDir, path[i:])
            
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
                if (teaseKey := path.removesuffix(f"{os.path.sep}eosscript.json")) in self.appWindow.teases:
                    logging.debug(f"Serving in-memory eosscript for {path}")
                    eosscript = json.dumps(self.appWindow.teases[teaseKey].eosscript).encode()
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
                    logging.debug(f"{teaseKey} was not in {self.appWindow.teases=} or has no eosscript.")
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
