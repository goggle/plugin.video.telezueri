# -*- coding: utf-8 -*-

# Copyright (C) 2018 Alexander Seiler
#
#
# This file is part of plugin.video.telezueri.
#
# plugin.video.telezueri is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# plugin.video.telezueri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with plugin.video.telezueri.
# If not, see <http://www.gnu.org/licenses/>.

import sys
import traceback

import json
import socket
import urllib
import urlparse

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import requests

# import dateutil.parser
from youtube_dl import YoutubeDL
import YDStreamExtractor

try:
    CompatStr = unicode  # Python2
except NameError:
    CompatStr = str  # Python3


def get_boolean_setting(label):
    """
    Retrieve the boolean value of a setting switch.

    Keyword arguments:
    label -- the settings label
    """
    return REAL_SETTINGS.getSetting(label) == 'true'


ADDON_ID = 'plugin.video.telezueri'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON = REAL_SETTINGS.getAddonInfo('icon')
FANART = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE = REAL_SETTINGS.getLocalizedString
PROFILE = xbmc.translatePath(
    REAL_SETTINGS.getAddonInfo('profile')).decode("utf-8")

TIMEOUT = 30
CONTENT_TYPE = 'videos'
DEBUG = get_boolean_setting('Enable_Debugging')
NUMBER_OF_EPISODES = 20


socket.setdefaulttimeout(TIMEOUT)


# General helper functions:

def log(msg, level=xbmc.LOGDEBUG):
    """
    Logs a message using Kodi's logging interface.

    Keyword arguments:
    msg   -- the message to log
    level -- the logging level
    """
    if isinstance(msg, str):
        msg = msg.decode('utf-8')
    if DEBUG:
        if level == xbmc.LOGERROR:
            msg += ' ,' + traceback.format_exc()
    message = ADDON_ID + '-' + ADDON_VERSION + '-' + msg
    xbmc.log(msg=message.encode('utf-8'), level=level)


def get_params():
    return dict(urlparse.parse_qsl(sys.argv[2][1:]))


class Telezueri(object):
    def __init__(self):
        log('__init__')
        self.ydl = YoutubeDL()

        self.PARTNER_ID = '1719221'
        self.HOST = 'telezueri.ch'
        self.HOST_URL = 'https://www.%s' % self.HOST
        name, dom = self.HOST.split('.')
        self.API_URL = '%s/api/pub/gql/%s' % (self.HOST_URL, name)

    @staticmethod
    def build_url(mode=None, name=None, group=None, kaltura_id=None):
        """Build a URL for this Kodi plugin.

        Keyword arguments:
        mode       -- an integer representing the mode
        name       -- a string containing some information, e.g. a video id
        group      -- a string for the group name
        kaltura_id -- a string containing the Kaltura video id.
        """
        if mode:
            mode = str(mode)
        added = False
        queries = (mode, name, group, kaltura_id)
        query_names = ('mode', 'name', 'group', 'kaltura_id')
        purl = sys.argv[0]
        for query, qname in zip(queries, query_names):
            if query:
                add = '?' if not added else '&'
                purl += '%s%s=%s' % (add, qname, urllib.quote_plus(query))
                added = True
        return purl

    def build_main_menu(self):
        """
        Builds the main menu of the plugin:

        All shows
        Newest shows
        Live TV
        """
        log('build_main_menu')
        main_menu_list = [
            {
                # All shows
                'name': LANGUAGE(30050),
                'mode': 10,
                'isFolder': True,
                'displayItem': True,
            }, {
                # Newest shows
                'name': 'News',  # TODO: LANGUAGE
                'mode': 11,
                'isFolder': True,
                'displayItem': True,
            }, {
                # Live TV
                'name': 'Categories',  # TODO: LANGUAGE
                'mode': 12,
                'isFolder': True,
                'displayItem': True,
            },
        ]
        for menu_item in main_menu_list:
            if menu_item['displayItem']:
                list_item = xbmcgui.ListItem(menu_item['name'])
                list_item.setProperty('IsPlayable', 'false')
                list_item.setArt({'thumb': ICON})
                purl = self.build_url(
                    mode=menu_item['mode'], name=menu_item['name'])
                xbmcplugin.addDirectoryItem(
                    handle=int(sys.argv[1]), url=purl,
                    listitem=list_item, isFolder=menu_item['isFolder'])

    def build_categories_menu(self):
        category_list = [
            {
                'display_name': 'Most viewed',  # TODO: LANGUAGE
                'group_name': 'am-meisten-gesehen',
                'relative_url': None,
            }, {
                'display_name': 'Viral',  # TODO: LANGUAGE
                'group_name': 'viral',
                'relative_url': None,
            }, {
                'display_name': 'Entertainment',  # TODO: LANGUAGE
                'group_name': 'unterhaltung',
                'relative_url': None,
            }, {
                'display_name': 'Sport',
                'group_name': 'sport',
                'relative_url': '/sport',
            }, {
                'display_name': 'News',
                'group_name': 'news',
                'relative_url': '/news',
            }]
        # The group 'Series' do not contain videos, but only links to shows,
        # so there is currently no need to add them to the list. They would
        # have the following category_list layout:
        # {
        #     'display_name': 'Series',
        #     'group_name': 'serien',
        #     'relative_url': None
        # }

        for cat_item in category_list:
            list_item = xbmcgui.ListItem(cat_item['display_name'])
            list_item.setProperty('IsPlayable', 'false')
            list_item.setArt({'thumb': ICON})
            if cat_item['relative_url']:
                url = self.build_url(
                    mode=20, name=cat_item['relative_url'])
            else:
                url = self.build_url(
                    mode=20, name='/videos', group=cat_item['group_name'])
            xbmcplugin.addDirectoryItem(
                    handle=int(sys.argv[1]), url=url,
                    listitem=list_item, isFolder=True)

    def build_all_shows_menu(self):
        """
        Builds a list of folders containing the names of all the current
        shows.
        """
        log('build_all_shows_menu')
        query = """query PageForUrl($url: String!) {
              pageForUrl(url: $url) {
                page {
                  name
                  slots {
                    context {
                      ... on Article {
                        lead
                        title
                        teaserImage {
                          imageUrl
                        }
                        headRessort {
                          relativeUrl
                        }
                      }
                    }
                  }
                }
              }
            }"""
        payload = {
            'operationName': 'PageForUrl',
            'query': query,
            'variables': {'url': '/sendungen'}
        }
        headers = {'Content-Type': 'application/json'}
        r = requests.post(
            self.API_URL, data=json.dumps(payload).encode(), headers=headers)
        if not r.ok:
            log('build_all_shows_menu: Request failed.', level=xbmc.LOGERROR)
        js = r.json()
        shows = []
        for show_entry in js['data']['pageForUrl']['page']['slots']:
            context = show_entry['context']
            if context:
                show = {
                    'title': context['title'],
                    'lead': context['lead'],
                    'description': context.get('text'),
                    'image': context['teaserImage']['imageUrl'],
                    'relative_url': context['headRessort']['relativeUrl'],
                }
                shows.append(show)

        list_items = []
        for show in shows:
            list_item = xbmcgui.ListItem(label=show['title'])
            list_item.setProperty('IsPlayable', 'false')
            list_item.setArt({
                'thumb': show['image'],
                'poster': show['image'],
            })
            surl = self.build_url(mode=20, name=show['relative_url'])
            list_items.append((surl, list_item, True))
        xbmcplugin.addDirectoryItems(
            int(sys.argv[1]), list_items, totalItems=len(list_items))

    def build_show_menu(self, variable, playlist=False, select_group=None):
        """
        Builds a list of videos for a show given by its show URL.

        Keyword arguments:
        variable     -- Either a relative URL of a show or a article id
        playlist     -- If true, interpret variable as a playlist, i.e.
                        variable is a article id.
        """
        if not playlist:
            shows = self.extract_show_info(variable, select_group=select_group)
        else:
            shows = self.extract_playlist(variable)
        for show in shows:
            list_item = xbmcgui.ListItem(label=show['title'])
            list_item.setProperty('IsPlayable', 'true')
            list_item.setArt({
                'thumb': show['image'],
                'poster': show['image'],
                'fanart': show['fanart'],
            })

            # We currently do not add dates to the show, because they
            # are wrong on the server.
            # date_string = show['date']
            # try:
            #     date_obj = dateutil.parser.parse(date_string)
            #     aired = "%s-%s-%s" % (str(date_obj.year),
            #                           str(date_obj.month).zfill(2),
            #                           str(date_obj.day).zfill(2))
            # except (TypeError, ValueError):
            #     aired = None

            list_item.setInfo('video', {
                # We do not set the date currently, because the given date
                # by the server is not correct.
                # 'aired': aired,
                'plot': show['lead'],
                'duration': show['duration'],
            })
            if show['is_folder']:
                url = self.build_url(mode=21, name=show['id'])
            else:
                url = self.build_url(
                    mode=50, name=show['title'].encode('utf-8'),
                    kaltura_id=show['kaltura_id'])  # TODO: better URL layout
            xbmcplugin.addDirectoryItem(
                int(sys.argv[1]), url, list_item, isFolder=show['is_folder'])

    def extract_playlist(self, article_id, fanart=None):
        query = """query VideoContext($articleId: ID!) {
            article: node(id: $articleId) {
              ... on Article {
                id
                title
                mainAssetRelation {
                  title
                  teaserImage {
                    imageUrl
                  }
                  asset {
                    ... on VideoAsset {
                      kalturaId
                      kalturaMeta {
                        tags
                        categories
                        duration
                      }
                      keywords
                    }
                  }
                }
              }
            }
            segments: nextPlayableArticles(articleId: $articleId) {
              data {
                id
                title
                relativeUrl
                mainAssetRelation {
                  title
                  teaserImage {
                    imageUrl
                  }
                  asset {
                    ... on VideoAsset {
                      kalturaId
                      kalturaMeta {
                        tags
                        categories
                        duration
                      }
                      keywords
                    }
                  }
                }
              }
              total
            }
          }"""
        payload = {
            'operationName': 'VideoContext',
            'query': query,
            'variables': {'articleId': article_id}
        }
        headers = {'Content-Type': 'application/json'}
        r = requests.post(
            self.API_URL, data=json.dumps(payload).encode(), headers=headers)
        if not r.ok:
            log('extract_playlist: Request failed for %s.' %
                article_id, level=xbmc.LOGERROR)
        js = r.json()
        videos = []
        segments = js['data']['segments']['data']
        for seg in segments:
            title = seg['title']
            mar = seg['mainAssetRelation']
            kaltura_id = mar['asset']['kalturaId']
            duration = mar['asset']['kalturaMeta']['duration']
            image = mar['teaserImage']['imageUrl']
            aid = seg['id']

            videos.append({
                'title': title,
                'lead': None,
                'image': image,
                'date': None,
                'duration': duration,
                'kaltura_id': kaltura_id,
                'fanart': fanart,
                'is_folder': False,
                'relative_url': None,
                'id': aid,
            })
        return videos

    def extract_show_info(self, relative_url, select_group=None):
        """
        Keyword arguments:
        select_group -- A group identifier. If this is set, only those
                        videos having this group tag will be extracted.
        """
        query = """query PageForUrl($url: String!) {
          pageForUrl(url: $url) {
            page {
              name
              slots {
                index
                group
                context {
                  __typename
                  ... on Article {
                    id
                    contextLabel
                    contentType
                    labeltype
                    lead
                    title
                    relativeUrl
                    dc {
                      effective
                    }
                    teaserImage {
                      imageUrl
                    }
                    mainAssetRelation {
                      teaserImage {
                        imageUrl
                      }
                      asset {
                        ... on VideoAsset {
                          kalturaId
                          kalturaMeta { duration }
                        }
                      }
                    }
                  }
                }
              }
            }
            context {
              ... on Ressort {
                id
                title
                keywords
                header {
                  title
                  lead
                  text
                  assets {
                    usage
                    imageUrl
                  }
                }
              }
            }
          }
        }"""
        payload = {
            'operationName': 'PageForUrl',
            'query': query,
            'variables': {'url': relative_url}
        }
        headers = {'Content-Type': 'application/json'}
        r = requests.post(
            self.API_URL, data=json.dumps(payload).encode(), headers=headers)
        if not r.ok:
            log('build_show_menu: Request failed for %s.' % relative_url,
                level=xbmc.LOGERROR)
        js = r.json()

        shows = []
        try:
            items = js['data']['pageForUrl']['context']['header']['assets']
            for elem in items:
                if elem['usage'] == 'teaser':
                    fanart = elem['imageUrl']
        except Exception:
            fanart = None
            log('extract_show_info: No fanart for show %s.' % relative_url)
        for (i, item) in enumerate(js['data']['pageForUrl']['page']['slots']):
            if select_group:
                if not item.get('group') == select_group:
                    continue

            try:
                title = item['context']['title']
                aid = item['context']['id']
            except Exception:
                log('Could not extract title or id for element %d in show %s' %
                    (i, relative_url))
                continue

            try:
                label_type = item['context']['labeltype']
                show_relative_url = item['context']['relativeUrl']
                if label_type == 'playlist' and show_relative_url:
                    is_folder = True
                else:
                    is_folder = False
            except Exception:
                label_type = ''
                show_relative_url = ''
                is_folder = False
                log(('extract_show_info: Could not extract labeltype or '
                    'RelativeUrl for element %d in show %s')
                    % (i, relative_url))

            try:
                asset = item['context']['mainAssetRelation']['asset']
                kaltura_id = asset['kalturaId']
                duration = asset['kalturaMeta']['duration']
            except Exception:
                kaltura_id = None
                duration = None
                log(('extract_show_info: Could not extract title or Kaltura '
                    'ID for element %d in show %s') % (i, relative_url))
                if not is_folder:
                    continue

            try:
                lead = item['context']['lead']
            except Exception:
                lead = None
                log('extract_show_info: No lead for %s' %
                    item['context']['id'])
            try:
                image = item['context']['teaserImage']['imageUrl']
            except Exception:
                image = None
                log('extract_show_info: No image for %s' %
                    item['context']['id'])
            try:
                date = item['context']['dc']['effective']
            except Exception:
                date = None
                log('extract_show_info: No date for %s' %
                    item['context']['id'])

            shows.append({
                'title': title,
                'id': aid,
                'lead': lead,
                'image': image,
                'date': date,
                'duration': duration,
                'kaltura_id': kaltura_id,
                'fanart': fanart,
                'is_folder': is_folder,
                'relative_url': show_relative_url,
            })
        return shows

    def build_live_menu(self):
        """
        Builds the live TV menu.
        """
        log('build_live_menu')
        list_item = xbmcgui.ListItem(label=LANGUAGE(30074))
        list_item.setProperty('IsPlayable', 'true')
        list_item.setArt({
            'thumb': ICON,
        })
        url = self.build_url(mode=51)
        xbmcplugin.addDirectoryItem(
            int(sys.argv[1]), url, list_item, isFolder=False)

    def play_video(self, name, kaltura_id):
        """
        Plays a video.

        Keyword arguments:
        kaltura_id  -- the Kaltura id of the video
        """
        log('play_video, kaltura_id=%s' % kaltura_id)
        # play_item = xbmcgui.ListItem('Telezüri Video', path=None)
        # xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, play_item)
        self.ydl.add_default_info_extractors()
        ytdl_url = 'kaltura:%s:%s' % (self.PARTNER_ID, kaltura_id)
        log('play_video, ytdl_url=%s' % ytdl_url)
        vid = YDStreamExtractor.getVideoInfo(ytdl_url, quality=2)
        stream_url = vid.streamURL()
        liz = xbmcgui.ListItem(name, path=stream_url)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)


def run():
    """
    Run the plugin.
    """
    params = get_params()
    try:
        url = urllib.unquote_plus(params['url'])
    except Exception:
        url = None
    try:
        name = urllib.unquote_plus(params['name'])
    except Exception:
        name = None
    try:
        mode = int(params['mode'])
    except Exception:
        mode = None
    try:
        group = urllib.unquote_plus(params['group'])
    except Exception:
        group = None
    try:
        kaltura_id = urllib.unquote_plus(params['kaltura_id'])
    except Exception:
        kaltura_id = None

    log('Mode: ' + str(mode))
    log('URL : ' + str(url))
    log('Name: ' + str(name))
    log('Group: ' + str(group))
    log('Kaltura ID: ' + str(kaltura_id))

    if mode is None:
        Telezueri().build_main_menu()
    elif mode == 10:
        Telezueri().build_all_shows_menu()
    elif mode == 11:
        Telezueri().build_show_menu('/news')
    elif mode == 12:
        Telezueri().build_categories_menu()
    elif mode == 20:
        Telezueri().build_show_menu(name, select_group=group)
    elif mode == 21:
        Telezueri().build_show_menu(name, playlist=True)
    elif mode == 50:
        Telezueri().play_video(name, kaltura_id)

    xbmcplugin.setContent(int(sys.argv[1]), CONTENT_TYPE)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)
    xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
