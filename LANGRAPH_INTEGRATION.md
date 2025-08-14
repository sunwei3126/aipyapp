# LangGraph Integration

This document describes the LangGraph integration for the AIPython agent system.

## Overview

The core agent has been refactored to use LangGraph for stateful, graph-based workflow execution while maintaining backward compatibility with the existing API.

## Architecture

### Before (Linear Execution)
```
Task Submission → Linear Execution → Result
```

### After (Graph-based Execution)
```
Task Submission → Parse Instruction → Execute Task → Handle Errors → Finalize Result
                     ↓                    ↓             ↓
                  Validation         Success/Retry    Retry Logic
```

## Key Components

### 1. LangGraphAgentWorkflow
- Implements the graph-based execution logic
- Defines nodes and edges for the workflow
- Handles error recovery and retry logic
- Provides fallback execution when LangGraph is not available

### 2. LangGraphAgentManager
- Replaces the original AgentTaskManager when LangGraph is available
- Maintains the same API interface for backward compatibility
- Manages LangGraph tasks and their states

### 3. AgentState
- TypedDict defining the complete state structure
- Includes task metadata, execution context, results, and errors
- Supports retry logic and step tracking

## Features

### Graph-based Execution
- **Parse Instruction**: Validates and prepares the task instruction
- **Execute Task**: Runs the actual task using existing task infrastructure  
- **Handle Error**: Manages errors and determines retry strategy
- **Finalize Result**: Completes the task and sets final status

### Error Handling & Retries
- Automatic retry on failures (configurable max retries)
- Error tracking throughout the workflow
- Graceful degradation when components fail

### Backward Compatibility
- Same API interface as original AgentTaskManager
- Automatic fallback when LangGraph is not available
- Seamless integration with existing CLI and HTTP API

### State Management
- Complete state tracking throughout task lifecycle
- Detailed execution context and results
- Status transitions with timestamps

## Usage

### Installation
Add langgraph dependency to requirements:
```toml
dependencies = [
    # ... other dependencies
    "langgraph>=0.2.0",
]
```

### Automatic Selection
The system automatically chooses the appropriate implementation:

```python
# Automatically uses LangGraph if available, otherwise falls back
manager = AgentTaskManager(settings, display_manager=display_manager)
```

### Task Execution
The API remains unchanged:

```python
# Submit task
task_id = await manager.submit_task("Process this data", metadata={"source": "api"})

# Execute task (now uses graph workflow)
result = await manager.execute_task(task_id)

# Get detailed results
final_result = await manager.get_task_result(task_id)
```

## Benefits

### 1. Better Error Handling
- Structured error recovery
- Retry logic with exponential backoff
- Clear error tracking and reporting

### 2. Enhanced Observability
- Step-by-step execution tracking
- Detailed state transitions
- Comprehensive logging

### 3. Improved Reliability
- Fault tolerance through retry mechanisms
- Graceful handling of edge cases
- Robust state management

### 4. Extensibility
- Easy to add new workflow steps
- Conditional branching support
- Plugin-friendly architecture

## Fallback Behavior

When LangGraph is not available:
1. System logs a warning about using fallback
2. Uses simple linear execution similar to original implementation
3. Maintains API compatibility
4. All features work with reduced workflow capabilities

## Testing

The implementation includes comprehensive tests for:
- Graph workflow creation and execution
- State management and transitions
- Error handling and retry logic
- Fallback execution
- API compatibility

## Migration

No migration is required - the system automatically uses the enhanced implementation when LangGraph is available.

## Configuration

The workflow behavior can be configured through settings:
- `max_retries`: Maximum number of retry attempts (default: 3)
- Debug settings are inherited from existing configuration

## Future Enhancements

Potential future improvements:
- Human-in-the-loop workflows
- Parallel execution branches
- Dynamic workflow modification
- Advanced conditional logic
- Workflow persistence and recovery