#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example usage of the LangGraph-enhanced AIPython agent

This example shows how to use the enhanced agent system with LangGraph
while maintaining backward compatibility.
"""

import asyncio
from typing import Dict, Any

# Example usage - the API remains exactly the same
async def example_basic_usage():
    """Basic usage example - same API as before"""
    
    # Import (automatically selects LangGraph or fallback)
    from aipyapp.aipy.agent_taskmgr import AgentTaskManager
    from aipyapp.display import DisplayManager
    
    # Setup (same as before)
    settings = {
        'auto_install': False,
        'auto_getenv': False,
        'debug': True
    }
    
    display_config = {'style': 'agent', 'quiet': True}
    display_manager = DisplayManager(display_config)
    
    # Initialize agent (automatically uses LangGraph if available)
    agent = AgentTaskManager(settings, display_manager=display_manager)
    
    # Submit task (same API)
    task_id = await agent.submit_task(
        instruction="Process CSV data and generate summary statistics",
        metadata={"source": "data.csv", "format": "csv"}
    )
    
    # Execute task (now uses LangGraph workflow internally)
    result = await agent.execute_task(task_id)
    
    # Get results (same API, enhanced data)
    detailed_result = await agent.get_task_result(task_id)
    
    print(f"Task completed: {detailed_result['status']}")
    print(f"Results: {detailed_result.get('output', {})}")

async def example_advanced_features():
    """Example showcasing LangGraph-enhanced features"""
    
    from aipyapp.aipy.agent_taskmgr import AgentTaskManager
    
    settings = {'debug': True, 'max_retries': 5}  # Enhanced retry control
    agent = AgentTaskManager(settings)
    
    # Submit complex task
    task_id = await agent.submit_task(
        instruction="Analyze sales data, detect anomalies, and create visualizations",
        metadata={
            "complexity": "high",
            "expected_duration": "5min",
            "requires_visualization": True
        }
    )
    
    # Monitor task progress (enhanced with LangGraph state tracking)
    while True:
        status = await agent.get_task_status(task_id)
        print(f"Current step: {status.get('current_step', 'unknown')}")
        print(f"Status: {status['status']}")
        print(f"Retry count: {status.get('retry_count', 0)}")
        
        if status['status'] in ['completed', 'failed', 'cancelled']:
            break
            
        await asyncio.sleep(1)  # Check every second
    
    # Get comprehensive results
    final_result = await agent.get_task_result(task_id)
    
    # Enhanced result data from LangGraph workflow
    print(f"Execution messages: {len(final_result.get('messages', []))}")
    print(f"Workflow steps completed: {final_result.get('current_step')}")
    print(f"Error recovery attempts: {final_result.get('retry_count', 0)}")

async def example_error_handling():
    """Example of enhanced error handling with LangGraph"""
    
    from aipyapp.aipy.agent_taskmgr import AgentTaskManager
    
    agent = AgentTaskManager({'max_retries': 3})
    
    # Submit a task that might fail
    task_id = await agent.submit_task(
        instruction="Process non-existent file data.csv",
        metadata={"expected_to_fail": True}
    )
    
    try:
        result = await agent.execute_task(task_id)
        
        if result['status'] == 'failed':
            print("Task failed as expected")
            print(f"Retry attempts made: {result.get('retry_count', 0)}")
            print(f"Error details: {result.get('errors', [])}")
        else:
            print("Task succeeded unexpectedly")
            
    except Exception as e:
        print(f"Execution error: {e}")

def example_migration_compatibility():
    """Example showing zero-impact migration"""
    
    # OLD CODE (still works exactly the same)
    """
    from aipyapp.aipy.agent_taskmgr import AgentTaskManager
    
    agent = AgentTaskManager(settings, display_manager=display_manager)
    task_id = await agent.submit_task("Do something")
    result = await agent.execute_task(task_id)
    """
    
    # NEW CODE (same API, enhanced internally)
    """
    from aipyapp.aipy.agent_taskmgr import AgentTaskManager  # Same import
    
    agent = AgentTaskManager(settings, display_manager=display_manager)  # Same initialization  
    task_id = await agent.submit_task("Do something")  # Same submission
    result = await agent.execute_task(task_id)  # Same execution (now with LangGraph!)
    """
    
    print("✅ Migration requires ZERO code changes!")
    print("✅ Enhanced features available automatically")
    print("✅ Fallback ensures compatibility")

async def example_langraph_specific():
    """Example showing LangGraph-specific benefits"""
    
    # When LangGraph is available, you get:
    benefits = {
        "state_management": "Complete workflow state tracking",
        "conditional_execution": "Smart branching based on results", 
        "error_recovery": "Automatic retry with exponential backoff",
        "observability": "Detailed step-by-step execution logs",
        "extensibility": "Easy to add custom workflow nodes"
    }
    
    print("🚀 LangGraph Enhancement Benefits:")
    for feature, description in benefits.items():
        print(f"   {feature}: {description}")
    
    # The workflow automatically includes:
    workflow_steps = [
        "1. Parse Instruction → Validate and prepare task",
        "2. Execute Task → Run with proper error handling", 
        "3. Handle Errors → Retry logic and error recovery",
        "4. Finalize Result → Complete with detailed results"
    ]
    
    print(f"\n🔄 Enhanced Workflow Steps:")
    for step in workflow_steps:
        print(f"   {step}")

if __name__ == "__main__":
    print("🎯 LangGraph Agent Usage Examples")
    print("=" * 50)
    
    print("\n📝 Migration Compatibility:")
    example_migration_compatibility()
    
    print("\n🚀 LangGraph Benefits:")
    asyncio.run(example_langraph_specific())
    
    print("\n💡 Ready to use with your existing code!")
    print("   Just install: pip install langgraph>=0.2.0")
    print("   Zero code changes required!")