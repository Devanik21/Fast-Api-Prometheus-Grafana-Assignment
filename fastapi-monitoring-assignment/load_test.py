import requests
import random
import time
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    "/",
    "/api/data"
]

def make_request():
    """Make a request to a random endpoint"""
    endpoint = random.choice(ENDPOINTS)
    url = f"{BASE_URL}{endpoint}"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        duration = time.time() - start_time
        
        logger.info(
            f"Request to {endpoint} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.4f}s"
        )
        
        return {
            'status': response.status_code,
            'duration': duration,
            'success': response.status_code < 400
        }
    except Exception as e:
        logger.error(f"Request to {endpoint} failed: {str(e)}")
        return {
            'status': 0,
            'duration': 0,
            'success': False
        }

def run_load_test(concurrent_users=5, duration_seconds=300):
    """Run load test with concurrent users for specified duration"""
    logger.info(f"Starting load test with {concurrent_users} users for {duration_seconds} seconds")
    
    results = {
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'total_duration': 0,
        'min_duration': float('inf'),
        'max_duration': 0
    }
    
    end_time = time.time() + duration_seconds
    
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        while time.time() < end_time:
            futures = [executor.submit(make_request) for _ in range(concurrent_users)]
            
            for future in futures:
                try:
                    result = future.result()
                    results['total_requests'] += 1
                    results['total_duration'] += result['duration']
                    
                    if result['success']:
                        results['successful_requests'] += 1
                    else:
                        results['failed_requests'] += 1
                    
                    results['min_duration'] = min(results['min_duration'], result['duration'])
                    results['max_duration'] = max(results['max_duration'], result['duration'])
                    
                except Exception as e:
                    logger.error(f"Error in load test: {str(e)}")
                    results['failed_requests'] += 1
            
            # Add a small delay between batches
            time.sleep(0.1)
    
    # Calculate averages
    if results['total_requests'] > 0:
        results['avg_duration'] = results['total_duration'] / results['total_requests']
        results['success_rate'] = (results['successful_requests'] / results['total_requests']) * 100
    else:
        results['avg_duration'] = 0
        results['success_rate'] = 0
    
    # Log summary
    logger.info("\n=== Load Test Summary ===")
    logger.info(f"Total Requests: {results['total_requests']}")
    logger.info(f"Successful Requests: {results['successful_requests']}")
    logger.info(f"Failed Requests: {results['failed_requests']}")
    logger.info(f"Success Rate: {results['success_rate']:.2f}%")
    logger.info(f"Average Duration: {results['avg_duration']:.4f}s")
    logger.info(f"Min Duration: {results['min_duration']:.4f}s")
    logger.info(f"Max Duration: {results['max_duration']:.4f}s")
    
    return results

if __name__ == "__main__":
    # Run with 5 concurrent users for 5 minutes (300 seconds)
    run_load_test(concurrent_users=5, duration_seconds=300)
