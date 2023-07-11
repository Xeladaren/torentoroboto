#!/usr/bin/python3

import argparse
import argcomplete
import configparser
import time

import ParseSeries
import TorrentAdd
import Print
import Notifs

config      = None
torrentAdd  = TorrentAdd.TorrentAdd()
parseSeries = ParseSeries.ParseSeries()

def startOneRun():

    # Find new files

    torrentAdd.readFeeds()
    torrentAdd.waitDownloadTorrents()

    # Parce download serie dir.

    parseSeries.scanAll()

def setConfigs():

    # Set Notifs configs

    if "discord" in config and "WebhookURL" in config["discord"]:
        Notifs.discord_webhook_url = config["discord"]["WebhookURL"]

    # Set config for Torrent Add

    if "log" in config and "RSSReadedPost" in config["log"]:
        torrentAdd.log_rss = config["log"]["RSSReadedPost"]

    if "torrent" in config and "SeriesRSS" in config["torrent"]:
        torrentAdd.rss_url = config["torrent"]["SeriesRSS"]

    if "torrent" in config and "SeriesTags" in config["torrent"]:
        torrentAdd.series_tags = config["torrent"]["SeriesTags"].split(" ")

    if "transmissiom" in config and "SeriesDir" in config["transmissiom"]:
        torrentAdd.trans_dl_dir = config["transmissiom"]["SeriesDir"]

    if "discord" in config and "WebhookURL" in config["discord"]:
        torrentAdd.discord_webhook = config["discord"]["WebhookURL"]

    if "series" in config and "OutputDir" in config["series"]:
        torrentAdd.series_dir      = config["series"]["OutputDir"]

    if "transmissiom" in config and "Host" in config["transmissiom"]:
        if "User" in config["transmissiom"] and "Pass" in config["transmissiom"] :
            torrentAdd.initTransmission(config["transmissiom"]["Host"], config["transmissiom"]["User"], config["transmissiom"]["Pass"])

    if "tvdb" in config and "EnableSearch" in config["tvdb"] and config["tvdb"]["EnableSearch"] == "yes" :
        if "ApiKey" in config["tvdb"] and "ApiPIN" in config["tvdb"]:
                torrentAdd.initTvDB(config["tvdb"]["ApiKey"], config["tvdb"]["ApiPIN"])

    # Set config for ParseSeries

    if "discord" in config and "WebhookURL" in config["discord"]:
        parseSeries.discord_webhook = config["discord"]["WebhookURL"]

    if "jellyfin" in config and "APIKey" in config["jellyfin"]:
        parseSeries.jellyfin_api = config["jellyfin"]["APIKey"]

    if "jellyfin" in config and "ServerURL" in config["jellyfin"]:
        parseSeries.jellyfin_url = config["jellyfin"]["ServerURL"]

    if "log" in config and "DoneFiles" in config["log"]:
        parseSeries.log_file_done   = config["log"]["DoneFiles"]

    if "log" in config and "ErrorFiles" in config["log"]:
        parseSeries.log_file_error  = config["log"]["ErrorFiles"]

    if "series" in config and "SearchDir" in config["series"]:
        parseSeries.scan_dir        = config["series"]["SearchDir"]

    if "series" in config and "OutputDir" in config["series"]:
        parseSeries.output_dir      = config["series"]["OutputDir"]

    if "series" in config and "Action" in config["series"]:
        parseSeries.file_action     = config["series"]["Action"]

    if "tvdb" in config and "EnableSearch" in config["tvdb"] and config["tvdb"]["EnableSearch"] == "yes" :
        if "ApiKey" in config["tvdb"] and "ApiPIN" in config["tvdb"]:
                parseSeries.initTvDB(config["tvdb"]["ApiKey"], config["tvdb"]["ApiPIN"])

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=argparse.FileType('r', encoding='utf-8'), help="Get the dir to parce")
    parser.add_argument("--verbose", action='store_true', help="Set the Print verbose mode")
    parser.add_argument("--verbose-discord", action='store_true', help="Set the Discord verbose mode")
    parser.add_argument("--daemon", action='store_true', help="Set the tool in Daemon mode (looping run, not stop)")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read_file(args.config)
    args.config.close()

    Print.verbose = args.verbose
    Notifs.verbose = args.verbose_discord

    setConfigs()

    if args.daemon:
        Print.Custom("DAEMON", "Start in Daemon mode", title_color=Print.COLOR_GREEN, always_print=True)

    while True:

        runAll = args.daemon

        Notifs.sendNotif("**Start All**")
        Print.Custom("DAEMON", "Start all", title_color=Print.COLOR_GREEN, always_print=True)

        try:
            startOneRun()
        except Exception as ex:
            Print.Error("Error to run all : {}".format(ex))
            Notifs.sendNotif("**Error to run all**: {}".format(ex), always_print=True)

        Notifs.sendNotif("**End All**")
        Print.Custom("DAEMON", "End all", title_color=Print.COLOR_GREEN, always_print=True)

        if "daemon" in config and "IdleTime" in config["daemon"]:
            idleTime = int(config["daemon"]["IdleTime"])
        else:
            Print.Error("Error no IdleTime, stop".format(ex))
            break

        if args.daemon:

            Print.Custom("DAEMON", "Wait for {} minutes".format(idleTime), title_color=Print.COLOR_GREEN, always_print=True)

            while idleTime > 0:
                time.sleep(60)
                idleTime -= 1
                Print.Custom("DAEMON", "Wait for {} minutes".format(idleTime), title_color=Print.COLOR_GREEN)
        else:
            break
