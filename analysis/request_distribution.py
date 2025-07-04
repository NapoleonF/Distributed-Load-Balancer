import asyncio
import httpx
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
import random

async def send_request(session, url):
    try:
        response = await session.get(url)
        data = response.json()
        return data.get("message", "")
    except:
        return "error"

async def main():
    url = "http://localhost:5005/home"
    request_count = 10_000
    concurrency = 1000
    results = defaultdict(int)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(0, request_count, concurrency):
            tasks = [send_request(client, url) for _ in range(concurrency)]
            responses = await asyncio.gather(*tasks)
            for res in responses:
                results[res] += 1

    # Extract server names from message strings
    counts = defaultdict(int)
    for message, count in results.items():
        if "Hello from Server:" in message:
            server = message.split("Server:")[1].strip()
            counts[server] += count

    # Plotting
    plt.figure(figsize=(10, 6))
    sns.barplot(x=list(counts.keys()), y=list(counts.values()))
    plt.title("Request Distribution among Servers (N=3, 10,000 Requests)")
    plt.xlabel("Server ID")
    plt.ylabel("Request Count")
    plt.tight_layout()
    filename = f"request_distribution2/{random.randint(1000, 9999)}.png"
    plt.savefig(filename, dpi=300)
    plt.show()
    

if __name__ == "__main__":
    asyncio.run(main())
