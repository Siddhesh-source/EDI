"""Demo script showing how to interact with the FastAPI backend."""

import asyncio
import json
from datetime import datetime, timedelta
import requests
import websockets

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/signals"
API_KEY = "default_api_key"  # Change this to your actual API key

# Headers for authenticated requests
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def check_health():
    """Check API health status."""
    print("\n=== Health Check ===")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def get_current_signal():
    """Get the current trading signal."""
    print("\n=== Current Signal ===")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/signal/current",
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data:
            print(f"Signal Type: {data['signal_type'].upper()}")
            print(f"CMS Score: {data['cms_score']:.2f}")
            print(f"Confidence: {data['confidence']:.2%}")
            print(f"\nExplanation:")
            print(f"  {data['explanation']['summary']}")
        else:
            print("No signal available yet")
    else:
        print(json.dumps(response.json(), indent=2))


def get_signal_history(limit=5):
    """Get historical trading signals."""
    print(f"\n=== Signal History (last {limit}) ===")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/signal/history?limit={limit}",
        headers=HEADERS
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        signals = response.json()
        print(f"Found {len(signals)} signals")
        for i, signal in enumerate(signals, 1):
            print(f"\n{i}. {signal['signal_type'].upper()} - CMS: {signal['cms_score']:.2f}")
            print(f"   Timestamp: {signal['timestamp']}")
    else:
        print(json.dumps(response.json(), indent=2))


def run_backtest():
    """Run a backtest."""
    print("\n=== Run Backtest ===")
    
    # Backtest configuration
    config = {
        "symbol": "RELIANCE",
        "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "initial_capital": 100000.0,
        "position_size": 0.1,
        "cms_buy_threshold": 60.0,
        "cms_sell_threshold": -60.0
    }
    
    print(f"Running backtest for {config['symbol']}...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/backtest",
        headers=HEADERS,
        json=config
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Backtest ID: {result['backtest_id']}")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        return result['backtest_id']
    else:
        print(json.dumps(response.json(), indent=2))
        return None


def get_backtest_results(backtest_id):
    """Get backtest results."""
    print(f"\n=== Backtest Results ===")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/backtest/{backtest_id}",
        headers=HEADERS
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        metrics = result['metrics']
        
        print(f"\nPerformance Metrics:")
        print(f"  Total Return: {metrics['total_return']:.2%}")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"  Win Rate: {metrics['win_rate']:.2%}")
        print(f"  Total Trades: {metrics['total_trades']}")
        
        print(f"\nTrades: {len(result['trades'])}")
        for i, trade in enumerate(result['trades'][:3], 1):  # Show first 3 trades
            print(f"\n  Trade {i}:")
            print(f"    Entry: {trade['entry_price']:.2f} @ {trade['entry_time']}")
            print(f"    Exit: {trade['exit_price']:.2f} @ {trade['exit_time']}")
            print(f"    P&L: {trade['pnl']:.2f}")
    else:
        print(json.dumps(response.json(), indent=2))


def get_orders(status=None, limit=5):
    """Get orders."""
    print(f"\n=== Orders ===")
    
    url = f"{API_BASE_URL}/api/v1/orders?limit={limit}"
    if status:
        url += f"&status={status}"
    
    response = requests.get(url, headers=HEADERS)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        orders = response.json()
        print(f"Found {len(orders)} orders")
        for i, order in enumerate(orders, 1):
            print(f"\n{i}. {order['side'].upper()} {order['quantity']} {order['symbol']}")
            print(f"   Order ID: {order['order_id']}")
            print(f"   Status: {order['status']}")
            print(f"   Type: {order['order_type']}")
            print(f"   Timestamp: {order['timestamp']}")
    else:
        print(json.dumps(response.json(), indent=2))


async def listen_websocket(duration=10):
    """Listen to WebSocket for real-time signals."""
    print(f"\n=== WebSocket - Listening for {duration} seconds ===")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("Connected to WebSocket")
            
            # Set a timeout for listening
            try:
                async with asyncio.timeout(duration):
                    while True:
                        # Receive message
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if data == "pong":
                            print("Received pong")
                        else:
                            print(f"\nReceived signal update:")
                            signal_data = data.get('data', {})
                            print(f"  Type: {signal_data.get('signal_type', 'N/A').upper()}")
                            print(f"  CMS: {signal_data.get('cms_score', 0):.2f}")
                            print(f"  Timestamp: {signal_data.get('timestamp', 'N/A')}")
                        
                        # Send ping every few seconds
                        await asyncio.sleep(3)
                        await websocket.send("ping")
                        
            except asyncio.TimeoutError:
                print(f"\nListening timeout reached ({duration}s)")
                
    except Exception as e:
        print(f"WebSocket error: {e}")


def main():
    """Run all demo functions."""
    print("=" * 60)
    print("FastAPI Backend Demo")
    print("=" * 60)
    
    # Check health
    check_health()
    
    # Get current signal
    get_current_signal()
    
    # Get signal history
    get_signal_history(limit=5)
    
    # Get orders
    get_orders(limit=5)
    
    # Run backtest (commented out by default as it may take time)
    # backtest_id = run_backtest()
    # if backtest_id:
    #     get_backtest_results(backtest_id)
    
    # Listen to WebSocket (commented out by default)
    # print("\nTo listen to WebSocket, uncomment the following line:")
    # asyncio.run(listen_websocket(duration=10))
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
