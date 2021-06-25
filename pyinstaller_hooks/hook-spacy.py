from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

for i in ('spacy', 'thinc', 'cymem', 'preshed', 'blis'):
    data = collect_all(i)
    datas += data[0]
    binaries += data[1]
    hiddenimports += data[2]
