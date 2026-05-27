import os
import urllib.request

os.makedirs('cache', exist_ok=True)

files = [
    ('rime-frost_base.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/base.dict.yaml'),
    ('rime-frost_ext.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/ext.dict.yaml'),
    ('rime-frost_8105.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/8105.dict.yaml'),
    ('rime-frost_others.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts/others.dict.yaml'),
    ('rime-frost_food.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/food.dict.yaml'),
    ('rime-frost_idiom.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/idiom.dict.yaml'),
    ('rime-frost_history.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/history.dict.yaml'),
    ('rime-frost_medication.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/medication.dict.yaml'),
    ('rime-frost_computer.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/computer.dict.yaml'),
    ('rime-frost_sport.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/sport.dict.yaml'),
    ('rime-frost_geography.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/geography.dict.yaml'),
    ('rime-frost_exthot.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/exthot.dict.yaml'),
    ('rime-frost_game.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/game.dict.yaml'),
    ('rime-frost_music.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/music.dict.yaml'),
    ('rime-frost_media.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/media.dict.yaml'),
    ('rime-frost_animal.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/animal.dict.yaml'),
    ('rime-frost_chess.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/chess.dict.yaml'),
    ('rime-frost_chess2.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/chess2.dict.yaml'),
    ('rime-frost_composite.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/composite.dict.yaml'),
    ('rime-frost_industry_product.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/industry_product.dict.yaml'),
    ('rime-frost_inputmethod.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/inputmethod.dict.yaml'),
    ('rime-frost_literature.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/literature.dict.yaml'),
    ('rime-frost_name.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/name.dict.yaml'),
    ('rime-frost_name2.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/name2.dict.yaml'),
    ('rime-frost_place.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/place.dict.yaml'),
    ('rime-frost_shulihua.txt', 'https://cdn.jsdelivr.net/gh/gaboolic/rime-frost@master/cn_dicts_cell/shulihua.dict.yaml'),
    ('rime-frost_luna_pinyin.txt', 'https://raw.githubusercontent.com/gaboolic/rime-frost/master/luna_pinyin.dict.yaml'),
]

for fname, url in files:
    out_path = f'cache/{fname}'
    if os.path.exists(out_path):
        print(f'SKIP {fname} ({os.path.getsize(out_path)//1024}KB)')
        continue
    print(f'DOWN {fname}...', flush=True)
    try:
        urllib.request.urlretrieve(url, out_path)
        size = os.path.getsize(out_path)
        print(f'  OK ({size//1024}KB)')
    except Exception as e:
        print(f'  FAIL: {e}')

print('\nAll done!')
