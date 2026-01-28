import asyncio
import json
from app.agents.negotiation_agent import analyze_feasibility

async def test_negotiation():
    test_cases = [
        {
            "goal": "Learn Python to get a job at Google",
            "category": "learning",
            "skill_level": "beginner",
            "cadence": "daily"
        },
        {
            "goal": "Read 50 pages of a novel every day",
            "category": "reading",
            "skill_level": "intermediate",
            "cadence": "daily"
        },
        {
            "goal": "Master Quantum Computing in 2 weeks",
            "category": "skill",
            "skill_level": "beginner",
            "cadence": "3x_week"
        }
    ]

    for case in test_cases:
        print(f"\n--- Testing Case ---")
        print(f"Goal: {case['goal']}")
        print(f"Skill: {case['skill_level']}")
        print(f"Cadence: {case['cadence']}")
        
        result = await analyze_feasibility(
            case["goal"],
            case["category"],
            case["skill_level"],
            case["cadence"]
        )
        
        print(f"Result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_negotiation())
