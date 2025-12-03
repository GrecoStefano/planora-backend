"""
Automation Rule Engine
Evaluates conditions and executes actions based on triggers
"""
from typing import Dict, Any, List
from app.models.automation import AutomationRule
from app.models.task import Task
from app.models.calendar import Event
import logging

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Engine for evaluating and executing automation rules."""
    
    @staticmethod
    def evaluate_condition(condition: Dict[str, Any], entity: Dict[str, Any]) -> bool:
        """Evaluate a single condition against an entity."""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if field not in entity:
            return False
        
        entity_value = entity[field]
        
        if operator == "equals":
            return entity_value == value
        elif operator == "not_equals":
            return entity_value != value
        elif operator == "contains":
            return value in str(entity_value)
        elif operator == "greater_than":
            return entity_value > value
        elif operator == "less_than":
            return entity_value < value
        elif operator == "in":
            return entity_value in value
        elif operator == "not_in":
            return entity_value not in value
        
        return False
    
    @staticmethod
    def evaluate_conditions(conditions: Dict[str, Any], entity: Dict[str, Any]) -> bool:
        """Evaluate all conditions (AND/OR logic)."""
        logic = conditions.get("logic", "AND")
        condition_list = conditions.get("conditions", [])
        
        if not condition_list:
            return True
        
        results = [
            AutomationEngine.evaluate_condition(cond, entity)
            for cond in condition_list
        ]
        
        if logic == "AND":
            return all(results)
        elif logic == "OR":
            return any(results)
        
        return False
    
    @staticmethod
    async def execute_action(action: Dict[str, Any], entity: Dict[str, Any], db):
        """Execute a single action."""
        action_type = action.get("type")
        
        if action_type == "assign_task":
            # Assign task to user
            task_id = entity.get("id")
            user_id = action.get("user_id")
            # Implementation would update task assignee
            logger.info(f"Assigning task {task_id} to user {user_id}")
        
        elif action_type == "send_notification":
            # Send notification
            user_id = action.get("user_id")
            message = action.get("message", "").format(**entity)
            # Implementation would create notification
            logger.info(f"Sending notification to user {user_id}: {message}")
        
        elif action_type == "update_field":
            # Update entity field
            field = action.get("field")
            value = action.get("value")
            entity[field] = value
            logger.info(f"Updating {field} to {value}")
        
        elif action_type == "create_task":
            # Create new task
            task_data = action.get("task_data", {})
            logger.info(f"Creating task: {task_data}")
        
        elif action_type == "set_reminder":
            # Set reminder
            reminder_time = action.get("reminder_time")
            logger.info(f"Setting reminder for {reminder_time}")
    
    @staticmethod
    async def process_rule(rule: AutomationRule, trigger_data: Dict[str, Any], db):
        """Process an automation rule when triggered."""
        if not rule.is_active:
            return
        
        # Evaluate conditions
        if not AutomationEngine.evaluate_conditions(rule.conditions, trigger_data):
            logger.debug(f"Rule {rule.id} conditions not met")
            return
        
        # Execute actions
        for action in rule.actions:
            try:
                await AutomationEngine.execute_action(action, trigger_data, db)
            except Exception as e:
                logger.error(f"Error executing action in rule {rule.id}: {e}")
    
    @staticmethod
    async def trigger_event(trigger_type: str, entity: Any, db):
        """Trigger automation rules for a specific event type."""
        from sqlalchemy import select
        
        # Find all active rules for this trigger
        result = await db.execute(
            select(AutomationRule).where(
                AutomationRule.trigger == trigger_type,
                AutomationRule.is_active == True
            )
        )
        rules = result.scalars().all()
        
        # Convert entity to dict
        entity_dict = {}
        if isinstance(entity, Task):
            entity_dict = {
                "id": entity.id,
                "title": entity.title,
                "status": entity.status.value if hasattr(entity.status, 'value') else str(entity.status),
                "priority": entity.priority.value if hasattr(entity.priority, 'value') else str(entity.priority),
                "project_id": entity.project_id,
                "tags": entity.tags,
            }
        elif isinstance(entity, Event):
            entity_dict = {
                "id": entity.id,
                "title": entity.title,
                "start": entity.start.isoformat() if entity.start else None,
                "calendar_id": entity.calendar_id,
            }
        
        # Process each rule
        for rule in rules:
            await AutomationEngine.process_rule(rule, entity_dict, db)

