"""
Growth Analytics — CAC:LTV Control Panel.

A BI cockpit: the left sidebar is the control panel (channel filter + a live
budget-reallocation planner); the main area is a spacious, single-column stack of
scorecard panels. Answers: which channels earn their spend, and where the next
dollar should go.

Run:  streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CAC:LTV Control Panel | Vidit Doshi",
                   layout="wide", page_icon="📊")

st.markdown("""
<style>
  /* centered, roomy column (not edge-to-edge) so charts breathe */
  .block-container {max-width: 1120px; margin: 0 auto;
                    padding-top: 2.6rem; padding-bottom: 5rem;}
  .topbar {height:6px; border-radius:5px; margin-bottom:18px;
           background:linear-gradient(90deg,#1d4ed8,#3b82f6,#22c55e);}
  .title {font-size:2rem; font-weight:800; color:#0f172a; letter-spacing:-.025em; margin:0;}
  .sub {color:#64748b; margin:.45rem 0 0; font-size:1.06rem;}
  .kpi {background:#fff; border:1px solid #e9edf2; border-radius:16px;
        padding:22px 24px; min-height:120px;
        box-shadow:0 1px 2px rgba(16,24,40,.05), 0 18px 36px -26px rgba(16,24,40,.35);}
  .kpi .v {font-size:2rem; font-weight:800; color:#0f172a; line-height:1.05;}
  .kpi .l {font-size:.77rem; color:#64748b; text-transform:uppercase;
           letter-spacing:.05em; margin-top:9px;}
  .kpi .s {font-size:.86rem; font-weight:700; margin-top:6px;}
  [data-testid="stVerticalBlockBorderWrapper"]{
     background:#fff; border:1px solid #e9edf2 !important; border-radius:18px;
     box-shadow:0 1px 2px rgba(16,24,40,.05), 0 22px 44px -30px rgba(16,24,40,.4);}
  .ph {font-size:1.2rem; font-weight:800; color:#0f172a; margin:2px 0 2px;
       letter-spacing:-.015em;}
  .ph-q {font-size:.96rem; color:#64748b; margin:0 0 8px;}
  .spacer {height:36px;}
  section[data-testid="stSidebar"] {border-right:1px solid #e9edf2;}
</style>
""", unsafe_allow_html=True)

DATA = ROOT / "data"
RATIO_TARGET, ELASTICITY = 3.0, 0.75
STAGES = ["Impressions", "Clicks", "Signups", "Activations", "Paying"]
INK, GRID = "#0f172a", "#eef1f5"


@st.cache_data
def load(name):
    return pd.read_csv(DATA / name)


def style(fig, h=420):
    fig.update_layout(height=h, paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(color=INK, size=13, family="Inter, sans-serif"),
                      margin=dict(t=18, l=18, r=22, b=18))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def spacer():
    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)


def panel(title, sub=""):
    st.markdown(f'<div class="ph">{title}</div>'
                + (f'<div class="ph-q">{sub}</div>' if sub else ''),
                unsafe_allow_html=True)


ch_all = load("channel_summary.csv")
funnel = load("funnel.csv")

# ================= SIDEBAR: CONTROL PANEL =================
with st.sidebar:
    st.header("🎛️ Control panel")
    st.caption("Filter the view and reallocate budget — everything updates live.")
    picked = st.multiselect("Channels in view", list(ch_all.channel),
                            default=list(ch_all.channel))
    if not picked:
        picked = list(ch_all.channel)
    st.divider()
    st.subheader("💸 Budget planner")
    st.caption(f"Diminishing returns (response ∝ spend^{ELASTICITY}).")
    new_spend = {}
    for c in ch_all.channel:
        cur = float(ch_all.loc[ch_all.channel == c, "spend"].iloc[0])
        new_spend[c] = st.slider(c, 0.0, round(cur*3, -3), cur, step=1000.0, format="$%d")

ch = ch_all[ch_all.channel.isin(picked)].copy()

# ================= HEADER =================
st.markdown('<div class="topbar"></div>'
            '<div class="title">📊 Growth Analytics — Acquisition & Unit Economics</div>'
            '<div class="sub">Where should the next marketing dollar go? '
            'CAC · LTV · payback · funnel · budget reallocation.</div>',
            unsafe_allow_html=True)
spacer()

# ================= KPI SCORECARD ROW =================
tot_spend, tot_cust = ch.spend.sum(), ch.paying_customers.sum()
blended_cac = tot_spend / tot_cust
blended_ltv = (ch.ltv * ch.paying_customers).sum() / tot_cust
ratio = blended_ltv / blended_cac
best = ch.sort_values("ltv_cac_ratio", ascending=False).iloc[0]


def kpi(col, value, label, sub="", color="#0f172a", accent="#2563eb"):
    col.markdown(f'<div class="kpi" style="border-top:4px solid {accent}">'
                 f'<div class="v">{value}</div><div class="l">{label}</div>'
                 + (f'<div class="s" style="color:{color}">{sub}</div>' if sub else '')
                 + '</div>', unsafe_allow_html=True)


k = st.columns(4, gap="large")
kpi(k[0], f"${tot_spend:,.0f}", "Spend (in view)")
kpi(k[1], f"{tot_cust:,.0f}", "Paying customers")
kpi(k[2], f"${blended_cac:,.0f}", "Blended CAC")
kpi(k[3], f"{ratio:.1f}×", "Blended LTV:CAC",
    "healthy ≥ 3×" if ratio >= 3 else "below 3×",
    "#059669" if ratio >= 3 else "#dc2626")
st.caption(f"Best channel in view: **{best.channel}** at "
           f"**{best.ltv_cac_ratio:.1f}× LTV:CAC**.")

# ================= FULL-WIDTH PANELS (single column) =================
spacer()
with st.container(border=True):
    panel("LTV : CAC by channel", "≥ 3:1 is healthy · 1–3 marginal · < 1 loses money")
    d = ch.sort_values("ltv_cac_ratio")
    fig = px.bar(d, x="ltv_cac_ratio", y="channel", orientation="h",
                 color="ltv_cac_ratio", color_continuous_scale="RdYlGn", text="ltv_cac_ratio")
    fig.add_vline(x=RATIO_TARGET, line_dash="dash", line_color="#334155", annotation_text="3:1 target")
    fig.update_traces(textposition="outside", cliponaxis=False)
    style(fig, 430)
    fig.update_layout(coloraxis_showscale=False, xaxis_title="LTV : CAC", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

spacer()
with st.container(border=True):
    panel("CAC vs LTV — value map", "dotted = break-even (1:1) · green dashed = 3:1 target · bubble = customers")
    fig = px.scatter(ch, x="cac", y="ltv", size="paying_customers", color="channel",
                     text="channel", size_max=60)
    lim = max(ch.cac.max(), ch.ltv.max())*1.12
    fig.add_shape(type="line", x0=0, y0=0, x1=lim, y1=lim, line=dict(dash="dot", color="#94a3b8"))
    fig.add_shape(type="line", x0=0, y0=0, x1=lim, y1=3*lim, line=dict(dash="dash", color="#22c55e"))
    fig.update_traces(textposition="top center")
    style(fig, 480)
    fig.update_layout(showlegend=False, xaxis_title="CAC ($)", yaxis_title="LTV ($)")
    st.plotly_chart(fig, use_container_width=True)

spacer()
with st.container(border=True):
    panel("Acquisition funnel", "impressions → clicks → signups → activations → paying (channels in view)")
    f = funnel[funnel.channel.isin(picked)].groupby("stage")["count"].sum().reindex(STAGES)
    fig = go.Figure(go.Funnel(y=STAGES, x=f.values, textinfo="value+percent initial",
                              marker=dict(color=["#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"])))
    style(fig, 440)
    st.plotly_chart(fig, use_container_width=True)

spacer()
with st.container(border=True):
    panel("CAC payback", "months of gross margin to recover CAC · under 12 is healthy")
    p = ch.sort_values("payback_months")
    fig = px.bar(p, x="payback_months", y="channel", orientation="h",
                 color="payback_months", color_continuous_scale="RdYlGn_r", text="payback_months")
    fig.add_vline(x=12, line_dash="dash", line_color="#334155", annotation_text="12-mo target")
    fig.update_traces(textposition="outside", cliponaxis=False)
    style(fig, 400)
    fig.update_layout(coloraxis_showscale=False, xaxis_title="payback (months)", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

# ================= BUDGET PLANNER OUTPUT =================
spacer()
with st.container(border=True):
    panel("💸 Budget reallocation — projected impact", "set each channel's spend in the sidebar")
    base = ch_all.set_index("channel")
    kconst = base.paying_customers / (base.spend ** ELASTICITY)
    proj = {c: float(kconst[c] * max(new_spend[c], 1) ** ELASTICITY) for c in base.index}
    proj_cust = pd.Series(proj)
    cur_cust, cur_spend = base.paying_customers, base.spend
    new_spend_tot, new_cust_tot = sum(new_spend.values()), float(proj_cust.sum())
    cur_rev, new_rev = float((cur_cust*base.ltv).sum()), float((proj_cust*base.ltv).sum())

    m = st.columns(4, gap="large")
    kpi(m[0], f"${new_spend_tot:,.0f}", "Planned spend",
        f"{new_spend_tot-cur_spend.sum():+,.0f} vs now",
        "#059669" if new_spend_tot <= cur_spend.sum() else "#dc2626")
    kpi(m[1], f"{new_cust_tot:,.0f}", "Paying customers",
        f"{new_cust_tot-cur_cust.sum():+,.0f}",
        "#059669" if new_cust_tot >= cur_cust.sum() else "#dc2626", "#22c55e")
    kpi(m[2], f"${new_spend_tot/max(new_cust_tot,1):,.0f}", "Blended CAC")
    kpi(m[3], f"${new_rev:,.0f}", "Projected LTV", f"{new_rev-cur_rev:+,.0f}",
        "#059669" if new_rev >= cur_rev else "#dc2626", "#22c55e")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    comp = pd.DataFrame({"channel": base.index, "current": cur_cust.values.astype(int),
                         "planned": proj_cust.round(0).astype(int).values})
    fig = px.bar(comp.melt(id_vars="channel", var_name="scenario", value_name="paying customers"),
                 x="channel", y="paying customers", color="scenario", barmode="group",
                 color_discrete_sequence=["#94a3b8", "#2563eb"])
    style(fig, 340)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Shift budget out of the money-losers (Display, Paid Social) into "
               "channels with headroom (Referral, Organic, Paid Search) to grow "
               "customers at equal or lower spend.")

# ================= SCORECARD TABLE =================
spacer()
with st.container(border=True):
    panel("Channel scorecard")
    show = ch[["channel", "spend", "paying_customers", "cac", "ltv",
               "ltv_cac_ratio", "payback_months"]].sort_values("ltv_cac_ratio", ascending=False)
    show.insert(0, "", show.ltv_cac_ratio.map(
        lambda v: "🟢" if v >= 3 else ("🟠" if v >= 1 else "🔴")))
    st.dataframe(show, hide_index=True, use_container_width=True,
                 column_config={
                     "spend": st.column_config.NumberColumn(format="$%d"),
                     "cac": st.column_config.NumberColumn(format="$%.0f"),
                     "ltv": st.column_config.NumberColumn(format="$%.0f"),
                     "ltv_cac_ratio": st.column_config.NumberColumn("LTV:CAC", format="%.2f×"),
                     "payback_months": st.column_config.NumberColumn("payback (mo)", format="%.1f")})

spacer()
with st.expander("📚 Methodology — CAC, LTV, payback, diminishing returns"):
    st.markdown("""
- **CAC** = channel spend ÷ paying customers acquired.
- **LTV** = monthly ARPU × gross margin × expected lifetime, where lifetime =
  1 ÷ (1 − monthly retention).
- **LTV:CAC** — the unit-economics headline: **≥ 3:1** healthy, **1–3** marginal,
  **< 1** loses money.
- **Payback** = months of gross margin to recover CAC; **< 12 months** is healthy.
- **Diminishing returns** — marginal CAC rises as you scale a channel, so the
  planner uses a concave response curve; the lever is *reallocation*, not just
  more budget.
- **Blended metrics mislead** — always decide at the channel level.
""")

st.caption("Built by Vidit Doshi · growth analytics · CAC/LTV · budget optimization "
           "· Python · Streamlit")
