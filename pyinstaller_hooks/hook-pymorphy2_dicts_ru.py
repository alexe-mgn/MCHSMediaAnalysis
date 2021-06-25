from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("pymorphy2_dicts_ru")
