#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, Any, Optional, List, TypedDict
from datetime import datetime
import uuid
import asyncio
from dataclasses import dataclass

from loguru import logger

# LangGraph imports - these would be imported when langgraph is available
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.state import CompiledStateGraph
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.warning("LangGraph not available, using fallback implementation")
    LANGGRAPH_AVAILABLE = False
    # Fallback types
    StateGraph = object
    START = "start"
    END = "end"
    CompiledStateGraph = object
    BaseMessage = dict
    HumanMessage = dict
    AIMessage = dict

from .task import Task
from .taskmgr import TaskManager


class AgentState(TypedDict):
    """Agent state for LangGraph workflow"""
    task_id: str
    instruction: str
    messages: List[Dict[str, Any]]
    current_step: str
    context: Dict[str, Any]
    results: Dict[str, Any]
    errors: List[str]
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    retry_count: int
    max_retries: int


@dataclass
class LangGraphTask:
    """LangGraph-based task wrapper"""
    task_id: str
    instruction: str
    task: Task
    display: Any
    graph: Optional[CompiledStateGraph]
    state: AgentState
    
    def __post_init__(self):
        if not self.state:
            self.state = AgentState(
                task_id=self.task_id,
                instruction=self.instruction,
                messages=[],
                current_step="init",
                context={},
                results={},
                errors=[],
                status="pending",
                created_at=datetime.now().isoformat(),
                started_at=None,
                completed_at=None,
                retry_count=0,
                max_retries=3
            )


class LangGraphAgentWorkflow:
    """LangGraph-based agent workflow implementation"""
    
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.log = logger.bind(src='langraph_agent')
        self.graph = None
        self._build_graph()
    
    def _build_graph(self) -> Optional[CompiledStateGraph]:
        """Build the LangGraph workflow"""
        if not LANGGRAPH_AVAILABLE:
            self.log.warning("LangGraph not available, using fallback")
            return None
            
        try:
            # Create the state graph
            workflow = StateGraph(AgentState)
            
            # Add nodes
            workflow.add_node("parse_instruction", self._parse_instruction)
            workflow.add_node("execute_task", self._execute_task)
            workflow.add_node("handle_error", self._handle_error)
            workflow.add_node("finalize_result", self._finalize_result)
            
            # Add edges
            workflow.add_edge(START, "parse_instruction")
            workflow.add_conditional_edges(
                "parse_instruction",
                self._should_execute,
                {
                    "execute": "execute_task",
                    "error": "handle_error"
                }
            )
            workflow.add_conditional_edges(
                "execute_task",
                self._check_execution_result,
                {
                    "success": "finalize_result",
                    "error": "handle_error",
                    "retry": "execute_task"
                }
            )
            workflow.add_conditional_edges(
                "handle_error",
                self._should_retry,
                {
                    "retry": "parse_instruction",
                    "fail": "finalize_result"
                }
            )
            workflow.add_edge("finalize_result", END)
            
            # Compile the graph
            self.graph = workflow.compile()
            self.log.info("LangGraph workflow compiled successfully")
            return self.graph
            
        except Exception as e:
            self.log.error(f"Failed to build LangGraph workflow: {e}")
            return None
    
    async def _parse_instruction(self, state: AgentState) -> AgentState:
        """Parse and validate the instruction"""
        self.log.info(f"Parsing instruction for task {state['task_id']}")
        
        try:
            # Add parsing logic here
            state["current_step"] = "parse_instruction"
            state["messages"].append({
                "type": "system",
                "content": f"Parsing instruction: {state['instruction']}"
            })
            
            # Validate instruction
            if not state["instruction"] or not state["instruction"].strip():
                state["errors"].append("Empty instruction provided")
                state["status"] = "error"
            else:
                state["context"]["parsed_instruction"] = state["instruction"].strip()
                state["status"] = "parsed"
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Failed to parse instruction: {str(e)}")
            state["status"] = "error"
            return state
    
    async def _execute_task(self, state: AgentState) -> AgentState:
        """Execute the main task"""
        self.log.info(f"Executing task {state['task_id']}")
        
        try:
            state["current_step"] = "execute_task"
            state["started_at"] = datetime.now().isoformat()
            state["status"] = "running"
            
            # Get the task from context (this would be passed in)
            task = state.get("_task_obj")
            if task:
                # Execute the task using the existing task system
                result = await self._run_task_async(task, state["instruction"])
                state["results"]["execution_result"] = result
                state["status"] = "executed"
            else:
                state["errors"].append("No task object available for execution")
                state["status"] = "error"
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Task execution failed: {str(e)}")
            state["status"] = "error"
            state["retry_count"] += 1
            return state
    
    async def _handle_error(self, state: AgentState) -> AgentState:
        """Handle errors and decide on retry strategy"""
        self.log.error(f"Handling error for task {state['task_id']}: {state['errors']}")
        
        state["current_step"] = "handle_error"
        
        # Log the error
        error_msg = "; ".join(state["errors"])
        state["messages"].append({
            "type": "error",
            "content": f"Error occurred: {error_msg}"
        })
        
        # Determine if we should retry
        if state["retry_count"] < state["max_retries"]:
            self.log.info(f"Preparing retry {state['retry_count'] + 1} for task {state['task_id']}")
            state["status"] = "retrying"
        else:
            self.log.error(f"Max retries exceeded for task {state['task_id']}")
            state["status"] = "failed"
            state["completed_at"] = datetime.now().isoformat()
        
        return state
    
    async def _finalize_result(self, state: AgentState) -> AgentState:
        """Finalize the task result"""
        self.log.info(f"Finalizing result for task {state['task_id']}")
        
        state["current_step"] = "finalize_result"
        state["completed_at"] = datetime.now().isoformat()
        
        # Set final status
        if state["errors"] and state["status"] != "executed":
            state["status"] = "failed"
        else:
            state["status"] = "completed"
        
        # Add final message
        state["messages"].append({
            "type": "system",
            "content": f"Task finalized with status: {state['status']}"
        })
        
        return state
    
    def _should_execute(self, state: AgentState) -> str:
        """Determine if we should proceed with execution"""
        if state["status"] == "error":
            return "error"
        return "execute"
    
    def _check_execution_result(self, state: AgentState) -> str:
        """Check the execution result and determine next step"""
        if state["status"] == "error":
            return "retry" if state["retry_count"] < state["max_retries"] else "error"
        return "success"
    
    def _should_retry(self, state: AgentState) -> str:
        """Determine if we should retry or fail"""
        if state["retry_count"] < state["max_retries"]:
            return "retry"
        return "fail"
    
    async def _run_task_async(self, task: Task, instruction: str) -> Dict[str, Any]:
        """Run the task asynchronously"""
        try:
            # This would run the task in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._run_task_sync, 
                task, 
                instruction
            )
            return result
        except Exception as e:
            raise Exception(f"Task execution failed: {str(e)}")
    
    def _run_task_sync(self, task: Task, instruction: str) -> Dict[str, Any]:
        """Run the task synchronously (existing logic)"""
        try:
            # Execute the task
            task.run(instruction)
            task.done()
            
            # Extract results from display
            result = {
                "success": True,
                "output": "Task completed successfully"
            }
            
            if hasattr(task, 'display') and hasattr(task.display, 'get_captured_data'):
                captured_data = task.display.get_captured_data()
                result.update({
                    "captured_data": captured_data,
                    "messages": captured_data.get("messages", []),
                    "results": captured_data.get("results", []),
                    "errors": captured_data.get("errors", [])
                })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None
            }
    
    async def execute_workflow(self, task: LangGraphTask) -> AgentState:
        """Execute the workflow for a given task"""
        if not LANGGRAPH_AVAILABLE or not self.graph:
            # Fallback to simple execution
            self.log.warning("Using fallback execution (LangGraph not available)")
            return await self._fallback_execution(task)
        
        try:
            # Add task object to state for execution
            task.state["_task_obj"] = task.task
            
            # Execute the graph
            result = await self.graph.ainvoke(task.state)
            return result
            
        except Exception as e:
            self.log.error(f"Workflow execution failed: {e}")
            task.state["errors"].append(f"Workflow execution failed: {str(e)}")
            task.state["status"] = "failed"
            task.state["completed_at"] = datetime.now().isoformat()
            return task.state
    
    async def _fallback_execution(self, task: LangGraphTask) -> AgentState:
        """Fallback execution when LangGraph is not available"""
        state = task.state
        
        try:
            state["status"] = "running"
            state["started_at"] = datetime.now().isoformat()
            
            # Simple execution without graph
            result = await self._run_task_async(task.task, task.instruction)
            
            if result.get("success"):
                state["results"]["execution_result"] = result
                state["status"] = "completed"
            else:
                state["errors"].append(result.get("error", "Unknown error"))
                state["status"] = "failed"
            
        except Exception as e:
            state["errors"].append(f"Fallback execution failed: {str(e)}")
            state["status"] = "failed"
        
        finally:
            state["completed_at"] = datetime.now().isoformat()
        
        return state


class LangGraphAgentManager(TaskManager):
    """LangGraph-based Agent Task Manager"""
    
    def __init__(self, settings, /, display_manager=None):
        super().__init__(settings, display_manager=display_manager)
        
        self.langraph_tasks: Dict[str, LangGraphTask] = {}
        self.workflow = LangGraphAgentWorkflow(settings)
        self.log = logger.bind(src='langraph_agent_manager')
    
    async def submit_task(self, instruction: str, metadata: Dict[str, Any] = None) -> str:
        """Submit a new task using LangGraph workflow"""
        task_id = str(uuid.uuid4())
        
        try:
            # Create the underlying task using parent class
            task = super().new_task()
            
            # Get display object
            display = task.display
            
            # Add metadata to display if available
            if display and hasattr(display, 'captured_data') and metadata:
                display.captured_data['metadata'].update(metadata)
                display.clear_captured_data()
                display.captured_data['metadata'].update(metadata)
            
            # Create LangGraph task wrapper
            langraph_task = LangGraphTask(
                task_id=task_id,
                instruction=instruction,
                task=task,
                display=display,
                graph=self.workflow.graph,
                state=None  # Will be initialized in __post_init__
            )
            
            self.langraph_tasks[task_id] = langraph_task
            self.log.info(f"LangGraph task submitted: {task_id}")
            
            return task_id
            
        except Exception as e:
            self.log.error(f"Failed to submit LangGraph task: {e}")
            raise
    
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute task using LangGraph workflow"""
        if task_id not in self.langraph_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        langraph_task = self.langraph_tasks[task_id]
        
        try:
            # Execute using LangGraph workflow
            final_state = await self.workflow.execute_workflow(langraph_task)
            
            # Update the task state
            langraph_task.state = final_state
            
            return self._state_to_dict(final_state)
            
        except Exception as e:
            self.log.error(f"LangGraph task execution failed: {e}")
            langraph_task.state["errors"].append(str(e))
            langraph_task.state["status"] = "failed"
            langraph_task.state["completed_at"] = datetime.now().isoformat()
            
            return self._state_to_dict(langraph_task.state)
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        if task_id not in self.langraph_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        return self._state_to_dict(self.langraph_tasks[task_id].state)
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get detailed task result"""
        if task_id not in self.langraph_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        langraph_task = self.langraph_tasks[task_id]
        result = self._state_to_dict(langraph_task.state)
        
        # Add captured data if available
        if langraph_task.display and hasattr(langraph_task.display, 'get_captured_data'):
            captured_data = langraph_task.display.get_captured_data()
            result['output'] = {
                'messages': captured_data['messages'],
                'results': captured_data['results'], 
                'errors': captured_data['errors'],
                'metadata': captured_data['metadata']
            }
        
        return result
    
    async def list_tasks(self) -> Dict[str, Any]:
        """List all tasks"""
        tasks = {}
        for task_id, langraph_task in self.langraph_tasks.items():
            state = langraph_task.state
            tasks[task_id] = {
                'task_id': task_id,
                'instruction': state['instruction'],
                'status': state['status'],
                'current_step': state['current_step'],
                'created_at': state['created_at'],
                'started_at': state.get('started_at'),
                'completed_at': state.get('completed_at'),
                'retry_count': state.get('retry_count', 0)
            }
        return tasks
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id not in self.langraph_tasks:
            return False
        
        langraph_task = self.langraph_tasks[task_id]
        
        if langraph_task.state['status'] in ['running', 'pending', 'retrying']:
            langraph_task.state['status'] = 'cancelled'
            langraph_task.state['completed_at'] = datetime.now().isoformat()
            
            # Stop the underlying task if possible
            if hasattr(langraph_task.task, 'stop'):
                langraph_task.task.stop()
            
            return True
        
        return False
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up completed tasks"""
        current_time = datetime.now()
        to_remove = []
        
        for task_id, langraph_task in self.langraph_tasks.items():
            state = langraph_task.state
            if state['status'] in ['completed', 'failed', 'cancelled']:
                if state.get('completed_at'):
                    completed_time = datetime.fromisoformat(state['completed_at'])
                    age = (current_time - completed_time).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.langraph_tasks[task_id]
            self.log.info(f"Cleaned up LangGraph task: {task_id}")
        
        return len(to_remove)
    
    def _state_to_dict(self, state: AgentState) -> Dict[str, Any]:
        """Convert AgentState to dictionary"""
        # Create a copy and remove internal objects
        result = dict(state)
        result.pop('_task_obj', None)  # Remove internal task object
        return result