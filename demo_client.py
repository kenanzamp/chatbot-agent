#!/usr/bin/env python3
"""
Demo client for testing the autonomous agent.
Run this after starting the server with: python -m agent.main
"""

import asyncio
import websockets
import json
import sys


async def run_demo():
    uri = "ws://localhost:8000/chat"
    
    print("🔌 Connecting to agent server...")
    
    try:
        async with websockets.connect(uri) as ws:
            # Wait for connection confirmation
            response = await ws.recv()
            data = json.loads(response)
            print(f"✅ Connected: {data.get('data', {}).get('client_id', 'unknown')}\n")
            
            # Demo conversations
            tests = [
                ("Basic chat", "Hello! What can you help me with?"),
                ("Direct tool", "What time is it right now?"),
                ("Skill: basic math", "Calculate 1024 divided by 16"),
                ("Skill: expression", "What is sqrt(144) + 5^2?"),
                ("Skill: array", "Find the average of [85, 92, 78, 96, 88]"),
                ("Skill: convert", "Convert 100 km to miles"),
                ("Combined", "What time is it, and what's 15% of 250?"),
            ]
            
            for test_name, message in tests:
                print(f"\n{'='*60}")
                print(f"TEST: {test_name}")
                print(f"USER: {message}")
                print(f"{'='*60}")
                
                # Send message
                await ws.send(json.dumps({"type": "chat", "content": message}))
                
                # Collect streaming response
                full_response = ""
                while True:
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "text_delta":
                        print(data.get("content", ""), end="", flush=True)
                        full_response += data.get("content", "")
                    elif data["type"] == "tool_start":
                        print(f"\n  [🔧 Calling tool: {data['data']['tool_name']}]")
                    elif data["type"] == "tool_result":
                        status = "✓" if data["data"]["success"] else "✗"
                        print(f"  [{status} Tool result: {data['data']['tool_name']}]")
                    elif data["type"] == "complete":
                        print(f"\n\n✅ Completed in {data['data'].get('iterations', '?')} iterations")
                        break
                    elif data["type"] == "error":
                        print(f"\n❌ Error: {data.get('content')}")
                        break
                    elif data["type"] == "max_iterations":
                        print(f"\n⚠️ Max iterations reached")
                        break
                
                # Small delay between tests
                await asyncio.sleep(1)
            
            # Test reset
            print(f"\n{'='*60}")
            print("TEST: Conversation Reset")
            print(f"{'='*60}")
            await ws.send(json.dumps({"type": "reset"}))
            response = await ws.recv()
            print(f"Reset response: {response}")
            
            print("\n\n🎉 DEMO COMPLETE!")
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"\n❌ Connection closed: {e}")
    except ConnectionRefusedError:
        print("\n❌ Could not connect to server.")
        print("Make sure the server is running with: python -m agent.main")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_demo())
