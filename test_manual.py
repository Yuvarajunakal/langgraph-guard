from src.langgraph_guard import load_policy

policy = load_policy("examples/basic_policy.yaml")

for tool_name, tool_policy in policy.items():
    print(f"{tool_name}: {tool_policy.action}")
    if tool_policy.reason:
        print(f"  reason: {tool_policy.reason}")