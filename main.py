import json
import os
import zipfile
import sys
import subprocess
import shutil
import configparser

from dnt_reader import get_charts_from_dnt
from dnt_extractor import extract_audio_auto
from convert_core_function import convert_core


def safe_filename(name):
    if not name:
        return "converted"
    return name


def fix_encoding(text):
    """尝试修复乱码"""
    if not text or not isinstance(text, str):
        return text
    try:
        return text.encode('latin1').decode('utf-8')
    except:
        try:
            return text.encode('cp437').decode('utf-8')
        except:
            try:
                return text.encode('utf-8').decode('utf-8')
            except:
                return text


# ===================== 打包资源路径兼容 =====================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ===================== 封面处理函数 =====================
def get_default_cover():
    external_path = os.path.join(os.path.dirname(__file__), 'default_cover.png')
    if os.path.exists(external_path):
        with open(external_path, 'rb') as f:
            return f.read()
    return b''


def extract_cover_from_mp3(mp3_path):
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, APIC
        audio = MP3(mp3_path, ID3=ID3)
        if audio.tags:
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    return tag.data
    except:
        pass
    return None


def extract_cover_from_audio_data(audio_data, tmp_dir):
    if audio_data and len(audio_data) > 3 and audio_data[:3] == b'ID3':
        temp_mp3 = os.path.join(tmp_dir, 'temp_cover.mp3')
        try:
            with open(temp_mp3, 'wb') as f:
                f.write(audio_data)
            cover_data = extract_cover_from_mp3(temp_mp3)
            return cover_data
        finally:
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
    return None


def get_cover_image(zip_path, audio_data=None, tmp_dir=None, user_cover_path=None):
    if user_cover_path and os.path.exists(user_cover_path):
        with open(user_cover_path, 'rb') as f:
            return f.read(), user_cover_path

    ext = os.path.splitext(zip_path)[1].lower()
    if ext == '.zip':
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    lower_name = name.lower()
                    if lower_name.endswith(('.png', '.jpg', '.jpeg')):
                        cover_data = zf.read(name)
                        return cover_data, None
        except:
            pass

    if audio_data and tmp_dir:
        cover_data = extract_cover_from_audio_data(audio_data, tmp_dir)
        if cover_data:
            return cover_data, None

    return get_default_cover(), None


# ===================== 文件查找 =====================
def find_files_in_dir(root_dir):
    json_file = None
    img_file = None
    audio_file = None
    json_exts = (".json")
    audio_exts = ('.mp3', '.ogg', '.wav', '.flac')
    img_exts = ('.png', '.jpg', '.jpeg')
    for cur, _, files in os.walk(root_dir):
        for f in files:
            fp = os.path.join(cur, f)
            if not json_file and f.lower().endswith(json_exts):
                json_file = fp
            if not img_file and f.lower().endswith(img_exts):
                img_file = fp
            if not audio_file and f.lower().endswith(audio_exts):
                audio_file = fp
    return json_file, img_file, audio_file


def convert_to_ogg(mp3_path):
    if not mp3_path or not mp3_path.lower().endswith('.mp3'):
        return mp3_path
    ogg_path = os.path.splitext(mp3_path)[0] + '.ogg'
    ffmpeg_paths = [
        os.path.join(os.path.dirname(sys.executable), 'ffmpeg.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
    ]
    ffmpeg = next((p for p in ffmpeg_paths if os.path.exists(p)), None)
    if ffmpeg:
        try:
            subprocess.run([
                ffmpeg, '-i', mp3_path,
                '-c:a', 'libvorbis', '-q:a', '4', '-ar', '44100', '-y', ogg_path
            ], check=True, capture_output=True)
            return ogg_path
        except:
            pass
    return mp3_path


# ===================== 读取 .ini 配置文件 =====================
def load_song_ini(zip_dir):
    ini_path = None
    for root, dirs, files in os.walk(zip_dir):
        for f in files:
            if f.lower().endswith('.ini'):
                ini_path = os.path.join(root, f)
                break
        if ini_path:
            break

    if not ini_path or not os.path.exists(ini_path):
        return {}

    config = configparser.RawConfigParser(interpolation=None)
    config.optionxform = str

    for enc in ['utf-8', 'gbk', 'gb2312', 'shift-jis', 'latin1']:
        try:
            config.read(ini_path, encoding=enc)
            if config.has_section('Song') or config.has_section('DEFAULT'):
                break
        except:
            continue

    result = {}

    def safe_get(section, key, default=''):
        try:
            val = config.get(section, key).strip()
            if ';' in val:
                val = val.split(';')[0].strip()
            try:
                val = val.encode('latin1').decode('utf-8')
            except:
                pass
            return val
        except:
            return default

    if config.has_section('Song'):
        result['song'] = safe_get('Song', 'Name')
        result['composer'] = safe_get('Song', 'Artist')
        result['charter'] = safe_get('Song', 'Noter')
        result['hard'] = safe_get('Song', 'Hard')
    else:
        result['song'] = safe_get('DEFAULT', 'Name')
        result['composer'] = safe_get('DEFAULT', 'Artist')
        result['charter'] = safe_get('DEFAULT', 'Noter')
        result['hard'] = safe_get('DEFAULT', 'Hard')

    return result


# ===================== 处理单个文件 =====================
def process_single_file(zip_path, output_dir, speed,
                        speed_coeff, speed_exp, width_coeff, width_exp, base_width_mult,
                        flick_click, hold_interval, hold_alpha,
                        custom_filename, custom_song, custom_composer, custom_charter, custom_hard,
                        convert_mp3_to_ogg,
                        appear_by_judge_order,
                        user_cover_path=None,
                        enable_sound_visualization=False,
                        original_filename=None):
    try:
        tmp = os.path.join(output_dir, '__tmp_batch')
        os.makedirs(tmp, exist_ok=True)

        ext = os.path.splitext(zip_path)[1].lower()

        # ========== 处理.dnt 格式（单文件）==========
        if ext in [".dnt"]:
            charts = get_charts_from_dnt(zip_path)
            if not charts:
                return False, '解析失败：未找到谱面数据'

            before, audio_data, after = extract_audio_auto(zip_path)

            audio_path = os.path.join(tmp, 'audio.ogg')
            with open(audio_path, 'wb') as f:
                f.write(audio_data)

            if original_filename:
                base_name = os.path.splitext(original_filename)[0]
            else:
                base_name = os.path.splitext(os.path.basename(zip_path))[0]

            if custom_filename and custom_filename.strip():
                base_name = fix_encoding(custom_filename.strip())
            else:
                base_name = fix_encoding(base_name)

            code_to_name = {0: 'Easy', 1: 'Normal', 2: 'Hard', 3: 'Extra'}
            results = []

            for chart_data in charts:
                difficulty_code = chart_data.get('difficulty_code', 2)
                difficulty_text = code_to_name.get(difficulty_code, 'Hard')

                if custom_song and custom_song.strip():
                    song = fix_encoding(custom_song.strip())
                else:
                    song = fix_encoding(chart_data.get('name', base_name))

                if custom_hard and custom_hard.strip():
                    hard = fix_encoding(custom_hard.strip())
                else:
                    hard = f"<DEEMO> Lv.{difficulty_text}"

                if custom_charter and custom_charter.strip():
                    charter = fix_encoding(custom_charter.strip())
                else:
                    charter = "Unknown"

                if custom_composer and custom_composer.strip():
                    composer = fix_encoding(custom_composer.strip())
                else:
                    composer = "Unknown"

                phi = convert_core(
                    json_path=chart_data,
                    speed=speed,
                    song=song,
                    composer=composer,
                    charter=charter,
                    hard=hard,
                    speed_coeff=speed_coeff,
                    speed_exp=speed_exp,
                    width_coeff=width_coeff,
                    width_exp=width_exp,
                    base_width_mult=base_width_mult,
                    flick_click=flick_click,
                    hold_drag_interval=hold_interval,
                    hold_alpha=hold_alpha,
                    appear_by_judge_order=appear_by_judge_order,
                    audio_filename='audio.ogg',
                    enable_sound_visualization=enable_sound_visualization
                )

                if not phi:
                    results.append((difficulty_text, False, '转换失败'))
                    continue

                phi_out = os.path.join(tmp, 'phi.json')
                with open(phi_out, 'w', encoding='utf-8') as f:
                    json.dump(phi, f, ensure_ascii=False, indent=2)

                if len(charts) > 1:
                    pez_name = f'{base_name}_{difficulty_text}.pez'
                    idx = 1
                    pez_path = os.path.join(output_dir, pez_name)
                    while os.path.exists(pez_path):
                        pez_name = f'{base_name}_{difficulty_text}_{idx}.pez'
                        pez_path = os.path.join(output_dir, pez_name)
                        idx += 1
                else:
                    pez_name = f'{base_name}.pez'
                    pez_path = os.path.join(output_dir, pez_name)
                    idx = 1
                    while os.path.exists(pez_path):
                        pez_name = f'{base_name}_{idx}.pez'
                        pez_path = os.path.join(output_dir, pez_name)
                        idx += 1

                cover_data, cover_source = get_cover_image(
                    zip_path, audio_data, tmp, user_cover_path
                )

                cover_path = os.path.join(tmp, 'cover.png')
                with open(cover_path, 'wb') as f:
                    f.write(cover_data)

                with zipfile.ZipFile(pez_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(phi_out, 'phi.json')
                    zf.write(audio_path, 'audio.ogg')
                    zf.write(cover_path, 'cover.png')

                results.append((difficulty_text, True, pez_path))

            shutil.rmtree(tmp, ignore_errors=True)

            success_list = [r for r in results if r[1]]
            if success_list:
                pez_paths = [r[2] for r in success_list]
                return True, pez_paths
            else:
                return False, results[0][2] if results else '未知错误'

        # ========== 处理 ZIP 格式 ==========
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp)

        chart_files = []
        for root, dirs, files in os.walk(tmp):
            for f in files:
                if f.lower().endswith('.json') or f.lower().endswith('.dnt'):
                    chart_files.append(os.path.join(root, f))

        if not chart_files:
            return False, '未找到任何谱面文件（.json 或 .dnt）'

        if original_filename:
            base_name = os.path.splitext(original_filename)[0]
        else:
            base_name = os.path.splitext(os.path.basename(zip_path))[0]

        base_name = fix_encoding(base_name)

        results = []
        chart_idx = 0

        for chart_path in chart_files:
            file_ext = os.path.splitext(chart_path)[1].lower()
            chart_idx += 1

            chart_dir = os.path.dirname(chart_path)
            folder_name = os.path.basename(chart_dir)

            # ========== 处理 .dnt 文件 ==========
            if file_ext == '.dnt':
                try:
                    dnt_charts = get_charts_from_dnt(chart_path)
                    if not dnt_charts:
                        results.append((f'谱面{chart_idx}', False, 'DNT解析失败'))
                        continue

                    before, audio_data, after = extract_audio_auto(chart_path)
                    audio_path = os.path.join(tmp, f'audio_{chart_idx}.ogg')
                    with open(audio_path, 'wb') as f:
                        f.write(audio_data)

                    for sub_idx, dnt_chart in enumerate(dnt_charts):
                        difficulty_code = dnt_chart.get('difficulty_code', 2)
                        code_to_name = {0: 'Easy', 1: 'Normal', 2: 'Hard', 3: 'Extra'}
                        difficulty_text = code_to_name.get(difficulty_code, 'Hard')

                        if custom_song and custom_song.strip():
                            song = fix_encoding(custom_song.strip())
                        else:
                            song = fix_encoding(dnt_chart.get('name', base_name))

                        if custom_hard and custom_hard.strip():
                            hard = fix_encoding(custom_hard.strip())
                        else:
                            hard = f"<DEEMO> Lv.{difficulty_text}"

                        if custom_charter and custom_charter.strip():
                            charter = fix_encoding(custom_charter.strip())
                        else:
                            charter = "Unknown"

                        if custom_composer and custom_composer.strip():
                            composer = fix_encoding(custom_composer.strip())
                        else:
                            composer = "Unknown"

                        if len(dnt_charts) > 1:
                            pez_name = f'{base_name}_{difficulty_text}.pez'
                            idx = 1
                            pez_path = os.path.join(output_dir, pez_name)
                            while os.path.exists(pez_path):
                                pez_name = f'{base_name}_{difficulty_text}_{idx}.pez'
                                pez_path = os.path.join(output_dir, pez_name)
                                idx += 1
                        else:
                            pez_name = f'{base_name}.pez'
                            pez_path = os.path.join(output_dir, pez_name)
                            idx = 1
                            while os.path.exists(pez_path):
                                pez_name = f'{base_name}_{idx}.pez'
                                pez_path = os.path.join(output_dir, pez_name)
                                idx += 1

                        phi = convert_core(
                            json_path=dnt_chart,
                            speed=speed,
                            song=song,
                            composer=composer,
                            charter=charter,
                            hard=hard,
                            speed_coeff=speed_coeff,
                            speed_exp=speed_exp,
                            width_coeff=width_coeff,
                            width_exp=width_exp,
                            base_width_mult=base_width_mult,
                            flick_click=flick_click,
                            hold_drag_interval=hold_interval,
                            hold_alpha=hold_alpha,
                            appear_by_judge_order=appear_by_judge_order,
                            audio_filename='audio.ogg',
                            enable_sound_visualization=enable_sound_visualization
                        )

                        if not phi:
                            results.append((song, False, '转换失败'))
                            continue

                        phi_out = os.path.join(tmp, f'phi_{chart_idx}_{sub_idx}.json')
                        with open(phi_out, 'w', encoding='utf-8') as f:
                            json.dump(phi, f, ensure_ascii=False, indent=2)

                        cover_data, _ = get_cover_image(chart_path, audio_data, tmp, user_cover_path)
                        cover_path = os.path.join(tmp, f'cover_{chart_idx}_{sub_idx}.png')
                        with open(cover_path, 'wb') as f:
                            f.write(cover_data)

                        with zipfile.ZipFile(pez_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                            zf.write(phi_out, 'phi.json')
                            zf.write(audio_path, 'audio.ogg')
                            zf.write(cover_path, 'cover.png')

                        results.append((song, True, pez_path))

                except Exception as e:
                    results.append((f'谱面{chart_idx}', False, f'DNT处理失败: {str(e)}'))
                    continue

            # ========== 处理 .json 文件 ==========
            else:
                try:
                    with open(chart_path, 'r', encoding='utf-8') as f:
                        chart_data = json.load(f)
                except:
                    results.append((f'谱面{chart_idx}', False, f'JSON解析失败: {chart_path}'))
                    continue

                ini_config = load_song_ini(chart_dir)

                if custom_song and custom_song.strip():
                    song = fix_encoding(custom_song.strip())
                elif ini_config.get('song'):
                    song = fix_encoding(ini_config['song'])
                else:
                    song = fix_encoding(folder_name if folder_name and folder_name != '.' else os.path.splitext(os.path.basename(chart_path))[0])

                if custom_hard and custom_hard.strip():
                    hard = fix_encoding(custom_hard.strip())
                elif ini_config.get('hard'):
                    hard = fix_encoding(ini_config['hard'])
                else:
                    hard = "Hard"

                if not (custom_hard and custom_hard.strip()):
                    hard = f"<Deemo> Lv.{hard}"

                if custom_composer and custom_composer.strip():
                    composer = fix_encoding(custom_composer.strip())
                elif ini_config.get('composer'):
                    composer = fix_encoding(ini_config['composer'])
                else:
                    composer = "Unknown"

                if custom_charter and custom_charter.strip():
                    charter = fix_encoding(custom_charter.strip())
                elif ini_config.get('charter'):
                    charter = fix_encoding(ini_config['charter'])
                else:
                    charter = "Unknown"

                # PEZ 文件名：用子文件夹名
                if custom_filename and custom_filename.strip():
                    safe = fix_encoding(custom_filename.strip())
                else:
                    safe = fix_encoding(folder_name if folder_name and folder_name != '.' else base_name)

                # 查找同目录的音频文件
                audio_file = None
                preview_file = None
                for ext in ['.mp3', '.ogg', '.wav', '.flac']:
                    for f in os.listdir(chart_dir):
                        if f.lower().endswith(ext):
                            if 'preview' in f.lower():
                                preview_file = os.path.join(chart_dir, f)
                            else:
                                audio_file = os.path.join(chart_dir, f)
                                break
                    if audio_file:
                        break

                if not audio_file:
                    audio_file = preview_file

                audio_filename = None
                audio_path = None
                if audio_file and os.path.exists(audio_file):
                    audio_ext = os.path.splitext(audio_file)[1].lower()
                    if convert_mp3_to_ogg and audio_ext == '.mp3':
                        audio_source = convert_to_ogg(audio_file)
                        audio_filename = 'audio.ogg'
                    else:
                        audio_source = audio_file
                        audio_filename = f'audio{audio_ext}'
                    audio_path = os.path.join(tmp, f'audio_{chart_idx}{audio_filename}')
                    shutil.copy(audio_source, audio_path)

                # 查找封面
                cover_data = None
                for ext in ['.png', '.jpg', '.jpeg']:
                    for f in os.listdir(chart_dir):
                        if f.lower().endswith(ext):
                            cover_path_src = os.path.join(chart_dir, f)
                            with open(cover_path_src, 'rb') as cf:
                                cover_data = cf.read()
                            break
                    if cover_data:
                        break

                if not cover_data:
                    cover_data, _ = get_cover_image(zip_path, None, tmp, user_cover_path)

                cover_path = os.path.join(tmp, f'cover_{chart_idx}.png')
                with open(cover_path, 'wb') as f:
                    f.write(cover_data)

                phi = convert_core(
                    json_path=chart_path,
                    speed=speed,
                    song=song,
                    composer=composer,
                    charter=charter,
                    hard=hard,
                    speed_coeff=speed_coeff,
                    speed_exp=speed_exp,
                    width_coeff=width_coeff,
                    width_exp=width_exp,
                    base_width_mult=base_width_mult,
                    flick_click=flick_click,
                    hold_drag_interval=hold_interval,
                    hold_alpha=hold_alpha,
                    appear_by_judge_order=appear_by_judge_order,
                    audio_filename=audio_filename if audio_filename else 'audio.ogg',
                    enable_sound_visualization=enable_sound_visualization
                )

                if not phi:
                    results.append((song, False, '转换失败'))
                    continue

                phi_out = os.path.join(tmp, f'phi_{chart_idx}.json')
                with open(phi_out, 'w', encoding='utf-8') as f:
                    json.dump(phi, f, ensure_ascii=False, indent=2)

                pez_path = os.path.join(output_dir, f'{safe}.pez')
                idx = 1
                while os.path.exists(pez_path):
                    pez_path = os.path.join(output_dir, f'{safe}_{idx}.pez')
                    idx += 1

                with zipfile.ZipFile(pez_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(phi_out, 'phi.json')
                    zf.write(cover_path, 'cover.png')
                    if audio_path and os.path.exists(audio_path):
                        zf.write(audio_path, audio_filename)

                results.append((song, True, pez_path))

        shutil.rmtree(tmp, ignore_errors=True)

        success_list = [r for r in results if r[1]]
        if success_list:
            pez_paths = [r[2] for r in success_list]
            return True, pez_paths
        else:
            return False, results[0][2] if results else '未知错误'

    except Exception as e:
        return False, str(e)