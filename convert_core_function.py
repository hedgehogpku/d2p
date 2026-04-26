import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union


# ========== 配置类 ==========
@dataclass
class ConvertConfig:
    """转换配置参数"""
    speed: float
    song: str
    composer: str
    charter: str
    hard: str
    audio_filename: str
    speed_coeff: float
    speed_exp: float
    width_coeff: float
    width_exp: float
    base_width_mult: float
    flick_click: bool
    hold_drag_interval: int
    hold_alpha: int
    appear_by_judge_order: bool
    enable_sound_visualization: bool


@dataclass
class SoundData:
    """单个声音事件"""
    d: float = 0.0      # duration 持续时间
    p: int = 0          # pitch 音高
    v: int = 0          # volume 音量
    w: float = 0.0      # offset


# ========== 中间数据结构 ==========
@dataclass
class NoteData:
    """解析后的单个音符数据"""
    pos: float
    time: float
    size: float
    is_flick: bool
    withhold: float
    original_speed: float
    notespeed: float
    appeartime: float
    shouldappear: float
    index: int
    sounds: List[SoundData] = field(default_factory=list)


# ========== 常量定义 ==========
class ChartConstants:
    RANGES = 450
    VISIBLE_LEAD_TIME = 7
    POSITION_THRESHOLD = 2.0001
    JUDGE_AREA_BASE = 0.8
    JUDGE_AREA_MIN = 0.4
    CHART_TIME_MAX = 99999
    DEFAULT_WIDTH = 1.0
    DEFAULT_ALPHA = 255
    MS_PER_SECOND = 1000
    DEFAULT_Y_OFFSET = 0.0
    DEFAULT_ABOVE = 1


# ========== 辅助函数 ==========
def load_json_data(json_path: Union[str, Dict]) -> Optional[Dict]:
    """加载 JSON 数据"""
    try:
        if isinstance(json_path, str):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return json_path
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        print(f"加载 JSON 失败: {e}")
        return None


def get_note_field(note: Dict, key: str, default: Any) -> Any:
    """安全获取音符字段"""
    value = note.get(key)
    return default if value is None else value


def time_to_ms(time_sec: float) -> int:
    return int(time_sec * ChartConstants.MS_PER_SECOND)


def calculate_judge_area(size: float) -> float:
    base = 0.8 * (1.0 + (size - 1)) + 0.2
    return max(base, ChartConstants.JUDGE_AREA_MIN)


def calculate_note_size(size_raw: float, config: ConvertConfig) -> float:
    return (config.width_coeff * size_raw ** config.width_exp + 1 - config.width_coeff) * config.base_width_mult


def calculate_note_speed(original_speed: float, config: ConvertConfig) -> float:
    return config.speed_coeff * original_speed ** config.speed_exp + 1 - config.speed_coeff


def calculate_appear_time(time_sec: float, notespeed: float, speed: float) -> float:
    return time_sec - ChartConstants.VISIBLE_LEAD_TIME / notespeed / speed


# ========== 颜色计算函数 ==========
def hsl_to_hex(h: float, s: float, l: float) -> str:
    """HSL 转 HEX，h: 0-360, s: 0-100, l: 0-100"""
    s /= 100
    l /= 100
    
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c/2
    
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    r = int((r + m) * 255)
    g = int((g + m) * 255)
    b = int((b + m) * 255)
    
    return f"#{r:02x}{g:02x}{b:02x}"


def calculate_tint(sounds: List[SoundData], note_type: str) -> str:
    """
    根据声音数据计算 tint 颜色
    
    规则：
    - 非 Tap 音符：白色 #FFFFFF
    - Tap 且无钢琴音：深灰 #222222
    - Tap 有钢琴音但全部 v=0：中灰 #999999
    - Tap 有钢琴音且 v>0：动态颜色
        色相：音高 0 → 240° (蓝)，127 → 140° (绿)
        饱和度：按最高力度映射 50%-100%
        明度：固定 60%
    """
    # 非 Tap 音符
    if note_type != "tap":
        return "#FFFFFF"
    
    # 没有钢琴音数据
    if not sounds:
        return "#222222"
    
    # 检查是否所有 v 都是 0
    all_volume_zero = all(s.v == 0 for s in sounds)
    if all_volume_zero:
        return "#999999"
    
    # 有钢琴音且 v>0，计算加权平均音高
    total_weight = 0
    weighted_pitch_sum = 0
    max_volume = 0
    
    for sound in sounds:
        weight = sound.v if sound.v > 0 else 1
        weighted_pitch_sum += sound.p * weight
        total_weight += weight
        max_volume = max(max_volume, sound.v)
    
    avg_pitch = weighted_pitch_sum / total_weight if total_weight > 0 else 60
    
    # 音高映射到色相
    # 范围 0-127，映射到 140°(绿) - 240°(蓝)
    pitch_min, pitch_max = 0, 127
    hue_min, hue_max = 240, 140
    
    pitch_clamped = max(pitch_min, min(pitch_max, avg_pitch))
    t = (pitch_clamped - pitch_min) / (pitch_max - pitch_min)
    hue = hue_min + (hue_max - hue_min) * t
    
    # 力度映射到饱和度 50%-100%
    volume_clamped = max(1, min(127, max_volume))
    saturation = 50 + (volume_clamped / 127) * 50
    saturation = max(50, min(100, saturation))
    
    # 明度固定 60%
    lightness = 60
    
    return hsl_to_hex(hue, saturation, lightness)


def hex_to_rgb(hex_color: str) -> List[int]:
    """将 HEX 颜色转换为 RGB 数组，如 '#999999' -> [153, 153, 153]"""
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]


# ========== 核心解析函数 ==========
def parse_notes(notes_data: List[Dict], config: ConvertConfig, speed: float) -> List[NoteData]:
    """解析原始 notes 数据"""
    note_list = []
    
    for idx, note in enumerate(notes_data):
        pos = get_note_field(note, "pos", 0.0)
        time_val = get_note_field(note, "_time", 0.0)
        size_raw = get_note_field(note, "size", 1.0)
        is_flick = get_note_field(note, "swipe", False)
        withhold = get_note_field(note, "duration", 0.0)
        original_speed = get_note_field(note, "speed", 1.0)
        
        # 解析 sounds
        sounds_raw = note.get("sounds", [])
        sounds = []
        if sounds_raw:
            for s in sounds_raw:
                sound = SoundData(
                    d=s.get("d", 0.0),
                    p=s.get("p", 0),
                    v=s.get("v", 0),
                    w=s.get("w", 0.0)
                )
                sounds.append(sound)
        
        size = calculate_note_size(size_raw, config)
        notespeed = calculate_note_speed(original_speed, config)
        appeartime = calculate_appear_time(time_val, notespeed, speed)
        
        note_list.append(NoteData(
            pos=pos,
            time=time_val,
            size=size,
            is_flick=is_flick,
            withhold=withhold,
            original_speed=original_speed,
            notespeed=notespeed,
            appeartime=appeartime,
            shouldappear=appeartime,
            index=idx,
            sounds=sounds
        ))
    
    return note_list


def compute_slide_flags(notes_count: int, links_data: List[Dict]) -> List[int]:
    """计算滑条标记"""
    slide_flags = [0] * notes_count
    
    slide_indices = []
    for link in links_data:
        for note_ref in link.get("notes", []):
            ref = note_ref.get("$ref")
            if ref is not None:
                slide_indices.append(int(ref))
    
    for idx in slide_indices:
        if idx - 1 < notes_count:
            slide_flags[idx - 1] = 1
    
    return slide_flags


def adjust_appear_times_by_judge_order(note_list: List[NoteData]) -> None:
    """根据判定顺序调整出现时间：O(n) 优化版，与原逻辑100%一致"""
    if not note_list:
        return
    
    # 维护前面所有 appeartime 的最大值
    max_prev_appear = note_list[0].appeartime
    
    for note in note_list[1:]:
        if note.shouldappear < max_prev_appear:
            note.shouldappear = max_prev_appear
        # 更新最大值，给后面音符用
        if note.appeartime > max_prev_appear:
            max_prev_appear = note.appeartime

def make_note_dict(
    start_time_sec: float,
    end_time_sec: float,
    position_x: float,
    size_val: float,
    speed_val: float,
    visible_time: float,
    note_type: int,
    is_fake: int,
    judge_area: float,
    alpha: int = ChartConstants.DEFAULT_ALPHA,
    tint: str = "#FFFFFF"
) -> Dict:
    """构造音符字典"""
    start_time_ms = time_to_ms(start_time_sec)
    end_time_ms = time_to_ms(end_time_sec)
    
    # 将 HEX 字符串转换为 RGB 数组
    tint_rgb = hex_to_rgb(tint)
    
    return {
        "above": ChartConstants.DEFAULT_ABOVE,
        "alpha": alpha,
        "endTime": [end_time_ms, 0, 1],
        "isFake": is_fake,
        "judgeArea": judge_area,
        "positionX": position_x,
        "size": size_val,
        "speed": speed_val,
        "startTime": [start_time_ms, 0, 1],
        "type": note_type,
        "visibleTime": visible_time,
        "yOffset": ChartConstants.DEFAULT_Y_OFFSET,
        "tint": tint_rgb
    }


def build_regular_notes(note_list: List[NoteData], slide_flags: List[int], config: ConvertConfig) -> List[Dict]:
    """构造普通音符和 Flick 音符"""
    notes = []

    
    for note in note_list:
        if abs(note.pos) >= ChartConstants.POSITION_THRESHOLD:
            continue
        
        # 确定计算tint用的音符类型
        if slide_flags[note.index]:
            note_type_str = "slide"
        elif note.is_flick:
            note_type_str = "flick"
        else:
            note_type_str = "tap"
        
        # 计算 tint
        if config.enable_sound_visualization:
            tint = calculate_tint(note.sounds, note_type_str)
        else:
            tint = "#FFFFFF"
        
        position_x = ChartConstants.RANGES * note.pos / 2
        size_val = ChartConstants.DEFAULT_WIDTH + (note.size - 1)
        if note_type_str == "slide":
            judge_area = max(calculate_judge_area(note.size),0.8)
        else:
            judge_area = calculate_judge_area(note.size)
        visible_time = (note.time - note.shouldappear) * (1 - int(note.is_flick))
        note_type = 1 + 3 * slide_flags[note.index]
        is_fake = int(note.is_flick and not config.flick_click)
        
        notes.append(make_note_dict(
            start_time_sec=note.time,
            end_time_sec=note.time,
            position_x=position_x,
            size_val=size_val,
            speed_val=note.notespeed,
            visible_time=visible_time,
            note_type=note_type,
            is_fake=is_fake,
            judge_area=judge_area,
            tint=tint
        ))
    
    # 额外的 Flick 层
    for note in note_list:
        if (note.pos) >= ChartConstants.POSITION_THRESHOLD or not note.is_flick:
            continue
        
        position_x = ChartConstants.RANGES * note.pos / 2
        size_val = ChartConstants.DEFAULT_WIDTH + 1 * (note.size - 1)
        visible_time = note.time - note.shouldappear
        
        notes.append(make_note_dict(
            start_time_sec=note.time,
            end_time_sec=note.time,
            position_x=position_x,
            size_val=size_val,
            speed_val=note.notespeed,
            visible_time=visible_time,
            note_type=3,
            is_fake=0,
            judge_area=calculate_judge_area(note.size),
            tint="#FFFFFF"
        ))
    
    return notes


def build_hold_notes(note_list: List[NoteData], config: ConvertConfig) -> tuple[List[Dict], List[Dict]]:
    """
    构造 Hold 音符和拖拽点
    返回: (hold_bodies, drag_points)
    - hold_bodies: 加到主判定线 (note_phi)
    - drag_points: 加到第二条透明判定线 (note_ex)
    """
    hold_bodies = []
    drag_points = []

    
    for note in note_list:
        if (note.pos) >= ChartConstants.POSITION_THRESHOLD or note.withhold == 0.0:
            continue
        
        position_x = ChartConstants.RANGES * note.pos / 2
        size_val = ChartConstants.DEFAULT_WIDTH +  (note.size - 1)
        judge_area = calculate_judge_area(note.size)
        visible_time = note.time - note.shouldappear
        
        # Hold 主体 - 放到主判定线
        hold_bodies.append(make_note_dict(
            start_time_sec=note.time,
            end_time_sec=note.time + note.withhold,
            position_x=position_x,
            size_val=size_val,
            speed_val=note.notespeed,
            visible_time=visible_time,
            note_type=2,
            is_fake=1,
            judge_area=judge_area,
            alpha=config.hold_alpha,
            tint="#FFFFFF"
        ))
        
        # 隐藏 Drag 模拟判定点 - 放到第二条判定线
        drag_count = max(int(note.withhold * ChartConstants.MS_PER_SECOND / config.hold_drag_interval) - 1, 1)
        for k in range(drag_count):
            drag_time = note.time + k * config.hold_drag_interval / ChartConstants.MS_PER_SECOND
            drag_points.append(make_note_dict(
                start_time_sec=drag_time,
                end_time_sec=drag_time,
                position_x=position_x,
                size_val=size_val,
                speed_val=note.notespeed,
                visible_time=visible_time,
                note_type=4,
                is_fake=0,
                judge_area=judge_area,
                alpha=0,
                tint="#FFFFFF"
            ))
    
    return hold_bodies, drag_points


def build_speed_events(speed: float) -> List[Dict]:
    """构造速度事件"""
    return [{
        "easingLeft": 0.0,
        "easingRight": 1.0,
        "easingType": 1,
        "end": speed,
        "endTime": [0, 0, 1],
        "linkgroup": 0,
        "start": speed,
        "startTime": [0, 0, 1]
    }]


def build_judge_line(name: str, notes: List[Dict], speed_events: List[Dict], y_offset: float) -> Dict:
    """构造判定线"""
    return {
        "Group": 0,
        "Name": name,
        "Texture": "line.png",
        "alphaControl": [{"alpha": 1.0, "easing": 1, "x": 0.0}, {"alpha": 1.0, "easing": 1, "x": 9999999.0}],
        "anchor": [0.5, 0.5],
        "bpmfactor": 1.0,
        "eventLayers": [{
            "alphaEvents": [{
                "bezier": 0, "bezierPoints": [0.0, 0.0, 0.0, 0.0],
                "easingLeft": 0.0, "easingRight": 1.0, "easingType": 1,
                "end": ChartConstants.DEFAULT_ALPHA, "endTime": [1, 0, 1],
                "linkgroup": 0, "start": ChartConstants.DEFAULT_ALPHA, "startTime": [0, 0, 1]
            }],
            "moveXEvents": [{
                "bezier": 0, "bezierPoints": [0.0, 0.0, 0.0, 0.0],
                "easingLeft": 0.0, "easingRight": 1.0, "easingType": 1,
                "end": 0.0, "endTime": [1, 0, 1], "linkgroup": 0,
                "start": 0.0, "startTime": [0, 0, 1]
            }],
            "moveYEvents": [{
                "bezier": 0, "bezierPoints": [0.0, 0.0, 0.0, 0.0],
                "easingLeft": 0.0, "easingRight": 1.0, "easingType": 1,
                "end": y_offset, "endTime": [1, 0, 1], "linkgroup": 0,
                "start": y_offset, "startTime": [0, 0, 1]
            }],
            "rotateEvents": [{
                "bezier": 0, "bezierPoints": [0.0, 0.0, 0.0, 0.0],
                "easingLeft": 0.0, "easingRight": 1.0, "easingType": 1,
                "end": 0.0, "endTime": [1, 0, 1], "linkgroup": 0,
                "start": 0.0, "startTime": [0, 0, 1]
            }],
            "speedEvents": speed_events
        }],
        "extended": {
            "inclineEvents": [{
                "bezier": 0, "bezierPoints": [0.0, 0.0, 0.0, 0.0],
                "easingLeft": 0.0, "easingRight": 1.0, "easingType": 0,
                "end": 0.0, "endTime": [1, 0, 1], "linkgroup": 0,
                "start": 0.0, "startTime": [0, 0, 1]
            }]
        },
        "father": -1,
        "isCover": 1,
        "isGif": False,
        "notes": notes,
        "posControl": [{"easing": 1, "pos": 1.0, "x": 0.0}, {"easing": 1, "pos": 1.0, "x": 9999999.0}],
        "rotateWithFather": True,
        "sizeControl": [{"easing": 1, "size": 1, "x": 9999999}, {"easing": 1, "size": 1, "x": 0}],
        "skewControl": [{"easing": 1, "skew": 0.0, "x": 0.0}, {"easing": 1, "skew": 0, "x": 0}],
        "yControl": [{"easing": 1, "x": 999999, "y": 1}, {"easing": 4, "x": 0, "y": 1}],
        "zOrder": 0
    }


def build_output_chart(note_phi: List[Dict], note_ex: List[Dict], config: ConvertConfig) -> Dict:
    """组装最终输出"""
    speed_events = build_speed_events(config.speed)
    
    line_main = build_judge_line("Untitled", note_phi, speed_events, -300.0)
    line_hold = build_judge_line("Hold", note_ex, speed_events, 1000.0)
    line_hold["eventLayers"][0]["alphaEvents"][0]["end"] = 0
    line_hold["eventLayers"][0]["alphaEvents"][0]["start"] = 0
    
    return {
        "BPMList": [{"bpm": 60000, "startTime": [0, 0, 1]}],
        "META": {
            "RPEVersion": 170,
            "background": "cover.png",
            "charter": config.charter,
            "composer": config.composer,
            "id": "123456",
            "illustration": "",
            "level": config.hard,
            "name": config.song,
            "offset": 0,
            "song": config.audio_filename
        },
        "chartTime": ChartConstants.CHART_TIME_MAX,
        "judgeLineGroup": ["Default"],
        "judgeLineList": [line_main, line_hold],
        "multiLineString": "0:10",
        "multiScale": 1.0,
        "xybind": False
    }


# ========== 主函数 ==========
def convert_core(
    json_path: Union[str, Dict],
    speed: float,
    song: str,
    composer: str,
    charter: str,
    hard: str,
    speed_coeff: float,
    speed_exp: float,
    width_coeff: float,
    width_exp: float,
    base_width_mult: float,
    flick_click: bool,
    hold_drag_interval: int,
    hold_alpha: int,
    appear_by_judge_order: bool,
    audio_filename: str,
    enable_sound_visualization: bool
) -> Optional[Dict]:
    """
    转换谱面核心函数
    
    所有参数由调用方提供，无默认值
    """
    config = ConvertConfig(
        speed=speed,
        song=song,
        composer=composer,
        charter=charter,
        hard=hard,
        audio_filename=audio_filename,
        speed_coeff=speed_coeff,
        speed_exp=speed_exp,
        width_coeff=width_coeff,
        width_exp=width_exp,
        base_width_mult=base_width_mult,
        flick_click=flick_click,
        hold_drag_interval=hold_drag_interval,
        hold_alpha=hold_alpha,
        appear_by_judge_order=appear_by_judge_order,
        enable_sound_visualization=enable_sound_visualization
    )
    
    data = load_json_data(json_path)
    if data is None:
        return None
    
    notes_data = data.get("notes", [])
    links_data = data.get("links", [])
    
    if not notes_data:
        return None
    
    note_list = parse_notes(notes_data, config, speed)
    slide_flags = compute_slide_flags(len(note_list), links_data)
    
    if appear_by_judge_order:
        adjust_appear_times_by_judge_order(note_list)
    
    note_phi = build_regular_notes(note_list, slide_flags, config)
    hold_bodies, drag_points = build_hold_notes(note_list, config)
    
    # Hold 主体加到 note_phi（主判定线）
    note_phi.extend(hold_bodies)
    
    # 拖拽点加到 note_ex（第二条透明判定线）
    note_ex = drag_points
    
    return build_output_chart(note_phi, note_ex, config)