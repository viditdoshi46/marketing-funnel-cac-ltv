"""
Growth Analytics — Acquisition Funnel & Unit Economics (CAC : LTV).

Where should the next marketing dollar go? The app breaks the funnel down by
channel, computes CAC, LTV, the LTV:CAC ratio and payback period, and lets you
reallocate budget under diminishing returns to see the projected impact.

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

st.set_page_config(page_title="Funnel & CAC:LTV | Vidit Doshi",
                   layout="wide", page_icon="📈")

st.markdown("""
<style>
  .block-container {max-width: 1120px; padding-top: 2.6rem;}
  .hero {background:linear-gradient(120deg,#1d4ed8 0%,#3b82f6 100%); color:#fff;
         padding:22px 26px; border-radius:14px; margin-bottom:6px;}
  .hero h1 {color:#fff; margin:0; font-size:1.6rem; font-weight:700;}
  .hero p {color:#dbeafe; margin:6px 0 0; font-size:1.0rem;}
  div[data-testid="stMetric"] {border:1px solid rgba(59,130,246,.30);
      border-radius:12px; padding:12px 16px;}
  .note {background:#eff6ff; border-left:4px solid #3b82f6; color:#1e3a8a;
         padding:12px 16px; border-radius:8px; margin-top:6px;}
</style>
""", unsafe_allow_html=True)

DATA = ROOT / "data"
RATIO_TARGET = 3.0          # LTV:CAC rule of thumb for a healthy channel
ELASTICITY = 0.75           # diminishing-returns exponent for the budget model


@st.cache_data
def load(name):
    return pd.read_csv(DATA / name)


ch = load("channel_summary.csv")
funnel = load("funnel.csv")

st.markdown("""
<div class="hero">
  <h1>📈 Growth Analytics — Funnel & Unit Economics</h1>
  <p>Acquisition funnel, CAC, LTV, payback, and a budget-reallocation model.
     Where should the next dollar go?</p>
</div>
""", unsafe_allow_html=True)

tab_econ, tab_funnel, tab_cacltv, tab_budget = st.tabs(
    ["💰  Unit economics", "🔽  Funnel", "⚖️  CAC vs LTV", "🎛️  Budget planner"])

# ============================ UNIT ECONOMICS ============================
with tab_econ:
    tot_spend = ch["spend"].sum()
    tot_cust = ch["paying_customers"].sum()
    blended_cac = tot_spend / tot_cust
    blended_ltv = (ch["ltv"] * ch["paying_customers"]).sum() / tot_cust
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total spend", f"${tot_spend:,.0f}")
    k2.metric("Paying customers", f"{tot_cust:,.0f}")
    k3.metric("Blended CAC", f"${blended_cac:,.0f}")
    k4.metric("Blended LTV:CAC", f"{blended_ltv/blended_cac:.1f}×",
              "healthy ≥ 3×" if blended_ltv/blended_cac >= 3 else "below 3×")

    show = ch[["channel", "spend", "paying_customers", "cac", "ltv",
               "ltv_cac_ratio", "payback_months"]].sort_values(
        "ltv_cac_ratio", ascending=False)

    def health(v):
        return "🟢" if v >= 3 else ("🟠" if v >= 1 else "🔴")
    show.insert(0, "", show["ltv_cac_ratio"].map(health))
    st.dataframe(show, hide_index=True, use_container_width=True,
                 column_config={
                     "spend": st.column_config.NumberColumn(format="$%d"),
                     "cac": st.column_config.NumberColumn(format="$%.0f"),
                     "ltv": st.column_config.NumberColumn(format="$%.0f"),
                     "ltv_cac_ratio": st.column_config.NumberColumn("LTV:CAC", format="%.2f×"),
                     "payback_months": st.column_config.NumberColumn("payback (mo)", format="%.1f"),
                 })

    fig = px.bar(show.sort_values("ltv_cac_ratio"), x="ltv_cac_ratio", y="channel",
                 orientation="h", color="ltv_cac_ratio",
                 color_continuous_scale="RdYlGn", text="ltv_cac_ratio")
    fig.add_vline(x=RATIO_TARGET, line_dash="dash", line_color="#334155",
                  annotation_text="3:1 target")
    fig.update_layout(height=340, coloraxis_showscale=False,
                      margin=dict(t=20, l=10, r=10, b=10), xaxis_title="LTV : CAC")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="note"><b>Read:</b> Referral, Organic and Email clear '
                'the 3:1 bar comfortably; <b>Paid Search is marginal (~2:1)</b>; '
                '<b>Paid Social and Display lose money</b> (below 1:1). The dollars '
                'want to move toward the owned/earned channels.</div>',
                unsafe_allow_html=True)

# ============================ FUNNEL ============================
with tab_funnel:
    sel = st.selectbox("Channel", ["All channels"] + list(ch["channel"]))
    stages = ["Impressions", "Clicks", "Signups", "Activations", "Paying"]
    if sel == "All channels":
        f = funnel.groupby("stage")["count"].sum().reindex(stages)
    else:
        f = funnel[funnel.channel == sel].set_index("stage")["count"].reindex(stages)

    fig = go.Figure(go.Funnel(y=stages, x=f.values, textinfo="value+percent initial",
                              marker=dict(color=["#93c5fd", "#60a5fa", "#3b82f6",
                                                 "#2563eb", "#1d4ed8"])))
    fig.update_layout(height=420, margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # stage-to-stage conversion table by channel
    piv = funnel.pivot(index="channel", columns="stage", values="count")[stages]
    conv = pd.DataFrame({
        "channel": piv.index,
        "CTR": (piv["Clicks"] / piv["Impressions"]),
        "click→signup": (piv["Signups"] / piv["Clicks"]),
        "signup→paying": (piv["Paying"] / piv["Signups"]),
        "overall (impr→pay)": (piv["Paying"] / piv["Impressions"]),
    })
    st.dataframe(conv, hide_index=True, use_container_width=True,
                 column_config={c: st.column_config.NumberColumn(format="%.2f%%")
                                for c in ["CTR", "click→signup", "signup→paying"]}
                 | {"overall (impr→pay)": st.column_config.NumberColumn(format="%.3f%%")})
    st.caption("Percentages shown ×100. Referral & Email convert far better per "
               "impression; Display buys huge reach that barely converts.")

# ============================ CAC vs LTV ============================
with tab_cacltv:
    fig = px.scatter(ch, x="cac", y="ltv", size="paying_customers", color="channel",
                     text="channel", size_max=55)
    lim = max(ch["cac"].max(), ch["ltv"].max()) * 1.1
    fig.add_shape(type="line", x0=0, y0=0, x1=lim, y1=lim,
                  line=dict(dash="dot", color="#94a3b8"))       # 1:1 breakeven
    fig.add_shape(type="line", x0=0, y0=0, x1=lim, y1=3*lim,
                  line=dict(dash="dash", color="#22c55e"))      # 3:1 target
    fig.update_traces(textposition="top center")
    fig.update_layout(height=460, xaxis_title="CAC ($)", yaxis_title="LTV ($)",
                      showlegend=False, margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="note"><b>How to read it:</b> the dotted line is '
                'break-even (LTV = CAC); the green dashed line is the 3:1 target. '
                'Channels above green are healthy; between the lines are marginal; '
                'below the dotted line destroy value. Bubble size = paying '
                'customers acquired.</div>', unsafe_allow_html=True)

    pay = ch.sort_values("payback_months")
    figp = px.bar(pay, x="payback_months", y="channel", orientation="h",
                  color="payback_months", color_continuous_scale="RdYlGn_r",
                  text="payback_months")
    figp.add_vline(x=12, line_dash="dash", line_color="#334155",
                   annotation_text="12-mo target")
    figp.update_layout(height=320, coloraxis_showscale=False,
                       xaxis_title="CAC payback (months)",
                       margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(figp, use_container_width=True)

# ============================ BUDGET PLANNER ============================
with tab_budget:
    st.markdown("Reallocate spend and see the projected impact. Each channel has "
                "**diminishing returns** — doubling spend does *not* double "
                f"customers (response ∝ spend^{ELASTICITY}).")
    # calibration constant k so current spend reproduces current customers
    base = ch.set_index("channel")
    k = base["paying_customers"] / (base["spend"] ** ELASTICITY)

    st.caption("Set each channel's monthly spend (defaults = current):")
    cols = st.columns(3)
    new_spend = {}
    for i, c in enumerate(base.index):
        cur = float(base.loc[c, "spend"])
        new_spend[c] = cols[i % 3].slider(
            c, 0.0, float(cur * 3), cur, step=1000.0, format="$%d")

    proj = {c: float(k[c] * (max(new_spend[c], 1)) ** ELASTICITY) for c in base.index}
    cur_cust = base["paying_customers"]
    proj_cust = pd.Series(proj)
    cur_total, new_total = float(cur_cust.sum()), float(proj_cust.sum())
    cur_spend, new_spend_total = float(base["spend"].sum()), float(sum(new_spend.values()))
    # revenue proxy = customers × channel LTV
    cur_rev = float((cur_cust * base["ltv"]).sum())
    new_rev = float((proj_cust * base["ltv"]).sum())

    m = st.columns(4)
    m[0].metric("Spend", f"${new_spend_total:,.0f}", f"{new_spend_total-cur_spend:+,.0f}")
    m[1].metric("Paying customers", f"{new_total:,.0f}", f"{new_total-cur_total:+,.0f}")
    m[2].metric("Blended CAC", f"${new_spend_total/max(new_total,1):,.0f}",
                f"{new_spend_total/max(new_total,1)-cur_spend/cur_total:+,.0f}")
    m[3].metric("Projected LTV", f"${new_rev:,.0f}", f"{new_rev-cur_rev:+,.0f}")

    comp = pd.DataFrame({"channel": base.index,
                         "current": cur_cust.values.astype(int),
                         "projected": proj_cust.round(0).astype(int).values})
    figc = px.bar(comp.melt(id_vars="channel", var_name="scenario",
                            value_name="paying customers"),
                  x="channel", y="paying customers", color="scenario",
                  barmode="group", color_discrete_sequence=["#94a3b8", "#2563eb"])
    figc.update_layout(height=340, margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(figc, use_container_width=True)
    st.markdown('<div class="note"><b>The move:</b> shifting budget out of Display '
                'and Paid Social into Referral, Organic and Paid Search raises total '
                'paying customers at equal or lower spend — because you\'re buying '
                'from channels with more headroom before returns diminish. Try it '
                'with the sliders.</div>', unsafe_allow_html=True)

    with st.expander("📚 Methodology — the concepts, in plain English"):
        st.markdown("""
- **CAC (Customer Acquisition Cost)** = channel spend ÷ paying customers acquired.
  What it costs to buy one paying customer.
- **LTV (Lifetime Value)** = monthly ARPU × gross margin × expected lifetime,
  where expected lifetime (months) = 1 ÷ (1 − monthly retention). The gross profit
  a customer generates before they churn.
- **LTV:CAC ratio.** The unit-economics headline. The rule of thumb: **≥ 3:1** is
  healthy, **1–3** is marginal, **< 1** means you lose money on every customer.
- **Payback period.** Months of gross margin needed to recover CAC; **under ~12
  months** is the usual target for healthy cash flow.
- **Diminishing returns.** Marginal CAC rises as you scale a channel (you exhaust
  the cheap, high-intent audience first), so the budget model uses a concave
  response curve — that's why you can't fix a bad channel just by spending more,
  and why reallocation (not just more budget) is the lever.
- **Blended vs. channel metrics.** Blended CAC hides winners and losers; always
  decide at the **channel** level.
""")

st.caption("Built by Vidit Doshi · Growth analytics · CAC/LTV · funnel analysis · "
           "budget optimization · Python · Streamlit")
