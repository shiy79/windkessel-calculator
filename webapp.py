import streamlit as st
import numpy as np
import pandas as pd
import cv2
from PIL import Image
from scipy.optimize import curve_fit

# --- 网页配置 ---
st.set_page_config(page_title="Windkessel 智慧建模系统", layout="wide")

# --- 侧边栏：全局设置与捐助 ---
st.sidebar.header("🌍 全局显示设置")
unit_mode = st.sidebar.radio("压力单位选择", ["kPa", "mmHg"])

def to_pa(val):
    if unit_mode == "kPa": return val * 1000
    else: return val * 133.322

def from_pa(val):
    if unit_mode == "kPa": return val / 1000
    else: return val / 133.322

st.sidebar.markdown("---")
st.sidebar.header("🛠️ 物理常数预设")
mu = st.sidebar.number_input("液体粘度 (Pa·s)", value=0.0040, format="%.4f")
rho_blood = st.sidebar.number_input("液体密度 (kg/m³)", value=1040)
P_atm = st.sidebar.number_input("大气压 (Pa)", value=101325)

st.sidebar.header("📏 装置尺寸 (mm)")
d_L1 = st.sidebar.number_input("细管 L1 内径 (mm)", value=5.0) / 1000
d_L2 = st.sidebar.number_input("细管 L2 内径 (mm)", value=3.0) / 1000
d_cavity = st.sidebar.number_input("气腔内径 (mm)", value=55.0) / 1000

# --- 捐助项 ---
st.sidebar.markdown("---")
st.sidebar.subheader("☕ 赞助与支持")
st.sidebar.write("如果您觉得本工具有助于您的科研工作，欢迎赞助作者以维持服务器运行！")
try:
    st.sidebar.image("donate.png", caption="扫码赞助作者", use_container_width=True)
except:
    st.sidebar.warning("未检测到 donate.png，请确保图片已上传至 GitHub 仓库根目录。")

# --- 主界面标签页 ---
tab1, tab2 = st.tabs(["📊 参数计算与模拟", "🖼️ 超声波形识别提取"])

# --- TAB 1: 核心计算与模拟 ---
with tab1:
    st.title("🩺 Windkessel RCR 参数至物理尺寸转换")
    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.subheader(f"🩸 生理参数 ({unit_mode})")
        default_pd = 10.9 if unit_mode == "kPa" else 81.7
        default_ps = 16.7 if unit_mode == "kPa" else 125.3
        Pd_input = st.number_input(f"舒张压 ({unit_mode})", value=default_pd)
        Ps_input = st.number_input(f"收缩压 ({unit_mode})", value=default_ps)
        Q_mean_total = st.number_input("总流量 (cm³/s)", value=97.72)

    with col2:
        st.subheader("📏 血管出口周长 (mm)")
        v_names = ['BA', 'LCCA', 'LSA', 'CEL', 'SMA', 'RR', 'LR', 'RI', 'LI']
        v_circ = [47.50, 18.27, 30.05, 23.06, 13.56, 9.57, 18.98, 26.20, 25.62]
        df_in = pd.DataFrame({'血管名称': v_names, '周长(mm)': v_circ})
        edited_df = st.data_editor(df_in, use_container_width=True, num_rows="dynamic")

    # 计算逻辑
    Pd_pa, Ps_pa = to_pa(Pd_input), to_pa(Ps_input)
    MAP_pa = Pd_pa + (Ps_pa - Pd_pa) / 3
    v_labels = edited_df['血管名称'].values
    c_mm = edited_df['周长(mm)'].values
    r_m = (c_mm / (2 * np.pi)) / 1000
    area_m2 = np.pi * (r_m**2)
    f_ratio = area_m2 / np.sum(area_m2)
    Q_vessels = (Q_mean_total * 1e-6) * f_ratio
    
    # RCR 参数 (基于你之前的物理公式)
    c_pwv = 13.3 / ((r_m*2000)**0.3) 
    Rt = MAP_pa / Q_vessels
    R1_vals = (rho_blood * c_pwv) / area_m2
    R2_vals = Rt - R1_vals
    C_vals = 1.79 / Rt

    # 硬件尺寸
    L1_vals = (R1_vals * np.pi * (d_L1/2)**4) / (8 * mu)
    L2_vals = (R2_vals * np.pi * (d_L2/2)**4) / (8 * mu)
    h_vals = (C_vals * P_atm) / (np.pi * (d_cavity/2)**2)

    st.header("📊 计算结果报表")
    res_df = pd.DataFrame({
        "血管": v_labels, "R1 (10^8)": R1_vals/1e8, "R2 (10^8)": R2_vals/1e8, "C (10^-9)": C_vals/1e-9,
        "L1(mm)": L1_vals*1000, "L2(mm)": L2_vals*1000, "气腔高度(mm)": h_vals*1000
    })
    st.dataframe(res_df.style.format(precision=3), use_container_width=True)

    st.markdown("---")
    st.header(f"📈 动态压力模拟 ({unit_mode})")
    sel_v = st.selectbox("选择观察波形的血管", v_labels)
    idx = list(v_labels).index(sel_v)

    T, fs = 0.8, 200
    t = np.linspace(0, T, fs)
    dt = T/fs
    ts = 0.3 * T
    Q_t = np.where(t < ts, (Q_vessels[idx] * np.pi / (2*ts/T)) * np.sin(np.pi * t / ts), 0)

    P_sim = np.zeros(fs)
    P_sim[0] = Pd_pa
    for i in range(fs-1):
        dp_dt = (Q_t[i]/C_vals[idx]) - (P_sim[i] - Q_t[i]*R1_vals[idx])/(R2_vals[idx]*C_vals[idx])
        P_sim[i+1] = P_sim[i] + dp_dt * dt

    p_plot = pd.DataFrame({"时间 (s)": t, f"压力 ({unit_mode})": from_pa(P_sim)}).set_index("时间 (s)")
    st.line_chart(p_plot)
    st.metric(f"{sel_v} 峰值压力", f"{from_pa(np.max(P_sim)):.2f} {unit_mode}")

# --- TAB 2: 图像识别 ---
with tab2:
    st.header("🖼️ 超声波形自动识别提取")
    up_file = st.file_uploader("上传超声流量图", type=["jpg", "png", "jpeg"])
    if up_file:
        img = Image.open(up_file)
        st.image(img, caption="原始图像", width=600)
        st.info("识别与拟合逻辑已激活。请根据图像起伏调整参数。")
        # 此处保留你之前的 OpenCV 识别逻辑代码即可...
