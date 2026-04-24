import streamlit as st
import os
import tempfile
import zipfile
import shutil
from main import process_single_file

st.set_page_config(
    page_title="Deemo I/II to Phigros",
    layout="centered"
)

if 'is_converting' not in st.session_state:
    st.session_state.is_converting = False

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), "settings.txt")
    defaults = {
        "speed": 10.0,
        "speed_coeff": 1.0,
        "speed_exp": 1.0,
        "width_coeff": 1.0,
        "width_exp": 1.0,
        "base_width_mult": 1.0,
        "flick_click": True,
        "hold_interval": 80,
        "hold_alpha": 165,
        "convert_mp3_to_ogg": False,
        "appear_by_judge_order": True,
        "enable_sound_viz": False,
    }
    
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, val = line.split('=', 1)
                        val = val.strip().lower()
                        if key in defaults:
                            if isinstance(defaults[key], bool):
                                defaults[key] = val in ('true', '1')
                            elif isinstance(defaults[key], int):
                                defaults[key] = int(float(val))
                            elif isinstance(defaults[key], float):
                                defaults[key] = float(val)
                            else:
                                defaults[key] = val
        except:
            pass
    return defaults

default_settings = load_settings()

st.markdown("""
<style>
    .title-text {
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-title {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        margin-top: 0.5rem;
        border-left: 4px solid #3A302A;
        padding-left: 0.8rem;
    }
    .stSlider {
        accent-color: #3A302A !important;
    }
    .stSlider div[data-baseweb="slider"] div[role="slider"] {
        background-color: #3A302A !important;
        border-color: #3A302A !important;
    }
    .stSlider div[data-baseweb="slider"] div[data-testid="track"] div:first-child {
        background-color: #3A302A !important;
    }
    .stSlider div[data-baseweb="slider"] div[data-testid="track"] {
        background-color: #D1C2B4 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #3A302A !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #5a4a3a !important;
        color: white !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem !important;
    }
    hr {
        margin: 0.5rem 0;
    }
    .stFileUploader [data-testid="stFileUploaderFileType"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-text">Deemo I/II to Phigros</h1>', unsafe_allow_html=True)
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-title">📁 导入谱面</div>', unsafe_allow_html=True)
    st.caption("支持.zip/.dnt格式")
    uploaded_files = st.file_uploader(
        "选择谱面文件",
        type=['zip', 'dnt', 'application/octet-stream'],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    if uploaded_files:
        st.markdown(f'已选择 {len(uploaded_files)} 个文件')
        for f in uploaded_files:
            st.markdown(f'- 📄 {f.name}')

with col2:
    st.markdown('<div class="section-title">🖼️ 曲绘图片</div>', unsafe_allow_html=True)
    st.caption("可选，不选则自动提取")
    user_cover = st.file_uploader(
        "选择图片",
        type=['png', 'jpg', 'jpeg'],
        label_visibility="collapsed"
    )

st.markdown("---")

with st.expander("📝 谱面信息", expanded=False):
    custom_filename = st.text_input("文件名", placeholder="若不填写则自动生成", label_visibility="visible")
    
    col1, col2 = st.columns(2)
    with col1:
        custom_song = st.text_input("曲名", placeholder="若不填写则自动识别")
        custom_charter = st.text_input("谱师", placeholder="若不填写则自动识别")
    with col2:
        custom_composer = st.text_input("曲师", placeholder="若不填写则自动识别")
        custom_hard = st.text_input("难度", placeholder="若不填写则自动识别")

with st.expander("⚙️ 谱面参数", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        speed = st.slider("基础流速", 1.0, 20.0, default_settings["speed"], 0.1)
        speed_coeff = st.slider("流速映射系数", 0.0, 1.0, default_settings["speed_coeff"], 0.05)
        speed_exp = st.slider("流速映射指数", 0.0, 3.0, default_settings["speed_exp"], 0.05)
        width_coeff = st.slider("键宽映射系数", 0.0, 1.0, default_settings["width_coeff"], 0.05)
    with col2:
        base_width_mult = st.slider("基础键宽", 0.0, 5.0, default_settings["base_width_mult"], 0.01)
        width_exp = st.slider("键宽映射指数", 0.0, 3.0, default_settings["width_exp"], 0.05)
        hold_interval = st.slider("Hold 填充 Drag 间隔(ms)", 5, 500, default_settings["hold_interval"], 5)
        hold_alpha = st.slider("Hold 透明度", 0, 255, default_settings["hold_alpha"], 1)
    
    col1, col2 = st.columns(2)
    with col1:
        flick_click = st.checkbox("Flick 需要点击", value=default_settings["flick_click"])
        appear_order = st.checkbox("Note按判定顺序出现", value=default_settings["appear_by_judge_order"])
    with col2:
        convert_mp3 = st.checkbox("将 .mp3 转换为 .ogg", value=default_settings["convert_mp3_to_ogg"])

progress_placeholder = st.empty()
status_placeholder = st.empty()

convert_clicked = st.button("🎵 开始转换", type="primary", use_container_width=True)

if convert_clicked and not st.session_state.is_converting:
    if not uploaded_files:
        st.error("请先选择谱面文件")
    else:
        st.session_state.is_converting = True
        
        temp_output = tempfile.mkdtemp()
        
        cover_path = None
        if user_cover:
            cover_path = os.path.join(temp_output, "user_cover.png")
            with open(cover_path, "wb") as f:
                f.write(user_cover.getbuffer())
        
        success_files = []
        fail_list = []
        total = len(uploaded_files)
        
        import uuid

        for idx, file in enumerate(uploaded_files):
            # 保存原始文件名
            original_name = file.name
            
            # 生成随机临时文件名（保证不包含中文）
            ext = os.path.splitext(file.name)[1]
            temp_filename = f"{uuid.uuid4().hex}{ext}"
            
            status_placeholder.info(f"正在转换: {original_name} ({idx+1}/{total})")
            progress_placeholder.progress(idx / total)
            
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, temp_filename)
            with open(temp_path, 'wb') as f:
                f.write(file.getbuffer())
            
            try:
                print(f"DEBUG: original_name = {repr(original_name)}")
                success, msg = process_single_file(
                    zip_path=temp_path,
                    output_dir=temp_output,
                    speed=speed,
                    speed_coeff=speed_coeff,
                    speed_exp=speed_exp,
                    width_coeff=width_coeff,
                    width_exp=width_exp,
                    base_width_mult=base_width_mult,
                    flick_click=flick_click,
                    hold_interval=hold_interval,
                    hold_alpha=hold_alpha,
                    custom_filename=custom_filename,
                    custom_song=custom_song,
                    custom_composer=custom_composer,
                    custom_charter=custom_charter,
                    custom_hard=custom_hard,
                    convert_mp3_to_ogg=convert_mp3,
                    appear_by_judge_order=appear_order,
                    user_cover_path=cover_path,
                    enable_sound_visualization=False,
                    original_filename=original_name  # 传递原始中文名
                )
                if success:
                    if isinstance(msg, list):
                        success_files.extend(msg)
                    else:
                        success_files.append(msg)
                    st.success(f"✅ {original_name} 转换成功")
                else:
                    fail_list.append(f"{original_name}: {msg}")
                    st.error(f"❌ {original_name} 失败: {msg}")
            except Exception as e:
                fail_list.append(f"{original_name}: {str(e)}")
                st.error(f"❌ {original_name} 出错: {str(e)}")
            finally:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
        progress_placeholder.progress(1.0)
        
        if success_files:
            temp_output = os.path.dirname(success_files[0])
            
            # 获取原始上传的文件名
            original_name = None
            if len(uploaded_files) == 1:
                original_name = os.path.splitext(uploaded_files[0].name)[0]
            
            # 显示成功信息
            status_placeholder.success(f"转换完成！成功: {len(success_files)}, 失败: {len(fail_list)}")
            
            # 逐个显示下载按钮
            for i, fpath in enumerate(success_files):
                with open(fpath, 'rb') as f:
                    file_data = f.read()
                st.download_button(
                    label=f"📥 下载 {os.path.basename(fpath)}",
                    data=file_data,
                    file_name=os.path.basename(fpath).encode('utf-8').decode('utf-8'),
                    mime="application/octet-stream",
                    use_container_width=True,
                    key=f"download_{i}"
                )
            
            # 如果文件数量大于1，额外提供打包下载选项
            if len(success_files) > 1:
                st.markdown("---")
                st.markdown("**或者打包下载全部文件：**")
                
                zip_path = os.path.join(temp_output, "temp.zip")
                with zipfile.ZipFile(zip_path, 'w') as zf:
                    for fpath in success_files:
                        zf.write(fpath, os.path.basename(fpath))
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                if original_name:
                    zip_filename = f"{original_name}_pez.zip"
                else:
                    zip_filename = "converted_files_pez.zip"
                
                st.download_button(
                    label=f"📦 打包下载全部 ({len(success_files)} 个文件)",
                    data=zip_data,
                    file_name=zip_filename,
                    mime="application/zip",
                    use_container_width=True,
                    key="download_pack"
                )
            
  
        else:
            status_placeholder.error(f"转换失败！全部 {len(fail_list)} 个文件失败")
        
        st.session_state.is_converting = False

st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)

if st.session_state.is_converting:
    st.warning("转换进行中，请稍候...")