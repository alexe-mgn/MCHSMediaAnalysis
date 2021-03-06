# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[("ui/UI/favicon.ico", "ui/UI"),
                    ("ui/plotly.min.js", "ui"), ("qt.conf", "."),
                    ("spacy_model", "spacy_model")],
             hiddenimports=['srsly.msgpack.util', 'spacy.lang.ru', 'pymorphy2_dicts_ru', 'mysql.connector.locales.eng.client_error'],
             hookspath=['pyinstaller_hooks'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='main',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False, icon='ui\\UI\\favicon.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='MCHS Media analysis')
