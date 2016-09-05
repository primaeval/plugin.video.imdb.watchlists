import time,datetime
import xbmc
import xbmcaddon

from datetime import date, timedelta

ADDON = xbmcaddon.Addon(id='plugin.video.imdb.watchlists')

def subscription_update():
    if ADDON.getSetting('subscription_update') == "true":
        return True
    else:
        return False

def update_tv():
    if ADDON.getSetting('update_tv') == "true":
        return True
    else:
        return False

def update_watchlists():
    if ADDON.getSetting('update_watchlists') == "true":
        return True
    else:
        return False

def subscription_timer():
    return int(ADDON.getSetting('subscription_timer'))

class AutoUpdater:
    def update(self):
        hours_list = [2, 5, 10, 15, 24]
        hours = hours_list[subscription_timer()]
        xbmc.log('[IMDb Watchlists] Updating', level=xbmc.LOGNOTICE)
        time.sleep(1)
        if update_watchlists():
            xbmc.log('[IMDb Watchlists] Updating Watchlists', level=xbmc.LOGNOTICE)
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.imdb.watchlists/update_watchlists)')
        if update_tv():
            xbmc.log('[IMDb Watchlists] Updating TV Shows', level=xbmc.LOGNOTICE)
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.imdb.watchlists/update_tv)')
        now = datetime.datetime.now()
        ADDON.setSetting('service_time', str(now + timedelta(hours=hours)).split('.')[0])
        xbmc.log("[IMDb Watchlists] Library updated. Next run at " + ADDON.getSetting('service_time'), level=xbmc.LOGNOTICE)
        if ADDON.getSetting('update_main') == "true":
            while (xbmc.getCondVisibility('Library.IsScanningVideo') == True):
                time.sleep(1)
                if xbmc.abortRequested:
                    return
            xbmc.log('[IMDb Watchlists] Updating Kodi Library', level=xbmc.LOGNOTICE)
            xbmc.executebuiltin('UpdateLibrary(video)')
        if ADDON.getSetting('update_clean') == "true":
            time.sleep(1)
            while (xbmc.getCondVisibility('Library.IsScanningVideo') == True):
                time.sleep(1)
                if xbmc.abortRequested:
                    return
            xbmc.log('[IMDb Watchlists] Cleaning Kodi Library', level=xbmc.LOGNOTICE)
            xbmc.executebuiltin('CleanLibrary(video)')

    def runProgram(self):
        if ADDON.getSetting('login_update') == "true":
            self.update()
        while not xbmc.abortRequested:
            if subscription_update():
                try:
                    next_run  = datetime.datetime.fromtimestamp(time.mktime(time.strptime(ADDON.getSetting('service_time').encode('utf-8', 'replace'), "%Y-%m-%d %H:%M:%S")))
                    now = datetime.datetime.now()
                    if now > next_run:
                        self.update()
                except Exception as detail:
                    xbmc.log("[IMDb Watchlists] Update Exception %s" % detail, level=xbmc.LOGERROR)
                    pass
            time.sleep(1)


xbmc.log("[IMDb Watchlists] Subscription service starting...", level=xbmc.LOGNOTICE)
AutoUpdater().runProgram()
