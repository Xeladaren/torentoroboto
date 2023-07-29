
import tvdb_v4_official
import unidecode
import string
import re

import Print

class Serie:

    seriesList = []
    tvdb = None

    @staticmethod
    def initTvDB(api_key, acount_pin):
        if Serie.tvdb:
            del Serie.tvdb
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
                    return self._getTVDBInfoSerie(name)
                elif "US" in name:
                    return self._getTVDBInfoSerie(name.replace("US", ""))

            for serie in Serie.seriesList:
                if serie == int(serieFountTvdb["tvdb_id"]):
                    return serie

            newSerie = Serie(serieFountTvdb["name"], int(serieFountTvdb["tvdb_id"]), serieFountTvdb)
            Serie.seriesList.append(newSerie)

            return newSerie
        else:
            return None

    @staticmethod
    def findSerieById(id, year=None):

        for serie in Serie.seriesList:
            if serie == id:
                return serie

        if Serie.tvdb:
            serieFountTvdb = Serie.tvdb.get_series(id)

            newSerie = Serie(serieFountTvdb["name"], int(serieFountTvdb["tvdb_id"]), serieFountTvdb)
            Serie.seriesList.append(newSerie)

            return newSerie
        else:
            return None


    def __init__(self, name, id, tvdb_info):
        print(f"New Serie : {name} ({id})")
        print(type(name), type(id))
        self.name      = name
        self.id        = id
        self.tvdb_info = tvdb_info

    def __eq__(self, other):
        print(f"{self.name} (type={type(self.name)}) == {other} (type={type(other)})")

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

    def getNormalizedName(self, no_space=False, add_year=True, add_tvdbid=True):

        name_normalized = unidecode.unidecode(self.name)
        name_normalized = string.capwords(name_normalized)

        if add_year:
            name_normalized = re.sub(r"\s*\(\d{4}\)\s*$", "", name_normalized)

        if no_space:

            name_normalized = re.sub("\s*-\s*", "-", name_normalized)
            name_normalized = re.sub("\s+", "_", name_normalized)
            name_normalized = re.sub("(?=\W)[^-]", "", name_normalized)

            if add_year:
                name_normalized = "{}.{}".format(name_normalized, self.tvdb_info["year"])

            if add_tvdbid:
                name_normalized = "{}.tvdbid-{}".format(name_normalized, self.tvdb_info["tvdb_id"])

        else:
            if add_year:
                name_normalized = "{} ({})".format(name_normalized, self.tvdb_info["year"])

            if add_tvdbid:
                name_normalized = "{} [tvdbid-{}]".format(name_normalized, self.tvdb_info["tvdb_id"])

        print("name='{}' name_normalized='{}'".format(self.name, name_normalized))
