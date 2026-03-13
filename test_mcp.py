#!/usr/bin/env python3
"""Test MCP server locally"""

import json
import subprocess

def test_mcp_server():
    """Test the MCP server initialization"""
    
    # Test initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    print("Testing MCP server initialization...")
    print(f"Request: {json.dumps(init_request, indent=2)}")
    
    try:
        # Run the MCP server
        proc = subprocess.Popen(
            ['python', 'kiro_integration/mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send request
        stdout, stderr = proc.communicate(input=json.dumps(init_request) + '\n', timeout=5)
        
        print(f"\nResponse: {stdout}")
        if stderr:
            print(f"Errors: {stderr}")
        
        # Test tools/list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        print("\n\nTesting tools/list...")
        proc = subprocess.Popen(
            ['python', 'kiro_integration/mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(input=json.dumps(tools_request) + '\n', timeout=5)
        print(f"Response: {stdout}")
        
    except subprocess.TimeoutExpired:
        print("ERROR: MCP server timed out")
        proc.kill()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    test_mcp_server()
