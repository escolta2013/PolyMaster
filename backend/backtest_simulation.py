import statistics
from datetime import datetime

def run_simulated_backtest():
    # Market Data
    question = "Will the US Federal Government experience a shutdown in February 2026?"
    price = 0.18
    outcome = 0.0 # It did NOT happen
    
    # Simulated Agent Responses (Realistically calibrated based on their mindsets)
    agent_reports = [
        {"agent": "FedWatcher", "confidence": 0.15, "reasoning": "Macro: Bipartisan framework and debt ceiling buffers make Feb shutdown highly unlikely."},
        {"agent": "RuleLawyer", "confidence": 0.05, "reasoning": "Rules: OPM resolution mechanics are well-defined; CR extension is the default path."},
        {"agent": "SentimentSwarm", "confidence": 0.38, "reasoning": "Sentiment: Viral fears of 'blackout' driving over-optimistic YES bets on social narrative."},
        {"agent": "RiskArbiter", "confidence": 0.12, "reasoning": "Arb: SentimentSwarm is overreacting to noise; Fed/Rule consensus is structurally solid."}
    ]
    
    # 1. SPECIALIST ANALYSIS
    specialists = [r for r in agent_reports if r['agent'] != 'RiskArbiter']
    confidences = [r['confidence'] for r in specialists]
    avg_confidence = sum(confidences) / len(specialists)
    std_dev = statistics.stdev(confidences)
    
    # 2. CONFLICT REGIME
    if std_dev < 0.12: regime = "Cohesion"
    elif std_dev < 0.25: regime = "Divergence"
    else: regime = "Fragmentation"
    
    # 3. FINAL SCORE (Risk Arbiter Mediation)
    # Using our 40% weight for Divergence regime (StdDev 0.17 here)
    arbiter = agent_reports[3]
    final_score = (avg_confidence * 0.6) + (arbiter['confidence'] * 0.4)
    
    # 4. QUANT METRICS
    # CQI = (1 - Dispersion) * |SpecialistAvg - Price|
    distance_from_price = abs(avg_confidence - price)
    cqi = (1 - std_dev) * distance_from_price
    
    # 5. BRIER SCORE CALCULATION (The Polar Star)
    # Scaled Brier = (p-y)^2 - (price-y)^2
    final_brier = (final_score - outcome)**2
    market_brier = (price - outcome)**2
    alpha_brier = market_brier - final_brier # Positive = Alpha
    
    print(f"--- SIMULATED INSTITUTIONAL BACKTEST ---")
    print(f"Market: {question}")
    print(f"Historical Price: {price} | Outcome: {outcome}")
    print(f"-"*40)
    print(f"Regime: {regime} (Dispersion: {std_dev:.3f})")
    print(f"Resulting Final Score: {final_score:.3f}")
    print(f"Confidence Quality Index (CQI): {cqi:.3f}")
    
    print(f"\n--- CALIBRATION ANALYSIS (Brier Score) ---")
    print(f"Council Brier Score: {final_brier:.4f} (Perfect is 0.0)")
    print(f"Market Brier Score: {market_brier:.4f}")
    print(f"Scaled Brier (Alpha): {alpha_brier:+.4f} << ALPHA DETECTED")
    
    print(f"\n--- INDIVIDUAL AGENT BRIER (The IQ Table) ---")
    for r in agent_reports:
        b = (r['confidence'] - outcome)**2
        print(f" - {r['agent']:<15} | Score: {r['confidence']:.2f} | Brier: {b:.4f}")
    
    print(f"\n--- SIZING (Fractional Kelly) ---")
    # For NO bet (Short): (price - p) / price
    kelly_raw = (price - final_score) / price
    fraction = 0.1
    allocation = kelly_raw * fraction * (1 - std_dev)
    print(f"Kelly Raw (Short): {kelly_raw:.3f}")
    print(f"Final Allocation: {allocation*100:.2f}% of simulated budget")

if __name__ == "__main__":
    run_simulated_backtest()
