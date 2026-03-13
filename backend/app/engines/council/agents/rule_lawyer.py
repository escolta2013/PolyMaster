import logging
import asyncio
from typing import Dict

logger = logging.getLogger("RuleLawyer")

class RuleLawyer:
    """
    The RuleLawyer Agent: Specializes in detecting ambiguities in Market Resolution Rules.
    Document requirement (Strategy #13): "Defensa de la resolución parcial".
    """
    def __init__(self):
        self.ambiguity_keywords = [
            "announce", "confirm", "official", "invade", "declare",
            "source", "reportedly", "according to", "if and only if"
        ]

    async def analyze_rules(self, question: str, rules_text: str) -> Dict:
        """
        Analyzes the text for slippery language.
        """
        logger.info(f"RuleLawyer analyzing: {question}")
        await asyncio.sleep(0.8) # Simulate deep legal reading
        
        found_triggers = [word for word in self.ambiguity_keywords if word in (rules_text + question).lower()]
        
        risk_level = "LOW"
        if len(found_triggers) > 1: risk_level = "MEDIUM"
        if len(found_triggers) > 3: risk_level = "HIGH"
        
        # Determine internal confidence score
        score = 0.9 if risk_level == "LOW" else 0.4 if risk_level == "HIGH" else 0.7
        
        reasoning = f"No major ambiguities found. Resolution source seems stable."
        if risk_level != "LOW":
            reasoning = f"WARNING: Detected ambiguous terms ({', '.join(found_triggers)}). This market relies on unconfirmed reports or subjective definitions."

        return {
            "agent": "RuleLawyer",
            "risk_level": risk_level,
            "confidence_score": score,
            "found_triggers": found_triggers,
            "reasoning": reasoning
        }
