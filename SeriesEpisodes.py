
import tvdb_v4_official
import unidecode
import string
import re
import os

import Series
import Print

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

            Print.Custom("Episode", "File match: Serie '{}' Year {} Season {} Episode {}".format(nameFormated, year, season, episode), title_color=Print.COLOR_GREEN)
#           Print.Custom("LINK", "{}".format(url), title_color=Print.COLOR_GREEN, start="\t")

            serie = Series.Serie.findSerieByName(nameFormated)
            print(f"Serie found {serie}")

            if serie:
                print(f"Serie {serie} Season {season} Episode {episode}")
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

    def __repr__(self):
        return f"SerieEpisode(name='{self.serie.name}', season={self.season}, episode={self.episode})"

    def __str__(self):
        return f"SerieEpisode(name='{self.serie.name}', season={self.season}, episode={self.episode})"

    def __format__(self, formatStr):
        return self.getFileName()

    def __getEpisodeInfo(self):
        pass

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
