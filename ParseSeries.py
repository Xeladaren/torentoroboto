import os
import magic
import re
import tvdb_v4_official
import sys
import shutil
import discord_webhook
import human_readable
import time
import jellyfinapi.jellyfinapi_client

import Print
import Notifs

if __name__ == '__main__':
    Print.Error("this file can't be run alone.")
    quit(1)

class ParseSeries:

    def __init__(self):
        self.discord_webhook = None
        self.log_file_done   = None
        self.log_file_error  = None
        self.scan_dir        = None
        self.output_dir      = None
        self.file_action     = None
        self.jellyfin_api    = None
        self.jellyfin_url    = None

        self._tvdb               = None
        self._added_file_count   = 0
        self._updated_serie_list = []

    def initTvDB(self, api_key, acount_pin):
        self._tvdb = tvdb_v4_official.TVDB(api_key, acount_pin)

    def _sendNotifDone(self, file_source, file_dest, skiped=False):

        if skiped:
            notif_msg = "**Fichier parcer avec succes** (skiped)\n\tSource = `{}`\n\tDestination = `{}`"
        else:
            notif_msg = "**Fichier parcer avec succes**\n\tSource = `{}`\n\tDestination = `{}`"

        notif_msg = notif_msg.format(os.path.basename(file_source), file_dest)

        Notifs.sendNotif(notif_msg, always_print=True)

    def _sendNotifStart(self):
        Notifs.sendNotif("**Start parse new file**")

    def _sendNotifEnd(self):
        Notifs.sendNotif("**End parse new file**: {} new files added".format(self._added_file_count))

    def _sendNotifError(self, error):
        Notifs.sendNotif("**Error**: {}".format(error), always_print=True)

    def _writeLogFile(self, status, file):

        if status == "Done":
            if self.log_file_done:
                doneFile = open(self.log_file_done, "a")
                doneFile.write(file)
                doneFile.write("\n")
            else:
                Print.Warning("No log file done.")
        else:
            self._sendNotifError("{} : {}".format(status, file))
            if self.log_file_error:
                doneFile = open(self.log_file_error, "a")
                doneFile.write("ERROR {} : {}".format(status, file))
                doneFile.write("\n")
            else:
                Print.Warning("No log file done.")

    def _isFileExistOnDoneLog(self, fileName):

        if self.log_file_done and os.path.isfile(self.log_file_done):
            with open(self.log_file_done, "r") as doneFile:

                fileLine = doneFile.readline().replace("\n", "")
                while fileLine != "":
                    if fileLine == fileName:
                        doneFile.close()
                        return True

                    fileLine = doneFile.readline().replace("\n", "")

                doneFile.close()
        return False

    # doMove False = copy
    # doMove True  = move
    def _transfertFile(self, src, dest, doMove=False):

        fork_ret = os.fork()

        if fork_ret < 0:
            Print.Error("Fork faild")
        if fork_ret == 0:
            timeout = 10
            runPrint = True

            sys.stdout.flush()
            while runPrint:

                time.sleep(1)

                if not os.path.isfile(src):
                    break

                if os.path.isfile(dest):
                    size_src  = os.path.getsize(src)
                    size_dest = os.path.getsize(dest)

                    if size_src > size_dest:
                        timeout += 1

                    size_src_h  = human_readable.file_size(size_src)
                    size_dest_h = human_readable.file_size(size_dest)

                    bareSize = 100;
                    bareDone = "#" * int((size_dest / size_src) * bareSize)
                    bareVoid = " " * (bareSize - len(bareDone))

                    if doMove:
                        Print.Custom("TRANSFERT", "Moving: [{}{}] {} / {}".format(bareDone, bareVoid, size_dest_h, size_src_h), title_color=Print.COLOR_GREEN, start="\t")
                    else:
                        Print.Custom("TRANSFERT", "Copping: [{}{}] {} / {}".format(bareDone, bareVoid, size_dest_h, size_src_h), title_color=Print.COLOR_GREEN, start="\t")

                    if size_src == size_dest:
                        break

                if timeout < 0:
                    runPrint = False
                timeout -= 1

            quit(0)

        if doMove:
            shutil.move(src, dest)
        else:
            shutil.copy(src, dest)

        try:
            os.waitpid(fork_ret, 0)
        except:
            pass
        Print.Custom("TRANSFERT", "Transfert Done", title_color=Print.COLOR_GREEN, start="\t", always_print=True)


    def _doActionOnFile(self, file, serieName, seasonNum, episodeNum):

        if not self.output_dir:
            Print.Error("Output not found")

        outputDir  = os.path.join(self.output_dir, serieName, "S{:02}".format(seasonNum))
        outputExt  = os.path.splitext(file)[1]
        outputName = "{}.S{:02}E{:02}{}".format(serieName, seasonNum, episodeNum, outputExt)
        outputPath = os.path.join(outputDir, outputName)

        if self.file_action == "none":
            Print.Custom("OUTPUT", "Do nothing: {}".format(outputPath), title_color=Print.COLOR_GREEN, start="\t")
            return
        elif self.file_action in ["link", "copy", "move"]:
            if os.path.isfile(outputPath):
                Print.Custom("OUTPUT", "File exist, skip: {}".format(outputPath), title_color=Print.COLOR_CYAN, start="\t")
                self._writeLogFile("Done", file)
                self._sendNotifDone(file, outputPath, skiped=True)

                return
            else:
                if os.path.isdir(outputDir):
                    pass
                elif os.path.exists(outputDir):
                    Print.Custom("OUTPUT", "non dir file exists on output dir path : {}".format(outputDir), title_color=Print.COLOR_RED, start="\t")
                    return
                else:
                    os.makedirs(outputDir)

                if self.file_action == "link":
                    Print.Custom("OUTPUT", "Create link: {}".format(outputPath), title_color=Print.COLOR_GREEN, start="\t", always_print=True)
                    os.symlink(os.path.abspath(file), outputPath)
                elif self.file_action == "copy":
                    Print.Custom("OUTPUT", "Copy file: {}".format(outputPath), title_color=Print.COLOR_GREEN, start="\t", always_print=True)
                    self._transfertFile(file, outputPath, doMove=False)
                elif self.file_action == "move":
                    Print.Custom("OUTPUT", "Move file: {}".format(outputPath), title_color=Print.COLOR_GREEN, start="\t", always_print=True)
                    self._transfertFile(file, outputPath, doMove=True)

                self._writeLogFile("Done", file)
                self._sendNotifDone(file, outputPath)

        else:
            Print.Error("Invalid Action {}".format(self.file_action))
            quit(1)

    def _getTVDBInfoSerie(self, name, year=None):

        if year != None:
            resultList = self._tvdb.search(name, type="series", year=year)
        else:
            resultList = self._tvdb.search(name, type="series")

        if len(resultList) > 0:
            result = resultList[0]
            Print.Custom("TvDB", "Serie found: id='{}' slug='{}' name='{}' url='https://thetvdb.com/series/{}'".format(result["id"], result["slug"], result["name"], result["slug"]), title_color=Print.COLOR_GREEN, always_print=True, start="\t")
            return (result["slug"], result["tvdb_id"])
        else:
            Print.Custom("TvDB", "Serie not found: {}".format(name), title_color=Print.COLOR_RED, start="\t", always_print=True)
            if year:
                return getTVDBInfoSerie(name)
            elif "US" in name:
                return getTVDBInfoSerie(name.replace("US", ""))
            return None

    def _parseSerieName(self, fileName):
        basename = os.path.basename(fileName)

        regexList = [
            "^(?P<name>.*)[Ss](?P<season>\d+)[Ee](?P<episode>\d+)",
            "^(?P<name>.*)S(?P<season>\d+)x(?P<episode>\d+)",
            "^(?P<name>.*)(?P<season>\d+)x(?P<episode>\d+)"
        ]
        matchSerie = None

        for regex in regexList:
            matchSerie = re.match(regex, basename)
            if matchSerie != None:
                break

        if matchSerie != None:
            name = matchSerie["name"]
            season = int(matchSerie["season"])
            episode = int(matchSerie["episode"])

            matchYear = re.match("(?P<name>.*)\W(?P<year>(19\d{2})|(20\d{2}))", name)
            if matchYear != None:
                name = matchYear["name"]
                year = matchYear["year"]
            else:
                year = None

            nameFormated = re.sub("[\W_]*$", "", name)
            nameFormated = re.sub("\W+", " ", nameFormated)

            Print.Custom("MATCH", "File match: Serie '{}' Year {} Season {} Episode {}".format(nameFormated, year, season, episode), title_color=Print.COLOR_GREEN, start="\t", always_print=True)
            if self._tvdb:
                (serieNameOutFile, serieId) = self._getTVDBInfoSerie(nameFormated, year=year)
                if serieNameOutFile == None:
                    self._writeLogFile("TvDB not found", fileName)
                    return
            else:
                serieNameOutFile = re.sub("\W+", "-", nameFormated).lower()

            self._doActionOnFile(fileName, serieNameOutFile, season, episode)
            self._added_file_count += 1
            if not serieId in self._updated_serie_list:
                self._updated_serie_list += [serieId]
        else:
            Print.Custom("MATCH", "File not match: {}".format(basename), title_color=Print.COLOR_RED, start="\t")
            self._writeLogFile("File not match", fileName)

    def _scanDir(self, basedir):

        dirList = os.listdir(basedir)

        for elem in dirList:
            file = os.path.join(basedir, elem)
            if os.path.isfile(file):
                if self._isFileExistOnDoneLog(file):
                    Print.Custom("SCANN", "File skip: {}".format(file), title_color=Print.COLOR_BLUE)
                else:
                    fileType = magic.from_file(file, mime=True)
                    if fileType.startswith("video/"):
                        Print.Custom("SCANN", "Valide file ({}): {}".format(fileType, file), title_color=Print.COLOR_GREEN, always_print=True)
                        self._parseSerieName(file)

                    else:
                        Print.Custom("SCANN", "Invalid file ({}): {}".format(fileType, file), title_color=Print.COLOR_RED)

            elif os.path.isdir(file):
                Print.Custom("SCANN", "Directory: {}".format(file), title_color=Print.COLOR_MAGENTA)
                self._scanDir(file)

            else:
                Print.Custom("SCANN", "Not file or dir: {}".format(file), title_color=Print.COLOR_RED)

    def _updateJellyfin(self):
        if self.jellyfin_api and self.jellyfin_url:
            try:
                jellyfin_client = jellyfinapi.jellyfinapi_client.JellyfinapiClient(x_emby_token=self.jellyfin_api, server_url=self.jellyfin_url)

                for serie in self._updated_serie_list:
                    Print.Custom("JELLYFIN", "Update Jellyfin serie: {}".format(serie), title_color=Print.COLOR_GREEN, always_print=True)
                    jellyfin_client.library.post_updated_series(tvdb_id=serie)

            except Exception as ex:
                Print.Error("Fail to update jellyfin series : {}".format(ex))
                Notifs.sendNotif("**Fail to update jellyfin series**: {}".format(ex), always_print=True)

        else:
            Print.Warning("No Jellyfin API link.")


    def scanAll(self):
        if self.scan_dir and os.path.isdir(self.scan_dir):

            Print.Custom("SCANN", "Scan all", title_color=Print.COLOR_GREEN, always_print=True)

            self._added_file_count   = 0
            self._updated_serie_list = []

            self._sendNotifStart()
            self._scanDir(self.scan_dir)
            self._sendNotifEnd()

            Print.Custom("SCANN", "Scan end : {} file added".format(self._added_file_count), title_color=Print.COLOR_GREEN, always_print=True)

            self._updateJellyfin()
            return self._added_file_count

        else:
            Print.Error("Invalid scandir: {}".format(self.scan_dir))
            quit(1)
