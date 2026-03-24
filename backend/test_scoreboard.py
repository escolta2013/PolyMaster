import asyncio
from dotenv import load_dotenv
load_dotenv(".env")
from run_autonomous_loop import OutcomeResolver

async def main():
    res = OutcomeResolver()
    sb = res._get_supabase()
    
    # 1. Run resolver
    result = await res.resolve_pending()
    print(f"This cycle: {result}")
    
    # 2. Show scoreboard (same logic as the new Step 0)
    totals = sb.table("autonomous_logs").select("correct").in_("correct", ["WIN", "LOSS", "PENDING"]).eq("decision", "WOULD_EXECUTE").execute().data
    total_w = sum(1 for r in totals if r["correct"] == "WIN")
    total_l = sum(1 for r in totals if r["correct"] == "LOSS")
    total_p = sum(1 for r in totals if r["correct"] == "PENDING")
    total_resolved = total_w + total_l
    accuracy = f"{total_w / total_resolved * 100:.1f}%" if total_resolved > 0 else "N/A"
    
    # 3. Count unresolvable (new status)
    unresolvable = sb.table("autonomous_logs").select("id", count="exact").eq("correct", "UNRESOLVABLE").execute()
    unresolvable_count = len(unresolvable.data) if unresolvable.data else 0
    
    print(f"\n=== TRIAL SCOREBOARD ===")
    print(f"  Wins:          {total_w}")
    print(f"  Losses:        {total_l}")
    print(f"  Accuracy:      {accuracy}")
    print(f"  Still Pending: {total_p}")
    print(f"  Unresolvable:  {unresolvable_count}")
    print(f"========================")

if __name__ == "__main__":
    asyncio.run(main())
