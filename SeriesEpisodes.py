
import tvdb_v4_official
import unidecode
import string
import re
import os
import discord_webhook

import Series
import Print

if __name__ == '__main__':
    Print.Error("this file can't be run alone.")
    quit(1)

regexList = [
    "^(?P<name>.*)[Ss](?P<season>\d+)[Ee](?P<episode>\d+)",
    "^(?P<name>.*)S(?P<season>\d+)x(?P<episode>\d+)",
    "^(?P<name>.*)(?P<season>\d+)x(?P<episode>\d+)"
]

class SerieEpisode:

    episodeList = []

    @staticmethod
    def findEpisodeByFileName(file_name):

        for episode in SerieEpisode.episodeList:
            if file_name == episode.getFileName(simple=True):
                return episode
            elif file_name == episode.getFileName(simple=False):
                return episode

        matchEpisode = None

        for regex in regexList:
            matchEpisode = re.match(regex, file_name)
            if matchEpisode != None:
                break

        if matchEpisode:
            name = matchEpisode["name"]
            season = int(matchEpisode["season"])
            episode = int(matchEpisode["episode"])

            matchYear = re.match("(?P<name>.*)\W(?P<year>(19\d{2})|(20\d{2}))", name)
            if matchYear != None:
                name = matchYear["name"]
                year = matchYear["year"]
            else:
                year = None

            nameFormated = re.sub("[\W_]*$", "", name)
            nameFormated = re.sub("\W+", " ", nameFormated)

            Print.Custom("Episode", f"File match: Serie '{nameFormated}' Year {year} Season {season} Episode {episode}", title_color=Print.COLOR_GREEN)
#           Print.Custom("LINK", "{}".format(url), title_color=Print.COLOR_GREEN, start="\t")

            serie = Series.Serie.findSerieByName(nameFormated, year=year)

            if serie:
                return SerieEpisode.findEpisodeBySerie(serie, season, episode)

            return None

    @staticmethod
    def findEpisodeBySerie(serie, season_num, episode_num):

        for episode in SerieEpisode.episodeList:
            if episode.serie == serie and episode.season == season_num and episode.episode == episode_num:
                return episode

        new_episode = SerieEpisode(serie, season_num, episode_num)
        SerieEpisode.episodeList.append(new_episode)

        return new_episode


    def __init__(self, serie, season, episode):
        self.serie      = serie
        self.season     = int(season)
        self.episode    = int(episode)

        self.__tvdb_info  = None

    def __eq__(self, other):

        if    type(other) == SerieEpisode:
            return self.serie == other.serie and self.season == other.season and self.episode == other.episode
        else:
            return False

    def __repr__(self):
        return f"SerieEpisode(name='{self.serie.name}', season={self.season}, episode={self.episode})"

    def __str__(self):
        return f"SerieEpisode(name='{self.serie.name}', season={self.season}, episode={self.episode})"

    def __format__(self, formatStr):
        return self.getFileName()

    def __hash__(self):
        return hash((self.serie, self.season, self.episode))

    def __getEpisodeInfo(self):

        if self.__tvdb_info == None:
            episodeList = Series.Serie.tvdb.get_series_episodes(self.serie.id)

            for item in episodeList["episodes"]:
                if item["seasonNumber"] == self.season and item["number"] == self.episode:

                    self.__tvdb_info = item
                    return

    def getTvDBInfo():
        self,__getEpisodeInfo()
        return self.__tvdb_info

    def getFileName(self, simple=True, file_extension=""):

        if simple:
            serie_name = self.serie.getFolderName(no_space=True, add_year=False, add_tvdbid=False)
            return f"{serie_name}.S{self.season:02}E{self.episode:02}{file_extension}"

        else:
            serie_name = self.serie.getFolderName(no_space=False, add_year=False, add_tvdbid=False)
            return f"{serie_name} - Season {self.season:02} Episode {self.episode:02}{file_extension}"

    def getFullPath(self, simple_serie=False, simple_season=False, simple_episode=True, file_extension=""):
        if simple_serie:
            serie_dir  = self.serie.getFolderName(no_space=True, add_year=False, add_tvdbid=False)
        else:
            serie_dir  = self.serie.getFolderName(no_space=False, add_year=True, add_tvdbid=True)

        if simple_season:
            season_dir = f"S{self.season:02}"
        else:
            season_dir = f"Season {self.season:02}"

        episode_file = self.getFileName(simple=simple_episode, file_extension=file_extension)

        return os.path.join(serie_dir, season_dir, episode_file)

    def getTranslateName(self, lang="eng"):

        if lang in self.getTvDBInfo()["nameTranslations"]:
            translation = Series.Serie.tvdb.get_episode_translation(self.getTvDBInfo()["id"], lang)

            if "name" in translation:
                return translation["name"]

        return None

    def getTranslateDesc(self, lang="eng"):

        if lang in self.getTvDBInfo()["overviewTranslations"]:
            translation = Series.Serie.tvdb.get_episode_translation(self.getTvDBInfo()["id"], lang)

            if "overview" in translation:
                return translation["overview"]

        return None

    def getDiscordEmbeded(self, custom_url=None, custom_footer=None, file_size=None):

        serie_title   = self.serie.getTranslateName("fra")
        if serie_title == None:
            serie_title  = self.serie.name

        episode_title = self.getTranslateName("fra")
        if episode_title == None:
            episode_title  = self.getTvDBInfo()["name"]

        episode_overview = self.getTranslateDesc("fra")
        if episode_overview == None:
            episode_overview = self.getTvDBInfo()["overview"]

        embed = discord_webhook.DiscordEmbed(title="{}\n{}".format(serie_title, episode_title), description=episode_overview)

        if "image" in self.getTvDBInfo():
            embed.set_image(url=self.getTvDBInfo()["image"])
        elif "image" in self.serie.getTvDBInfo():
            embed.set_image(url=self.serie.getTvDBInfo()["image"])

        if custom_footer:
            embed.set_footer(text=custom_footer)
        else:
            embed.set_footer(text=self.getFullPath())

        if custom_url:
            embed.set_url(url=custom_url)
        else:
            slug = self.serie.getTvDBInfo()["slug"]
            episode_id = self.getTvDBInfo()["id"]
            embed.set_url(url=f"https://thetvdb.com/series/{slug}/episodes/{episode_id}")

        embed.add_embed_field(name='Saison', value="{}".format(self.season))
        embed.add_embed_field(name='Épisode', value="{}".format(self.episode))
        if file_size:
            embed.add_embed_field(name='Taille', value="{}".format(file_size))

        return embed
