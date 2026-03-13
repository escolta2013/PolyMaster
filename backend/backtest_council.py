import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path so we can import 'app'
sys.path.append(os.getcwd())

from app.engines.council.orchestrator import AgentOrchestrator

async def run_backtest():
    load_dotenv()
    
    # Instance the orchestrator
    orchestrator = AgentOrchestrator()
    
    # Market Data for the US Government Shutdown (Resolved to NO on Feb 14)
    # We simulate evaluating this on Feb 12, when price was around 0.18
    market_data = {
        "id": "us-shutdown-feb-2026",
        "question": "Will the US Federal Government experience a shutdown due to lapsed funding in February 2026?",
        "price": 0.18,
        "spike_magnitude": 1.2 # Moderate tension
    }
    
    print(f"\n--- BACKTEST: {market_data['question']} ---")
    print(f"Historical Price: {market_data['price']} | Outcome: NO (0.0)")
    
    # Run Consensus
    result = await orchestrator.get_market_consensus(market_data)
    
    # Logic for Brier and LogLoss
    outcome = 0.0 # Resolution was NO
    final_p = result['final_score']
    
    # Brier Score
    brier = (final_p - outcome)**2
    
    # Scaled Brier (Alpha)
    market_p = market_data['price']
    market_brier = (market_p - outcome)**2
    alpha_brier = market_brier - brier  # Positive is better
    
    print("\n--- RESULTS ---")
    print(f"Final Council Score: {final_p}")
    print(f"Regime: {result['regime']} (Dispersion: {result['metrics']['dispersion']})")
    print(f"CQI: {result['cqi']}")
    print(f"Sizing (Kelly): {result['suggested_sizing']['allocation_pct'] * 100:.2f}%")
    print(f"Arbiter Decision: {result['arbiter_report']['reasoning']}")
    
    print("\n--- PERFORMANCE EVALUATION ---")
    print(f"Brier Score: {brier:.4f}")
    print(f"Market Brier: {market_brier:.4f}")
    print(f"Edge (Alpha Brier): {alpha_brier:.4f}")
    
    if alpha_brier > 0:
        print("RESULT: ALPHAGEN (The system outperformed the market consensus)")
    else:
        print("RESULT: DE-CALIBRATED (The market was smarter than the council)")

    print("\n--- INDIVIDUAL AGENT BRIER ---")
    for report in result['agent_reports']:
        agent_p = report['confidence']
        agent_brier = (agent_p - outcome)**2
        print(f" - {report['agent']}: {agent_p} (Brier: {agent_brier:.4f})")

if __name__ == "__main__":
    async def main():
        await run_backtest()
    
    asyncio.run(main())
