
import tvdb_v4_official
import unidecode
import string
import re

import Print

if __name__ == '__main__':
    Print.Error("this file can't be run alone.")
    quit(1)

tag_list = ["\\bus\\b", "\\bmulti\\b", "\\bvff\\b", "\\b\d+p\\b"]

class Serie:

    seriesList = []
    tvdb = None

    @staticmethod
    def initTvDB(api_key, acount_pin):
        if not Serie.tvdb:
            Serie.tvdb = tvdb_v4_official.TVDB(api_key, acount_pin)


    @staticmethod
    def findSerieByName(name, year=None):

        for serie in Serie.seriesList:
            if serie == name:
                return serie

        if Serie.tvdb:
            if year != None:
                resultList = Serie.tvdb.search(name, type="series", year=year)
            else:
                resultList = Serie.tvdb.search(name, type="series")

            serieFountTvdb = None

            if len(resultList) > 0:
                result = resultList[0]
                Print.Custom("Serie", "Serie found: id='{}' slug='{}' name='{}' url='https://thetvdb.com/series/{}'".format(
                    result["id"], result["slug"], result["name"], result["slug"]), title_color=Print.COLOR_GREEN, start="\t")
                serieFountTvdb = result
            else:
                Print.Custom("Serie", "Serie not found: '{}'".format(name), title_color=Print.COLOR_RED, start="\t")
                if year:
                    return Serie.findSerieByName(name)

                for tag in tag_list:
                    if re.search(tag, name, flags=re.I):
                        name = re.sub(tag, "", name, flags=re.I)
                        return Serie.findSerieByName(name)

            if serieFountTvdb:

                for serie in Serie.seriesList:
                    if serie == int(serieFountTvdb["tvdb_id"]):
                        return serie

                newSerie = Serie.findSerieById(int(serieFountTvdb["tvdb_id"]))
                Serie.seriesList.append(newSerie)

                return newSerie
            else:
                Print.Error(f"[Serie] Serie not found {name}")
                return None
        else:
            Print.Error("[Serie] TVDB not initialised")
            return None

    @staticmethod
    def findSerieById(id):

        for serie in Serie.seriesList:
            if serie == id:
                return serie

        return Serie(id)

    @staticmethod
    def findSerieBySlug(slug):

        for serie in Serie.seriesList:
            if serie.tvdb_info["slug"] == slug:
                return serie

        if Serie.tvdb:
            serieFountTvdb = Serie.tvdb.get_series_by_slug(slug)

            if serieFountTvdb:
                newSerie = Serie.findSerieById(serieFountTvdb["id"])

                return newSerie
            else:
                return None
        else:
            return None


    def __init__(self, id):

        serieTvdb = Serie.tvdb.get_series(id)

        if serieTvdb:
            self.name      = serieTvdb["name"]
            self.id        = serieTvdb["id"]
            self.tvdb_info = serieTvdb
            self.name_normalized = None

            Serie.seriesList.append(self)
        else:
            del self

    def __eq__(self, other):

        if    type(other) == Serie:
            return self.id == other.id
        elif  type(other) == str:
            return self.name == other
        elif type(other) == int:
            return self.id == other
        else:
            return False

    def __repr__(self):
        return f"Serie(name='{self.name}', id='{self.id}')"

    def __str__(self):
        return f"Serie(name='{self.name}', id='{self.id}')"

    def __format__(self, formatStr):
        return self.name

    def __hash__(self):
        return hash(self.id)

    def __normaliseAndCheck(self, name):

        name_normalized = unidecode.unidecode(name)
        name_normalized = string.capwords(name_normalized)

        resultList = Serie.tvdb.search(name_normalized, type="series")

        if len(resultList) > 0:
            if int(resultList[0]["tvdb_id"]) == self.id:
                return name_normalized

        name_eng = self.getTranslateName()
        if name_eng:
            name_normalized = unidecode.unidecode(name_eng)
            name_normalized = string.capwords(name_normalized)

            resultList = Serie.tvdb.search(name_normalized, type="series")

            if len(resultList) > 0:
                if int(resultList[0]["tvdb_id"]) == self.id:
                    return name_normalized

        name_normalized = self.tvdb_info["slug"].replace("-", " ")
        name_normalized = string.capwords(name_normalized)

        return None

    def getTranslateName(self, lang="eng"):

        if lang in self.tvdb_info["nameTranslations"]:
            translation = Serie.tvdb.get_series_translation(self.id, lang)

            if "name" in translation:
                return translation["name"]

        return None

    def getNormalizedName(self):

        if not self.name_normalized:
            self.name_normalized = self.__normaliseAndCheck(self.name)

        return self.name_normalized

    def getFolderName(self, no_space=False, add_year=True, add_tvdbid=True):

        name_normalized = self.getNormalizedName()

        if name_normalized:
            if add_year:
                name_normalized = re.sub(r"\s*\(\d{4}\)\s*$", "", name_normalized)

            if no_space:

                name_normalized = re.sub("\s*-\s*", "-", name_normalized)
                name_normalized = re.sub("\s+", "_", name_normalized)
                name_normalized = re.sub("(?=\W)[^-]", "", name_normalized)

                if add_year:
                    name_normalized = "{}.{}".format(name_normalized, self.tvdb_info["year"])

                if add_tvdbid:
                    name_normalized = "{}.tvdbid-{}".format(name_normalized, self.id)

            else:
                if add_year:
                    name_normalized = "{} ({})".format(name_normalized, self.tvdb_info["year"])

                if add_tvdbid:
                    name_normalized = "{} [tvdbid-{}]".format(name_normalized, self.id)

            return name_normalized
        else:
            return None
