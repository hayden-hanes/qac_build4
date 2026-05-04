# Comapny dashboard formatting

html = f"""
<div style="font-family: Arial, sans-serif; padding: 24px; background:#0d0f14; color:#e8eaf0; border-radius: 14px;">
  <h1 style="color:#c8a96e; margin-bottom: 4px;">
    {results.get("company", ticker)} ({ticker})
  </h1>
  <p style="color:#aaa;">Company financial dashboard</p>

  <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 20px;">
    <div style="background:#171a22; padding:16px; border-radius:12px;">
      <div style="color:#aaa;">EV/EBIT</div>
      <div style="font-size:28px; font-weight:bold;">{results.get("ev_ebit", "N/A")}x</div>
    </div>
    <div style="background:#171a22; padding:16px; border-radius:12px;">
      <div style="color:#aaa;">Market Cap</div>
      <div style="font-size:28px; font-weight:bold;">${results.get("market_cap", 0):,.0f}M</div>
    </div>
    <div style="background:#171a22; padding:16px; border-radius:12px;">
      <div style="color:#aaa;">EBIT</div>
      <div style="font-size:28px; font-weight:bold;">${results.get("ebit", 0):,.0f}M</div>
    </div>
  </div>

  <h2 style="margin-top:28px;">Quality & Risk Scores</h2>
  <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
    <div style="background:#171a22; padding:14px; border-radius:12px;">Franchise Power: <b>{results.get("franchise_power", "N/A")}</b></div>
    <div style="background:#171a22; padding:14px; border-radius:12px;">Financial Strength: <b>{results.get("financial_strength", "N/A")}</b></div>
    <div style="background:#171a22; padding:14px; border-radius:12px;">Quality: <b>{results.get("quality", "N/A")}</b></div>
    <div style="background:#171a22; padding:14px; border-radius:12px;">Accruals: <b>{results.get("accruals", "N/A")}</b></div>
    <div style="background:#171a22; padding:14px; border-radius:12px;">Beneish PMAN: <b>{results.get("beneish", "N/A")}</b></div>
    <div style="background:#171a22; padding:14px; border-radius:12px;">Distress PFD: <b>{results.get("distress", "N/A")}</b></div>
  </div>

  <h2 style="margin-top:28px;">Analyst Blurb</h2>
  <div style="background:#171a22; padding:16px; border-radius:12px; line-height:1.5;">
    {results.get("blurb", "")}
  </div>
</div>
"""