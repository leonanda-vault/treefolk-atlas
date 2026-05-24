"""
i-Tree SEA Dashboard — Streamlit Frontend
==========================================
Run with:  streamlit run itree_sea/dashboard.py
"""

import io
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ──
st.set_page_config(
    page_title="Treefolk Atlas",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auto-initialize and seed SQLite database if missing ──
from itree_sea.config import DATABASE_PATH
if not DATABASE_PATH.exists():
    try:
        from itree_sea.database import init_db, seed_from_csv
        init_db()
        seed_from_csv()
    except Exception as e:
        st.error(f"Failed to auto-initialize species database: {e}")

# ── Custom CSS ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .metric-card {
        background: linear-gradient(135deg, #1a3a2a 0%, #0d1f17 100%);
        border: 1px solid #2d5a3d;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-card h2 { color: #7fdb98; margin: 0; font-size: 2rem; }
    .metric-card p { color: #a0c4aa; margin: 0; font-size: 0.85rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: #0d1f17; border-radius: 8px 8px 0 0;
        border: 1px solid #2d5a3d; padding: 8px 20px;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a3a2a 0%, #0d1f17 100%);
        border: 1px solid #2d5a3d; border-radius: 12px; padding: 1rem;
    }
    div[data-testid="stMetric"] label { color: #a0c4aa !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #7fdb98 !important; }
</style>
""", unsafe_allow_html=True)

# ── Color palette ──
COLORS = [
    "#2ecc71", "#27ae60", "#1abc9c", "#16a085", "#3498db",
    "#2980b9", "#9b59b6", "#8e44ad", "#f39c12", "#e67e22",
    "#e74c3c", "#d35400", "#1dd1a1", "#10ac84", "#48dbfb",
    "#0abde3", "#feca57", "#ff9ff3", "#54a0ff", "#5f27cd",
]

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#c0c0c0"),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


from itree_sea.config import SITE_PROFILES, DEFAULT_SITE_PROFILE
from itree_sea.simulation import project_coordinates, compute_simulation
from itree_sea.translations import t
import json


def process_file(uploaded_file, forecast_years, selected_layers, site_profile_key):
    """Process uploaded file through Treefolk Atlas engine."""
    suffix = Path(uploaded_file.name).suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    if suffix == ".dxf":
        from itree_sea.cad_bridge import parse_dxf, extract_planting_blocks, generate_schedule
        profile = SITE_PROFILES[site_profile_key]
        doc = parse_dxf(tmp_path)
        layers = selected_layers if selected_layers else None
        entries = extract_planting_blocks(doc, layers)
        if not entries:
            return None, None

        # Resolve parameters — use advanced overrides if custom profile
        if site_profile_key == "custom_advanced":
            lai = st.session_state.get("advanced_lai", profile.lai)
            rain_events = st.session_state.get("advanced_rain_events", profile.rain_events)
            pollution_multiplier = st.session_state.get("advanced_pollution_multiplier", profile.pollution_multiplier)
        else:
            lai = profile.lai
            rain_events = profile.rain_events
            pollution_multiplier = profile.pollution_multiplier

        schedule = generate_schedule(
            entries, forecast_years,
            lai=lai,
            rain_events=rain_events,
            pollution_multiplier=pollution_multiplier,
        )
        return schedule, "cad"

    elif suffix in (".geojson", ".json", ".shp"):
        from itree_sea.gis_bridge import run_gis_pipeline
        out_path = Path(tmp_path).parent / "enriched.geojson"
        run_gis_pipeline(tmp_path, str(out_path))
        import geopandas as gpd
        gdf = gpd.read_file(str(out_path))
        return gdf, "gis"

    elif suffix == ".csv":
        df = pd.read_csv(tmp_path)
        # Convert legacy columns for backward compatibility
        legacy_mappings = {
            "epa_gasoline_gallons_yr": ("epa_gasoline_liters_yr", 3.78541),
            "epa_miles_driven_yr": ("epa_km_driven_yr", 1.60934),
            "cumulative_epa_gallons": ("cumulative_epa_liters", 3.78541),
            "cumulative_epa_miles": ("cumulative_epa_km", 1.60934),
        }
        for old_col, (new_col, multiplier) in legacy_mappings.items():
            if old_col in df.columns:
                df[new_col] = df[old_col] * multiplier
                if old_col != new_col:
                    df = df.drop(columns=[old_col])
        return df, "csv"

    return None, None


def get_layers_from_dxf(uploaded_file):
    """Extract layer names from a DXF file."""
    import tempfile
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix != ".dxf":
        return []
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    try:
        from itree_sea.cad_bridge import parse_dxf
        doc = parse_dxf(tmp_path)
        layers = [l.dxf.name for l in doc.layers
                  if not l.dxf.name.startswith("*")]
        tree_layers = [l for l in layers
                       if any(k in l.upper() for k in ["POHON", "PHN", "TREE", "PLNT"])]
        return tree_layers if tree_layers else layers[:20]
    except Exception:
        return []


def build_summary(schedule_df):
    """Build summary from schedule DataFrame."""
    max_year = schedule_df["year"].max()
    final = schedule_df[schedule_df["year"] == max_year].copy()
    
    # Calculate growth metrics (Final - Initial)
    initial = schedule_df[schedule_df["year"] == 0][["tree_id", "dbh_cm", "height_m"]]
    final = final.merge(initial, on="tree_id", suffixes=("", "_initial"))
    final["dbh_growth_cm"] = final["dbh_cm"] - final["dbh_cm_initial"]
    final["height_growth_m"] = final["height_m"] - final["height_m_initial"]

    cumul_cols = ["carbon_seq_kg", "co2_seq_kg", "o2_production_kg_yr", "epa_gasoline_liters_yr", "epa_km_driven_yr"]
    
    # Handle cases where new columns might not exist (e.g. old CSV upload)
    existing_cumul_cols = [c for c in cumul_cols if c in schedule_df.columns]
    
    cumul = (schedule_df.groupby("tree_id")[existing_cumul_cols]
             .sum().reset_index()
             .rename(columns={
                 "carbon_seq_kg": "cumulative_seq_kg",
                 "co2_seq_kg": "cumulative_co2_seq_kg",
                 "o2_production_kg_yr": "cumulative_o2_production_kg",
                 "epa_gasoline_liters_yr": "cumulative_epa_liters",
                 "epa_km_driven_yr": "cumulative_epa_km"
             }))
    
    summary = final.merge(cumul, on="tree_id", how="left")
    # Clean up the initial columns to keep the dataframe clean
    summary = summary.drop(columns=["dbh_cm_initial", "height_m_initial"])
    return summary


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    if "lang" not in st.session_state:
        st.session_state.lang = "English"
    
    lang_choice = st.selectbox(
        "🌐 Language / Bahasa",
        ["English", "Bahasa Indonesia"],
        index=0 if st.session_state.lang == "English" else 1
    )
    st.session_state.lang = lang_choice
    st.divider()

    st.image("https://img.icons8.com/fluency/96/deciduous-tree.png", width=60)
    st.title(t("title"))
    st.caption(t("caption"))
    st.divider()

    uploaded = st.file_uploader(
        t("upload_label"),
        type=["dxf", "geojson", "json", "csv", "shp"],
        help=t("upload_help"),
    )

    forecast_years = st.slider(t("forecast_label"), 1, 100, 25, 1)

    # Site profile selector
    profile_keys = list(SITE_PROFILES.keys())
    profile_labels = [t(f"sp_{k}_label") for k in profile_keys]
    default_idx = profile_keys.index(DEFAULT_SITE_PROFILE)
    selected_profile_label = st.selectbox(
        t("site_profile_label"),
        profile_labels,
        index=default_idx,
        help=t("site_profile_help"),
    )
    selected_profile_key = profile_keys[profile_labels.index(selected_profile_label)]
    st.caption(t(f"sp_{selected_profile_key}_desc"))

    # ── Advanced mode controls ──
    advanced_rain_csv = None
    advanced_pollution = None
    advanced_lai = None

    if selected_profile_key == "custom_advanced":
        st.markdown("---")
        st.markdown(f"#### {t('adv_params_header')}")

        with st.expander(t("adv_rain_header"), expanded=True):
            st.markdown(t("adv_rain_desc"))
            advanced_rain_csv = st.file_uploader(
                t("adv_rain_label"),
                type=["csv"],
                key="rain_csv",
                help=t("adv_rain_help"),
            )
            if advanced_rain_csv:
                try:
                    rain_df = pd.read_csv(advanced_rain_csv)
                    col = rain_df.columns[0]
                    rain_data = rain_df[col].dropna().tolist()
                    from itree_sea.engine import derive_rain_events
                    n_events = derive_rain_events(rain_data)
                    total_mm = sum(rain_data)
                    st.success(
                        t("adv_rain_success", hours=len(rain_data), mm=total_mm, events=n_events)
                    )
                    # Store for processing
                    st.session_state["advanced_rain_data"] = rain_data
                    st.session_state["advanced_rain_events"] = n_events
                except Exception as e:
                    st.error(t("adv_rain_error", error=str(e)))

        with st.expander(t("adv_pollution_header"), expanded=True):
            st.markdown(t("adv_pollution_desc"))
            from itree_sea.config import BASELINE_CONCENTRATIONS
            c1, c2 = st.columns(2)
            with c1:
                adv_pm25 = st.number_input(
                    "PM2.5 (µg/m³)", min_value=0.0, value=float(BASELINE_CONCENTRATIONS.pm25),
                    step=1.0, key="adv_pm25",
                )
                adv_o3 = st.number_input(
                    "O₃ (µg/m³)", min_value=0.0, value=float(BASELINE_CONCENTRATIONS.o3),
                    step=5.0, key="adv_o3",
                )
            with c2:
                adv_no2 = st.number_input(
                    "NO₂ (µg/m³)", min_value=0.0, value=float(BASELINE_CONCENTRATIONS.no2),
                    step=1.0, key="adv_no2",
                )
                adv_so2 = st.number_input(
                    "SO₂ (µg/m³)", min_value=0.0, value=float(BASELINE_CONCENTRATIONS.so2),
                    step=1.0, key="adv_so2",
                )

            from itree_sea.engine import derive_pollution_multiplier
            derived_mult = derive_pollution_multiplier(adv_pm25, adv_no2, adv_o3, adv_so2)
            st.metric(t("adv_pollution_mult_label"), f"{derived_mult:.2f}×")
            st.session_state["advanced_pollution_multiplier"] = derived_mult

        with st.expander(t("adv_canopy_header")):
            advanced_lai = st.slider(
                t("adv_lai_label"), 1.0, 10.0, 5.0, 0.5,
                key="adv_lai",
                help=t("adv_lai_help"),
            )
            st.session_state["advanced_lai"] = advanced_lai

    selected_layers = []
    if uploaded and uploaded.name.lower().endswith(".dxf"):
        with st.expander(t("layer_filter"), expanded=True):
            layers = get_layers_from_dxf(uploaded)
            if layers:
                selected_layers = st.multiselect(
                    t("include_layers"), layers, default=layers
                )

    run_btn = st.button(t("run_calc"), type="primary", use_container_width=True)
    sandbox_btn = st.button(t("blank_sandbox"), use_container_width=True)
    st.divider()
    st.caption(t("version_info"))


# ══════════════════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════════════════

if "schedule" not in st.session_state:
    st.session_state.schedule = None
    st.session_state.summary = None
    st.session_state.mode = None
if "manual_trees" not in st.session_state:
    st.session_state.manual_trees = []
if "removed_tree_ids" not in st.session_state:
    st.session_state.removed_tree_ids = []
if "moved_trees" not in st.session_state:
    st.session_state.moved_trees = {}

# ── Process on button click ──
if run_btn and uploaded:
    with st.spinner(t("processing")):
        result, mode = process_file(uploaded, forecast_years, selected_layers, selected_profile_key)
        if result is not None and mode == "cad":
            st.session_state.schedule = result
            st.session_state.summary = build_summary(result)
            st.session_state.mode = mode
            st.session_state.manual_trees = []
            st.session_state.removed_tree_ids = []
            st.session_state.moved_trees = {}
            st.success(t("processed_trees", n=len(st.session_state.summary)))
        elif result is not None:
            st.session_state.schedule = result
            st.session_state.summary = result
            st.session_state.mode = mode
            st.session_state.manual_trees = []
            st.session_state.removed_tree_ids = []
            st.session_state.moved_trees = {}
            st.success(t("file_processed"))
        else:
            st.error(t("no_data_found"))
elif sandbox_btn:
    st.session_state.schedule = pd.DataFrame(columns=[
        "tree_id", "block_name", "species", "x", "y", "layer",
        "year", "dbh_cm", "height_m", "carbon_storage_kg", "carbon_seq_kg",
        "co2_storage_kg", "co2_seq_kg", "o2_production_kg_yr", "epa_gasoline_liters_yr",
        "epa_km_driven_yr", "stormwater_l", "pm25_removed_g",
        "no2_removed_g", "o3_removed_g", "so2_removed_g", "match_level"
    ])
    st.session_state.summary = pd.DataFrame(columns=[
        "tree_id", "block_name", "species", "x", "y", "layer",
        "dbh_cm", "height_m", "carbon_storage_kg",
        "co2_storage_kg", "cumulative_seq_kg", "cumulative_co2_seq_kg",
        "cumulative_o2_production_kg", "cumulative_epa_liters", "cumulative_epa_km",
        "stormwater_l", "pm25_removed_g", "no2_removed_g", "o3_removed_g", "so2_removed_g",
        "dbh_growth_cm", "height_growth_m", "match_level"
    ])
    st.session_state.mode = "sandbox"
    st.session_state.manual_trees = []
    st.session_state.removed_tree_ids = []
    st.session_state.moved_trees = {}
    st.success(t("sandbox_init"))

# ── Landing page ──
if st.session_state.schedule is None:
    # ── Hero Section ──
    title_text = t("title")
    caption_text = t("caption")
    tagline_text = t("hero_tagline")
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #0d2818 0%, #1a4731 40%, #0b3d2e 100%);
        border: 1px solid #2d5a3d;
        border-radius: 16px;
        padding: 2.5rem 2rem;
        margin-bottom: 1.5rem;
        text-align: center;
    ">
        <h1 style="
            font-size: 2.8rem;
            background: linear-gradient(135deg, #7fdb98, #1abc9c, #48dbfb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.3rem;
                ">🌳 {title_text}</h1>
        <p style="color: #a0c4aa; font-size: 1.15rem; margin-bottom: 0.2rem;">
            {caption_text}
        </p>
        <p style="color: #5a8a6a; font-size: 0.9rem;">
            {tagline_text}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Feature Cards ──
    fc1, fc2, fc3, fc4 = st.columns(4)
    
    feature_cards = [
        ("📁", t("fc_upload_title"), t("fc_upload_desc")),
        ("⚡", t("fc_calc_title"), t("fc_calc_desc")),
        ("🗺️", t("fc_map_title"), t("fc_map_desc")),
        ("🧪", t("fc_sandbox_title"), t("fc_sandbox_desc")),
    ]
    
    for col, (icon, title, desc) in zip([fc1, fc2, fc3, fc4], feature_cards):
        col.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a3a2a 0%, #0d1f17 100%);
            border: 1px solid #2d5a3d;
            border-radius: 12px;
            padding: 1.2rem;
            text-align: center;
            min-height: 140px;
        ">
            <div style="font-size: 2rem;">{icon}</div>
            <h4 style="color: #7fdb98; margin: 0.3rem 0 0.2rem;">{title}</h4>
            <p style="color: #a0c4aa; font-size: 0.8rem; margin: 0;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ── Supported DXF Formats ──
    with st.expander(t("supported_dxf_title"), expanded=True):
        fmt_col1, fmt_col2 = st.columns(2)
        
        with fmt_col1:
            st.markdown(t("attr_mode_title"))
            st.markdown(t("dxf_attr_desc"))
            
            st.markdown(t("indonesian_mode_title"))
            st.markdown(t("dxf_indo_desc"))
        
        with fmt_col2:
            st.markdown(t("clean_up_title"))
            st.markdown(t("dxf_clean_desc"))

    # ── Species Database Coverage ──
    try:
        from itree_sea.config import DATABASE_PATH
        import sqlite3 as _sql
        _conn = _sql.connect(str(DATABASE_PATH))
        _cur = _conn.cursor()
        _cur.execute("SELECT COUNT(*) FROM species_lookup")
        species_count = _cur.fetchone()[0]
        _cur.execute("SELECT scientific_name, common_name, family, growth_rate FROM species_lookup ORDER BY scientific_name")
        all_species = _cur.fetchall()
        _conn.close()
    except Exception:
        species_count = 89
        all_species = []

    with st.expander(t("species_db_title", n=species_count), expanded=False):
        if all_species:
            cols = ["Scientific Name", "Common Name", "Family", "Growth Rate"] if st.session_state.lang == "English" else ["Nama Ilmiah", "Nama Umum", "Famili", "Laju Pertumbuhan"]
            sp_df = pd.DataFrame(all_species, columns=cols)
            st.dataframe(sp_df, use_container_width=True, height=300)
        else:
            st.info(t("db_not_init"))

    # ── CAD Standardization Guide ──
    with st.expander(t("cad_standard_title"), expanded=False):
        st.markdown(t("cad_standard_desc"))

    with st.expander(t("advanced_standards_title"), expanded=False):
        st.markdown(t("advanced_standards_desc"))

    # ── Quick Start Demo ──
    st.markdown("---")
    st.markdown(f"### {t('quick_start')}")
    st.markdown(t("quick_start_desc"))
    
    if st.button(t("load_demo"), use_container_width=True, type="primary"):
        # Generate a small demo dataset inline
        demo_species = [
            ("Pterocarpus indicus", "Angsana", 15.0, 3.5, 106.845, -6.208),
            ("Swietenia macrophylla", "Mahoni", 12.0, 3.0, 106.846, -6.209),
            ("Samanea saman", "Trembesi", 25.0, 5.0, 106.847, -6.207),
            ("Delonix regia", "Flamboyan", 10.0, 2.5, 106.844, -6.210),
            ("Ficus benjamina", "Beringin", 20.0, 4.0, 106.848, -6.208),
            ("Terminalia catappa", "Ketapang", 8.0, 2.0, 106.843, -6.209),
            ("Mimusops elengi", "Tanjung", 10.0, 2.5, 106.849, -6.207),
            ("Tectona grandis", "Jati", 15.0, 3.5, 106.845, -6.211),
            ("Callistemon viminalis", "Sikat Botol", 5.0, 2.0, 106.846, -6.206),
            ("Adansonia digitata", "Baobab", 30.0, 4.0, 106.847, -6.210),
        ]
        
        from itree_sea.cad_bridge import PlantingEntry, generate_schedule
        entries = [
            PlantingEntry(
                block_name=cn,
                species_name=sci,
                dbh_cm=dbh,
                height_m=h,
                x=lon,
                y=lat,
                layer="L-PLNT-TREE-PROP",
                handle=f"demo_{i+1}",
            )
            for i, (sci, cn, dbh, h, lon, lat) in enumerate(demo_species)
        ]
        
        # Run the schedule generator
        result = generate_schedule(
            entries,
            forecast_years=forecast_years,
            lai=6.0,
            rain_events=180,
            pollution_multiplier=1.2,
        )
        
        st.session_state.schedule = result
        st.session_state.summary = build_summary(result)
        st.session_state.mode = "cad"
        st.session_state.manual_trees = []
        st.session_state.removed_tree_ids = []
        st.session_state.moved_trees = {}
        st.toast(t("demo_loaded"))
        st.rerun()

    st.stop()

# ── We have data — show tabs ──
# Show a simulation toggle in the sidebar
show_sim = st.sidebar.checkbox(
    t("enable_sandbox"),
    value=(st.session_state.mode == "sandbox" or len(st.session_state.manual_trees) > 0 or len(st.session_state.removed_tree_ids) > 0 or len(st.session_state.moved_trees) > 0),
    help=t("enable_sandbox_help")
)

if show_sim:
    from itree_sea.simulation import compute_simulation
    # Resolve parameters from site profile
    profile = SITE_PROFILES[selected_profile_key]
    if selected_profile_key == "custom_advanced":
        lai_val = st.session_state.get("advanced_lai", profile.lai)
        rain_events_val = st.session_state.get("advanced_rain_events", profile.rain_events)
        pollution_mult_val = st.session_state.get("advanced_pollution_multiplier", profile.pollution_multiplier)
    else:
        lai_val = profile.lai
        rain_events_val = profile.rain_events
        pollution_mult_val = profile.pollution_multiplier

    # Calculate simulated schedule
    sim_schedule_df = compute_simulation(
        baseline_schedule=st.session_state.schedule,
        manual_plantings=st.session_state.manual_trees,
        removed_tree_ids=st.session_state.removed_tree_ids,
        moved_trees=st.session_state.moved_trees,
        forecast_years=forecast_years,
        lai=lai_val,
        rain_events=rain_events_val,
        pollution_multiplier=pollution_mult_val,
    )
    # Re-calculate summary dataframe from the simulated schedule
    sim_summary_df = build_summary(sim_schedule_df) if not sim_schedule_df.empty else pd.DataFrame(columns=st.session_state.summary.columns)
    
    # Override defaults
    schedule_df = sim_schedule_df
    summary_df = sim_summary_df
else:
    schedule_df = st.session_state.schedule
    summary_df = st.session_state.summary

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    t("tab_overview"),
    t("tab_analysis"),
    t("tab_map"),
    t("tab_species"),
    t("tab_export"),
    t("tab_methodology")
])

# ══════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW
# ══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f"## {t('eco_summary')}")

    if summary_df.empty:
        st.info(t("overview_no_data_info"))
    else:
        # Metric cards
        c1, c2, c3, c4 = st.columns(4)
        n_trees = len(summary_df)
        
        # Use CO2 if available, otherwise fallback to Carbon
        if "co2_storage_kg" in summary_df.columns:
            total_co2 = summary_df["co2_storage_kg"].sum()
            total_co2_seq = summary_df.get("cumulative_co2_seq_kg", pd.Series([0])).sum()
            c2.metric(t("co2_stored"), f"{total_co2/1000:,.1f} {t('units_abbr_t')}")
            c3.metric(t("cum_co2_seq"), f"{total_co2_seq/1000:,.1f} {t('units_abbr_t')}")
        else:
            total_carbon = summary_df.get("carbon_storage_kg", pd.Series([0])).sum()
            total_seq = summary_df.get("cumulative_seq_kg", pd.Series([0])).sum()
            c2.metric(t("carbon_stored"), f"{total_carbon/1000:,.1f} {t('units_abbr_t')}")
            c3.metric(t("cum_c_seq"), f"{total_seq/1000:,.1f} {t('units_abbr_t')}")

        match_pct = (summary_df["match_level"] == "species").mean() * 100

        c1.metric(t("trees"), f"{n_trees:,}")
        c4.metric(t("species_match"), f"{match_pct:.0f}%")

        # EPA Equivalencies
        if "cumulative_epa_liters" in summary_df.columns:
            st.markdown(f"### {t('env_equiv')}")
            e1, e2, e3, e4, e5 = st.columns(5)
            total_epa_liters = summary_df.get("cumulative_epa_liters", pd.Series([0])).sum()
            total_epa_km = summary_df.get("cumulative_epa_km", pd.Series([0])).sum()
            total_o2 = summary_df.get("cumulative_o2_production_kg", pd.Series([0])).sum()
            total_co2_seq = summary_df.get("cumulative_co2_seq_kg", pd.Series([0])).sum()
            
            total_motorcycle_km = total_co2_seq * 20.0
            total_smartphones = total_co2_seq * 80.645
            
            e1.metric(t("o2_produced"), f"{total_o2/1000:,.1f} {t('units_abbr_t')}")
            e2.metric(t("gasoline_saved"), f"{total_epa_liters:,.0f} {t('units_abbr_liters')}")
            e3.metric(t("car_avoided"), f"{total_epa_km:,.0f} {t('units_abbr_km')}")
            e4.metric(t("motorcycle_avoided"), f"{total_motorcycle_km:,.0f} {t('units_abbr_km')}")
            e5.metric(t("smartphones_charged"), f"{total_smartphones:,.0f} {t('units_abbr_charges')}")

        st.markdown("---")

        # Two columns: species donut + layer bar
        col_a, col_b = st.columns(2)

        with col_a:
            sp_carbon = (summary_df.groupby("species")["carbon_storage_kg"]
                         .sum().sort_values(ascending=False).reset_index())
            fig = px.pie(
                sp_carbon, names="species", values="carbon_storage_kg",
                title=t("carbon_by_species"),
                color_discrete_sequence=COLORS, hole=0.45,
            )
            fig.update_layout(**PLOT_LAYOUT)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            if "layer" in summary_df.columns:
                layer_carbon = (summary_df.groupby("layer")["carbon_storage_kg"]
                               .sum().sort_values(ascending=False).reset_index())
                fig = px.bar(
                    layer_carbon, x="layer", y="carbon_storage_kg",
                    title=t("carbon_by_layer"),
                    color="layer", color_discrete_sequence=COLORS,
                )
                fig.update_layout(**PLOT_LAYOUT, showlegend=False)
                y_label_str = t("carbon_stored") + " (kg)"
                fig.update_yaxes(title=y_label_str)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(t("no_layer_data"))

        # Species table
        st.markdown(f"### {t('species_efficiency_breakdown')}")
        sp_table = (summary_df.groupby("species").agg(
            count=("tree_id", "size"),
            carbon_kg=("carbon_storage_kg", "sum"),
            avg_carbon=("carbon_storage_kg", "mean"),
            stormwater_l=("stormwater_l", "sum"),
        ).sort_values("carbon_kg", ascending=False).reset_index())
        sp_table["carbon_kg"] = sp_table["carbon_kg"].round(1)
        sp_table["avg_carbon"] = sp_table["avg_carbon"].round(1)
        sp_table["stormwater_l"] = sp_table["stormwater_l"].round(0)
        
        # Rename columns using t()
        sp_table.columns = [
            t("col_species"),
            t("col_count"),
            t("col_total_carbon"),
            t("col_avg_carbon"),
            t("col_stormwater")
        ]
        st.dataframe(sp_table, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 2: ANALYSIS
# ══════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"## {t('growth_analysis')}")

    if summary_df.empty:
        st.info(t("analysis_no_data_info"))
    elif "year" in schedule_df.columns:
        # Carbon growth curve
        yearly = (schedule_df.groupby("year")
                  .agg(carbon=("carbon_storage_kg", "sum"),
                       seq=("carbon_seq_kg", "sum"),
                       co2_storage=("co2_storage_kg", "sum"),
                       co2_seq=("co2_seq_kg", "sum"),
                       o2_prod=("o2_production_kg_yr", "sum"),
                       storm=("stormwater_l", "sum"))
                  .reset_index())
        yearly["carbon_t"] = yearly["carbon"] / 1000
        yearly["seq_t"] = yearly["seq"] / 1000

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yearly["year"], y=yearly["carbon_t"],
            mode="lines+markers", name=t("carbon_stored_t"),
            line=dict(color="#2ecc71", width=3),
            fill="tozeroy", fillcolor="rgba(46,204,113,0.15)",
        ))
        fig.update_layout(
            title=t("total_c_stored_over_time"),
            xaxis_title=t("year"), yaxis_title=t("tonnes"),
            **PLOT_LAYOUT,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(t("methodology_caption_agb"))

        # Sequestration & Oxygen curves
        col1, col2 = st.columns(2)

        with col1:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=yearly["year"], y=yearly["co2_seq"],
                mode="lines+markers", name=t("co2_seq_yr"),
                line=dict(color="#3498db", width=3),
                fill="tozeroy", fillcolor="rgba(52,152,219,0.15)",
            ))
            fig2.add_trace(go.Scatter(
                x=yearly["year"], y=yearly["o2_prod"],
                mode="lines+markers", name=t("o2_prod_yr"),
                line=dict(color="#e74c3c", width=3),
                fill="tonexty", fillcolor="rgba(231,76,60,0.15)",
            ))
            fig2.update_layout(
                title=t("annual_co2_vs_o2"),
                xaxis_title=t("year"), yaxis_title=t("kg_yr"),
                hovermode="x unified",
                **PLOT_LAYOUT,
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.caption(t("methodology_caption_o2"))

        with col2:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=yearly["year"], y=yearly["storm"] / 1000,
                mode="lines+markers", name=t("stormwater_kl_yr"),
                line=dict(color="#1abc9c", width=3),
                fill="tozeroy", fillcolor="rgba(26,188,156,0.15)",
            ))
            fig3.update_layout(
                title=t("stormwater_interception"),
                xaxis_title=t("year"), yaxis_title=t("kl_yr"),
                **PLOT_LAYOUT,
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.caption(t("methodology_caption_stormwater"))

        # Stacked area by species
        st.markdown(f"### {t('carbon_growth_by_species')}")
        top_species = (summary_df.groupby("species")["carbon_storage_kg"]
                       .sum().nlargest(8).index.tolist())
        sp_yearly = schedule_df[schedule_df["species"].isin(top_species)]
        sp_yearly_agg = (sp_yearly.groupby(["year", "species"])["carbon_storage_kg"]
                         .sum().reset_index())
        sp_yearly_agg["carbon_t"] = sp_yearly_agg["carbon_storage_kg"] / 1000

        fig4 = px.area(
            sp_yearly_agg, x="year", y="carbon_t", color="species",
            title=t("carbon_storage_top8"),
            color_discrete_sequence=COLORS,
        )
        fig4.update_layout(**PLOT_LAYOUT)
        fig4.update_yaxes(title=t("tonnes"))
        fig4.update_xaxes(title=t("year"))
        st.plotly_chart(fig4, use_container_width=True)
        st.caption(t("methodology_caption_height"))
    else:
        st.info(t("time_series_required_dxf"))


# ══════════════════════════════════════════════════════════════════════
# TAB 3: MAP
# ══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown(f"## {t('map_title')}")

    # If we have trees (either baseline or simulation)
    if "x" in summary_df.columns and "y" in summary_df.columns and not summary_df.empty:
        # Check if coordinates look like lat/lng or local (already projected or not)
        is_geo = summary_df["y"].between(-90, 90).all() and summary_df["x"].between(-180, 180).all()
        
        # Interchangeable basemap styles selection at the top of the map
        col_m_title, col_m_style = st.columns([2, 1])
        with col_m_style:
            basemap_options = [
                t("basemap_dark"),
                t("basemap_osm"),
                t("basemap_light")
            ]
            basemap_style = st.selectbox(
                t("basemap_style"),
                basemap_options,
                index=0,
                key="basemap_style_select",
                help=t("basemap_style_help")
            )
        style_map = {
            t("basemap_dark"): "carto-darkmatter",
            t("basemap_osm"): "open-street-map",
            t("basemap_light"): "carto-positron"
        }
        style_key = style_map[basemap_style]

        # Determine if CAD coordinates are in UTM range (Indonesia)
        # Easting (X) in [100000, 900000] and Northing (Y) in [8000000, 10000000]
        # Skip checking if already geographic (is_geo)
        is_utm = False
        if not is_geo and not summary_df.empty:
            try:
                valid_x = summary_df["x"]
                valid_y = summary_df["y"]
                mean_x = valid_x.mean()
                mean_y = valid_y.mean()
                is_utm = (100000 <= abs(mean_x) <= 900000) and (8000000 <= abs(mean_y) <= 10000000)
            except Exception:
                pass

        # Georeferencing interface for CAD
        use_basemap = False
        anchor_lat = -6.2088
        anchor_lon = 106.8456
        scale_factor = 1.0
        easting_shift = 0.0
        northing_shift = 0.0
        anchor_mode = "Center of Trees"
        projection_system = "Flat Earth Center Anchor (Manual)"

        if not is_geo:
            # Set default depending on UTM detection
            default_proj_idx = 0 if is_utm else 2
            with st.expander(t("georef_cad"), expanded=is_utm):
                col_geo1, col_geo2 = st.columns(2)
                # If UTM is detected, we check Project CAD by default
                use_basemap = col_geo1.checkbox(t("project_cad"), value=is_utm)
                
                # Projection system dropdown
                projection_system = col_geo2.selectbox(
                    t("coordinate_system"),
                    [
                        t("utm_48s"),
                        t("utm_49s"),
                        t("flat_earth")
                    ],
                    index=default_proj_idx
                )
                
                if is_utm:
                    st.success(t("georef_detected"))
                
                if use_basemap:
                    col_geo3, col_geo4 = st.columns(2)
                    if "UTM" in projection_system or "Zona" in projection_system or "Zone" in projection_system:
                        st.info(t("utm_info"))
                        anchor_mode = "UTM"
                    else:
                        anchor_mode_display = col_geo3.selectbox(t("align_anchor"), [t("align_center"), t("align_origin")])
                        anchor_mode = "Center of Trees" if anchor_mode_display == t("align_center") else "CAD Origin (0,0)"
                        col_geo_lat, col_geo_lon = st.columns(2)
                        anchor_lat = col_geo_lat.number_input(t("anchor_lat"), value=-6.2088, format="%.6f")
                        anchor_lon = col_geo_lon.number_input(t("anchor_lon"), value=106.8456, format="%.6f")
                        
                    col_geo5, col_geo6 = st.columns(2)
                    unit_selection = col_geo5.selectbox(
                        t("cad_scale"),
                        [t("scale_meters"), t("scale_cms"), t("scale_mms"), t("scale_custom")]
                    )
                    if unit_selection == t("scale_meters"):
                        scale_factor = 1.0
                    elif unit_selection == t("scale_cms"):
                        scale_factor = 0.01
                    elif unit_selection == t("scale_mms"):
                        scale_factor = 0.001
                    else:
                        scale_factor = col_geo5.number_input(t("custom_mult"), value=1.0, format="%.6f")
                        
                    col_geo7, col_geo8 = st.columns(2)
                    easting_shift = col_geo7.slider(t("east_west_shift"), min_value=-1000.0, max_value=1000.0, value=0.0, step=1.0)
                    northing_shift = col_geo8.slider(t("north_south_shift"), min_value=-1000.0, max_value=1000.0, value=0.0, step=1.0)

        # Prepare map dataframe
        # Filter out removed trees from map so they disappear
        map_df = summary_df[~summary_df["layer"].eq("L-PLNT-TREE-RMVL")].copy()
        
        event_data = None
        if not map_df.empty:
            map_df = map_df.dropna(subset=["x", "y"])
            
            if is_geo:
                map_df = map_df.rename(columns={"x": "lon", "y": "lat"})
                map_df["lon"] = pd.to_numeric(map_df["lon"])
                map_df["lat"] = pd.to_numeric(map_df["lat"])
                
                # Plotly Express Mapbox with free basemap
                fig = px.scatter_mapbox(
                    map_df, lat="lat", lon="lon", color="species",
                    size="dbh_cm",
                    hover_data=["tree_id", "species", "block_name", "dbh_cm", "carbon_storage_kg"],
                    mapbox_style=style_key,
                    zoom=15,
                    color_discrete_sequence=COLORS,
                    title=t("map_title_geo"),
                )
                fig.update_layout(**PLOT_LAYOUT, height=600, clickmode="event+select")
                event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            elif use_basemap:
                # Project coordinates
                map_df = project_coordinates(
                    map_df,
                    anchor_lat=anchor_lat,
                    anchor_lon=anchor_lon,
                    scale_factor=scale_factor,
                    easting_offset=easting_shift,
                    northing_offset=northing_shift,
                    anchor_mode=anchor_mode,
                    projection_system=projection_system
                )
                
                fig = px.scatter_mapbox(
                    map_df, lat="lat", lon="lon", color="species",
                    size="dbh_cm",
                    hover_data=["tree_id", "species", "block_name", "dbh_cm", "carbon_storage_kg"],
                    mapbox_style=style_key,
                    zoom=17,
                    color_discrete_sequence=COLORS,
                    title=t("map_title_cad"),
                )
                fig.update_layout(**PLOT_LAYOUT, height=600, clickmode="event+select")
                fig.update_layout(mapbox=dict(
                    center=dict(lat=map_df["lat"].mean(), lon=map_df["lon"].mean())
                ))
                event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            else:
                # Local coordinate scatter plot
                fig = px.scatter(
                    map_df, x="x", y="y", color="species",
                    size="dbh_cm",
                    hover_data=["tree_id", "species", "block_name", "dbh_cm", "carbon_storage_kg"],
                    title=t("map_title_local"),
                    color_discrete_sequence=COLORS,
                )
                fig.update_layout(**PLOT_LAYOUT, height=600, clickmode="event+select")
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

            # Interactive point actions container
            selected_tree_ids = []
            if event_data and "selection" in event_data and "points" in event_data["selection"]:
                for p in event_data["selection"]["points"]:
                    if "customdata" in p and p["customdata"]:
                        selected_tree_ids.append(p["customdata"][0])
            
            selected_tree_id = None
            selected_x = None
            selected_y = None
            selected_species = None
            selected_dbh = None

            if len(selected_tree_ids) == 1:
                selected_tree_id = selected_tree_ids[0]
                clicked_rows = map_df[map_df["tree_id"] == selected_tree_id]
                if not clicked_rows.empty:
                    clicked_row = clicked_rows.iloc[0]
                    selected_species = clicked_row["species"]
                    selected_dbh = clicked_row["dbh_cm"]
                    
                    is_manual_chk = any(t["tree_id"] == selected_tree_id for t in st.session_state.manual_trees)
                    is_baseline_chk = (st.session_state.summary is not None and selected_tree_id in st.session_state.summary["tree_id"].values)
                    if is_baseline_chk:
                        base_row = st.session_state.summary[st.session_state.summary["tree_id"] == selected_tree_id]
                        if not base_row.empty:
                            selected_dbh = base_row.iloc[0]["dbh_cm"]
                    elif is_manual_chk:
                        manual_row = [t for t in st.session_state.manual_trees if t["tree_id"] == selected_tree_id]
                        if manual_row:
                            selected_dbh = manual_row[0]["dbh_cm"]
                            
                    orig_row = summary_df[summary_df["tree_id"] == selected_tree_id]
                    if not orig_row.empty:
                        selected_x = orig_row.iloc[0]["x"]
                        selected_y = orig_row.iloc[0]["y"]

            if len(selected_tree_ids) > 1:
                st.markdown(t("group_actions"))
                st.info(t("selected_trees_count", n=len(selected_tree_ids)))
                
                g_col1, g_col2 = st.columns(2)
                
                with g_col1:
                    st.markdown(t("group_removal"))
                    if st.button(t("remove_all_selected"), use_container_width=True, type="primary"):
                        removed_count = 0
                        cancelled_count = 0
                        for tid in selected_tree_ids:
                            # If manual tree, cancel it
                            if any(t["tree_id"] == tid for t in st.session_state.manual_trees):
                                st.session_state.manual_trees = [t for t in st.session_state.manual_trees if t["tree_id"] != tid]
                                cancelled_count += 1
                            else:
                                if tid not in st.session_state.removed_tree_ids:
                                    st.session_state.removed_tree_ids.append(tid)
                                    removed_count += 1
                        st.toast(t("removed_baseline_cancelled_manual", r=removed_count, c=cancelled_count))
                        st.rerun()
                        
                with g_col2:
                    st.markdown(t("group_move"))
                    st.write(t("shift_selected_delta"))
                    g_dx = st.number_input(t("delta_x"), value=0.0, step=1.0, key="group_move_dx")
                    g_dy = st.number_input(t("delta_y"), value=0.0, step=1.0, key="group_move_dy")
                    
                    if st.button(t("apply_shift"), use_container_width=True):
                        if g_dx != 0.0 or g_dy != 0.0:
                            moved_count = 0
                            for tid in selected_tree_ids:
                                # Find current position
                                orig_row = summary_df[summary_df["tree_id"] == tid]
                                if not orig_row.empty:
                                    curr_x = orig_row.iloc[0]["x"]
                                    curr_y = orig_row.iloc[0]["y"]
                                    new_x = curr_x + g_dx
                                    new_y = curr_y + g_dy
                                    
                                    # Update position
                                    is_manual = False
                                    for t in st.session_state.manual_trees:
                                        if t["tree_id"] == tid:
                                            t["x"] = new_x
                                            t["y"] = new_y
                                            is_manual = True
                                            break
                                    if not is_manual:
                                        st.session_state.moved_trees[tid] = (new_x, new_y)
                                    moved_count += 1
                            st.toast(t("shifted_trees", n=moved_count, x=g_dx, y=g_dy))
                            st.rerun()

            elif selected_tree_id is not None:
                st.markdown(t("interactive_actions"))
                st.info(t("selected_tree_info", tid=selected_tree_id, species=selected_species, dbh=selected_dbh, x=selected_x, y=selected_y))
                
                sel_col1, sel_col2, sel_col3 = st.columns(3)
                
                is_manual = any(t["tree_id"] == selected_tree_id for t in st.session_state.manual_trees)
                is_baseline = (st.session_state.summary is not None and selected_tree_id in st.session_state.summary["tree_id"].values)
                
                with sel_col1:
                    if is_baseline:
                        if selected_tree_id in st.session_state.removed_tree_ids:
                            if st.button(t("restore_tree"), use_container_width=True):
                                st.session_state.removed_tree_ids.remove(selected_tree_id)
                                st.toast(t("restored_tree", tid=selected_tree_id))
                                st.rerun()
                        else:
                            if st.button(t("remove_tree"), use_container_width=True, type="primary"):
                                st.session_state.removed_tree_ids.append(selected_tree_id)
                                st.toast(t("marked_removed", tid=selected_tree_id))
                                st.rerun()
                    elif is_manual:
                        if st.button(t("cancel_manual"), use_container_width=True, type="primary"):
                            st.session_state.manual_trees = [t for t in st.session_state.manual_trees if t["tree_id"] != selected_tree_id]
                            st.toast(t("planting_cancelled"))
                            st.rerun()
                            
                with sel_col2:
                    if st.button(t("prefill_form"), use_container_width=True):
                        st.session_state["prefilled_x"] = float(selected_x)
                        st.session_state["prefilled_y"] = float(selected_y)
                        st.session_state["prefilled_species"] = selected_species
                        st.session_state["prefilled_dbh"] = float(selected_dbh)
                        st.toast(t("prefill_form"))
                        st.rerun()

                with sel_col3:
                    if st.button(t("quick_plant"), use_container_width=True):
                        next_id = 9000 + len(st.session_state.manual_trees) + 1
                        offset = 0.0001 if (is_geo or use_basemap) else 2.0
                        st.session_state.manual_trees.append({
                            "tree_id": next_id,
                            "species": selected_species,
                            "dbh_cm": selected_dbh,
                            "height_m": None,
                            "x": float(selected_x) + offset,
                            "y": float(selected_y) + offset,
                            "condition": "good"
                        })
                        st.toast(t("successfully_planted", sp=selected_species))
                        st.rerun()

                # Add precise single tree move tool
                st.markdown(t("move_tree_tool"))
                
                # Track selection to avoid retaining offsets from previously selected trees
                if "last_selected_tree_id" not in st.session_state or st.session_state.last_selected_tree_id != selected_tree_id:
                    st.session_state.last_selected_tree_id = selected_tree_id
                    st.session_state.sel_tree_orig_x = float(selected_x)
                    st.session_state.sel_tree_orig_y = float(selected_y)

                m_tab1, m_tab2 = st.tabs([t("input_abs"), t("sliders_nudge")])

                with m_tab1:
                    col_mx, col_my = st.columns(2)
                    new_x_val = col_mx.number_input(
                        t("new_x_coord"), 
                        value=float(selected_x), 
                        format="%.5f",
                        key=f"abs_x_{selected_tree_id}"
                    )
                    new_y_val = col_my.number_input(
                        t("new_y_coord"), 
                        value=float(selected_y), 
                        format="%.5f",
                        key=f"abs_y_{selected_tree_id}"
                    )
                    
                    if st.button(t("apply_coords_move"), key=f"btn_abs_{selected_tree_id}", use_container_width=True):
                        if is_manual:
                            for t in st.session_state.manual_trees:
                                if t["tree_id"] == selected_tree_id:
                                    t["x"] = new_x_val
                                    t["y"] = new_y_val
                                    break
                        else:
                            st.session_state.moved_trees[selected_tree_id] = (new_x_val, new_y_val)
                        
                        st.session_state.sel_tree_orig_x = new_x_val
                        st.session_state.sel_tree_orig_y = new_y_val
                        st.toast(t("restored_tree", tid=selected_tree_id))
                        st.rerun()

                with m_tab2:
                    st.write(t("nudge_sliders_desc"))
                    
                    is_currently_geo = (is_geo or (use_basemap and "UTM" not in projection_system))
                    if is_currently_geo:
                        slider_min = -0.002
                        slider_max = 0.002
                        slider_step = 0.00001
                    else:
                        slider_min = -50.0
                        slider_max = 50.0
                        slider_step = 0.5
                    
                    slide_x = st.slider(
                        t("move_east_west"), 
                        min_value=slider_min, 
                        max_value=slider_max, 
                        value=0.0, 
                        step=slider_step,
                        key=f"slider_x_{selected_tree_id}"
                    )
                    slide_y = st.slider(
                        t("move_north_south"), 
                        min_value=slider_min, 
                        max_value=slider_max, 
                        value=0.0, 
                        step=slider_step,
                        key=f"slider_y_{selected_tree_id}"
                    )
                    
                    preview_x = st.session_state.sel_tree_orig_x + slide_x
                    preview_y = st.session_state.sel_tree_orig_y + slide_y
                    
                    if slide_x != 0.0 or slide_y != 0.0:
                        st.markdown(t("nudging_preview", x=preview_x, dx=slide_x, y=preview_y, dy=slide_y))
                        
                        # Live update during slider drag
                        if is_manual:
                            for t in st.session_state.manual_trees:
                                if t["tree_id"] == selected_tree_id:
                                    t["x"] = preview_x
                                    t["y"] = preview_y
                                    break
                        else:
                            st.session_state.moved_trees[selected_tree_id] = (preview_x, preview_y)
                        
                        if st.button(t("lock_nudge"), key=f"btn_nudge_{selected_tree_id}", use_container_width=True):
                            st.session_state.sel_tree_orig_x = preview_x
                            st.session_state.sel_tree_orig_y = preview_y
                            st.toast(t("lock_nudge"))
                            st.rerun()
        else:
            st.info(t("all_removed_info"))
    else:
        st.info(t("no_active_trees_info"))

    st.markdown("---")
    st.markdown(t("sandbox_panel"))
    
    sim_col1, sim_col2 = st.columns([1, 1])

    with sim_col1:
        st.markdown(t("plant_tree_sim"))
        # Load all species from database
        try:
            from itree_sea.config import DATABASE_PATH
            import sqlite3
            conn = sqlite3.connect(str(DATABASE_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT scientific_name FROM species_lookup ORDER BY scientific_name")
            db_species = [row[0] for row in cursor.fetchall()]
            conn.close()
        except Exception:
            db_species = ["Swietenia macrophylla", "Pterocarpus indicus", "Samanea saman", "Ficus benjamina"]

        pref_x = st.session_state.get("prefilled_x", 0.0)
        pref_y = st.session_state.get("prefilled_y", 0.0)
        pref_species = st.session_state.get("prefilled_species", db_species[0])
        pref_dbh = float(st.session_state.get("prefilled_dbh", 15.0))

        sp_idx = 0
        if pref_species in db_species:
            sp_idx = db_species.index(pref_species)

        with st.form("add_tree_form_tab3", clear_on_submit=True):
            sp = st.selectbox(t("botanical_species"), db_species, index=sp_idx)
            col_d, col_h = st.columns(2)
            dbh = col_d.number_input(t("dbh_label"), min_value=1.0, max_value=250.0, value=pref_dbh, step=1.0)
            h = col_h.number_input(t("height_label"), min_value=0.0, max_value=100.0, value=0.0, step=1.0)
            
            col_x, col_y = st.columns(2)
            x_coord = col_x.number_input(t("x_label"), value=pref_x, format="%.5f")
            y_coord = col_y.number_input(t("y_label"), value=pref_y, format="%.5f")
            
            cond_options = [t("cond_excellent"), t("cond_good"), t("cond_fair"), t("cond_poor")]
            cond_map = {
                t("cond_excellent"): "excellent",
                t("cond_good"): "good",
                t("cond_fair"): "fair",
                t("cond_poor"): "poor"
            }
            cond_display = st.selectbox(t("tree_condition"), cond_options, index=1)
            cond = cond_map[cond_display]
            
            submit_add = st.form_submit_button(t("plant_tree_btn"))
            if submit_add:
                # Assign new tree_id
                next_id = 9000 + len(st.session_state.manual_trees) + 1
                st.session_state.manual_trees.append({
                    "tree_id": next_id,
                    "species": sp,
                    "dbh_cm": dbh,
                    "height_m": h if h > 0 else None,
                    "x": x_coord,
                    "y": y_coord,
                    "condition": cond.lower()
                })
                st.success(t("successfully_planted", sp=sp))
                st.rerun()

        # Remove trees
        st.markdown(t("remove_tree_sim"))
        # Show dropdown of baseline trees
        baseline_sum = st.session_state.summary
        if baseline_sum is not None and not baseline_sum.empty:
            active_trees = baseline_sum[~baseline_sum["tree_id"].isin(st.session_state.removed_tree_ids)]
            if not active_trees.empty:
                tree_options = [
                    f"{row['tree_id']}: {row['species']} (DBH: {row['dbh_cm']}cm, Block: {row['block_name']})"
                    for _, row in active_trees.iterrows()
                ]
                selected_remove_str = st.selectbox(t("select_tree_remove"), tree_options)
                if st.button(t("remove_tree_btn")):
                    tid = int(selected_remove_str.split(":")[0])
                    st.session_state.removed_tree_ids.append(tid)
                    st.success(t("marked_removed", tid=tid))
                    st.rerun()
            else:
                st.info(t("no_trees_to_remove"))
        else:
            st.info(t("upload_first_remove"))

        # Export/Import Sandbox Configuration
        st.markdown(t("export_import_sim"))
        sim_data_to_save = {
            "manual_trees": st.session_state.manual_trees,
            "removed_tree_ids": st.session_state.removed_tree_ids,
            "moved_trees": st.session_state.moved_trees
        }
        json_str = json.dumps(sim_data_to_save, indent=2)
        st.download_button(
            label=t("export_sandbox_btn"),
            data=json_str,
            file_name="treefolk_atlas_simulation.json",
            mime="application/json",
            use_container_width=True
        )
        
        uploaded_sim = st.file_uploader(t("load_sandbox_btn"), type=["json"], key="uploader_tab3")
        if uploaded_sim is not None:
            try:
                loaded_data = json.load(uploaded_sim)
                if "manual_trees" in loaded_data and "removed_tree_ids" in loaded_data:
                    st.session_state.manual_trees = loaded_data["manual_trees"]
                    st.session_state.removed_tree_ids = loaded_data["removed_tree_ids"]
                    st.session_state.moved_trees = {
                        int(k): v for k, v in loaded_data.get("moved_trees", {}).items()
                    }
                    st.success(t("sim_loaded_success"))
                    st.rerun()
                else:
                    st.error(t("invalid_file_format"))
            except Exception as e:
                st.error(t("error_loading_config", error=str(e)))

    with sim_col2:
        st.markdown(t("active_interventions"))
        
        # Clear button
        if st.session_state.manual_trees or st.session_state.removed_tree_ids or st.session_state.moved_trees:
            if st.button(t("reset_sandbox"), use_container_width=True):
                st.session_state.manual_trees = []
                st.session_state.removed_tree_ids = []
                st.session_state.moved_trees = {}
                st.success(t("cleared_sandbox"))
                st.rerun()

        # Display manual plantings table
        if st.session_state.manual_trees:
            st.markdown(t("manually_planted"))
            plant_df = pd.DataFrame(st.session_state.manual_trees)
            plant_df_display = plant_df[["tree_id", "species", "dbh_cm", "height_m", "x", "y", "condition"]].copy()
            plant_df_display.columns = [
                t("col_tree_id"),
                t("col_species"),
                t("dbh_label"),
                t("height_label").split("[")[0].strip(),
                t("col_x"),
                t("col_y"),
                t("col_condition")
            ]
            st.dataframe(plant_df_display, use_container_width=True, hide_index=True)
            
            tree_to_delete = st.selectbox(
                t("cancel_manual_planting"),
                [f"{t['tree_id']}: {t['species']} ({t['dbh_cm']}cm)" for t in st.session_state.manual_trees]
            )
            if st.button(t("delete_planting_btn")):
                del_id = int(tree_to_delete.split(":")[0])
                st.session_state.manual_trees = [t for t in st.session_state.manual_trees if t["tree_id"] != del_id]
                st.success(t("planting_cancelled"))
                st.rerun()

        # Display removals table
        if st.session_state.removed_tree_ids and baseline_sum is not None and not baseline_sum.empty:
            st.markdown(t("manually_removed"))
            rem_df = baseline_sum[baseline_sum["tree_id"].isin(st.session_state.removed_tree_ids)]
            rem_df_display = rem_df[["tree_id", "species", "dbh_cm", "block_name"]].copy()
            rem_df_display.columns = [
                t("col_tree_id"),
                t("col_species"),
                t("dbh_label"),
                t("col_block")
            ]
            st.dataframe(rem_df_display, use_container_width=True, hide_index=True)
            
            tree_to_restore = st.selectbox(
                t("restore_removed_tree"),
                [f"{tid}" for tid in st.session_state.removed_tree_ids]
            )
            if st.button(t("restore_tree_btn")):
                restore_id = int(tree_to_restore)
                st.session_state.removed_tree_ids.remove(restore_id)
                st.success(t("restored_tree", tid=restore_id))
                st.rerun()

        if not st.session_state.manual_trees and not st.session_state.removed_tree_ids:
            st.info(t("no_active_interventions"))

        # Show simulation delta stats
        if show_sim:
            st.markdown(t("sim_delta_stats"))
            
            def safe_sum(df, col):
                if df is not None and not df.empty and col in df.columns:
                    return df[col].sum()
                return 0.0

            # Calculate base metrics
            base_count = len(st.session_state.summary) if st.session_state.summary is not None else 0
            sim_count = len(summary_df)
            count_delta = sim_count - base_count
            
            # Base data sums
            base_c = safe_sum(st.session_state.summary, "carbon_storage_kg") / 1000.0
            base_co2 = safe_sum(st.session_state.summary, "co2_storage_kg") / 1000.0
            base_storm = safe_sum(st.session_state.summary, "stormwater_l") / 1000.0
            base_o2 = safe_sum(st.session_state.summary, "cumulative_o2_production_kg") / 1000.0
            base_pm25 = safe_sum(st.session_state.summary, "pm25_removed_g") / 1000.0

            # Sim data sums
            sim_c = safe_sum(summary_df, "carbon_storage_kg") / 1000.0
            sim_co2 = safe_sum(summary_df, "co2_storage_kg") / 1000.0
            sim_storm = safe_sum(summary_df, "stormwater_l") / 1000.0
            sim_o2 = safe_sum(summary_df, "cumulative_o2_production_kg") / 1000.0
            sim_pm25 = safe_sum(summary_df, "pm25_removed_g") / 1000.0

            # Deltas
            c_delta = sim_c - base_c
            co2_delta = sim_co2 - base_co2
            storm_delta = sim_storm - base_storm
            o2_delta = sim_o2 - base_o2
            pm25_delta = sim_pm25 - base_pm25

            col_m1, col_m2 = st.columns(2)
            col_m1.metric(t("tree_count"), f"{sim_count} {t('trees').lower()}", f"{count_delta:+d} {t('trees').lower()}" if count_delta != 0 else None)
            col_m2.metric(t("carbon_stored"), f"{sim_c:.2f} {t('units_abbr_t')}", f"{c_delta:+.2f} {t('units_abbr_t')}" if c_delta != 0 else None)
            
            col_m3, col_m4 = st.columns(2)
            col_m3.metric(t("stormwater_intercepted"), f"{sim_storm:.2f} kL", f"{storm_delta:+.2f} kL" if storm_delta != 0 else None)
            col_m4.metric(t("co2_equivalent_stored"), f"{sim_co2:.2f} {t('units_abbr_t')}", f"{co2_delta:+.2f} {t('units_abbr_t')}" if co2_delta != 0 else None)

            col_m5, col_m6 = st.columns(2)
            col_m5.metric(t("oxygen_production"), f"{sim_o2:.2f} {t('units_abbr_t')}", f"{o2_delta:+.2f} {t('units_abbr_t')}" if o2_delta != 0 else None)
            col_m6.metric(t("pm25_removed"), f"{sim_pm25:.2f} kg", f"{pm25_delta:+.2f} kg" if pm25_delta != 0 else None)


# ══════════════════════════════════════════════════════════════════════
# TAB 4: SPECIES BREAKDOWN
# ══════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown(f"## {t('species_efficiency_breakdown')}")

    if summary_df.empty:
        st.info(t("species_breakdown_info"))
    elif schedule_df is not None:
        # Benefit radar
        st.markdown(f"### {t('radar_title')}")
        
        sp_totals = (summary_df.groupby("species")
                .agg(carbon=("carbon_storage_kg", "mean"),
                     seq=("carbon_seq_kg", "mean"),
                     storm=("stormwater_l", "mean"),
                     pm25=("pm25_removed_g", "mean"),
                     no2=("no2_removed_g", "mean")))
                     
        all_species = sp_totals.index.tolist()
        top5_default = sp_totals.nlargest(5, "carbon").index.tolist()
        
        selected_radar_species = st.multiselect(
            t("radar_select"),
            options=all_species,
            default=top5_default if len(top5_default) > 0 else all_species
        )

        if selected_radar_species:
            radar_data = sp_totals.loc[selected_radar_species]
            
            # Normalize 0-1 for radar against the maximum value of ALL species in the dataset
            radar_norm = radar_data.copy()
            for col in radar_norm.columns:
                mx = sp_totals[col].max()
                if mx > 0:
                    radar_norm[col] = radar_norm[col] / mx

            fig5 = go.Figure()
            cats = [t("radar_carbon"), t("radar_seq"), t("radar_storm"), t("radar_pm25"), t("radar_no2")]
            for i, (sp, row) in enumerate(radar_norm.iterrows()):
                fig5.add_trace(go.Scatterpolar(
                    r=[row["carbon"], row["seq"], row["storm"], row["pm25"], row["no2"]],
                    theta=cats, fill="toself", name=sp,
                    line=dict(color=COLORS[i % len(COLORS)]),
                ))
            fig5.update_layout(
                polar=dict(bgcolor="rgba(0,0,0,0)",
                           radialaxis=dict(visible=True, range=[0, 1])),
                **PLOT_LAYOUT,
            )
            st.plotly_chart(fig5, use_container_width=True)
            st.caption(t("radar_caption"))
        else:
            st.warning(t("select_one_species"))

        st.markdown(f"### {t('species_table_title')}")
        
        # Calculate per-tree metrics for all species
        sp_perf = summary_df.groupby("species").agg(
            count=("tree_id", "size"),
            avg_dbh_growth_cm=("dbh_growth_cm", "mean"),
            avg_height_growth_m=("height_growth_m", "mean"),
            avg_carbon_kg=("carbon_storage_kg", "mean"),
            avg_seq_kg=("carbon_seq_kg", "mean"),
            avg_stormwater_l=("stormwater_l", "mean"),
            avg_pm25_g=("pm25_removed_g", "mean"),
            avg_no2_g=("no2_removed_g", "mean"),
            total_carbon_kg=("carbon_storage_kg", "sum"),
            total_stormwater_l=("stormwater_l", "sum")
        ).copy()

        # Normalize components relative to max in dataset to calculate Eco-Efficiency Score (0-100)
        norm_components = pd.DataFrame(index=sp_perf.index)
        for col in ["avg_carbon_kg", "avg_seq_kg", "avg_stormwater_l", "avg_pm25_g", "avg_no2_g"]:
            mx = sp_perf[col].max()
            norm_components[col] = sp_perf[col] / mx if mx > 0 else 0.0
            
        sp_perf["eco_efficiency_score"] = norm_components.mean(axis=1) * 100

        # Sort by eco-efficiency to get ranks
        sp_perf = sp_perf.sort_values("eco_efficiency_score", ascending=False)
        sp_perf["efficiency_rank"] = range(1, len(sp_perf) + 1)

        # Select, order, and rename columns for display
        sp_agg_display = sp_perf[[
            "efficiency_rank",
            "count",
            "eco_efficiency_score",
            "avg_dbh_growth_cm",
            "avg_height_growth_m",
            "avg_carbon_kg",
            "avg_stormwater_l",
            "total_carbon_kg",
            "total_stormwater_l"
        ]].reset_index()

        sp_agg_display.columns = [
            t("col_species"),
            t("col_rank"),
            t("col_count"),
            t("col_score"),
            t("col_avg_dbh_growth"),
            t("col_avg_height_growth"),
            t("col_avg_carbon_storage"),
            t("col_avg_stormwater"),
            t("col_total_carbon_storage"),
            t("col_total_stormwater")
        ]

        st.dataframe(sp_agg_display.round(1), use_container_width=True, hide_index=True)
    else:
        st.info(t("species_breakdown_dxf_required"))


# ══════════════════════════════════════════════════════════════════════
# TAB 5: EXPORT
# ══════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown(f"## {t('download_reports')}")

    if summary_df.empty:
        st.info(t("export_info"))
    else:
        col1, col2, col3 = st.columns(3)

        with col1:
            csv_sched = schedule_df.to_csv(index=False)
            st.download_button(
                t("dl_full_sched"),
                csv_sched, "treefolk_atlas_schedule.csv", "text/csv",
                use_container_width=True,
            )
            st.caption(t("rows_count", n=len(schedule_df)))

        with col2:
            csv_sum = summary_df.to_csv(index=False)
            st.download_button(
                t("dl_summary"),
                csv_sum, "treefolk_atlas_summary.csv", "text/csv",
                use_container_width=True,
            )
            st.caption(t("trees_count", n=len(summary_df)))

        with col3:
            sp_agg = (summary_df.groupby("species").agg(
                count=("tree_id", "size"),
                avg_dbh_growth_cm=("dbh_growth_cm", "mean"),
                avg_height_growth_m=("height_growth_m", "mean"),
                total_carbon_kg=("carbon_storage_kg", "sum"),
                total_stormwater_l=("stormwater_l", "sum"),
            ).sort_values("total_carbon_kg", ascending=False).reset_index())
            csv_sp = sp_agg.to_csv(index=False)
            st.download_button(
                t("dl_species"),
                csv_sp, "treefolk_atlas_species.csv", "text/csv",
                use_container_width=True,
            )
            st.caption(t("species_count_msg", n=len(sp_agg)))

        st.markdown("---")
        st.markdown(f"### {t('full_data_table')}")
        
        summary_df_display = summary_df.copy()
        if "cumulative_co2_seq_kg" in summary_df_display.columns:
            summary_df_display["cumulative_motorcycle_km"] = summary_df_display["cumulative_co2_seq_kg"] * 20.0
            summary_df_display["cumulative_smartphones"] = summary_df_display["cumulative_co2_seq_kg"] * 80.645
        
        col_mapping = {
            "tree_id": t("col_tree_id"),
            "block_name": t("col_block"),
            "species": t("col_species"),
            "x": t("col_x"),
            "y": t("col_y"),
            "layer": t("layer_filter"),
            "dbh_cm": t("dbh_label"),
            "height_m": t("height_label").split("[")[0].strip(),
            "carbon_storage_kg": t("col_avg_carbon").split("(")[0].strip() + " (kg)",
            "co2_storage_kg": t("co2_equivalent_stored").split("(")[0].strip() + " (kg)",
            "cumulative_seq_kg": t("cum_c_seq").split("(")[0].strip() + " (kg)",
            "cumulative_co2_seq_kg": t("cum_co2_seq").split("(")[0].strip() + " (kg)",
            "cumulative_o2_production_kg": t("oxygen_production").split("(")[0].strip() + " (kg)",
            "cumulative_epa_liters": f"{t('gasoline_saved')} ({t('units_abbr_liters')})",
            "cumulative_epa_km": f"{t('car_avoided')} ({t('units_abbr_km')})",
            "cumulative_motorcycle_km": f"{t('motorcycle_avoided')} ({t('units_abbr_km')})",
            "cumulative_smartphones": f"{t('smartphones_charged')} ({t('units_abbr_charges')})",
            "stormwater_l": t("stormwater_intercepted").split("(")[0].strip() + " (L)",
            "pm25_removed_g": "PM2.5 (g)",
            "no2_removed_g": "NO₂ (g)",
            "o3_removed_g": "O₃ (g)",
            "so2_removed_g": "SO₂ (g)",
            "dbh_growth_cm": t("col_avg_dbh_growth"),
            "height_growth_m": t("col_avg_height_growth"),
            "match_level": t("species_match")
        }
        
        rename_dict = {k: v for k, v in col_mapping.items() if k in summary_df_display.columns}
        summary_df_display = summary_df_display.rename(columns=rename_dict)
        
        st.dataframe(
            summary_df_display.round(2),
            use_container_width=True,
            hide_index=True,
            height=500,
        )


# ══════════════════════════════════════════════════════════════════════
# TAB 6: METHODOLOGY
# ══════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown(f"## {t('methodology_title')}")
    if st.session_state.lang == "Bahasa Indonesia":
        methodology_path = Path(__file__).parent.parent / "docs" / "methodology_id.md"
    else:
        methodology_path = Path(__file__).parent.parent / "docs" / "methodology.md"
        
    if methodology_path.exists():
        st.markdown(methodology_path.read_text(encoding="utf-8"))
    else:
        st.info(t("methodology_not_found"))
