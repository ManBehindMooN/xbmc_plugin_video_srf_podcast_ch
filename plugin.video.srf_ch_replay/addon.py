#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import json
import urllib.request
import urllib.parse
import socket
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import traceback
from io import StringIO
import gzip
from urllib.parse import urlparse
from string import ascii_lowercase

addon = xbmcaddon.Addon()
#addonID = 'plugin.video.srf_ch_replay'
pluginhandle = int(sys.argv[1])
socket.setdefaulttimeout(30)
xbmcplugin.setPluginCategory(pluginhandle, "News")
xbmcplugin.setContent(pluginhandle, "tvshows")
numberOfEpisodesPerPage = str(addon.getSetting("numberOfShowsPerPage"))
tr = addon.getLocalizedString

def list_all_tv_shows(letter):
    """
    this method list all available TV shows
    """
    url = 'https://il.srgssr.ch/integrationlayer/2.0/srf/showList/tv/alphabetical?vector=portalplay&pageSize=unlimited&onlyActiveShows=false'
    response = json.load(_open_srf_url(url))
    shows = response["showList"]
    title = ''
    desc = ''
    picture = ''
    mode = 'listEpisodes'
    for show in shows:
        try:
            title = show['title']
        except:
            title = tr(30007)
        try:
            desc = show['description']
        except:
            desc = tr(30008)
        try:
            picture = show['imageUrl']
        except:
            picture = ''

        firstTitleLetter = title[:1]
        if (firstTitleLetter.lower() == letter) or (not firstTitleLetter.isalpha() and not str(letter).isalpha()):
            _add_show(title, show['id'], mode, desc, picture)

    xbmcplugin.addSortMethod(pluginhandle, 1)
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def _add_show(name, url, mode, desc, iconimage):
    """
    helper method to create a folder with subitems
    """
    directoryurl = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode) + "&showbackground=" + urllib.parse.quote_plus(iconimage)
    liz = xbmcgui.ListItem(name)
    liz.setLabel2(desc)
    liz.setArt({'poster': iconimage, 'banner': iconimage, 'fanart': iconimage, 'thumb': iconimage})
    liz.setInfo(type="Video", infoLabels={"title": name, "plot": desc, "plotoutline": desc})
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
    return ok


def list_all_episodes(showid, showbackground, nextPageUrl):
    """
    this method list all episodes of the selected show
    """

    response = ''
    if nextPageUrl == '':
        url = 'https://il.srgssr.ch/integrationlayer/2.0/srf/mediaList/video/latest/byShow/' + showid + '.json?pageSize=' + str(numberOfEpisodesPerPage)
        response = json.load(_open_srf_url(url))
    else:
        response = json.load(_open_srf_url(nextPageUrl))

    show = response["mediaList"]

    for episode in show:
        title = episode['title']
        urn = ''
        desc = ''
        picture = ''
        pubdate = episode['episode']['publishedDate']

        try:
            desc = episode['episode']['description']
        except:
            desc = tr(30008)
        try:
            picture = episode['imageUrl']
        except:
            # no picture
            picture = ''
        try:
            length = int(episode['duration']) / 1000 / 60
        except:
            length = 0
        try:
            urn = episode['urn']
        except:
            urn = tr(30009)
        try:
            titleextended = ' - ' + episode['lead']
        except:
            titleextended = ''

        _addLink(title + titleextended, urn, 'playepisode', desc, picture, length, pubdate, showbackground)

    # check if another page is available
    try:
        _addnextpage(tr(30005), showid, 'listEpisodes', showbackground, response["next"])
    finally:
        xbmcplugin.endOfDirectory(pluginhandle)


def _addLink(name, url, mode, desc, iconurl, length, pubdate, showbackground):
    """
    helper method to create an item in the list
    """
    linkurl = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode)
    liz = xbmcgui.ListItem(name)
    liz.setLabel2(desc)
    liz.setArt({'poster': iconurl, 'banner': iconurl, 'fanart': showbackground, 'thumb': iconurl})
    liz.setInfo(type='Video', infoLabels={"Title": name, "Duration": length, "Plot": desc, "Aired": pubdate})
    liz.setProperty('IsPlayable', 'true')
    xbmcplugin.setContent(pluginhandle, 'episodes')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=linkurl, listitem=liz)
    return ok


def _addnextpage(name, url, mode, showbackground, nextPageUrl):
    """
    helper method to create a folder with subitems
    """
    directoryurl = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode) + "&showbackground=" + urllib.parse.quote_plus(showbackground) + "&nextPage=" + urllib.parse.quote_plus(nextPageUrl)
    liz = xbmcgui.ListItem(name)
    liz.setInfo(type="Video", infoLabels={"title": name})
    xbmcplugin.setContent(pluginhandle, 'episodes')
    ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
    return ok


def playepisode(urn):
    """
    this method plays the selected episode
    """

    besturl = _parse_integrationplayer_2(urn)

    # add authentication token for akamaihd
    if "akamaihd" in urlparse(besturl).netloc:
        url = "http://tp.srgssr.ch/akahd/token?acl=" + urlparse(besturl).path
        response = json.load(_open_srf_url(url))
        token = response["token"]["authparams"]
        besturl = besturl + '?' + token

    listitem = xbmcgui.ListItem(path=besturl)
    xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)


def _parse_integrationplayer_2(urn):
    integrationlayerUrl = f'https://il.srgssr.ch/integrationlayer/2.0/mediaComposition/byUrn/{urn}.json'
    response = json.load(_open_srf_url(integrationlayerUrl))

    resourceList = response['chapterList'][0]['resourceList']
    sdHlsUrls = []
    for play in resourceList:
        if play['protocol'] == 'HLS':
            if play['quality'] == 'HD':
                return _remove_params(play['url'])
            else:
                sdHlsUrls.append(play)

    if not sdHlsUrls:
        return _remove_params(resourceList[0]['url'])
    else:
        return _remove_params(sdHlsUrls[0]['url'])


def _remove_params(url):
    parsed = urlparse(url)
    return f'{parsed.scheme}://{parsed.netloc}{parsed.path}'


def _open_srf_url(urlstring):
    request = urllib.request.Request(urlstring)
    request.add_header('Accept-encoding', 'gzip')
    response = ''
    try:
        response = urllib.request.urlopen(urlstring)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(response.read())
            f = gzip.GzipFile(fileobj=buf)
            response = StringIO(f.read())
    except Exception as e:
        xbmc.log(traceback.format_exc())
        xbmcgui.Dialog().ok(tr(30006), str(e))
    return response


def choose_tv_show_letter():
    nextMode = 'listTvShows'
    _add_letter('#', tr(30019), nextMode)
    for c in ascii_lowercase:
        _add_letter(c, c, nextMode)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def _add_letter(letter, letterDescription, mode):
    directoryurl = sys.argv[0] + "?mode=" + str(mode) + "&letter=" + letter
    liz = xbmcgui.ListItem(letterDescription)
    return xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)


def _parameters_string_to_dict(parameters):
    """
    helper method to retrieve parameters in a dict from the arguments given to this plugin by xbmc
    """
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict


#'Start'
params = _parameters_string_to_dict(sys.argv[2])
mode = params.get('mode', '')
url = params.get('url', '')
showbackground = urllib.parse.unquote_plus(params.get('showbackground', ''))
nextPage = urllib.parse.unquote_plus(params.get('nextPage', ''))
letter = params.get('letter', '')

if mode == 'playepisode':
    playepisode(url)
elif mode == 'listEpisodes':
    list_all_episodes(url, showbackground, nextPage)
elif mode == 'listTvShows':
    list_all_tv_shows(letter)
else:
    choose_tv_show_letter()