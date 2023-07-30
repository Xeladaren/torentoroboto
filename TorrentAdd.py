#!/usr/bin/python3

import feedparser
import re
import os
import tvdb_v4_official
import transmission_rpc
import discord_webhook
import time
import human_readable
import unidecode
import string

import Notifs
import Print
import Series
import SeriesEpisodes

class TorrentAdd:

    def __init__(self):
        self.rss_url         = None
        self.discord_webhook = None
        self.series_dir      = None
        self.series_tags     = None
        self.trans_dl_dir    = None
        self.log_rss         = None

        self._trans_client = None
        self._serieList = {}
        self._addedTorrentList = []

    def initTransmission(self, host, username, password, port=9091):
        self._trans_client = transmission_rpc.Client(host=host, port=port, username=username, password=password)

    def __updateSeriesList(self):

        Print.Custom("Series", f"Update Episodes on medias dir", title_color=Print.COLOR_GREEN, always_print=True)
        for serie_dir in os.listdir(self.series_dir):

            serieMatch = re.search(r"\[tvdbid-(?P<serie_id>\d+)\]", serie_dir)
            if serieMatch:
                serie = Series.Serie.findSerieById(serieMatch["serie_id"])

                if not serie in self._serieList:
                    self._serieList[serie] = []

                serie_dir_path = os.path.join(self.series_dir, serie_dir)

                for season_dir in os.listdir(serie_dir_path):

                    season_dir_path = os.path.join(serie_dir_path, season_dir)

                    for episode_file in os.listdir(season_dir_path):

                        matchEpisode = re.search(r"S(?P<season>\d+)E(?P<episode>\d+)", episode_file)
                        if matchEpisode:
                            episode_serie = SeriesEpisodes.SerieEpisode.findEpisodeBySerie(serie, int(matchEpisode["season"]), int(matchEpisode["episode"]))
                            if episode_serie and not episode_serie in self._serieList[serie]:
                                Print.Custom("Series", f"Add : {episode_serie}", title_color=Print.COLOR_GREEN, start="\t", always_print=True)
                                self._serieList[serie] += [episode_serie]

        Print.Custom("Series", f"Update Episodes on medias dir end", title_color=Print.COLOR_GREEN, always_print=True)



    def _checkIfNeeded(self, episode_serie):

        self.__updateSeriesList()

        if episode_serie.serie in self._serieList:
            if not episode_serie in self._serieList[episode_serie.serie]:
                Print.Custom("NEED", f"Needed Episode {episode_serie}", title_color=Print.COLOR_GREEN, start="\t", always_print=True)
                return True
        return False

    def _getBestTorrent(self, first, second):

        result = None

        if self.series_tags:
            for tag in self.series_tags:
                if   tag.lower() in first["title"].lower()  and not tag.lower() in second["title"].lower():
                    result = first
                    break
                elif tag.lower() in second["title"].lower() and not tag.lower() in first["title"].lower():
                    result = second
                    break
        else:
            Print.Warning("Not series tags")

        if result == None:
            if int(first["links"][1]["length"]) < int(second["links"][1]["length"]):
                result = first
            else:
                result = second

        return result

    def _cleanNeeded(self, needList):
        finalNeeded = {}

        for episode in needList:

            while len(needList[episode]) > 1:

                newFileList = [self._getBestTorrent(needList[episode][0], needList[episode][1])]

                if len(needList[episode]) > 2:
                    newFileList += needList[episode][2:]

                needList[episode] = newFileList

            finalNeeded[episode] = needList[episode][0]

        return finalNeeded

    def _startTorrent(self, torrent_file):

        torrent_link = torrent_file["links"][1]["href"]

        if self._trans_client:
            try:
                if self.trans_dl_dir:
                    self._addedTorrentList += [self._trans_client.add_torrent(torrent_link, download_dir=self.trans_dl_dir)]
                else:
                    self._addedTorrentList += [self._trans_client.add_torrent(torrent_link)]
            except:
                Print.Custom("TORRENT", f"Download start faild : {torrent_link}", title_color=Print.COLOR_RED, always_print=True)
                Notifs.sendNotif(f"**Download start faild** : {torrent_link}", always_print=True)
                return False
        else:
            Print.Warning("Not transmissiom connected")
            return False
        Print.Custom("TORRENT", "Download start : {}".format(torrent_file["title"]), title_color=Print.COLOR_GREEN, always_print=True)
        return True

    def _sendAddedNotif(self, episode, torrent_file=None):

        file_size = int(torrent_file["links"][1]["length"])
        file_size = human_readable.file_size(file_size)

        footer = None
        if torrent_file:
            footer = torrent_file["title"]

        url = None
        if torrent_file:
            url = torrent_file["link"]

        embed = episode.getDiscordEmbeded(custom_url=url, custom_footer=footer, file_size=file_size)

        Notifs.sendNotif("**Nouveau Torrent ajouté :**", embed=embed, always_print=True)

    def _sendEndDownloadNotif(self, torrent_name, is_stoped=False, is_error=False):

        if is_error:
            Notifs.sendNotif("**Erreur sur le torrent**:\n\t`{}`".format(torrent_name), always_print=True)
        elif is_stoped:
            Notifs.sendNotif("**Torrent stoppé**:\n\t`{}`".format(torrent_name), always_print=True)
        else:
            Notifs.sendNotif("**Torrent téléchargé**:\n\t`{}`".format(torrent_name), always_print=True)

    def _addReededRSSPost(self, post):
        if self.log_rss:
            logFile = open(self.log_rss, "a")
            logFile.write(post["link"])
            logFile.write("\n")
        else:
            Print.Warning("No RSS Readed Log")

    def _isReededRSSPost(self, post):

        if self.log_rss and os.path.isfile(self.log_rss):
            with open(self.log_rss, "r") as doneFile:

                fileLine = doneFile.readline().replace("\n", "")
                while fileLine != "":
                    if fileLine == post["link"]:
                        doneFile.close()
                        return True

                    fileLine = doneFile.readline().replace("\n", "")

                doneFile.close()
        else:
            Print.Warning("No RSS Readed Log")
        return False

    def waitDownloadTorrents(self):

        Print.Custom("TORRENT", "Wait Download Torrents", title_color=Print.COLOR_GREEN, always_print=True)
        self.__updateSeriesList()

        while len(self._addedTorrentList) > 0:
            for torrent in self._addedTorrentList:
                percent_done = 0
                is_stoped = False

                try:
                    torrent_update = self._trans_client.get_torrent(torrent.hashString)
                except:
                    Print.Custom("TORRENT", "Download error : {}".format(torrent.name), title_color=Print.COLOR_RED, always_print=True)
                    self._sendEndDownloadNotif(torrent.name, is_stoped=False, is_error=True)
                    self._addedTorrentList.remove(torrent)
                    break

                try:
                    Print.Custom("TORRENT", "Downloading : {} {} {} %".format(torrent_update.name, torrent_update.status, int(torrent_update.percent_done * 100)), title_color=Print.COLOR_GREEN)
                    percent_done = torrent_update.percent_done
                    is_stoped = torrent_update.status == "stopped"

                except:
                    Print.Custom("TORRENT", "Downloading : {}".format(torrent.name), title_color=Print.COLOR_RED)

                if percent_done == 1:
                    Print.Custom("TORRENT", "Download end : {}".format(torrent.name), title_color=Print.COLOR_GREEN, always_print=True)
                    self._sendEndDownloadNotif(torrent.name, is_stoped=False, is_error=False)
                    self._addedTorrentList.remove(torrent)
                elif is_stoped == True:
                    Print.Custom("TORRENT", "Download stoped : {}".format(torrent.name), title_color=Print.COLOR_YELLOW, always_print=True)
                    self._sendEndDownloadNotif(torrent.name, is_stoped=True, is_error=False)
                    self._addedTorrentList.remove(torrent)

            time.sleep(1)
        Print.Custom("TORRENT", "Stop Wait Download Torrents", title_color=Print.COLOR_GREEN, always_print=True)

    def readFeeds(self):

        if self.rss_url:

            feeds = feedparser.parse(self.rss_url)

            import json

            if "status" in feeds and feeds["status"] != 200:
                Print.Error(f"Error to get RSS-feed : {feeds['status']}")
                print(feeds)
                Notifs.sendNotif(f"**Error to read RSS**: {feeds['status']}", always_print=True)

            needsFiles = {}

            Print.Custom("FEEDS", "Start Read Feeds", title_color=Print.COLOR_GREEN, always_print=True)
            Notifs.sendNotif("**Start Read Feeds**")

            for entrie in feeds["entries"]:
                if not self._isReededRSSPost(entrie):

                    Print.Custom("RSS", "Unreaded post : {}".format(entrie["title"]), title_color=Print.COLOR_GREEN, always_print=True)
                    Notifs.sendNotif("**Unreaded post**: {}".format(entrie["title"]))
                    self._addReededRSSPost(entrie)

                    serie_episode = SeriesEpisodes.SerieEpisode.findEpisodeByFileName(entrie["title"])

                    if serie_episode and self._checkIfNeeded(serie_episode):

                        if serie_episode in needsFiles:
                            needsFiles[serie_episode] += [entrie]
                        else:
                            needsFiles[serie_episode] = [entrie]
                else:
                    Print.Custom("RSS", "Readed post, skip : {}".format(entrie["title"]), title_color=Print.COLOR_BLUE)

            needsFiles = self._cleanNeeded(needsFiles)

            for episode in needsFiles:
                if self._startTorrent(needsFiles[episode]):
                    self._sendAddedNotif(file, episode, needsFiles[episode])

            Print.Custom("FEEDS", "End Read Feeds: {} new files added".format(len(needsFiles)), title_color=Print.COLOR_GREEN, always_print=True)
            Notifs.sendNotif("**End Read Feeds**: {} new files added".format(len(needsFiles)))

        else:
            Print.Warning("No RSS URL")
