from dnt_extractor import extract_audio_auto
from chart_parser import ChartParser
import os
import json

# ============================
# 新增：读取 DNT 项目头（最干净）
# ============================
def read_dnt_metadata(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
    
    offset = 0

    # 读文件头 E0 DE
    magic = data[offset:offset+2]
    offset += 2
    if magic.hex() != "e0de":
        raise ValueError("无效的DNT文件头")

    # 读版本 01
    ver = data[offset]
    offset += 1
    if ver != 1:
        raise ValueError(f"不支持的DNT版本: {ver}")

    # 读取 UTF8 字符串（ULEB128 长度）
    def read_str():
        nonlocal offset
        length = 0
        shift = 0
        while True:
            b = data[offset]
            length |= (b & 0x7F) << shift
            offset += 1
            if not (b & 0x80):
                break
        s = data[offset:offset+length].decode("utf-8")
        offset += length
        return s

    project_name = read_str()
    composer     = read_str()
    charter      = read_str()

    return {
        "project_name": project_name,
        "composer": composer,
        "charter": charter
    }

def parse_dnt_file(input_file: str):
    """提取并解析 dnt 文件中的谱面"""
    print(f"正在解析: {input_file}")
    _, _, chart_bytes = extract_audio_auto(input_file)
    parser = ChartParser(chart_bytes)
    result = parser.parse_all()
    return result

def convert_to_target_format(result):
    """将解析结果转换为目标JSON格式"""
    output = []
    
    for chart in result['charts']:
        all_velocities = []
        for note in chart['notes']:
            for piano in note['piano_events']:
                all_velocities.append(piano['v'])
        
        ori_v_min = min(all_velocities) if all_velocities else 0
        ori_v_max = max(all_velocities) if all_velocities else 0
        
        notes_list = []
        for idx, note in enumerate(chart['notes'], start=1):
            note_data = {
                "$id": str(idx),
                "sounds": note['piano_events'],
                "pos": note['position'],
                "size": note['size'],
                "_time": note['time'],
                "shift": note['shift'],
                "speed": note['speed'],
                "duration": note['hold_duration'],
                "swipe": note['type'] == 2,
                "eventId": note['event_id']
            }
            notes_list.append(note_data)
        
        links_list = []
        for idx, note in enumerate(chart['notes'], start=1):
            if note['type'] == 1:
                links_list.append({
                    "notes": [{"$ref": str(idx)}]
                })
        
        chart_data = {
            "speed": chart['speed'],
            "oriVMin": ori_v_min,
            "oriVMax": ori_v_max,
            "remapVMin": chart['remap_min_volume'],
            "remapVMax": chart['remap_max_volume'],
            "notes": notes_list,
            "links": links_list,
            "difficulty_code": chart['difficulty_code'],
            "difficulty": chart['difficulty'],
            "level": chart['level'],
            "name": chart['name']
        }
        
        output.append(chart_data)
    
    return output

def get_charts_from_dnt(dnt_path: str):
    """一步到位：从 dnt 文件获取所有谱面的 chart_data 列表"""
    # 1. 读取项目头
    meta = read_dnt_metadata(dnt_path)

    # 2. 读取谱面数据（你原有逻辑不变）
    result = parse_dnt_file(dnt_path)
    charts = convert_to_target_format(result)

    # 3. 把真正的项目信息塞进每个谱面
    for chart in charts:
        chart["name"] = meta["project_name"]
        chart["composer"] = meta["composer"]
        chart["charter"] = meta["charter"]

    return charts

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "MORNINGLOOM.dnt")
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    result = parse_dnt_file(file_path)
    output = convert_to_target_format(result)
    
    code_to_name = {0: 'Easy', 1: 'Normal', 2: 'Hard', 3: 'Extra'}
    
    for i, chart_data in enumerate(output):
        difficulty_code = result['charts'][i]['difficulty_code']
        difficulty_text = code_to_name.get(difficulty_code, f'Unknown_{difficulty_code}')
        
        json_filename = f"{base_name}_{difficulty_text}.json"
        json_path = os.path.join(script_dir, json_filename)
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(chart_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已保存: {json_filename} ")