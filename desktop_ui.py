import json
import os
import zipfile
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import shutil
import configparser
from tkinter import font
import threading
import tkinter.ttk as ttk
_ui_running = False
# 导入你的模块
from dnt_reader import get_charts_from_dnt
from dnt_extractor import extract_audio_auto
from convert_core_function import convert_core 
from main import process_single_file
def batch_ui():
    global _ui_running
    if _ui_running:
        return
    _ui_running = True

    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # ==========================
    # 主题系统
    # ==========================
    theme = {}

    def load_theme_from_file():
        path = filedialog.askopenfilename(
            title="选择主题文件",
            filetypes=[("主题文件", "*.json")],
            initialdir=os.path.join(BASE_DIR, "themes")
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                nonlocal theme
                theme = json.load(f)
            apply_theme()
            with open(last_theme_path, "w", encoding="utf-8") as f:
                f.write(path)
        except Exception as e:
            messagebox.showerror("错误", f"主题加载失败：{str(e)}")

    def load_default_theme():
        if os.path.exists(last_theme_path):
            try:
                with open(last_theme_path, "r", encoding="utf-8") as f:
                    saved_path = f.read().strip()
                if os.path.exists(saved_path):
                    with open(saved_path, "r", encoding="utf-8") as f:
                        return json.load(f)
            except:
                pass

        default_theme_path = os.path.join(BASE_DIR, "themes", "deemo.json")
        if os.path.exists(default_theme_path):
            with open(default_theme_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "light": {
                "bg": "#F7F2E9",
                "entry_bg": "#FFFFFF",
                "text": "#3D322C",
                "btn_bg": "#3A302A",
                "btn_text": "#FFFFFF",
                "scale_trough": "#E2D8CC",
                "entry_border": "#D1C2B4",
                "check_fg": "#3A302A",
                "placeholder": "#A89A8A"
            },
            "dark": {
                "bg": "#14100B",
                "entry_bg": "#27221C",
                "text": "#F0EAE0",
                "btn_bg": "#E2D8CC",
                "btn_text": "#1A1612",
                "scale_trough": "#4A3E34",
                "entry_border": "#6B594C",
                "check_fg": "#F0EAE0",
                "placeholder": "#B4A494"
            }
        }

    last_theme_path = os.path.join(BASE_DIR, "last_theme.txt")
    theme = load_default_theme()

    # ==========================
    # 设置
    # ==========================
    def load_default_settings():
        settings_path = os.path.join(BASE_DIR, "settings.txt")
        defaults = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, val = line.split("=", 1)
                            defaults[key.strip()] = val.strip()
            except:
                pass
        return defaults

    default_cfg = load_default_settings()

    def get_def(key, default):
        if key not in default_cfg:
            return default
        val = default_cfg[key].lower()
        if isinstance(default, bool):
            return val in ("true", "1")
        return type(default)(val)

    # ==========================
    # 窗口
    # ==========================
    root = tk.Tk()
    root.title("Deemo I/II to Phigros")
    root.geometry("720x720")
    root.resizable(False, False)

    def resource_path_local(p):
        try:
            return os.path.join(sys._MEIPASS, p)
        except:
            return os.path.abspath(p)

    try:
        root.iconbitmap(resource_path_local("piano.ico"))
    except:
        pass

    def on_closing():
        global _ui_running
        _ui_running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # 字体
    try:
        path_font = resource_path_local("LXGWWenKai-Regular.ttf")
        font.Font(family='LXGW WenKai', file=path_font)
    except:
        pass

    FONT_TITLE = ("LXGW WenKai", 22, "bold")
    FONT_LABEL = ("LXGW WenKai", 14)
    FONT_ENTRY = ("LXGW WenKai", 13)
    FONT_BUTTON = ("LXGW WenKai", 13)
    FONT_BUTTON_START = ("LXGW WenKai", 16, "bold")
    FONT_META_LABEL = ("LXGW WenKai", 15, "bold")
    FONT_META_ROW = ("LXGW WenKai", 14)
    FONT_SUFFIX = ("LXGW WenKai", 14, "bold")
    FONT_SPEED_LABEL = ("LXGW WenKai", 15, "bold")
    FONT_SCALE = ("LXGW WenKai", 12)
    FONT_ADV_BTN = ("LXGW WenKai", 14)
    FONT_SLIDER_LABEL = ("LXGW WenKai", 13)
    FONT_SLIDER_SCALE = ("LXGW WenKai", 11)
    FONT_CHECK = ("LXGW WenKai", 14)
    FONT_TOGGLE_BTN = ("LXGW WenKai", 13)

    # ==========================
    # 变量
    # ==========================
    current_mode = tk.StringVar(value="light")
    zip_paths = tk.StringVar()
    out_dir = tk.StringVar(value=get_def("output_dir", os.path.join(BASE_DIR, "output")))
    speed = tk.DoubleVar(value=get_def("speed", 10.0))
    speed_coeff = tk.DoubleVar(value=get_def("speed_coeff", 1.0))
    speed_exp = tk.DoubleVar(value=get_def("speed_exp", 1.0))
    width_coeff = tk.DoubleVar(value=get_def("width_coeff", 1.0))
    width_exp = tk.DoubleVar(value=get_def("width_exp", 1.0))
    base_width_mult = tk.DoubleVar(value=get_def("base_width_mult", 1.0))
    flick_click = tk.BooleanVar(value=get_def("flick_click", True))
    hold_interval = tk.IntVar(value=get_def("hold_interval", 80))
    hold_alpha = tk.IntVar(value=get_def("hold_alpha", 165))
    adv_show = tk.BooleanVar(value=False)
    convert_mp3_to_ogg = tk.BooleanVar(value=get_def("convert_mp3_to_ogg", False))
    appear_by_judge_order = tk.BooleanVar(value=get_def("appear_by_judge_order", True))
    enable_sound_viz = tk.BooleanVar(value=get_def("enable_sound_visualization", False))

    custom_filename = tk.StringVar()
    custom_song = tk.StringVar()
    custom_composer = tk.StringVar()
    custom_charter = tk.StringVar()
    custom_hard = tk.StringVar()
    user_cover_path = tk.StringVar()

    # ==========================
    # 占位符
    # ==========================
    def add_placeholder(entry, placeholder_text):
        entry.placeholder_text = placeholder_text

        def update():
            t = theme[current_mode.get()]
            if entry.get() == placeholder_text:
                entry.config(fg=t["placeholder"])
            else:
                entry.config(fg=t["text"])

        entry.insert(0, placeholder_text)
        update()

        def on_focus(e):
            if entry.get() == placeholder_text:
                entry.delete(0, tk.END)
            update()

        def on_blur(e):
            if not entry.get().strip():
                entry.insert(0, placeholder_text)
            update()

        entry.bind("<FocusIn>", on_focus)
        entry.bind("<FocusOut>", on_blur)
        entry.update_placeholder_style = update

    # ==========================
    # 主题应用
    # ==========================
    def apply_theme_to_widget(widget, t):
        try:
            if isinstance(widget, tk.Entry):
                widget.config(bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], bd=1, relief="solid")
            elif isinstance(widget, tk.Button):
                if "开始转换" in widget.cget("text") or "转换中" in widget.cget("text"):
                    widget.config(bg=t["text"], fg=t["bg"])
                elif "取消" in widget.cget("text"):
                    pass
                else:
                    widget.config(bg=t["btn_bg"], fg=t["btn_text"])
            elif isinstance(widget, tk.Label):
                widget.config(bg=t["bg"], fg=t["text"])
            elif isinstance(widget, tk.Frame):
                widget.config(bg=t["bg"])
            elif isinstance(widget, tk.Scale):
                widget.config(bg=t["bg"], fg=t["text"], troughcolor=t["scale_trough"])
            elif isinstance(widget, tk.Checkbutton):
                widget.config(bg=t["bg"], fg=t["check_fg"], selectcolor=t["bg"])
            elif isinstance(widget, ttk.Progressbar):
                pass
        except:
            pass
        for child in widget.winfo_children():
            apply_theme_to_widget(child, t)

    def apply_theme():
        t = theme[current_mode.get()]
        root.config(bg=t["bg"])
        apply_theme_to_widget(root, t)
        toggle_btn.config(text="🌞日间模式" if current_mode.get() == "dark" else "🌙夜间模式")

        def refresh(w):
            if hasattr(w, "update_placeholder_style"):
                w.update_placeholder_style()
            for c in w.winfo_children():
                refresh(c)
        refresh(root)

    def toggle_mode():
        current_mode.set("dark" if current_mode.get() == "light" else "light")
        apply_theme()

    # ==========================
    # 功能函数
    # ==========================
    def select_zips():
        files = filedialog.askopenfilenames(filetypes=[("Deemo 谱面", "*.zip;*.dnt;")])
        if files:
            zip_paths.set("|".join(files))

    def select_out():
        d = filedialog.askdirectory()
        if d:
            out_dir.set(d)

    def select_cover():
        p = filedialog.askopenfilename(filetypes=[("图片", "*.png;*.jpg;*.jpeg")])
        if p:
            user_cover_path.set(p)

    def set_current_as_default():
        settings = {
            "speed": speed.get(),
            "speed_coeff": speed_coeff.get(),
            "speed_exp": speed_exp.get(),
            "width_coeff": width_coeff.get(),
            "width_exp": width_exp.get(),
            "base_width_mult": base_width_mult.get(),
            "flick_click": flick_click.get(),
            "hold_interval": hold_interval.get(),
            "hold_alpha": hold_alpha.get(),
            "convert_mp3_to_ogg": convert_mp3_to_ogg.get(),
            "appear_by_judge_order": appear_by_judge_order.get(),
            "enable_sound_visualization": enable_sound_viz.get(),
            "output_dir": out_dir.get()
        }
        settings_path = os.path.join(BASE_DIR, "settings.txt")
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                for k, v in settings.items():
                    f.write(f"{k}={v}\n")
            messagebox.showinfo("成功", "当前参数已保存为默认！")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{str(e)}")

    def reset_to_factory_default():
        speed.set(10.0)
        speed_coeff.set(1.0)
        speed_exp.set(1.0)
        width_coeff.set(1.0)
        width_exp.set(1.0)
        base_width_mult.set(1.0)
        flick_click.set(True)
        hold_interval.set(80)
        hold_alpha.set(165)
        convert_mp3_to_ogg.set(False)
        appear_by_judge_order.set(True)
        enable_sound_viz.set(False)
        out_dir.set(os.path.join(BASE_DIR, "output"))
        messagebox.showinfo("已恢复", "已重置为出厂参数")

    def load_user_default():
        default_cfg = load_default_settings()
        def get_def(key, default):
            if key not in default_cfg:
                return default
            val = default_cfg[key].strip().lower()
            if isinstance(default, bool):
                return val == "true" or val == "1"
            return type(default)(val)

        speed.set(get_def("speed", 10.0))
        speed_coeff.set(get_def("speed_coeff", 1.0))
        speed_exp.set(get_def("speed_exp", 1.0))
        width_coeff.set(get_def("width_coeff", 1.0))
        width_exp.set(get_def("width_exp", 1.0))
        base_width_mult.set(get_def("base_width_mult", 1.0))
        flick_click.set(get_def("flick_click", True))
        hold_interval.set(get_def("hold_interval", 80))
        hold_alpha.set(get_def("hold_alpha", 165))
        convert_mp3_to_ogg.set(get_def("convert_mp3_to_ogg", False))
        appear_by_judge_order.set(get_def("appear_by_judge_order", True))
        enable_sound_viz.set(get_def("enable_sound_visualization", False))
        out_dir.set(get_def("output_dir", os.path.join(BASE_DIR, "output")))
        messagebox.showinfo("已加载", "已恢复为你保存的默认参数")

    def toggle_adv():
        adv_show.set(not adv_show.get())
        if adv_show.get():
            adv_frame.grid()
            root.geometry("720x1120")
        else:
            adv_frame.grid_remove()
            root.geometry("720x720")

    # ==========================
    # 转换相关（多线程）
    # ==========================
    is_converting = False
    cancel_convert = False

    def update_progress(current, total, status_text):
        def _update():
            if total > 0:
                progress_bar['value'] = (current / total) * 100
            progress_label.config(text=status_text)
            progress_frame.grid()
        root.after(0, _update)

    def hide_progress():
        def _hide():
            progress_frame.grid_remove()
            progress_bar['value'] = 0
            progress_label.config(text="")
        root.after(0, _hide)

    def convert_worker(zip_list, output, settings):
        nonlocal is_converting, cancel_convert
        
        success_count = 0
        fail_count = 0
        fail_list = []
        total = len(zip_list)
        
        for idx, zip_path in enumerate(zip_list):
            if cancel_convert:
                update_progress(idx, total, f"已取消转换")
                break
            
            if not zip_path:
                continue
            
            filename = os.path.basename(zip_path)
            update_progress(idx, total, f"正在转换: {filename} ({idx+1}/{total})")
            
            success, msg = process_single_file(
                zip_path=zip_path,
                output_dir=output,
                speed=settings['speed'],
                speed_coeff=settings['speed_coeff'],
                speed_exp=settings['speed_exp'],
                width_coeff=settings['width_coeff'],
                width_exp=settings['width_exp'],
                base_width_mult=settings['base_width_mult'],
                flick_click=settings['flick_click'],
                hold_interval=settings['hold_interval'],
                hold_alpha=settings['hold_alpha'],
                custom_filename=settings['custom_filename'],
                custom_song=settings['custom_song'],
                custom_composer=settings['custom_composer'],
                custom_charter=settings['custom_charter'],
                custom_hard=settings['custom_hard'],
                convert_mp3_to_ogg=settings['convert_mp3_to_ogg'],
                appear_by_judge_order=settings['appear_by_judge_order'],
                user_cover_path=settings['user_cover_path'],
                enable_sound_visualization=settings.get('enable_sound_visualization', False)
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                fail_list.append(f"{filename}: {msg}")
        
        def show_result():
            nonlocal is_converting
            is_converting = False
            convert_btn.config(text="开始转换 🎵", state="normal")
            cancel_btn.grid_remove()
            hide_progress()
            
            result_msg = f"转换完成！\n成功: {success_count}\n失败: {fail_count}"
            if fail_list:
                result_msg += "\n\n失败详情:\n" + "\n".join(fail_list[:5])
                if len(fail_list) > 5:
                    result_msg += f"\n... 等{len(fail_list)}个"
            
            if success_count > 0 or fail_count > 0:
                messagebox.showinfo("完成", result_msg)
        
        root.after(0, show_result)

    def start_convert():
        nonlocal is_converting, cancel_convert
        
        if is_converting:
            return
        
        zip_list = zip_paths.get().split("|") if zip_paths.get() else []
        if not zip_list:
            messagebox.showerror("错误", "请先选择谱面文件")
            return
        
        output = out_dir.get()
        if not output:
            messagebox.showerror("错误", "请选择输出目录")
            return
        
        if not os.path.exists(output):
            os.makedirs(output, exist_ok=True)
        
        settings = {
            'speed': speed.get(),
            'speed_coeff': speed_coeff.get(),
            'speed_exp': speed_exp.get(),
            'width_coeff': width_coeff.get(),
            'width_exp': width_exp.get(),
            'base_width_mult': base_width_mult.get(),
            'flick_click': flick_click.get(),
            'hold_interval': hold_interval.get(),
            'hold_alpha': hold_alpha.get(),
            'custom_filename': custom_filename.get(),
            'custom_song': custom_song.get(),
            'custom_composer': custom_composer.get(),
            'custom_charter': custom_charter.get(),
            'custom_hard': custom_hard.get(),
            'convert_mp3_to_ogg': convert_mp3_to_ogg.get(),
            'appear_by_judge_order': appear_by_judge_order.get(),
            'user_cover_path': user_cover_path.get() if user_cover_path.get() else None,
            'enable_sound_visualization': enable_sound_viz.get()
        }
        
        is_converting = True
        cancel_convert = False
        
        convert_btn.config(text="转换中...", state="disabled")
        cancel_btn.grid()
        progress_bar['value'] = 0
        progress_frame.grid()
        
        thread = threading.Thread(
            target=convert_worker,
            args=(zip_list, output, settings),
            daemon=True
        )
        thread.start()

    def cancel_conversion():
        nonlocal cancel_convert
        cancel_convert = True
        update_progress(0, 1, "正在取消...")

    # ==========================
    # 布局
    # ==========================
    root.grid_rowconfigure(0, weight=0)
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # 标题栏
    title_frame = tk.Frame(root)
    title_frame.grid(row=0, column=0, sticky="ew", pady=16)
    title_frame.grid_columnconfigure(0, weight=1)

    title_label = tk.Label(title_frame, text="Deemo I/II to Phigros Ver II", font=FONT_TITLE)
    title_label.grid(row=0, column=0, sticky="w", padx=25)

    right_frame = tk.Frame(title_frame)
    right_frame.grid(row=0, column=1, sticky="e", padx=25)

    theme_btn = tk.Button(right_frame, text="加载主题", command=load_theme_from_file, font=FONT_TOGGLE_BTN)
    theme_btn.grid(row=0, column=0, padx=4)

    toggle_btn = tk.Button(right_frame, text="🌙夜间模式", command=toggle_mode, font=FONT_TOGGLE_BTN)
    toggle_btn.grid(row=0, column=1, padx=4)

    # 主内容
    main_frame = tk.Frame(root)
    main_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=10)
    main_frame.grid_columnconfigure(0, weight=1)

    # 导入谱面
    row0 = tk.Frame(main_frame)
    row0.grid(row=0, column=0, sticky="ew", pady=8)
    row0.grid_columnconfigure(1, weight=1)
    tk.Label(row0, text="导入谱面(.zip/.dnt)：", font=FONT_LABEL, width=16, anchor="w").grid(row=0, column=0)
    e0 = tk.Entry(row0, textvariable=zip_paths, font=FONT_ENTRY)
    e0.grid(row=0, column=1, sticky="ew", padx=6)
    tk.Button(row0, text="浏览", command=select_zips, font=FONT_BUTTON).grid(row=0, column=2)
    tk.Button(row0, text="清除", command=lambda: zip_paths.set(""), font=FONT_BUTTON).grid(row=0, column=3, padx=5)

    # 封面
    row1 = tk.Frame(main_frame)
    row1.grid(row=1, column=0, sticky="ew", pady=8)
    row1.grid_columnconfigure(1, weight=1)
    tk.Label(row1, text="选择封面：", font=FONT_LABEL, width=16, anchor="w").grid(row=0, column=0)
    e1 = tk.Entry(row1, textvariable=user_cover_path, font=FONT_ENTRY)
    e1.grid(row=0, column=1, sticky="ew", padx=6)
    tk.Button(row1, text="浏览", command=select_cover, font=FONT_BUTTON).grid(row=0, column=2)
    tk.Button(row1, text="清除", command=lambda: user_cover_path.set(""), font=FONT_BUTTON).grid(row=0, column=3, padx=5)

    # 输出
    row2 = tk.Frame(main_frame)
    row2.grid(row=2, column=0, sticky="ew", pady=8)
    row2.grid_columnconfigure(1, weight=1)
    tk.Label(row2, text="输出文件夹：", font=FONT_LABEL, width=16, anchor="w").grid(row=0, column=0)
    e2 = tk.Entry(row2, textvariable=out_dir, font=FONT_ENTRY)
    e2.grid(row=0, column=1, sticky="ew", padx=6)
    tk.Button(row2, text="浏览", command=select_out, font=FONT_BUTTON).grid(row=0, column=2)
    tk.Button(row2, text="清除", command=lambda: out_dir.set(""), font=FONT_BUTTON).grid(row=0, column=3, padx=5)

    # 谱面信息
    tk.Label(main_frame, text="谱面信息（可自动生成）", font=FONT_META_LABEL).grid(row=3, column=0, sticky="w", pady=(12, 6))

    # 文件名
    row_fn = tk.Frame(main_frame)
    row_fn.grid(row=4, sticky="ew", pady=5)
    row_fn.grid_columnconfigure(1, weight=1)
    tk.Label(row_fn, text="文件名：", font=FONT_META_ROW, width=12).grid(row=0, column=0)
    tk.Entry(row_fn, textvariable=custom_filename, font=FONT_ENTRY).grid(row=0, column=1, sticky="ew", padx=6)
    tk.Label(row_fn, text=".pez", font=FONT_SUFFIX).grid(row=0, column=2)

    # 快捷行
    def meta_row(text, var, r):
        f = tk.Frame(main_frame)
        f.grid(row=r, sticky="ew", pady=5)
        f.grid_columnconfigure(1, weight=1)
        tk.Label(f, text=text, font=FONT_META_ROW, width=12).grid(row=0, column=0)
        tk.Entry(f, textvariable=var, font=FONT_ENTRY).grid(row=0, column=1, sticky="ew", padx=6)

    meta_row("曲名：", custom_song, 5)
    meta_row("曲师：", custom_composer, 6)
    meta_row("谱师：", custom_charter, 7)
    meta_row("难度：", custom_hard, 8)

    # 流速
    tk.Label(main_frame, text="基础流速", font=FONT_SPEED_LABEL).grid(row=9, sticky="w", pady=(12, 5))
    tk.Scale(main_frame, variable=speed, from_=1, to=20, resolution=0.1, orient="horizontal",
         bd=0, highlightthickness=0).grid(row=10, sticky="ew", pady=(0, 20))
    
    # 进度条区域
    progress_frame = tk.Frame(main_frame)
    progress_frame.grid(row=11, column=0, sticky="ew", pady=(10, 5))
    progress_frame.grid_columnconfigure(0, weight=1)
    
    progress_label = tk.Label(progress_frame, text="", font=FONT_SLIDER_LABEL)
    progress_label.grid(row=0, column=0, sticky="w")
    
    progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
    progress_bar.grid(row=1, column=0, sticky="ew", pady=(5, 0))
    progress_frame.grid_remove()
    
    # 按钮行
    btn_frame = tk.Frame(main_frame)
    btn_frame.grid(row=12, sticky="ew", pady=(20, 10))
    btn_frame.grid_propagate(False)
    btn_frame.config(height=50)
    for i in range(6):
        btn_frame.grid_columnconfigure(i, weight=1)

    tk.Button(btn_frame, text="高级选项", command=toggle_adv, font=FONT_ADV_BTN).grid(row=0, column=0, sticky="w")
    tk.Button(btn_frame, text="恢复出厂", command=reset_to_factory_default, font=FONT_BUTTON).grid(row=0, column=1)
    tk.Button(btn_frame, text="加载默认", command=load_user_default, font=FONT_BUTTON).grid(row=0, column=2)
    tk.Button(btn_frame, text="保存默认", command=set_current_as_default, font=FONT_BUTTON).grid(row=0, column=3)
    
    convert_btn = tk.Button(btn_frame, text="开始转换 🎵", command=start_convert, font=FONT_BUTTON_START)
    convert_btn.grid(row=0, column=4, sticky="e")
    
    cancel_btn = tk.Button(btn_frame, text="取消", command=cancel_conversion, font=FONT_BUTTON, bg="#cc4444", fg="white")
    cancel_btn.grid(row=0, column=5, sticky="e", padx=(5, 0))
    cancel_btn.grid_remove()

    # 高级选项面板
    adv_frame = tk.Frame(main_frame)
    adv_frame.grid(row=13, column=0, sticky="nsew", pady=10)
    adv_frame.grid_columnconfigure(0, weight=1)
    adv_frame.grid_columnconfigure(1, weight=1)
    adv_frame.grid_remove()

    def double_slider_row(parent, text1, var1, from1, to1, text2, var2, from2, to2, row_num):
        row_frame = tk.Frame(parent)
        row_frame.grid(row=row_num, column=0, columnspan=2, sticky="ew", pady=4)
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, weight=1)
        
        left_f = tk.Frame(row_frame)
        left_f.grid(row=0, column=0, sticky="ew", padx=4)
        lbl1 = tk.Label(left_f, text=text1, font=FONT_SLIDER_LABEL)
        lbl1.pack(anchor="w")
        s1 = tk.Scale(left_f, variable=var1, from_=from1, to=to1, resolution=0.05, orient="horizontal", font=FONT_SLIDER_SCALE, bd=0, highlightthickness=0)
        s1.pack(fill="x")
        
        right_f = tk.Frame(row_frame)
        right_f.grid(row=0, column=1, sticky="ew", padx=4)
        lbl2 = tk.Label(right_f, text=text2, font=FONT_SLIDER_LABEL)
        lbl2.pack(anchor="w")
        s2 = tk.Scale(right_f, variable=var2, from_=from2, to=to2, resolution=0.05, orient="horizontal", font=FONT_SLIDER_SCALE, bd=0, highlightthickness=0)
        s2.pack(fill="x")

    double_slider_row(adv_frame, "流速映射系数", speed_coeff, 0, 1.0, "流速映射指数", speed_exp, 0, 3.0, 0)
    double_slider_row(adv_frame, "键宽映射系数", width_coeff, 0, 1.0, "键宽映射指数", width_exp, 0, 3.0, 1)

    bw_frame = tk.Frame(adv_frame)
    bw_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
    lbl_bw = tk.Label(bw_frame, text="基础键宽倍率", font=FONT_SLIDER_LABEL)
    lbl_bw.pack(anchor="w")
    bw_scale = tk.Scale(bw_frame, variable=base_width_mult, from_=0, to=5.0, resolution=0.01, orient="horizontal", font=FONT_SLIDER_SCALE, bd=0, highlightthickness=0)
    bw_scale.pack(fill="x")

    hold_row = tk.Frame(adv_frame)
    hold_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
    hold_row.grid_columnconfigure(0, weight=1)
    hold_row.grid_columnconfigure(1, weight=1)

    left_hold = tk.Frame(hold_row)
    left_hold.grid(row=0, column=0, sticky="ew", padx=4)
    lbl_int = tk.Label(left_hold, text="Hold 填充 Drag 间隔(ms)", font=FONT_SLIDER_LABEL)
    lbl_int.pack(anchor="w")
    int_scale = tk.Scale(left_hold, variable=hold_interval, from_=5, to=500, resolution=5, orient="horizontal", font=FONT_SLIDER_SCALE, bd=0, highlightthickness=0)
    int_scale.pack(fill="x")

    right_hold = tk.Frame(hold_row)
    right_hold.grid(row=0, column=1, sticky="ew", padx=4)
    lbl_alpha = tk.Label(right_hold, text="Hold 透明度", font=FONT_SLIDER_LABEL)
    lbl_alpha.pack(anchor="w")
    alpha_scale = tk.Scale(right_hold, variable=hold_alpha, from_=0, to=255, resolution=1, orient="horizontal", font=FONT_SLIDER_SCALE, bd=0, highlightthickness=0)
    alpha_scale.pack(fill="x")

    # 勾选框区域（两列布局）
    check_frame = tk.Frame(adv_frame)
    check_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)
    check_frame.grid_columnconfigure(0, weight=1)
    check_frame.grid_columnconfigure(1, weight=1)
    
    left_col = tk.Frame(check_frame)
    left_col.grid(row=0, column=0, sticky="w", padx=10)
    
    flick_check = tk.Checkbutton(left_col, text="Flick 需要点击", variable=flick_click, font=FONT_CHECK)
    flick_check.pack(anchor="w", pady=3)
    
    appear_order_check = tk.Checkbutton(left_col, text="Note按判定顺序出现", variable=appear_by_judge_order, font=FONT_CHECK)
    appear_order_check.pack(anchor="w", pady=3)
    
    right_col = tk.Frame(check_frame)
    right_col.grid(row=0, column=1, sticky="w", padx=10)
    
    mp3_check = tk.Checkbutton(right_col, text="将 .mp3 转换为 .ogg", variable=convert_mp3_to_ogg, font=FONT_CHECK)
    mp3_check.pack(anchor="w", pady=3)
    
    sound_viz_check = tk.Checkbutton(right_col, text="Note音可视化（测试功能）", variable=enable_sound_viz, font=FONT_CHECK)
    sound_viz_check.pack(anchor="w", pady=3)

    # ==========================
    # 最终初始化
    # ==========================
    apply_theme()
    add_placeholder(e0, "请选择谱面文件...")
    add_placeholder(e1, "选择封面（留空自动提取）")

    root.mainloop()

# ===================== 程序入口 =====================
if __name__ == "__main__":
    batch_ui()