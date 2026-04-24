import struct
from typing import List, Dict, Any, Tuple

def read_uleb128(data: bytes, offset: int) -> Tuple[int, int]:
    value = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        value |= (b & 0x7F) << shift
        shift += 7
        if (b & 0x80) == 0:
            break
    return value, offset

def read_utf8_string(data: bytes, offset: int) -> Tuple[str, int]:
    length, offset = read_uleb128(data, offset)
    string_bytes = data[offset:offset + length]
    offset += length
    return string_bytes.decode('utf-8'), offset


class ChartParser:
    def __init__(self, raw_data: bytes):
        self.data = raw_data
        self.offset = 0
        # print(f"初始化: 数据总长度 = {len(raw_data)} 字节")
    
    def read_int32(self) -> int:
        if self.offset + 4 > len(self.data):
            raise EOFError(f"读取INT32失败: 需要4字节, 剩余{len(self.data)-self.offset}字节")
        val = struct.unpack('<i', self.data[self.offset:self.offset+4])[0]
        self.offset += 4
        return val
    
    def read_float32(self) -> float:
        if self.offset + 4 > len(self.data):
            raise EOFError(f"读取FLOAT32失败: 需要4字节, 剩余{len(self.data)-self.offset}字节")
        val = struct.unpack('<f', self.data[self.offset:self.offset+4])[0]
        self.offset += 4
        return val
    
    def read_bool(self) -> bool:
        if self.offset >= len(self.data):
            raise EOFError(f"读取BOOL失败: 无数据")
        val = self.data[self.offset] != 0
        self.offset += 1
        return val
    
    def parse_chart_footer(self) -> Dict[str, Any]:
        footer = {}
        
        # 1. BackgroundSoundNotes 部分
        bg_sound_note_count = self.read_int32()
        footer['bg_sound_note_count'] = bg_sound_note_count
        footer['bg_sound_notes'] = []
        
        for _ in range(bg_sound_note_count):
            bg_note = {
                'time': self.read_float32(),
                'piano_event_count': self.read_int32(),
                'piano_events': []
            }
            
            # 解析钢琴音效列表
            for _ in range(bg_note['piano_event_count']):
                bg_note['piano_events'].append({
                    'delay': self.read_float32(),
                    'duration': self.read_float32(),
                    'pitch': self.read_int32(),
                    'volume': self.read_int32()
                })
            
            footer['bg_sound_notes'].append(bg_note)
        
        # 2. SpeedChangeWarnings 部分
        speed_change_warning_count = self.read_int32()
        footer['speed_change_warning_count'] = speed_change_warning_count
        footer['speed_change_warnings'] = []
        
        for _ in range(speed_change_warning_count):
            footer['speed_change_warnings'].append({
                'time': self.read_float32()
            })
        
        # 3. SpeedLines 部分
        speed_line_count = self.read_int32()
        footer['speed_line_count'] = speed_line_count
        footer['speed_lines'] = []
        
        for _ in range(speed_line_count):
            footer['speed_lines'].append({
                'start_time': self.read_float32(),
                'speed': self.read_float32(),
                'warning_type': self.read_int32()
            })
        
        return footer
    
    def parse_piano_event(self) -> Dict[str, Any]:
        return {
            'w': self.read_float32(),
            'd': self.read_float32(),
            'p': self.read_int32(),
            'v': self.read_int32()
        }
    
    def parse_note(self) -> Dict[str, Any]:
        
        # print(f"      解析 Note 起始偏移: {self.offset}")
        # print(f"      原始数据: {self.data[self.offset:self.offset+32].hex().upper()}")
        note = {
            'position': self.read_float32(),
            'time': self.read_float32(),
            'size': self.read_float32(),
            'hold_duration': self.read_float32(),
            'type': self.read_int32(),
            'speed': self.read_float32(),
            'piano_events': []
        }
        
        piano_count = self.read_int32()
        # print(f"    钢琴音数量: {piano_count}")
        
        for _ in range(piano_count):
            note['piano_events'].append(self.parse_piano_event())
        
        note['shift'] = self.read_float32()
        note['event_id'], self.offset = read_utf8_string(self.data, self.offset)
        placeholder = self.read_int32()
        note['vibrate'] = self.read_bool()
        note['linked_id'] = self.read_int32()
        
        return note
    
    def parse_chart(self) -> Dict[str, Any]:
        # print(f"\n[解析谱面] 当前偏移: {self.offset}")
        
        name, self.offset = read_utf8_string(self.data, self.offset)
        # print(f"  名称: '{name}' (长度={len(name)})")
        
        difficulty_code = self.read_int32()
        # print(f"  难度代码: {difficulty_code}")
        
        level_name, self.offset = read_utf8_string(self.data, self.offset)
        # print(f"  等级: '{level_name}'")
        
        speed = self.read_float32()
        # print(f"  Speed: {speed}")
        
        remap_min_vol = self.read_int32()
        remap_max_vol = self.read_int32()
        # print(f"  音量映射: {remap_min_vol} - {remap_max_vol}")
        
        note_count = self.read_int32()
        # print(f"  音符数量: {note_count}")
        
        difficulty_map = {0: 'EASY', 1: 'NORMAL', 2: 'HARD', 3: 'EXTRA'}
        
        chart = {
            'name': name,
            'difficulty_code': difficulty_code,
            'difficulty': difficulty_map.get(difficulty_code, 'UNKNOWN'),
            'level': level_name,
            'speed': speed,
            'remap_min_volume': remap_min_vol,
            'remap_max_volume': remap_max_vol,
            'note_count': note_count,
            'notes': []
        }
        
        for i in range(note_count):
            # if i < 3:  # 只打印前3个音符的调试信息
            #     print(f"\n  解析音符 {i+1}/{note_count}")
            chart['notes'].append(self.parse_note())
        
        # print(f"\n  解析谱面尾部...")
        chart['footer'] = self.parse_chart_footer()
        
        return chart
    
    def parse_bpm_list(self) -> List[Dict[str, Any]]:
        bpm_count = self.read_int32()
        # print(f"\n[BPM列表] 数量: {bpm_count}")
        bpm_list = []
        for _ in range(bpm_count):
            bpm_list.append({
                'bpm': self.read_float32(),
                'start_time': self.read_float32()
            })
        return bpm_list

    
    def parse_all(self) -> Dict[str, Any]:
        # 解析文件头 + 元信息

        chart_count = self.read_int32()
        charts = []
        for _ in range(chart_count):
            charts.append(self.parse_chart())

        bpm_list = self.parse_bpm_list()

        return {
            "chart_count": chart_count,
            "charts": charts,
            "bpm_list": bpm_list
        }