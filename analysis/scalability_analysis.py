import asyncio
import httpx
import random
import string
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json

def random_hostname():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

async def send_request(client, url):
    try:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json().get("message", "")
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Exception: {e}"

async def run_load_test(N, url="http://localhost:5005/home", request_count=10_000, concurrency=1000):
    results = defaultdict(int)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Get current replicas
        rep_response = await client.get("http://localhost:5005/rep")
        rep_data = rep_response.json()
        current_replicas = rep_data["message"]["replicas"]
        current_N = rep_data["message"]["N"]

        # Step 2: Adjust replicas to match N
        if current_N < N:
            needed = N - current_N
            hostnames = [random_hostname() for _ in range(needed)]
            add_payload = {
                "n": needed,
                "hostnames": hostnames
            }
            add_response = await client.post("http://localhost:5005/add", json=add_payload)
            if add_response.status_code != 200:
                print("Failed to add servers:", add_response.text)
                return None
            print(f"Added {needed} replicas: {hostnames}")

        elif current_N > N:
            to_remove = current_N - N
            remove_hosts = current_replicas[:to_remove]
            rm_payload = {
                "n": to_remove,
                "hostnames": remove_hosts
            }
            rm_response = await client.request(
                method="DELETE",
                url="http://localhost:5005/rm",
                content=json.dumps(rm_payload),
                headers={"Content-Type": "application/json"}
            )
            if rm_response.status_code != 200:
                print("Failed to remove servers:", rm_response.text)
                return None
            print(f"Removed {to_remove} replicas: {remove_hosts}")

        # Step 3: Perform load test
        for i in range(0, request_count, concurrency):
            tasks = [send_request(client, url) for _ in range(concurrency)]
            responses = await asyncio.gather(*tasks)
            for res in responses:
                results[res] += 1

    # Step 4: Count requests per server
    counts = defaultdict(int)
    for message, count in results.items():
        if "Hello from Server:" in message:
            server = message.split("Server:")[1].strip()
            counts[server] += count

    total_requests = sum(counts.values())
    num_servers = len(counts)
    avg_load = total_requests / num_servers if num_servers else 0

    return N, avg_load, counts

# Main test loop for N=2 to 6
async def main():
    N_values = list(range(2, 7))  # N = 2 to 6
    avg_loads = []

    os.makedirs("scalability2", exist_ok=True)  # Ensure output directory exists

    for N in N_values:
        print(f"Testing with N = {N} servers...")
        result = await run_load_test(N)
        if result is None:
            print(f"Skipping N={N} due to error.")
            continue
        _, avg_load, distribution = result
        avg_loads.append((N, avg_load))

        print(f"Average Load: {avg_load:.2f}")
        print(f"Distribution: {distribution}")

    if not avg_loads:
        print("No successful results to plot.")
        return

    # Plotting the average load vs number of servers
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    x_vals, y_vals = zip(*avg_loads)
    sns.lineplot(x=x_vals, y=y_vals, marker='o')
    plt.title("Scalability: Average Load vs Number of Servers")
    plt.xlabel("Number of Servers (N)")
    plt.ylabel("Average Requests per Server")
    plt.xticks(x_vals)
    plt.tight_layout()

    filename = f"scalability2/scalability_plot_{random.randint(1000, 9999)}.png"
    plt.savefig(filename, dpi=300)
    plt.close()

    print(f"Saved scalability plot as: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
