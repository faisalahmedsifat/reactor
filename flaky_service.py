
import logging
import random
import time
import sys

# Configure logging
logging.basicConfig(filename='service_errors.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def simulate_service_call():
    error_types = [
        "ConnectionError: Failed to connect to database",
        "TimeoutError: Backend service took too long to respond",
        "AuthenticationError: Invalid API key",
        "ValueError: Invalid input data",
        "IndexError: List index out of range",
        "TypeError: Unsupported operand type(s)",
        "KeyError: Missing key in dictionary",
        "ZeroDivisionError: Division by zero"
    ]
    
    if random.random() < 0.5:  # 50% chance of error
        error_message = random.choice(error_types)
        logging.error(f"Service call failed: {error_message}")
        # Simulate a crash for some errors to demonstrate the "fix" later

    else:
        print("Service call successful.")

if __name__ == "__main__":
    print("Simulating flaky service. Press Ctrl+C to stop.")
    start_time = time.time()
    try:
        while time.time() - start_time < 10:  # Run for 10 seconds
            simulate_service_call()
            time.sleep(random.uniform(0.1, 0.5))
    except KeyboardInterrupt:
        print("Simulation stopped by user.")
    except Exception as e:
        logging.critical(f"Script crashed: {e}")
        print(f"Script crashed unexpectedly: {e}")
    finally:
        print("Simulation finished.")
