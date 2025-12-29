
import asyncio
import aiohttp
import time

# Settings
URL = "https://vietcv.seedoo.vn/api/all_jobsv2?page=1"
TOTAL_REQUESTS = 10000
CONCURRENCY_LIMIT = 100 # How many "simultaneous" shots to allow

async def fire_request(session, sem):
    async with sem: # Wait for a slot to open up
        try:
            # We set a tiny timeout because we don't care about the response body
            async with session.get(URL, timeout=5) as response:
                # We don't 'await response.text()', we just move on
                status = response.status
        except Exception:
            pass

async def stress_test():
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.perf_counter()
        
        print(f"🚀 Starting stress test: {TOTAL_REQUESTS} requests...")
        
        for _ in range(TOTAL_REQUESTS):
            # Create a task and add to our list
            task = asyncio.create_task(fire_request(session, sem))
            tasks.append(task)
        
        # This waits for all the 'fires' to at least complete their attempt
        await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"🏁 Done! Sent {TOTAL_REQUESTS} requests in {duration:.2f} seconds.")
        print(f"📈 Avg Rate: {TOTAL_REQUESTS / duration:.2f} req/s")

# If you're in Jupyter, use: 
# await stress_test()
# If you're in a script, use:
asyncio.run(stress_test())