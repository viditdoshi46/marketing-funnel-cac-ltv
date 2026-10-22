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
  @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@500;600&display=swap');
  html, body, [class*="css"], .stMarkdown {font-family:'Manrope', sans-serif;}
  .stApp {background: radial-gradient(900px 400px at 0% -10%, rgba(37,99,235,.12), transparent 60%),
                      radial-gradient(700px 360px at 100% 0%, rgba(34,197,94,.10), transparent 60%), #f3f5f9;}
  .block-container {max-width: 1120px; margin: 0 auto; padding-top: 2.4rem; padding-bottom: 5rem;}
  @keyframes rise {from {opacity:0; transform:translateY(14px);} to {opacity:1; transform:none;}}

  .head {position:relative; overflow:hidden; border-radius:22px; padding:30px 34px; color:#fff; animation: rise .5s both;
         background: radial-gradient(520px 220px at 100% 0%, rgba(96,165,250,.55), transparent 60%),
                     linear-gradient(120deg, #0b1f4d 0%, #1d4ed8 100%);
         box-shadow: 0 24px 48px -26px rgba(29,78,216,.8);}
  .head .eb {font-size:.74rem; font-weight:800; letter-spacing:.18em; color:#93c5fd; text-transform:uppercase;}
  .head h1 {color:#fff; font-size:2.35rem; font-weight:800; letter-spacing:-.03em; line-height:1.1; margin:8px 0 8px;}
  .head p {color:#cfe0ff; font-size:1.05rem; margin:0; max-width:66ch; line-height:1.55;}
  .head .bar {position:absolute; left:0; right:0; bottom:0; height:5px; background:linear-gradient(90deg,#22c55e,#3b82f6,#a78bfa);}

  .kpi {position:relative; background:#fff; border:1px solid #e6ebf3; border-radius:18px; padding:20px 22px 18px; min-height:122px;
        box-shadow:0 1px 2px rgba(16,24,40,.05), 0 20px 38px -28px rgba(16,24,40,.4); animation: rise .6s both; transition:transform .25s;}
  .kpi:hover {transform:translateY(-4px);}
  .kpi::before {content:""; position:absolute; left:0; top:18px; bottom:18px; width:4px; border-radius:0 4px 4px 0; background:var(--a,#2563eb);}
  .kpi .l {font-size:.72rem; color:#6b7a90; text-transform:uppercase; letter-spacing:.1em; font-weight:700;}
  .kpi .v {font-family:'IBM Plex Mono', monospace; font-size:1.9rem; font-weight:600; color:#0b1530; line-height:1.15; margin-top:6px;}
  .kpi .s {font-size:.84rem; font-weight:700; margin-top:6px;}

  .play {border-radius:18px; padding:18px 20px; color:#fff; height:100%; animation: rise .6s both;}
  .play .t {font-size:.72rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; opacity:.9;}
  .play .h {font-size:1.3rem; font-weight:800; margin:6px 0 8px; letter-spacing:-.02em;}
  .play ul {margin:0; padding-left:18px; font-size:.92rem; line-height:1.6;} .play li b {font-family:'IBM Plex Mono', monospace;}

  .step {background:#f6f8fc; border:1px solid #e6ebf3; border-radius:12px; padding:10px 12px; text-align:center;}
  .step .v {font-family:'IBM Plex Mono', monospace; font-size:1.2rem; font-weight:600; color:#0b1530;}
  .step .l {font-size:.7rem; color:#6b7a90; letter-spacing:.06em; text-transform:uppercase; margin-top:2px;}

  [data-testid="stVerticalBlockBorderWrapper"]{
     background:#fff; border:1px solid #e6ebf3 !important; border-radius:20px;
     box-shadow:0 1px 2px rgba(16,24,40,.05), 0 24px 46px -32px rgba(16,24,40,.45);}
  .ph {font-size:1.22rem; font-weight:800; color:#0b1530; margin:2px 0 2px; letter-spacing:-.02em;}
  .ph-q {font-size:.95rem; color:#6b7a90; margin:0 0 8px;}
  .spacer {height:34px;}
  section[data-testid="stSidebar"] {background:#fff; border-right:1px solid #e6ebf3;}
  .sbhead {background:linear-gradient(120deg,#0b1f4d,#1d4ed8); color:#fff; border-radius:14px; padding:14px 16px; margin-bottom:10px;}
  .sbhead b {font-size:1.05rem;} .sbhead div {font-size:.82rem; color:#cfe0ff; margin-top:2px;}
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
    st.markdown('<div class="sbhead"><b>Control panel</b><div>Filter the view and reallocate budget. Everything updates live.</div></div>',
                unsafe_allow_html=True)
    picked = st.multiselect("Channels in view", list(ch_all.channel),
                            default=list(ch_all.channel))
    if not picked:
        picked = list(ch_all.channel)
    st.divider()
    st.subheader("Budget planner")
    st.caption(f"Diminishing returns (response ∝ spend^{ELASTICITY}).")
    new_spend = {}
    for c in ch_all.channel:
        cur = float(ch_all.loc[ch_all.channel == c, "spend"].iloc[0])
        new_spend[c] = st.slider(c, 0.0, round(cur*3, -3), cur, step=1000.0, format="$%d")

ch = ch_all[ch_all.channel.isin(picked)].copy()

# ================= HEADER =================
st.markdown('<div class="head"><div class="eb">Growth analytics · Unit economics</div>'
            '<h1>Where should the next marketing dollar go?</h1>'
            '<p>CAC, LTV, payback and the acquisition funnel across six channels, plus a live '
            'budget-reallocation planner with diminishing returns.</p><div class="bar"></div></div>',
            unsafe_allow_html=True)
spacer()

# ================= KPI SCORECARD ROW =================
tot_spend, tot_cust = ch.spend.sum(), ch.paying_customers.sum()
blended_cac = tot_spend / tot_cust
blended_ltv = (ch.ltv * ch.paying_customers).sum() / tot_cust
ratio = blended_ltv / blended_cac
best = ch.sort_values("ltv_cac_ratio", ascending=False).iloc[0]


def kpi(col, value, label, sub="", color="#0f172a", accent="#2563eb", delay=0):
    col.markdown(f'<div class="kpi" style="--a:{accent}; animation-delay:{delay}ms">'
                 f'<div class="l">{label}</div><div class="v">{value}</div>'
                 + (f'<div class="s" style="color:{color}">{sub}</div>' if sub else '')
                 + '</div>', unsafe_allow_html=True)


k = st.columns(4, gap="large")
kpi(k[0], f"${tot_spend:,.0f}", "Spend (in view)", "", "#0f172a", "#2563eb", 0)
kpi(k[1], f"{tot_cust:,.0f}", "Paying customers", "", "#0f172a", "#22c55e", 70)
kpi(k[2], f"${blended_cac:,.0f}", "Blended CAC", "", "#0f172a", "#a78bfa", 140)
kpi(k[3], f"{ratio:.1f}×", "Blended LTV:CAC",
    "healthy at 3x or more" if ratio >= 3 else "below 3x",
    "#059669" if ratio >= 3 else "#dc2626", "#f59e0b", 210)
st.caption(f"Best channel in view: **{best.channel}** at **{best.ltv_cac_ratio:.1f}× LTV:CAC**. "
           "A blended number hides the losers, so read the channel panels below.")

# ================= THE PLAYBOOK =================
spacer()
_r = ch_all.set_index("channel").ltv_cac_ratio.sort_values(ascending=False)


def _lis(names):
    return "".join(f"<li>{n} <b>{_r[n]:.1f}×</b></li>" for n in names) or "<li>none</li>"


scale = [n for n in _r.index if _r[n] >= 10]
fix = [n for n in _r.index if 1 <= _r[n] < 10]
cut = [n for n in _r.index if _r[n] < 1]
pb = st.columns(3, gap="large")
pb[0].markdown(f'<div class="play" style="background:linear-gradient(135deg,#047857,#10b981)"><div class="t">Scale</div>'
               f'<div class="h">Put more here</div><ul>{_lis(scale)}</ul></div>', unsafe_allow_html=True)
pb[1].markdown(f'<div class="play" style="background:linear-gradient(135deg,#b45309,#f59e0b); animation-delay:80ms"><div class="t">Fix</div>'
               f'<div class="h">Tighten efficiency</div><ul>{_lis(fix)}</ul></div>', unsafe_allow_html=True)
pb[2].markdown(f'<div class="play" style="background:linear-gradient(135deg,#b91c1c,#ef4444); animation-delay:160ms"><div class="t">Cut</div>'
               f'<div class="h">Loses money per customer</div><ul>{_lis(cut)}</ul></div>', unsafe_allow_html=True)

# ================= FULL-WIDTH PANELS (single column) =================
GOOD, MID, BAD = "#10b981", "#f59e0b", "#ef4444"
spacer()
with st.container(border=True):
    panel("LTV : CAC by channel", "3:1 or better is healthy · 1 to 3 is marginal · under 1 loses money")
    d = ch.sort_values("ltv_cac_ratio").copy()
    d["tier"] = np.where(d.ltv_cac_ratio >= 3, "Healthy", np.where(d.ltv_cac_ratio >= 1, "Marginal", "Loses money"))
    fig = px.bar(d, x="ltv_cac_ratio", y="channel", orientation="h", color="tier",
                 color_discrete_map={"Healthy": GOOD, "Marginal": MID, "Loses money": BAD},
                 text=d.ltv_cac_ratio.round(1))
    fig.add_vline(x=RATIO_TARGET, line_dash="dash", line_color="#334155", annotation_text="3:1 target")
    fig.update_traces(texttemplate="%{text}×", textposition="outside", cliponaxis=False, marker_cornerradius=8)
    style(fig, 430)
    fig.update_layout(xaxis_title="LTV : CAC", yaxis_title="", legend=dict(orientation="h", y=1.1, x=0, title_text=""))
    st.plotly_chart(fig, use_container_width=True)

spacer()
with st.container(border=True):
    panel("CAC vs LTV: value map", "green zone beats 3:1 · red zone is below break-even · bubble size is paying customers")
    fig = px.scatter(ch, x="cac", y="ltv", size="paying_customers", color="channel",
                     text="channel", size_max=60,
                     color_discrete_sequence=["#2563eb", "#7c3aed", "#ef4444", "#10b981", "#f59e0b", "#0ea5e9"])
    lim = max(ch.cac.max(), ch.ltv.max())*1.12
    fig.add_shape(type="path", path=f"M0,0 L{lim},0 L{lim},{lim} Z", fillcolor="rgba(239,68,68,.07)", line_width=0, layer="below")
    fig.add_shape(type="path", path=f"M0,0 L{lim/3},{lim} L0,{lim} Z", fillcolor="rgba(16,185,129,.09)", line_width=0, layer="below")
    fig.add_shape(type="line", x0=0, y0=0, x1=lim, y1=lim, line=dict(dash="dot", color="#94a3b8"))
    fig.add_shape(type="line", x0=0, y0=0, x1=lim/3, y1=lim, line=dict(dash="dash", color="#22c55e"))
    fig.update_traces(textposition="top center", marker=dict(line=dict(color="white", width=2)))
    style(fig, 480)
    fig.update_layout(showlegend=False, xaxis_title="CAC ($)", yaxis_title="LTV ($)",
                      xaxis=dict(range=[0, lim]), yaxis=dict(range=[0, lim]))
    st.plotly_chart(fig, use_container_width=True)

spacer()
with st.container(border=True):
    panel("Acquisition funnel", "impressions to clicks to signups to activations to paying (channels in view)")
    f = funnel[funnel.channel.isin(picked)].groupby("stage")["count"].sum().reindex(STAGES)
    steps = [("Click-through", f["Clicks"] / f["Impressions"]), ("Click to signup", f["Signups"] / f["Clicks"]),
             ("Signup to active", f["Activations"] / f["Signups"]), ("Active to paying", f["Paying"] / f["Activations"])]
    sc = st.columns(4)
    for col, (lbl, v) in zip(sc, steps):
        col.markdown(f'<div class="step"><div class="v">{v*100:.1f}%</div><div class="l">{lbl}</div></div>',
                     unsafe_allow_html=True)
    fig = go.Figure(go.Funnel(y=STAGES, x=f.values, textinfo="value+percent initial",
                              marker=dict(color=["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#1d4ed8"])))
    style(fig, 420)
    st.plotly_chart(fig, use_container_width=True)

spacer()
with st.container(border=True):
    panel("CAC payback", "months of gross margin to recover CAC · under 12 is healthy")
    p = ch.sort_values("payback_months", ascending=False).copy()
    p["ok"] = np.where(p.payback_months <= 12, "Within 12 months", "Slower than 12 months")
    fig = px.bar(p, x="payback_months", y="channel", orientation="h", color="ok",
                 color_discrete_map={"Within 12 months": GOOD, "Slower than 12 months": BAD},
                 text=p.payback_months.round(1))
    fig.add_vline(x=12, line_dash="dash", line_color="#334155", annotation_text="12-month target")
    fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=8)
    style(fig, 400)
    fig.update_layout(xaxis_title="payback (months)", yaxis_title="", legend=dict(orientation="h", y=1.1, x=0, title_text=""))
    st.plotly_chart(fig, use_container_width=True)

# ================= BUDGET PLANNER OUTPUT =================
spacer()
with st.container(border=True):
    panel("Budget reallocation: projected impact", "set each channel's spend in the sidebar")
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
        "#059669" if new_spend_tot <= cur_spend.sum() else "#dc2626", "#2563eb")
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
                 color_discrete_sequence=["#cbd5e1", "#2563eb"])
    fig.update_traces(marker_cornerradius=6)
    style(fig, 340)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Shift budget out of the money-losers (Display, Paid Social) into "
               "channels with headroom (Referral, Organic, Paid Search) to grow "
               "customers at equal or lower spend.")

# ================= SCORECARD TABLE =================
spacer()
with st.container(border=True):
    panel("Channel scorecard", "every channel in one table, best unit economics first")
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
with st.expander("Methodology: CAC, LTV, payback, diminishing returns"):
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

st.caption("Built by Vidit Doshi · growth analytics · CAC and LTV · budget optimization "
           "· Python · Streamlit")
