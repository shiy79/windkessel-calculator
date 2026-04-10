import streamlit as st
import numpy as np
import pandas as pd

# --- 网页配置 ---
st.set_page_config(page_title="Windkessel 物理参数转换器", layout="wide")

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

st.sidebar.header("📏 装置尺寸预设 (mm)")
d_L1 = st.sidebar.number_input("细管 L1 内径 (mm)", value=5.0) / 1000
d_L2 = st.sidebar.number_input("细管 L2 内径 (mm)", value=3.0) / 1000
d_cavity = st.sidebar.number_input("气腔内径 (mm)", value=55.0) / 1000

# --- 捐助项 ---
st.sidebar.markdown("---")
st.sidebar.subheader("☕ 赞助与支持")
st.sidebar.write("如果您觉得本工具有助于您的科研工作，欢迎赞助作者以维持服务器运行！")
try:
    # 尝试加载 GitHub 仓库中的图片
    st.sidebar.image("donate.png", caption="扫码赞助作者", use_container_width=True)
except:
    st.sidebar.info("🙏 感谢您的支持！")

# --- 主界面 ---
st.title("🩺 Windkessel RCR 参数至物理尺寸转换工具")
st.markdown("---")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader(f"🩸 生理压力与总流量 ({unit_mode})")
    default_pd = 10.9 if unit_mode == "kPa" else 81.7
    default_ps = 16.7 if unit_mode == "kPa" else 125.3
    
    Pd_input = st.number_input(f"舒张压 ({unit_mode})", value=default_pd, step=0.1)
    Ps_input = st.number_input(f"收缩压 ({unit_mode})", value=default_ps, step=0.1)
    Q_mean_total_cm3_s = st.number_input("总流量 (cm³/s)", value=97.72)

with col2:
    st.subheader("📏 血管出口周长 (mm)")
    vessel_names = ['BA', 'LCCA', 'LSA', 'CEL', 'SMA', 'RR', 'LR', 'RI', 'LI']
    default_c = [47.50, 18.27, 30.05, 23.06, 13.56, 9.57, 18.98, 26.20, 25.62]
    df_input = pd.DataFrame({'血管名称': vessel_names, '周长(mm)': default_c})
    edited_df = st.data_editor(df_input, use_container_width=True, num_rows="dynamic")

# --- 核心计算逻辑 ---
Pd_pa = to_pa(Pd_input)
Ps_pa = to_pa(Ps_input)
MAP_pa = Pd_pa + (Ps_pa - Pd_pa) / 3

vessel_labels = edited_df['血管名称'].values
C_outlet_mm = edited_df['周长(mm)'].values

r_mm = C_outlet_mm / (2 * np.pi)
area_mm2 = np.pi * (r_mm**2)
flow_ratio = area_mm2 / np.sum(area_mm2)
Q_mean_vessels = (Q_mean_total_cm3_s * 1e-6) * flow_ratio

#
