from ytmusicapi import YTMusic

yt = YTMusic("browser.json")
print(yt.get_history()[:3])
