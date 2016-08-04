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

def update_watchlists():
    if ADDON.getSetting('update_watchlists') == "true":
        return True
    else:
        return False

def subscription_timer():
    return int(ADDON.getSetting('subscription_timer'))

class AutoUpdater:
    def runProgram(self):
        time.sleep(40)
        self.last_run = 0
        hours_list = [2, 5, 10, 15, 24]
        hours = hours_list[subscription_timer()]
        while not xbmc.abortRequested:
            if subscription_update():
                try:
                    next_run  = datetime.datetime.fromtimestamp(time.mktime(time.strptime(ADDON.getSetting('service_time').encode('utf-8', 'replace'), "%Y-%m-%d %H:%M:%S")))
                    now = datetime.datetime.now()
                    if now > next_run:
                        if xbmc.Player().isPlaying() == False:
                            if xbmc.getCondVisibility('Library.IsScanningVideo') == False:
                                xbmc.log('[IMDb Watchlists] Updating video library')
                                time.sleep(1)
                                if update_watchlists():
                                    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.imdb.watchlists/update_watchlists)')
                                xbmc.executebuiltin('RunPlugin(plugin://plugin.video.imdb.watchlists/update_tv)')
                                self.last_run = now
                                ADDON.setSetting('service_time', str(datetime.datetime.now() + timedelta(hours=hours)).split('.')[0])
                                xbmc.log("[IMDb Watchlists] Library updated. Next run at " + ADDON.getSetting('service_time'))
                                xbmc.executebuiltin('UpdateLibrary(video)')
                        else:
                            xbmc.log("[IMDb Watchlists] Player is running, waiting until finished")
                except:
                    pass
            xbmc.sleep(1000)


xbmc.log("[IMDb Watchlists] Subscription service starting...")
AutoUpdater().runProgram()
