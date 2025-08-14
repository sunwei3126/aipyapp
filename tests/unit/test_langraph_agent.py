#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from aipyapp.aipy.langraph_agent import LangGraphAgentManager, LangGraphAgentWorkflow, LANGGRAPH_AVAILABLE
from aipyapp.aipy.agent_taskmgr import AgentTaskManager


class TestLangGraphAgent:
    """Test LangGraph agent implementation"""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        return {
            'auto_install': False,
            'auto_getenv': False,
            'debug': False
        }
    
    @pytest.fixture
    def mock_display_manager(self):
        """Mock display manager"""
        display_manager = Mock()
        return display_manager
    
    @pytest.fixture
    def mock_task(self):
        """Mock task object"""
        task = Mock()
        task.run = Mock()
        task.done = Mock()
        
        # Mock display
        display = Mock()
        display.get_captured_data = Mock(return_value={
            'messages': [],
            'results': [],
            'errors': [],
            'metadata': {}
        })
        display.captured_data = {'metadata': {}}
        display.clear_captured_data = Mock()
        
        task.display = display
        return task
    
    def test_langraph_workflow_creation(self, mock_settings):
        """Test LangGraph workflow creation"""
        workflow = LangGraphAgentWorkflow(mock_settings)
        
        # Should create workflow regardless of LangGraph availability
        assert workflow is not None
        assert workflow.settings == mock_settings
        
        if LANGGRAPH_AVAILABLE:
            assert workflow.graph is not None
        else:
            assert workflow.graph is None
    
    @pytest.mark.asyncio
    async def test_agent_manager_factory(self, mock_settings, mock_display_manager):
        """Test that AgentTaskManager factory creates correct implementation"""
        
        # Mock the TaskManager initialization to avoid dependencies
        with pytest.mock.patch('aipyapp.aipy.agent_taskmgr.TaskManager.__init__', return_value=None):
            with pytest.mock.patch('aipyapp.aipy.langraph_agent.TaskManager.__init__', return_value=None):
                manager = AgentTaskManager(mock_settings, display_manager=mock_display_manager)
                
                if LANGGRAPH_AVAILABLE:
                    # Should be LangGraphAgentManager
                    assert isinstance(manager, LangGraphAgentManager)
                else:
                    # Should be regular AgentTaskManager
                    assert type(manager).__name__ == 'AgentTaskManager'
    
    @pytest.mark.asyncio 
    async def test_langraph_agent_task_submission(self, mock_settings, mock_display_manager, mock_task):
        """Test task submission with LangGraph agent"""
        
        if not LANGGRAPH_AVAILABLE:
            pytest.skip("LangGraph not available")
        
        # Mock dependencies
        with pytest.mock.patch('aipyapp.aipy.langraph_agent.TaskManager.__init__', return_value=None):
            with pytest.mock.patch('aipyapp.aipy.langraph_agent.TaskManager.new_task', return_value=mock_task):
                
                manager = LangGraphAgentManager(mock_settings, display_manager=mock_display_manager)
                manager.langraph_tasks = {}  # Initialize the tasks dict
                
                # Submit a task
                task_id = await manager.submit_task("Test instruction", {"test": "metadata"})
                
                # Verify task was created
                assert task_id is not None
                assert task_id in manager.langraph_tasks
                
                langraph_task = manager.langraph_tasks[task_id]
                assert langraph_task.instruction == "Test instruction"
                assert langraph_task.task == mock_task
    
    @pytest.mark.asyncio
    async def test_workflow_fallback_execution(self, mock_settings, mock_task):
        """Test fallback execution when LangGraph is not available"""
        
        workflow = LangGraphAgentWorkflow(mock_settings)
        
        # Create a mock LangGraphTask
        from aipyapp.aipy.langraph_agent import LangGraphTask
        
        langraph_task = LangGraphTask(
            task_id="test-123",
            instruction="Test instruction",
            task=mock_task,
            display=mock_task.display,
            graph=None,
            state=None
        )
        
        # Execute workflow (should use fallback)
        result = await workflow.execute_workflow(langraph_task)
        
        # Verify execution
        assert result is not None
        assert result['task_id'] == "test-123"
        assert result['instruction'] == "Test instruction"
        assert result['status'] in ['completed', 'failed']
    
    @pytest.mark.asyncio
    async def test_agent_manager_task_lifecycle(self, mock_settings, mock_display_manager, mock_task):
        """Test complete task lifecycle"""
        
        # Mock dependencies to avoid initialization issues
        with pytest.mock.patch('aipyapp.aipy.agent_taskmgr.TaskManager.__init__', return_value=None):
            with pytest.mock.patch('aipyapp.aipy.langraph_agent.TaskManager.__init__', return_value=None):
                with pytest.mock.patch('aipyapp.aipy.langraph_agent.TaskManager.new_task', return_value=mock_task):
                    
                    manager = AgentTaskManager(mock_settings, display_manager=mock_display_manager)
                    
                    # Initialize required attributes for both implementations
                    if hasattr(manager, 'langraph_tasks'):
                        manager.langraph_tasks = {}
                    else:
                        manager.agent_tasks = {}
                    
                    # Submit task
                    task_id = await manager.submit_task("Test task")
                    assert task_id is not None
                    
                    # Check status
                    status = await manager.get_task_status(task_id)
                    assert status['task_id'] == task_id
                    
                    # Execute task
                    result = await manager.execute_task(task_id)
                    assert result['task_id'] == task_id
                    
                    # Get result
                    final_result = await manager.get_task_result(task_id)
                    assert final_result['task_id'] == task_id
    
    @pytest.mark.asyncio
    async def test_task_cancellation(self, mock_settings, mock_display_manager, mock_task):
        """Test task cancellation"""
        
        with pytest.mock.patch('aipyapp.aipy.agent_taskmgr.TaskManager.__init__', return_value=None):
            with pytest.mock.patch('aipyapp.aipy.langraph_agent.TaskManager.__init__', return_value=None):
                with pytest.mock.patch('aipyapp.aipy.langraph_agent.TaskManager.new_task', return_value=mock_task):
                    
                    manager = AgentTaskManager(mock_settings, display_manager=mock_display_manager)
                    
                    # Initialize required attributes
                    if hasattr(manager, 'langraph_tasks'):
                        manager.langraph_tasks = {}
                    else:
                        manager.agent_tasks = {}
                    
                    # Submit and cancel task
                    task_id = await manager.submit_task("Test task")
                    success = await manager.cancel_task(task_id)
                    
                    assert success is True or success is False  # Should return boolean
    
    def test_langraph_state_management(self):
        """Test LangGraph state structure"""
        from aipyapp.aipy.langraph_agent import AgentState
        
        # Test state creation
        state = AgentState(
            task_id="test-123",
            instruction="Test instruction", 
            messages=[],
            current_step="init",
            context={},
            results={},
            errors=[],
            status="pending",
            created_at="2023-01-01T00:00:00",
            started_at=None,
            completed_at=None,
            retry_count=0,
            max_retries=3
        )
        
        # Verify state structure
        assert state['task_id'] == "test-123"
        assert state['instruction'] == "Test instruction"
        assert state['status'] == "pending"
        assert state['retry_count'] == 0
        assert state['max_retries'] == 3


if __name__ == "__main__":
    pytest.main([__file__])