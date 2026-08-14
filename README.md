# Growth Analytics — Acquisition Funnel & CAC:LTV

**Business question:** A growth team spends ~$580k across six marketing channels. **Where should the next dollar go?** The answer isn't "spend more" — it's knowing each channel's unit economics and moving budget to where it pays back.

**Headline results:**

- Channel economics vary wildly. Sorted by **LTV:CAC**: **Email 29×, Referral 20×, Organic 12×** (owned/earned channels win), **Paid Search ~1.9×** (marginal, below the 3:1 target), **Paid Social 0.6×** and **Display 0.2×** (both destroy value — you lose money on every customer).
- **Blended metrics hide this.** Blended LTV:CAC looks healthy (~7×) only because cheap high-volume channels mask the paid losers. The decision has to be made **per channel**.
- **Recommendation:** cut Display, fix or pause Paid Social, tighten Paid Search efficiency, and **shift budget into Referral, Organic, and Email**, which still have headroom before returns diminish.
- The included **budget planner** models diminishing returns and shows that reallocating out of the losers raises total paying customers at equal or lower spend.

---

## What the app does

A Streamlit **BI control panel** — a sidebar cockpit driving a reactive grid of scorecard panels (no tabs):

- **Sidebar controls:** a channel filter and a live **budget-reallocation planner** (per-channel spend sliders with diminishing returns).
- **Scorecard grid:** KPI cards (blended CAC and LTV:CAC), **LTV:CAC by channel**, a **CAC-vs-LTV value map** with break-even and 3:1 lines, the acquisition **funnel**, **payback** bars, a **projected-impact** panel, and a channel scorecard table — all reacting to the sidebar.

▶ **Live app:** _deploy to Streamlit Community Cloud and drop the link here._

## Concepts demonstrated

CAC, LTV (margin- and retention-based), the **LTV:CAC ratio** and the 3:1 rule of thumb, **payback period**, funnel-stage conversion, **diminishing returns** on paid spend, budget reallocation, and why **blended metrics mislead** vs. channel-level decisions.

## Reproduce

```bash
pip install -r requirements.txt
python run_all.py                      # writes the small channel + funnel tables
streamlit run app/streamlit_app.py
```

## A note on the data

Runs offline on a **synthetic but carefully calibrated** channel model (`src/make_data.py`): each channel has its own funnel rates, cost model, ARPU, and retention, tuned to a realistic spread (efficient owned/earned channels vs. money-losing display). The economics (CAC, LTV, payback) are computed from transparent formulas you can audit.

*Built by Vidit Doshi · Growth analytics · unit economics · Python · Streamlit*
