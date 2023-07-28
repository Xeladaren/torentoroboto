#!/usr/bin/python3

import feedparser
import re
import os
import tvdb_v4_official
import transmission_rpc
import discord_webhook
import time
import human_readable

import Notifs
import Print

class TorrentAdd:

    def __init__(self):
        self.rss_url         = None
        self.discord_webhook = None
        self.series_dir      = None
        self.series_tags     = None
        self.trans_dl_dir    = None
        self.log_rss         = None

        self._tvdb = None
        self._trans_client = None
        self._serieList = None
        self._addedTorrentList = []

    def initTvDB(self, api_key, acount_pin):
        self._tvdb = tvdb_v4_official.TVDB(api_key, acount_pin)

    def initTransmission(self, host, username, password, port=9091):
        self._trans_client = transmission_rpc.Client(host=host, port=port, username=username, password=password)

    def _getTVDBInfoSerie(self, name, year=None):

        if year != None:
            resultList = self._tvdb.search(name, type="series", year=year)
        else:
            resultList = self._tvdb.search(name, type="series")

        if len(resultList) > 0:
            result = resultList[0]
            Print.Custom("TvDB", "Serie found: id='{}' slug='{}' name='{}' url='https://thetvdb.com/series/{}'".format(result["id"], result["slug"], result["name"], result["slug"]), title_color=Print.COLOR_GREEN, start="\t")
            return (result["slug"], result)
        else:
            Print.Custom("TvDB", "Serie not found: '{}'".format(name), title_color=Print.COLOR_RED, start="\t")
            if year:
                return self._getTVDBInfoSerie(name)
            elif "US" in name:
                return self._getTVDBInfoSerie(name.replace("US", ""))
            return None

    def _getTVDBInfoEpisode(self, serie_id, season, episode):
        episodeList = self._tvdb.get_series_episodes(serie_id)

        episode_tvdb = None
        episode_fra  = None

        for item in episodeList["episodes"]:
            if item["seasonNumber"] == season and item["number"] == episode:

                episode_tvdb = item

                if "fra" in item["nameTranslations"] or "fra" in item["overviewTranslations"] :
                    episode_fra = self._tvdb.get_episode_translation(item["id"], "fra")

                return (episode_tvdb, episode_fra)

    def _parseSerieName(self, torrent_name, url):

        regexList = [
            r"^(?P<name>.*)[Ss](?P<season>\d+)[Ee](?P<episode>\d+)"
        ]
        matchSerie = None

        for regex in regexList:
            matchSerie = re.match(regex, torrent_name)
            if matchSerie != None:
                break

        if matchSerie != None:
            name = matchSerie["name"]
            season = int(matchSerie["season"])
            episode = int(matchSerie["episode"])

            matchYear = re.match(r"(?P<name>.*)\W(?P<year>(19\d{2})|(20\d{2}))", name)
            if matchYear != None:
                name = matchYear["name"]
                year = matchYear["year"]
            else:
                year = None

            nameFormated = re.sub("[\W_]*$", "", name)
            nameFormated = re.sub("\W+", " ", nameFormated)

            Print.Custom("MATCH", "File match: Serie '{}' Year {} Season {} Episode {}".format(nameFormated, year, season, episode), title_color=Print.COLOR_GREEN)
#           Print.Custom("LINK", "{}".format(url), title_color=Print.COLOR_GREEN, start="\t")

            result = self._getTVDBInfoSerie(nameFormated, year)
            if result:
                return (result[0], season, episode, result[1])
        return None

    def _getSeriesList(self):
        if self._serieList == None and os.path.isdir(self.series_dir):

            self._serieList = {}
            for serie_dir in os.listdir(self.series_dir):

                self._serieList[serie_dir] = []
                serie_dir_path = os.path.join(self.series_dir, serie_dir)

                for season_dir in os.listdir(serie_dir_path):

                    season_dir_path = os.path.join(serie_dir_path, season_dir)

                    for episode_file in os.listdir(season_dir_path):

                        matchSerie = re.match(r"^.*S(?P<season>\d+)E(?P<episode>\d+)", episode_file)
                        self._serieList[serie_dir] += [(int(matchSerie["season"]), int(matchSerie["episode"]))]



    def _checkIfNeeded(self, serie_name, season, episode):

        self._getSeriesList()

        if os.path.isdir(self.series_dir):
            dirList = os.listdir(self.series_dir)
            if serie_name in self._serieList:
                if not (season, episode) in self._serieList[serie_name]:
                    Print.Custom("NEED", "Needed Episode {} {}".format(serie_name, (season, episode)), title_color=Print.COLOR_GREEN, start="\t", always_print=True)
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

            while len(needList[episode]["file-list"]) > 1:

                newFileList = [self._getBestTorrent(needList[episode]["file-list"][0], needList[episode]["file-list"][1])]

                if len(needList[episode]["file-list"]) > 2:
                    newFileList += needList[episode]["file-list"][2:]

                needList[episode]["file-list"] = newFileList

            finalNeeded[episode] = {"TvDB-serie": needList[episode]["TvDB-serie"], "torrent-file": needList[episode]["file-list"][0]}

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
                Print.Custom("TORRENT", "Download start faild : {}".format(torrent_file["title"]), title_color=Print.COLOR_RED, always_print=True)
                return False
        else:
            Print.Warning("Not transmissiom connected")
            return False
        Print.Custom("TORRENT", "Download start : {}".format(torrent_file["title"]), title_color=Print.COLOR_GREEN, always_print=True)
        return True

    def _sendAddedNotif(self, episode, tvdb_serie, torrent_file=None):

        tvdb_episode = self._getTVDBInfoEpisode(int(tvdb_serie["tvdb_id"]), episode[1], episode[2])

        serie_title   = tvdb_serie["name"]
        if "fra" in tvdb_serie["translations"]:
            serie_title = tvdb_serie["translations"]["fra"]

        episode_title = tvdb_episode[0]["name"]
        if tvdb_episode[1] and "name" in tvdb_episode[1]:
            episode_title = tvdb_episode[1]["name"]

        episode_overview = tvdb_episode[0]["overview"]
        if tvdb_episode[1] and "overview" in tvdb_episode[1]:
            episode_overview = tvdb_episode[1]["overview"]

        image = tvdb_serie["image_url"]
        if "image" in tvdb_episode[0] and tvdb_episode[0]["image"]:
            image = tvdb_episode[0]["image"]

        file_size = int(torrent_file["links"][1]["length"])
        file_size = human_readable.file_size(file_size)

        embed = discord_webhook.DiscordEmbed(title="{}\n{}".format(serie_title, episode_title), description=episode_overview)
        embed.set_image(url=image)

#            if tvdb_serie["thumbnail"]:
#                embed.set_thumbnail(url=tvdb_serie["thumbnail"])

        if torrent_file:
            embed.set_footer(text=torrent_file["title"])

        if torrent_file:
            embed.set_url(url=torrent_file["link"])

        embed.add_embed_field(name='Saison', value="{}".format(episode[1]))
        embed.add_embed_field(name='Épisode', value="{}".format(episode[2]))
        embed.add_embed_field(name='Taille', value="{}".format(file_size))

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

            self._serieList = None

            feeds = feedparser.parse(self.rss_url)
            needsFiles = {}

            Print.Custom("FEEDS", "Start Read Feeds", title_color=Print.COLOR_GREEN, always_print=True)
            Notifs.sendNotif("**Start Read Feeds**")

            for entrie in feeds["entries"]:
                if not self._isReededRSSPost(entrie):
                    Print.Custom("RSS", "Unreaded post : {}".format(entrie["title"]), title_color=Print.COLOR_GREEN, always_print=True)
                    Notifs.sendNotif("**Unreaded post**: {}".format(entrie["title"]))
                    self._addReededRSSPost(entrie)
                    result = self._parseSerieName(entrie["title"], entrie["id"])
                    if result and self._checkIfNeeded(result[0], result[1], result[2]):

                        if result[0:3] in needsFiles:
                            needsFiles[result[0:3]]["file-list"] += [entrie]
                        else:
                            needsFiles[result[0:3]] = {"TvDB-serie": result[3], "file-list": [entrie]}
                else:
                    Print.Custom("RSS", "Readed post, skip : {}".format(entrie["title"]), title_color=Print.COLOR_BLUE)

            needsFiles = self._cleanNeeded(needsFiles)

            for file in needsFiles:
                if self._startTorrent(needsFiles[file]["torrent-file"]):
                    self._sendAddedNotif(file, needsFiles[file]["TvDB-serie"], needsFiles[file]["torrent-file"])

            Print.Custom("FEEDS", "End Read Feeds: {} new files added".format(len(needsFiles)), title_color=Print.COLOR_GREEN, always_print=True)
            Notifs.sendNotif("**End Read Feeds**: {} new files added".format(len(needsFiles)))

        else:
            Print.Warning("No RSS URL")
