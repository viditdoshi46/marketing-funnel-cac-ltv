"""
Growth Analytics — CAC:LTV Control Panel.

A BI cockpit, not a slide deck: the left sidebar is the control panel (channel
filter + a live budget-reallocation planner), and the main area is a reactive
grid of scorecard panels. Answers: which channels earn their spend, and where the
next dollar should go.

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
  .block-container {padding-top: 1.8rem; max-width: 1280px;}
  .topbar {height:5px; border-radius:4px; margin-bottom:10px;
           background:linear-gradient(90deg,#1d4ed8,#3b82f6,#22c55e);}
  .title {font-size:1.5rem; font-weight:800; color:#0f172a; letter-spacing:-.02em; margin:0;}
  .sub {color:#64748b; margin:.2rem 0 1rem;}
  .kpi {background:#fff; border:1px solid #e5e7eb; border-radius:14px;
        padding:14px 16px; text-align:left;}
  .kpi .v {font-size:1.55rem; font-weight:800; color:#0f172a; line-height:1.05;}
  .kpi .l {font-size:.74rem; color:#64748b; text-transform:uppercase; letter-spacing:.03em; margin-top:3px;}
  .kpi .s {font-size:.82rem; font-weight:600; margin-top:2px;}
  .panel-h {font-size:1.02rem; font-weight:700; color:#0f172a; margin:0 0 4px;}
</style>
""", unsafe_allow_html=True)

DATA = ROOT / "data"
RATIO_TARGET = 3.0
ELASTICITY = 0.75
STAGES = ["Impressions", "Clicks", "Signups", "Activations", "Paying"]


@st.cache_data
def load(name):
    return pd.read_csv(DATA / name)


ch_all = load("channel_summary.csv")
funnel = load("funnel.csv")

# ================= SIDEBAR: CONTROL PANEL =================
with st.sidebar:
    st.header("🎛️ Control panel")
    st.caption("Filter the view and reallocate budget. Everything updates live.")
    picked = st.multiselect("Channels in view", list(ch_all.channel),
                            default=list(ch_all.channel))
    if not picked:
        picked = list(ch_all.channel)
    st.divider()
    st.subheader("💸 Budget planner")
    st.caption(f"Response has diminishing returns (∝ spend^{ELASTICITY}).")
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

# ================= KPI SCORECARD ROW =================
tot_spend = ch.spend.sum()
tot_cust = ch.paying_customers.sum()
blended_cac = tot_spend / tot_cust
blended_ltv = (ch.ltv * ch.paying_customers).sum() / tot_cust
best = ch.sort_values("ltv_cac_ratio", ascending=False).iloc[0]


def kpi(col, label, value, sub="", color="#0f172a", accent="#2563eb"):
    col.markdown(f'<div class="kpi" style="border-top:3px solid {accent}">'
                 f'<div class="v">{value}</div><div class="l">{label}</div>'
                 f'<div class="s" style="color:{color}">{sub}</div></div>',
                 unsafe_allow_html=True)


k = st.columns(5)
kpi(k[0], "Spend (in view)", f"${tot_spend:,.0f}")
kpi(k[1], "Paying customers", f"{tot_cust:,.0f}")
kpi(k[2], "Blended CAC", f"${blended_cac:,.0f}")
ratio = blended_ltv/blended_cac
kpi(k[3], "Blended LTV:CAC", f"{ratio:.1f}×",
    "healthy ≥ 3×" if ratio >= 3 else "below 3×",
    "#059669" if ratio >= 3 else "#dc2626")
kpi(k[4], "Best channel", best.channel, f"{best.ltv_cac_ratio:.1f}× LTV:CAC", "#059669")

st.markdown("")

# ================= GRID: ROW 1 =================
r1a, r1b = st.columns(2)
with r1a:
    with st.container(border=True):
        st.markdown('<div class="panel-h">LTV : CAC by channel</div>', unsafe_allow_html=True)
        d = ch.sort_values("ltv_cac_ratio")
        fig = px.bar(d, x="ltv_cac_ratio", y="channel", orientation="h",
                     color="ltv_cac_ratio", color_continuous_scale="RdYlGn",
                     text="ltv_cac_ratio")
        fig.add_vline(x=RATIO_TARGET, line_dash="dash", line_color="#334155",
                      annotation_text="3:1")
        fig.update_layout(height=300, coloraxis_showscale=False,
                          xaxis_title="", yaxis_title="", margin=dict(t=6, l=6, r=6, b=6))
        st.plotly_chart(fig, use_container_width=True)
with r1b:
    with st.container(border=True):
        st.markdown('<div class="panel-h">CAC vs LTV — value map</div>', unsafe_allow_html=True)
        fig = px.scatter(ch, x="cac", y="ltv", size="paying_customers",
                         color="channel", text="channel", size_max=48)
        lim = max(ch.cac.max(), ch.ltv.max())*1.1
        fig.add_shape(type="line", x0=0, y0=0, x1=lim, y1=lim,
                      line=dict(dash="dot", color="#94a3b8"))
        fig.add_shape(type="line", x0=0, y0=0, x1=lim, y1=3*lim,
                      line=dict(dash="dash", color="#22c55e"))
        fig.update_traces(textposition="top center")
        fig.update_layout(height=300, showlegend=False, xaxis_title="CAC ($)",
                          yaxis_title="LTV ($)", margin=dict(t=6, l=6, r=6, b=6))
        st.plotly_chart(fig, use_container_width=True)

# ================= GRID: ROW 2 =================
r2a, r2b = st.columns(2)
with r2a:
    with st.container(border=True):
        st.markdown('<div class="panel-h">Acquisition funnel (channels in view)</div>',
                    unsafe_allow_html=True)
        f = funnel[funnel.channel.isin(picked)].groupby("stage")["count"].sum().reindex(STAGES)
        fig = go.Figure(go.Funnel(y=STAGES, x=f.values, textinfo="value+percent initial",
                                  marker=dict(color=["#93c5fd", "#60a5fa", "#3b82f6",
                                                     "#2563eb", "#1d4ed8"])))
        fig.update_layout(height=300, margin=dict(t=6, l=6, r=6, b=6))
        st.plotly_chart(fig, use_container_width=True)
with r2b:
    with st.container(border=True):
        st.markdown('<div class="panel-h">CAC payback (months)</div>', unsafe_allow_html=True)
        p = ch.sort_values("payback_months")
        fig = px.bar(p, x="payback_months", y="channel", orientation="h",
                     color="payback_months", color_continuous_scale="RdYlGn_r",
                     text="payback_months")
        fig.add_vline(x=12, line_dash="dash", line_color="#334155",
                      annotation_text="12-mo")
        fig.update_layout(height=300, coloraxis_showscale=False, xaxis_title="",
                          yaxis_title="", margin=dict(t=6, l=6, r=6, b=6))
        st.plotly_chart(fig, use_container_width=True)

# ================= BUDGET PLANNER OUTPUT =================
with st.container(border=True):
    st.markdown('<div class="panel-h">💸 Budget reallocation — projected impact '
                '(set spend in the sidebar)</div>', unsafe_allow_html=True)
    base = ch_all.set_index("channel")
    kconst = base.paying_customers / (base.spend ** ELASTICITY)
    proj = {c: float(kconst[c] * max(new_spend[c], 1) ** ELASTICITY) for c in base.index}
    proj_cust = pd.Series(proj)
    cur_cust, cur_spend = base.paying_customers, base.spend
    new_spend_tot, new_cust_tot = sum(new_spend.values()), float(proj_cust.sum())
    cur_rev = float((cur_cust*base.ltv).sum())
    new_rev = float((proj_cust*base.ltv).sum())

    mcols = st.columns(4)
    kpi(mcols[0], "Planned spend", f"${new_spend_tot:,.0f}",
        f"{new_spend_tot-cur_spend.sum():+,.0f} vs now",
        "#059669" if new_spend_tot <= cur_spend.sum() else "#dc2626")
    kpi(mcols[1], "Paying customers", f"{new_cust_tot:,.0f}",
        f"{new_cust_tot-cur_cust.sum():+,.0f}",
        "#059669" if new_cust_tot >= cur_cust.sum() else "#dc2626", "#22c55e")
    kpi(mcols[2], "Blended CAC", f"${new_spend_tot/max(new_cust_tot,1):,.0f}")
    kpi(mcols[3], "Projected LTV", f"${new_rev:,.0f}",
        f"{new_rev-cur_rev:+,.0f}", "#059669" if new_rev >= cur_rev else "#dc2626", "#22c55e")

    comp = pd.DataFrame({"channel": base.index,
                         "current": cur_cust.values.astype(int),
                         "planned": proj_cust.round(0).astype(int).values})
    fig = px.bar(comp.melt(id_vars="channel", var_name="scenario", value_name="paying customers"),
                 x="channel", y="paying customers", color="scenario", barmode="group",
                 color_discrete_sequence=["#94a3b8", "#2563eb"])
    fig.update_layout(height=280, margin=dict(t=6, l=6, r=6, b=6))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Shift budget out of the money-losers (Display, Paid Social) into "
               "channels with headroom (Referral, Organic, Paid Search) to grow "
               "customers at equal or lower spend.")

# ================= SCORECARD TABLE =================
with st.container(border=True):
    st.markdown('<div class="panel-h">Channel scorecard</div>', unsafe_allow_html=True)
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
