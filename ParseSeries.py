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
import SeriesEpisodes

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

        self._added_file_count   = 0
        self._updated_serie_list = []

    def _sendNotifDone(self, serie_episode, skiped=False):

        if skiped:
            notif_msg = "**Nouvel épisode ajouté** (skip)"
        else:
            notif_msg = "**Nouvel épisode ajouté**"

        embed = serie_episode.getDiscordEmbeded()

        Notifs.sendNotif(notif_msg, embed=embed, always_print=True)

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

    def _doActionOnFile(self, file, serie_episode):

        if not self.output_dir:
            Print.Error("Output not found")

        outputExt  = os.path.splitext(file)[1]
        outputFile = serie_episode.getFullPath(file_extension=outputExt)
        outputPath = os.path.join(self.output_dir, outputFile)
        outputDir = os.path.dirname(outputPath)

        if self.file_action == "none":
            Print.Custom("OUTPUT", "Do nothing: {}".format(outputPath), title_color=Print.COLOR_GREEN, start="\t")
            return
        elif self.file_action in ["link", "copy", "move"]:
            if os.path.isfile(outputPath):
                Print.Custom("OUTPUT", "File exist, skip: {}".format(outputPath), title_color=Print.COLOR_CYAN, start="\t")
                self._writeLogFile("Done", file)
                self._sendNotifDone(serie_episode, skiped=True)

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
                self._sendNotifDone(serie_episode)

        else:
            Print.Error("Invalid Action {}".format(self.file_action))
            quit(1)

    def _parseSerieName(self, fileName):
        basename = os.path.basename(fileName)

        serieEpisode = SeriesEpisodes.SerieEpisode.findEpisodeByFileName(basename)

        if serieEpisode:
            Print.Custom(f"MATCH", "File match: Serie '{serieEpisode}'", title_color=Print.COLOR_GREEN, start="\t", always_print=True)


            self._doActionOnFile(fileName, serieEpisode)
            self._added_file_count += 1
            if not serieEpisode.serie.id in self._updated_serie_list:
                self._updated_serie_list += [serieEpisode.serie.id]
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
                    #jellyfin_client.library.post_updated_series(tvdb_id=serie)

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
