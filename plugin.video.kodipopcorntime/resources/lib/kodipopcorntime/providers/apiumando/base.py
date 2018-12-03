import json
import os
import sys
import urllib2

import xbmc

from kodipopcorntime import settings
from kodipopcorntime.exceptions import Abort
from kodipopcorntime.providers.movies import metadata_tmdb
from kodipopcorntime.settings import addon as _settings


__addon__ = sys.modules['__main__'].__addon__


class BaseContent(object):
    @classmethod
    def _create_item(cls, data):
        if not cls._is_item_valid_for_data(data):
            return {}

        torrents = cls._get_torrents_information(data)
        # Do not show content without torrents
        if not torrents:
            return {}

        return {
            'label': cls._get_item_label(data),
            'icon': cls._get_item_icon(data),
            'thumbnail': cls._get_item_icon(data),
            'info': cls._get_item_info(data),
            'properties': cls._get_item_properties(data),
            'stream_info': cls._get_item_stream_info(torrents),
            'params': torrents,
        }

    @classmethod
    def _get_item_stream_info(cls, torrents):
        # Set video width and hight
        width = 640
        height = 480
        if torrents.get('1080p'):
            width = 1920
            height = 1080
        elif torrents.get('720p'):
            width = 1280
            height = 720

        return {
            'video': {
                'codec': u'h264',
                'duration': int(0),
                'width': width,
                'height': height,
            },
            'audio': {
                'codec': u'aac',
                'language': u'en',
                'channels': 2,
            },
        }


class BaseContentWithSeasons(BaseContent):
    @classmethod
    def get_meta_info(a, result, season):
        info = {
            'mediatype': 'tvshow',
            'title': result['title'],
            'originaltitle': result['title'],
            'year': int(result['year']),
            'rating': result.get('rating'),
            'votes': 1,
            'code': result['imdb'],
            'imdbnumber': result['imdb'],
        }
        if season == 0 and result['imdb'].startswith('tt'):
            try:
                meta = metadata_tmdb._get_info(result['imdb'], 0)
                castandrole = []
                for c in meta['credits'].get("cast", []):
                    castandrole.append((c["name"], c.get("character", '')))
                info = {
                    'mediatype': 'tvshow',
                    'title': meta['name'],
                    'originaltitle': meta['original_name'],
                    'year': int(result['year']),
                    'rating': float(meta['vote_average']),
                    'votes': meta['vote_count'],
                    'status': meta['status'],
                    'country': meta['origin_country'][0],
                    'code': result['imdb'],
                    'imdbnumber': result['imdb'],
                    'plot': meta['overview'],
                    'plotoutline': meta['overview'],
                    'castandrole': castandrole,
                }
            except:
                pass
        if not season == 0 and result['imdb'].startswith('tt'):
            try:
                meta = metadata_tmdb._get_info(result['imdb'], season)
                castandrole = []
                for c in meta['credits'].get("cast", []):
                    castandrole.append((c["name"], c.get("character", '')))
                info = {
                    "mediatype": "season",
                    "title": result['title'],
                    "tvshowtitle": result['title'],
                    'season': season,
                    'status': result['status'],
                    'code': result['imdb'],
                    'imdbnumber': result['imdb'],
                    "plotoutline": meta['overview'] or None,
                    "plot": meta['overview'] or None,
                    'castandrole': castandrole,
                }
            except:
                info = {
                    "mediatype": "season",
                    "title": result['title'],
                    "tvshowtitle": result['title'],
                    "plotoutline": result['description'] or None,
                    "plot": result['description'] or None
                }
        else:
            try:
                meta = metadata_tmdb._get_anime_info(result['_id'])
                info = {
                    'mediatype': 'tvshow',
                    'title': meta['attributes']['titles']['en'],
                    'originaltitle': meta['attributes']['titles']['ja_jp'],
                    'year': int(result['year']),
                    'rating': float(int(result.get('rating').get('percentage'))/10),
                    'votes': result.get('rating').get('votes'),
                    'code': result['_id'],
                    'plot':  meta['attributes']['synopsis'],
                    'plotoutline': meta['attributes']['synopsis'],
                }
            except:
                pass
        return info

    @classmethod
    def get_shows(cls, dom, **kwargs):
        if kwargs['search'] == 'true':
            search_string = xbmc.getInfoLabel("ListItem.Property(searchString)")
            if not search_string:
                keyboard = xbmc.Keyboard('', __addon__.getLocalizedString(30001), False)
                keyboard.doModal()
                if not keyboard.isConfirmed() or not keyboard.getText():
                    raise Abort()
                search_string = keyboard.getText()
                search_string = search_string.replace(' ', '+')
            search = '{domain}/{search_path}?page=1&keywords={keywords}'.format(
                domain=dom[0],
                search_path=cls.search_path,
                keywords=search_string,
            )
        else:
            search = '{domain}/{search_path}?page={page}?genre={genre}&sort={sort}'.format(
                domain=dom[0],
                search_path=cls.search_path,
                page=kwargs['page'],
                genre=kwargs['genre'],
                sort=kwargs['act'],
            )

        req = urllib2.Request(
            search,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.66 Safari/537.36",
                "Accept-Encoding": "none",
            },
        )
        response = urllib2.urlopen(req)
        results = json.loads(response.read())

        items = [
            {
                "label": result['title'],  # "label" is required
                "icon": result.get('poster_med'),
                "thumbnail": result.get('poster_med'),
                "info": cls.get_meta_info(result, 0),
                "properties": {
                    "fanart_image": result.get('poster_big'),
                },
                "params": {
                    "endpoint": "folders",  # "endpoint" is required
                    'action': "{category}-seasons".format(category=cls.category),  # Required when calling browse or folders (Action is used to separate the content)
                    cls.id_field: result[cls.id_field],
                    'poster': result.get('poster_med'),
                    'fanart': result.get('poster_med'),
                    'tvshow': result['title']
                },
                "context_menu": [
                    (
                        '%s' % __addon__.getLocalizedString(30039),
                        'RunPlugin(plugin://plugin.video.kodipopcorntime?cmd=add_fav&action={action}&id={id})'.format(
                            action=cls.action,
                            id=result[cls.id_field],
                        ),
                    )
                ],
                "replace_context_menu": True
            }
            for result in results['MovieList']
        ]

        # Next Page
        items.append({
            "label": 'Show more',  # "label" is required
            "icon": os.path.join(settings.addon.resources_path, 'media', 'movies', 'more.png'),
            "thumbnail": os.path.join(settings.addon.resources_path, 'media', 'movies', 'more_thumbnail.png'),
            "params": {
                "endpoint": "folders",  # "endpoint" is required
                'action': "{category}-list".format(category=cls.category),  # Required when calling browse or folders (Action is used to separate the content)
                'act': kwargs['act'],
                'genre': kwargs['genre'],
                'search': kwargs['search'],
                'page': int(kwargs['page']) + 1,
            },
        })

        return items

    @classmethod
    def get_seasons(cls, dom, **kwargs):
        req = urllib2.Request(
            '{domain}/{request_path}?imdb={content_id}'.format(
                domain=dom[0],
                request_path=cls.request_path,
                content_id=kwargs[cls.id_field]
            ),
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.66 Safari/537.36",
                "Accept-Encoding": "none",
            },
        )

        response = urllib2.urlopen(req)
        result = json.loads(response.read())
        seasons = result

        season_list = sorted(list(set(
            season
            for season, result in seasons
        )))

        return [
            {
                "label": 'Season %s' % season,  # "label" is required
                "icon": kwargs['poster'],
                "thumbnail": kwargs['poster'],
                "info": cls.get_meta_info(result, season),
                "properties": {
                    "fanart_image": kwargs['fanart']
                },
                "params": {
                    'categ': cls.category,  # "categ" is required when using browse as an endpoint
                    'seasons': season,
                    'image': kwargs['poster'],
                    'image2': kwargs['fanart'],
                    'tvshow': kwargs['tvshow'],
                    "status": result['status'],
                    "runtime": result['runtime'],
                    "country": country,
                    "endpoint": "browse",  # "endpoint" is required
                    'action': kwargs[cls.id_field]  # Required when calling browse or folders (Action is used to separate the content)
                }
            }
            for season in season_list
        ]

    @staticmethod
    def _is_item_valid_for_data(data):
        # seasondata0 has all the data from show
        seasondata0 = int(data[0]['season'])
        # seasondata_1 carries additional user data not included in show data
        seasondata_1 = int(data[-1]['seasons'])

        return (seasondata0 == seasondata_1)

    @staticmethod
    def _get_item_icon(data):
        return data[-1]['image']

    @staticmethod
    def _get_item_label(data):
        return 'Episode {number}: {title}'.format(
            number=data[0]['episode'],
            title=data[0]['title'],
        )

    @staticmethod
    def _get_item_properties(data):
        return {
            'fanart_image': data[-1]['image2'],
            'tvshowthumb': data[-1]['image2'],
        }

    @staticmethod
    def _get_torrents_information(data):
        torrents = {}
        for quality, torrent_info in data[0].get('torrents', {}).items():
            torrent_url = torrent_info.get('url')
            if quality in settings.QUALITIES and torrent_url is not None:
                torrents.update({
                    quality: torrent_url,
                    '{0}size'.format(quality): 1000000000*60,
                })
        return torrents
