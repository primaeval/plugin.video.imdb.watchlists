from xbmcswift2 import Plugin
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import re
import HTMLParser
import requests
#import random
from datetime import datetime,timedelta
#import time
import urllib
#import HTMLParser
import xbmcplugin
#import xml.etree.ElementTree as ET
#import sqlite3
import os
#import shutil
#from rpc import RPC
from types import *
import zipfile
import StringIO

import sys
#xbmc.log(repr(sys.argv))

plugin = Plugin()

if plugin.get_setting('english') == 'true':
    headers={'Accept-Language' : 'en',"X-Forwarded-For": "8.8.8.8"}
else:
    headers={}


big_list_view = False

def log(x):
    xbmc.log(repr(x))

def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")

def get_tvdb_id(imdb_id):
    tvdb_url = "http://thetvdb.com//api/GetSeriesByRemoteID.php?imdbid=%s" % imdb_id
    r = requests.get(tvdb_url)
    tvdb_html = r.text
    tvdb_id = ''
    tvdb_match = re.search(r'<seriesid>(.*?)</seriesid>', tvdb_html, flags=(re.DOTALL | re.MULTILINE))
    if tvdb_match:
        tvdb_id = tvdb_match.group(1)
    return tvdb_id

@plugin.route('/rss/<url>/<type>/<export>')
def rss(url,type,export):
    big_list_view = True
    r = requests.get(url, headers=headers)
    html = r.text

    match = re.compile(
        '<link>http://www\.imdb\.com/title/(.*?)/</link>'
        ).findall(html)
    ids = match

    if not ids:
        return
    url = 'http://www.imdb.com/title/data?ids=%s' % ','.join(ids)
    r = requests.get(url, headers=headers)
    html = r.text

    import json
    imdb = json.loads(html)
    imdb_ids = {}
    for imdb_id in imdb:
       imdb_ids[imdb_id] = imdb[imdb_id]['title']

    return list_titles(imdb_ids,type,export)

@plugin.route('/watchlist/<url>/<type>/<export>')
def watchlist(url,type,export):
    big_list_view = True
    r = requests.get(url, headers=headers)
    html = r.text

    match = re.search(r'IMDbReactInitialState\.push\(({.*?})\);',html)
    if match:
        data = match.group(1)
        import json
        imdb = json.loads(data)
        imdb_list = imdb['list']
        imdb_items = imdb_list['items']
        imdb_ids = imdb['titles']
        all = [i['const'] for i in imdb_items]
        got = [i for i in imdb_ids]
        missing = set(all) - set(got)
        if missing:
            ids = list(missing)
            url = 'http://www.imdb.com/title/data?ids=%s' % ','.join(ids)
            r = requests.get(url, headers=headers)
            html = r.text
            imdb = json.loads(html)
            for imdb_id in imdb:
               imdb_ids[imdb_id] = imdb[imdb_id]['title']
        return list_titles(imdb_ids,type,export)

def list_titles(imdb_ids,list_type,export):
    main_context_items = []
    main_context_items.append(('Update Video Library', 'UpdateLibrary(video)'))
    main_context_items.append(('Update TV Shows', 'XBMC.RunPlugin(%s)' % (plugin.url_for('update_tv'))))
    main_context_items.append(('Delete and Clean Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for('nuke'))))

    if export == "True":
        xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
        xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')
    items = []
    for imdb_id in imdb_ids:
        imdb_data = imdb_ids[imdb_id]
        title = '-'
        year = ''
        try:
            primary = imdb_data['primary']
            title = primary['title']
            year = primary['year'][0]
        except:
            pass
        type = ''
        try:
            type = imdb_data['type']
        except:
            pass
        plot = ''
        try:
            plot = imdb_data['plot']
            plot = HTMLParser.HTMLParser().unescape(plot.decode('utf-8'))
        except:
            pass
        cast = []
        try:
            credits = imdb_data['credits']
            director = credits['director']
            cast.append(director[0]['name'])
        except:
            pass
        try:
            credits = imdb_data['credits']
            stars = credits['star']
            for star in stars:
                cast.append(star['name'])
        except:
            pass
        thumbnail = 'DefaultFolder.png'
        try:
            poster = imdb_data['poster']
            thumbnail = poster['url']
        except:
            pass
        rating = ''
        votes = ''
        try:
            ratings = imdb_data['ratings']
            rating = ratings['rating']
            votes = ratings['votes']
        except:
            pass
        genres = []
        certificate = '-'
        runtime = ''
        try:
            metadata = imdb_data['metadata']
            genres = metadata['genres']
            certificate = metadata['certificate']
            runtime = metadata['runtime']
        except:
            pass

        if type == "series": #TODO episode
            meta_url = "plugin://plugin.video.imdb.watchlists/meta_tvdb/%s/%s" % (imdb_id,urllib.quote_plus(title.encode("utf8")))
        elif type == "featureFilm":
            meta_url = 'plugin://plugin.video.meta/movies/play/imdb/%s/library' % imdb_id
        context_items = []
        context_items.append(
        ('Add to Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for('add_to_library', imdb_id=imdb_id, type=type))))
        try:
            if type == 'featureFilm' and xbmcaddon.Addon('plugin.video.couchpotato_manager'):
                context_items.append(
                ('Add to Couch Potato', "XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add-by-id/%s)" % (imdb_id)))
        except:
            pass
        try:
            if type == 'series' and xbmcaddon.Addon('plugin.video.sickrage'):
                context_items.append(
                ('Add to Sickrage', "XBMC.RunPlugin(plugin://plugin.video.sickrage?action=addshow&&show_name=%s)" % (urllib.quote_plus(title.encode("utf8")))))
        except:
            pass
        try:
            if xbmcaddon.Addon('plugin.program.super.favourites'):
                context_items.append(
                ('iSearch', 'ActivateWindow(%d,"plugin://%s/?mode=%d&keyword=%s",return)' % (10025,'plugin.program.super.favourites', 0, urllib.quote_plus(title))))
        except:
            pass

        context_items = context_items + main_context_items
        item = {
            'label': title,
            'path': meta_url,
            'thumbnail': thumbnail,
            'info': {'title': title, 'genre': ','.join(genres),'code': imdb_id,
            'year':year,'rating':rating,'plot': plot,
            'mpaa': certificate,'cast': cast,'duration': runtime, 'votes': votes},
            'context_menu': context_items,
            'replace_context_menu': False,
        }
        if list_type == "tv":
            if type == "series": #TODO episode
                items.append(item)
        elif list_type == "movies":
            if type == "featureFilm":
                items.append(item)
        else:
            items.append(item)

        if export == "True":
            add_to_library(imdb_id, type)

    if export == "True" and plugin.get_setting('update') == 'true':
        xbmc.executebuiltin('UpdateLibrary(video)')

    plugin.add_sort_method(xbmcplugin.SORT_METHOD_UNSORTED)
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_TITLE)
    return items


@plugin.route('/add_to_library/<imdb_id>/<type>')
def add_to_library(imdb_id,type):
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')
    if type == "series":
        try: xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s' % imdb_id)
        except: pass
        update_tv_series(imdb_id)
    else:
        f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/Movies/%s.strm' % (imdb_id), "wb")
        meta_url = 'plugin://plugin.video.meta/movies/play/imdb/%s/library' % imdb_id
        f.write(meta_url.encode("utf8"))
        f.close()
        f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/Movies/%s.nfo' % (imdb_id), "wb")
        str = "http://www.imdb.com/title/%s/" % imdb_id
        f.write(str.encode("utf8"))
        f.close()


@plugin.route('/meta_tvdb/<imdb_id>/<title>')
def meta_tvdb(imdb_id,title):
    tvdb_id = get_tvdb_id(imdb_id)
    meta_url = "plugin://plugin.video.meta/tv/tvdb/%s" % tvdb_id

    item ={'label':title, 'path':meta_url, 'thumbnail': get_icon_path('meta')}
    #TODO launch into Meta seasons view
    return [item]

@plugin.route('/update_tv')
def update_tv():
    root = 'special://profile/addon_data/plugin.video.imdb.watchlists/TV'
    dirs, files = xbmcvfs.listdir(root)
    for imdb_id in dirs:
        update_tv_series(imdb_id)
    xbmc.executebuiltin('UpdateLibrary(video)')

def update_tv_series(imdb_id):
    tvdb_id = get_tvdb_id(imdb_id)
    meta_url = "plugin://plugin.video.meta/tv/tvdb/%s" % tvdb_id
    f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s/tvshow.nfo' % imdb_id,"wb")
    str = "http://thetvdb.com/index.php?tab=series&id=%s" % tvdb_id
    f.write(str.encode("utf8"))
    f.close()
    url = 'http://thetvdb.com/api/77DDC569F4547C45/series/%s/all/en.zip' % tvdb_id
    results = requests.get(url)
    data = results.content
    try:
        zip = zipfile.ZipFile(StringIO.StringIO(data))
        z = zip.open('en.xml')
        xml = z.read()
    except:
        return
    match = re.compile(
        '<Episode>.*?<id>(.*?)</id>.*?<EpisodeNumber>(.*?)</EpisodeNumber>.*?<FirstAired>(.*?)</FirstAired>.*?<SeasonNumber>(.*?)</SeasonNumber>.*?</Episode>',
        flags=(re.DOTALL | re.MULTILINE)
        ).findall(xml)
    for id,episode,aired,season in match:
        if aired:
            match = re.search(r'([0-9]*?)-([0-9]*?)-([0-9]*)',aired)
            if match:
                year = match.group(1)
                month = match.group(2)
                day = match.group(3)
                aired = datetime(year=int(year), month=int(month), day=int(day))
                today = datetime.today()
                if aired <= today:
                    f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s/S%02dE%02d.strm' % (imdb_id,int(season),int(episode)),"wb")
                    str = "plugin://plugin.video.meta/tv/play/%s/%d/%d/library" % (tvdb_id,int(season),int(episode))
                    f.write(str.encode("utf8"))
                    f.close()

@plugin.route('/nuke')
def nuke():
    dialog = xbmcgui.Dialog()
    ok = dialog.ok('Delete Library', 'Are you sure?')
    if not ok:
        return
    for root in ['special://profile/addon_data/plugin.video.imdb.watchlists/TV','special://profile/addon_data/plugin.video.imdb.watchlists/Movies']:
        root_dirs, root_files = xbmcvfs.listdir(root)
        for root_dir in root_dirs:
            dir = root+"/"+root_dir
            dirs, files = xbmcvfs.listdir(dir)
            for file in files:
                xbmcvfs.delete("%s/%s" % (dir,file))
            xbmcvfs.rmdir(dir)
        for file in root_files:
            xbmcvfs.delete("%s/%s" % (root,file))
    xbmc.executebuiltin('CleanLibrary(video)')

@plugin.route('/add_watchlist')
def add_watchlist():
    dialog = xbmcgui.Dialog()
    url = dialog.input('Enter Watchlist Url', type=xbmcgui.INPUT_ALPHANUM)
    if url:
        name = dialog.input('Enter Watchlist Name', type=xbmcgui.INPUT_ALPHANUM)
        if name:
            watchlists = plugin.get_storage('watchlists')
            if url.startswith('ur'):
                url = "http://www.imdb.com/user/%s/watchlist" % url
            watchlists[name] = url

@plugin.route('/remove_watchlist_dialog/')
def remove_watchlist_dialog():
    watchlists = plugin.get_storage('watchlists')
    names = sorted([w for w in watchlists])
    dialog = xbmcgui.Dialog()
    index = dialog.select('Select Watchlist to Remove', names)
    if index >= 0:
        name = names[index]
        remove_watchlist(name)

@plugin.route('/remove_watchlist/<watchlist>')
def remove_watchlist(watchlist):
    watchlists = plugin.get_storage('watchlists')
    del watchlists[watchlist]

@plugin.route('/category/<type>')
def category(type):
    main_context_items = []
    main_context_items.append(('Add Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('add_watchlist'))))
    #main_context_items.append(('Remove Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('remove_watchlist'))))
    main_context_items.append(('Update TV Shows', 'XBMC.RunPlugin(%s)' % (plugin.url_for('update_tv'))))
    main_context_items.append(('Delete and Clean Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for('nuke'))))
    if type == "all":
        icon = "favourites"
    elif type == "movies":
        icon = "movies"
    else:
        icon = "tv"
    watchlists = plugin.get_storage('watchlists')
    items = []
    for watchlist in sorted(watchlists):
        if 'rss.imdb' in watchlists[watchlist]:
            route = 'rss'
        else:
            route = 'watchlist'
        context_items = []
        context_items.append(
        ('Add to Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for(route, url=watchlists[watchlist], type=type, export=True))))
        context_items.append(('Remove Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('remove_watchlist', watchlist=watchlist))))
        context_items = context_items + main_context_items
        items.append(
        {
            'label': watchlist,
            'path': plugin.url_for(route, url=watchlists[watchlist], type=type, export=False),
            'thumbnail':get_icon_path(icon),
            'context_menu': context_items,
        })


    return items

@plugin.route('/')
def index():
    context_items = []
    context_items.append(('Add Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('add_watchlist'))))
    context_items.append(('Remove Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('remove_watchlist_dialog'))))
    context_items.append(('Update TV Shows', 'XBMC.RunPlugin(%s)' % (plugin.url_for('update_tv'))))
    context_items.append(('Delete and Clean Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for('nuke'))))
    items = []
    items.append(
    {
        'label': "All",
        'path': plugin.url_for('category', type="all"),
        'thumbnail':get_icon_path('favourites'),
        'context_menu': context_items,
    })
    items.append(
    {
        'label': "Movies",
        'path': plugin.url_for('category', type="movies"),
        'thumbnail':get_icon_path('movies'),
        'context_menu': context_items,
    })
    items.append(
    {
        'label': "TV",
        'path': plugin.url_for('category', type="tv"),
        'thumbnail':get_icon_path('tv'),
        'context_menu': context_items,
    })

    return items

if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)
