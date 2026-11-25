import json
import re
from datetime import datetime
from pathlib import Path

import requests

from tools import search_nasa, calculator, compare_planets, get_source

MODEL = "qwen3:1.7b"
MAX_STEPS = 8
MAX_RETRIES = 3

TOOLS = {
    "search_nasa": search_nasa,
    "calculator": calculator,
    "compare_planets": compare_planets,
    "get_source": get_source
}

SYSTEM_PROMPT = """
You are a NASA solar system research assistant.

Answer questions using only the NASA documents.

Available tools:
1. search_nasa(query)
2. calculator(expression)
3. compare_planets(planet1, planet2)
4. get_source(name)

Respond using valid JSON only.

Search example:
{"action": "search_nasa", "args": {"query": "Mars radius"}}

Calculator example:
{"action": "calculator", "args": {"expression": "3390 * 2"}}

Finish example:
{"action": "finish", "answer": "Your answer with NASA sources."}

Rules:
- Read and use previous tool results.
- Never repeat a completed action.
- Search for radius if diameter is unavailable.
- Diameter equals radius multiplied by 2.
- Use the calculator when math is required.
- Finish immediately when enough information is available.
- Include NASA sources in the final answer.
- Never invent missing information.
- Complete the task within 8 steps.
"""


def ask_model(messages):
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 350,
                "num_ctx": 4096
            }
        },
        timeout=300
    )

    response.raise_for_status()
    return response.json()["message"]["content"]


def parse_decision(text):
    try:
        decision = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if not match:
            raise ValueError("Model did not return valid JSON")

        decision = json.loads(match.group())

    if not isinstance(decision, dict):
        raise ValueError("Invalid decision")

    return decision


def finish_from_results(question, trajectory):
    evidence = [
        {
            "decision": item["decision"],
            "result": item["result"]
        }
        for item in trajectory
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "Answer the question using only the collected "
                "NASA evidence. Do not request another tool. "
                "Include sources. If evidence is insufficient, "
                "explain what information is missing. "
                'Return JSON: {"action": "finish", "answer": "..."}'
            )
        },
        {
            "role": "user",
            "content": (
                f"Question: {question}\n"
                f"Collected evidence: {json.dumps(evidence)}"
            )
        }
    ]

    decision = parse_decision(ask_model(messages))

    if decision.get("action") != "finish":
        return "The agent could not produce a final answer."

    return decision.get("answer", "No answer provided.")


def run_agent(question):
    trajectory = []
    completed_actions = set()
    final_answer = None

    for step in range(1, MAX_STEPS + 1):
        print(f"\nStep {step}")

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Original question: {question}\n"
                    f"Current step: {step} of {MAX_STEPS}\n"
                    f"Previous actions and results: "
                    f"{json.dumps(trajectory)}\n"
                    "Choose the next necessary action. "
                    "If enough information is available, finish."
                )
            }
        ]

        decision = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = ask_model(messages)
                candidate = parse_decision(response)

                action = candidate.get("action")
                args = candidate.get("args", {})

                if action == "finish":
                    decision = candidate
                    break

                if action not in TOOLS:
                    raise ValueError("Unknown tool requested")

                if not isinstance(args, dict):
                    raise ValueError("Invalid tool arguments")

                action_key = json.dumps(
                    {"action": action, "args": args},
                    sort_keys=True
                )

                if action_key in completed_actions:
                    print("Duplicate action blocked.")

                    messages.append({
                        "role": "assistant",
                        "content": json.dumps(candidate)
                    })

                    messages.append({
                        "role": "user",
                        "content": (
                            "That action has already been completed. "
                            "Read the previous results. Choose a "
                            "different action or finish."
                        )
                    })

                    continue

                decision = candidate
                break

            except (requests.RequestException, ValueError) as error:
                print(f"Retry {attempt + 1}: {error}")

        if decision is None:
            print("No new valid action. Ending tool loop.")
            break

        action = decision.get("action")
        args = decision.get("args", {})

        print("Decision:", action)
        print("Arguments:", args)

        if action == "finish":
            final_answer = decision.get("answer", "")

            trajectory.append({
                "step": step,
                "decision": decision,
                "result": final_answer
            })

            break

        action_key = json.dumps(
            {"action": action, "args": args},
            sort_keys=True
        )

        completed_actions.add(action_key)

        try:
            result = TOOLS[action](**args)
        except Exception as error:
            result = f"Tool error: {error}"

        print("Result:", str(result)[:500])

        trajectory.append({
            "step": step,
            "decision": decision,
            "result": result
        })

    # Generate a final answer if the tool loop ends
    if not final_answer:
        if trajectory:
            print("\nGenerating final answer from collected results...")

            try:
                final_answer = finish_from_results(
                    question, trajectory
                )
            except (requests.RequestException, ValueError) as error:
                final_answer = f"Final answer failed: {error}"

            trajectory.append({
                "step": len(trajectory) + 1,
                "decision": {
                    "action": "finish",
                    "method": "fallback"
                },
                "result": final_answer
            })

        else:
            final_answer = "The agent could not retrieve information."

    # Save the complete trajectory
    Path("logs").mkdir(exist_ok=True)

    filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    log_data = {
        "question": question,
        "model": MODEL,
        "max_steps": MAX_STEPS,
        "trajectory": trajectory,
        "final_answer": final_answer
    }

    log_path = Path("logs") / f"trajectory_{filename}.json"

    log_path.write_text(
        json.dumps(log_data, indent=2),
        encoding="utf-8"
    )

    print("\nFINAL ANSWER:")
    print(final_answer)
    print(f"\nLog saved: {log_path}")

    return final_answer


if __name__ == "__main__":
    question = input("Ask a NASA question: ")
    run_agent(question)