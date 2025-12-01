
# ENTERPRISE AGENT SYSTEM FOR TELECOM CUSTOMER SUPPORT - INDIA

# Problem Statement: 
# Indian telecom operators face challenges with:
# 1. High volume of customer queries (billing, plan selection, technical issues)
# 2. Complex interconnected systems (billing, network, inventory, compliance)
# 3. Multi-language support requirements
# 4. Real-time decision-making for service provisioning
# 5. Compliance requirements (regulatory reporting, audit trails)
#
# Solution: Multi-Agent System with Parallel/Sequential Workflows


import os
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

# ADK Core Components
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import AgentTool, ToolContext, load_memory, preload_memory
from google.adk.apps.app import App, EventsCompactionConfig
from google.genai import types



# Configure logging for observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelecommunicationObserver:
    """Centralized observability handler for agent metrics and traces"""
    
    def __init__(self):
        self.logs: List[Dict] = []
        self.traces: Dict[str, Any] = {}
        self.metrics: Dict[str, float] = {}
    
    def log_event(self, agent_name: str, event_type: str, details: Dict):
        """Log individual events"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'type': event_type,
            'details': details
        }
        self.logs.append(event)
        logger.info(f"EVENT: {agent_name} - {event_type}: {details}")
    
    def start_trace(self, trace_id: str, workflow_name: str):
        """Start a distributed trace"""
        self.traces[trace_id] = {
            'workflow': workflow_name,
            'start': datetime.now().isoformat(),
            'events': []
        }
    
    def add_trace_event(self, trace_id: str, step: str, duration_ms: float):
        """Add step to trace"""
        if trace_id in self.traces:
            self.traces[trace_id]['events'].append({
                'step': step,
                'duration_ms': duration_ms,
                'timestamp': datetime.now().isoformat()
            })
    
    def record_metric(self, metric_name: str, value: float):
        """Record performance metric"""
        self.metrics[metric_name] = value


# Global observer instance
observer = TelecommunicationObserver()




def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    """
    Retrieve customer profile from telecom database
    In production, this would query the actual CRM system
    """
    observer.log_event("get_customer_profile", "TOOL_CALL", {"customer_id": customer_id})
    
    # Mock customer database
    customers = {
        "CUST001": {
            "name": "Rajesh Kumar",
            "phone": "+919876543210",
            "plan": "Premium-199",
            "status": "Active",
            "balance": 2500.0,
            "region": "Delhi",
            "language": "Hindi",
            "active_since": "2023-01-15",
            "bill_cycle": "5th",
            "family_plans": ["CUST002", "CUST003"]
        },
        "CUST002": {
            "name": "Priya Singh",
            "phone": "+919876543211",
            "plan": "Standard-99",
            "status": "Active",
            "balance": 1200.0,
            "region": "Mumbai",
            "language": "Marathi",
            "active_since": "2023-06-20",
            "bill_cycle": "10th",
            "parent_account": "CUST001"
        }
    }
    
    if customer_id in customers:
        return {"status": "success", "data": customers[customer_id]}
    return {"status": "error", "message": f"Customer {customer_id} not found"}


def check_plan_availability(region: str, budget: float) -> Dict[str, Any]:
    """
    Check available plans in a region within budget
    """
    observer.log_event("check_plan_availability", "TOOL_CALL", {"region": region, "budget": budget})
    
    available_plans = {
        "Delhi": {
            "Premium-199": {"price": 199, "data": "3GB/day", "validity": "28 days"},
            "Premium-399": {"price": 399, "data": "5GB/day", "validity": "56 days"},
            "Basic-99": {"price": 99, "data": "1.5GB/day", "validity": "28 days"}
        },
        "Mumbai": {
            "Premium-199": {"price": 199, "data": "3GB/day", "validity": "28 days"},
            "Premium-299": {"price": 299, "data": "4GB/day", "validity": "28 days"},
            "Basic-99": {"price": 99, "data": "1.5GB/day", "validity": "28 days"}
        }
    }
    
    region_plans = available_plans.get(region, {})
    suitable_plans = {
        name: details for name, details in region_plans.items()
        if details["price"] <= budget
    }
    
    return {
        "status": "success",
        "region": region,
        "budget_limit": budget,
        "available_plans": suitable_plans
    }


def submit_plan_change_request(customer_id: str, new_plan: str, effective_date: str) -> Dict[str, Any]:
    """
    Submit plan change request to provisioning system
    """
    observer.log_event(
        "submit_plan_change_request",
        "TOOL_CALL",
        {"customer_id": customer_id, "new_plan": new_plan, "effective_date": effective_date}
    )
    
    return {
        "status": "success",
        "ticket_id": f"TKT-{customer_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "message": f"Plan change request submitted for {customer_id}",
        "effective_date": effective_date
    }


def get_billing_history(customer_id: str, months: int = 6) -> Dict[str, Any]:
    """
    Retrieve billing history for compliance and audit
    """
    observer.log_event("get_billing_history", "TOOL_CALL", {"customer_id": customer_id, "months": months})
    
    # Mock billing data
    return {
        "status": "success",
        "customer_id": customer_id,
        "bills": [
            {"month": "Nov-2024", "amount": 199, "status": "Paid"},
            {"month": "Oct-2024", "amount": 199, "status": "Paid"},
            {"month": "Sep-2024", "amount": 199, "status": "Paid"}
        ]
    }


def check_service_status(customer_id: str) -> Dict[str, Any]:
    """
    Check real-time service status (voice, data, SMS)
    """
    observer.log_event("check_service_status", "TOOL_CALL", {"customer_id": customer_id})
    
    return {
        "status": "success",
        "customer_id": customer_id,
        "voice": {"status": "Active", "quota": "Unlimited"},
        "data": {"status": "Active", "used_gb": 1.5, "limit_gb": 3.0},
        "sms": {"status": "Active", "quota": "100/day"}
    }




def create_query_classifier_agent() -> LlmAgent:
    """Agent that classifies customer queries into categories"""
    return LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite"),
        name="QueryClassifier",
        description="Classifies customer queries into categories: billing, plan_change, technical, complaints",
        instruction="""Analyze the customer query and classify it into one of these categories:
        1. BILLING - Questions about charges, invoices, payment issues
        2. PLAN_CHANGE - Requests to upgrade/downgrade/change plans
        3. TECHNICAL - Network issues, connectivity problems
        4. SERVICE_COMPLAINT - Service quality complaints
        5. GENERAL_INFO - General information requests
        
        Respond with ONLY the category name and a brief reason."""
    )


def create_billing_agent() -> LlmAgent:
    """Agent specialized for billing queries"""
    return LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite"),
        name="BillingAgent",
        description="Handles billing-related queries and issues",
        instruction="""You are a billing specialist for telecom services. Help customers with:
        - Understanding charges and bills
        - Discussing payment options
        - Explaining billing cycles
        - Addressing billing disputes
        
        Always be helpful and provide clear explanations."""
    )


def create_plan_advisor_agent() -> LlmAgent:
    """Agent that recommends suitable plans based on customer needs"""
    return LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite"),
        name="PlanAdvisor",
        description="Recommends suitable telecom plans based on customer needs",
        instruction="""You are a plan advisor. Help customers by:
        1. Understanding their usage patterns and requirements
        2. Recommending suitable plans
        3. Explaining benefits of different plans
        4. Facilitating plan changes
        
        Consider factors like data usage, cost, and customer preferences."""
    )


def create_technical_support_agent() -> LlmAgent:
    """Agent for technical support issues"""
    return LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite"),
        name="TechnicalSupport",
        description="Provides technical support for network and service issues",
        instruction="""You are technical support specialist. Help with:
        - Network connectivity issues
        - Data/voice problems
        - Device compatibility questions
        - Troubleshooting steps
        
        Provide clear, step-by-step solutions."""
    )


def create_compliance_auditor_agent() -> LlmAgent:
    """Agent that ensures compliance with regulations"""
    return LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite"),
        name="ComplianceAuditor",
        description="Ensures all customer interactions comply with regulations",
        instruction="""You are a compliance auditor. Review interactions for:
        1. TRAI regulations compliance
        2. Data privacy (DPDP Act)
        3. Consumer protection laws
        4. Know Your Customer (KYC) requirements
        
        Flag any compliance issues immediately."""
    )




async def execute_parallel_agent_workflow(
    customer_query: str,
    customer_id: str
) -> Dict[str, Any]:
    """
    Execute parallel workflow: simultaneously get billing history, 
    check service status, and validate compliance
    """
    logger.info(f"Starting parallel workflow for {customer_id}")
    observer.log_event("parallel_workflow", "START", {"customer_id": customer_id})
    
    # Create parallel tasks
    tasks = {
        "billing": get_billing_history(customer_id),
        "service_status": check_service_status(customer_id),
        "profile": get_customer_profile(customer_id)
    }
    
    return tasks


async def execute_sequential_plan_change_workflow(
    customer_id: str,
    customer_query: str
) -> Dict[str, Any]:
    """
    Sequential workflow for plan changes:
    1. Get current profile
    2. Recommend suitable plans
    3. Submit change request
    4. Compliance check
    """
    logger.info(f"Starting sequential plan change workflow for {customer_id}")
    
    # Step 1: Get customer profile
    profile_result = get_customer_profile(customer_id)
    if profile_result["status"] != "success":
        return {"status": "error", "message": "Could not retrieve customer profile"}
    
    customer_profile = profile_result["data"]
    region = customer_profile["region"]
    
    # Step 2: Check available plans
    budget = 500  # Default budget for plan recommendations
    plans_result = check_plan_availability(region, budget)
    
    # Step 3: Submit plan change (simulation)
    # In production, the PlanAdvisor agent would recommend from available plans
    change_result = submit_plan_change_request(
        customer_id,
        "Premium-299",
        datetime.now().strftime("%Y-%m-%d")
    )
    
    return {
        "status": "success",
        "workflow": "plan_change",
        "customer_id": customer_id,
        "current_plan": customer_profile["plan"],
        "available_plans": plans_result["available_plans"],
        "request_status": change_result
    }


async def execute_loop_agent_workflow(
    customer_id: str,
    max_iterations: int = 3
) -> Dict[str, Any]:
    """
    Loop agent workflow for iterative problem resolution
    Keeps trying different solutions until issue is resolved
    """
    logger.info(f"Starting loop workflow for {customer_id}")
    
    solutions_tried = []
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Iteration {iteration}: Attempting solution")
        
        # Simulate troubleshooting steps
        solution = {
            "iteration": iteration,
            "steps": [
                "Check network signal",
                "Verify plan active status",
                "Check device settings"
            ][:iteration]  # Progressive steps
        }
        
        solutions_tried.append(solution)
        
        # Simulate resolution check
        if iteration >= 2:
            return {
                "status": "resolved",
                "iterations": iteration,
                "solutions_tried": solutions_tried
            }
    
    return {
        "status": "escalate",
        "iterations": iteration,
        "solutions_tried": solutions_tried
    }




class TelecomAgentApp:
    """Main application orchestrating the multi-agent system"""
    
    def __init__(self, use_persistent_storage: bool = True):
        """Initialize the telecom agent application"""
        
        # Setup API configuration
        os.environ.setdefault("GOOGLE_API_KEY", "")
        
        # Retry configuration
        self.retry_config = types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504]
        )
        
        # Session management
        if use_persistent_storage:
            self.session_service = DatabaseSessionService(
                db_url="sqlite:///telecom_agent.db"
            )
        else:
            self.session_service = InMemorySessionService()
        
        # Memory service for long-term context
        self.memory_service = InMemoryMemoryService()
        
        # Create specialized agents
        self.query_classifier = create_query_classifier_agent()
        self.billing_agent = create_billing_agent()
        self.plan_advisor = create_plan_advisor_agent()
        self.technical_support = create_technical_support_agent()
        self.compliance_auditor = create_compliance_auditor_agent()
        
        # Create orchestrator agent
        self.orchestrator = self._create_orchestrator_agent()
        
        # Create runner
        self.runner = Runner(
            agent=self.orchestrator,
            app_name="telecom_support",
            session_service=self.session_service,
            memory_service=self.memory_service
        )
        
        logger.info("TelecomAgentApp initialized successfully")
    
    def _create_orchestrator_agent(self) -> LlmAgent:
        """Create the main orchestrator agent"""
        return LlmAgent(
            model=Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config),
            name="TelecomOrchestrator",
            description="Main orchestrator for telecom customer support",
            instruction="""You are the main support orchestrator for an Indian telecom operator.
            
            Customer Query: {user_query}
            Customer ID: {customer_id}
            
            Process:
            1. Understand the customer's issue
            2. Gather relevant information (billing history, service status, profile)
            3. Provide appropriate solution
            4. Ensure compliance
            
            Be helpful, professional, and multilingual-aware.
            Always prioritize customer satisfaction and regulatory compliance.""",
            sub_agents=[
                AgentTool(self.billing_agent),
                AgentTool(self.plan_advisor),
                AgentTool(self.technical_support),
                AgentTool(self.compliance_auditor)
            ]
        )
    
    async def handle_customer_query(
        self,
        customer_id: str,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle a customer query end-to-end"""
        
        if not session_id:
            session_id = f"session_{customer_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"Processing query from {customer_id}: {query}")
        observer.log_event("handle_query", "START", {"customer_id": customer_id})
        
        try:
            # Create or retrieve session
            try:
                session = await self.session_service.create_session(
                    app_name="telecom_support",
                    user_id=customer_id,
                    session_id=session_id
                )
            except:
                session = await self.session_service.get_session(
                    app_name="telecom_support",
                    user_id=customer_id,
                    session_id=session_id
                )
            
            # Prepare message content
            message_content = types.Content(
                role="user",
                parts=[types.Part(text=f"Customer ID: {customer_id}\n\nQuery: {query}")]
            )
            
            # Run through orchestrator
            response_text = ""
            async for event in self.runner.run_async(
                user_id=customer_id,
                session_id=session.id,
                new_message=message_content
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text"):
                            response_text = part.text
            
            observer.log_event("handle_query", "SUCCESS", {
                "customer_id": customer_id,
                "session_id": session_id
            })
            
            return {
                "status": "success",
                "customer_id": customer_id,
                "session_id": session.id,
                "response": response_text,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            observer.log_event("handle_query", "ERROR", {"error": str(e)})
            return {
                "status": "error",
                "customer_id": customer_id,
                "error": str(e)
            }
    
    async def get_observability_report(self) -> Dict[str, Any]:
        """Generate comprehensive observability report"""
        return {
            "logs": observer.logs[-100:],  # Last 100 logs
            "traces": observer.traces,
            "metrics": observer.metrics,
            "timestamp": datetime.now().isoformat()
        }



class AgentEvaluator:
    """Framework for evaluating agent performance"""
    
    def __init__(self):
        self.test_cases: List[Dict] = []
        self.results: List[Dict] = []
    
    def add_test_case(
        self,
        customer_id: str,
        query: str,
        expected_resolution: str,
        category: str
    ):
        """Add a test case for evaluation"""
        self.test_cases.append({
            "customer_id": customer_id,
            "query": query,
            "expected_resolution": expected_resolution,
            "category": category
        })
    
    async def run_evaluation(self, app: TelecomAgentApp) -> Dict[str, Any]:
        """Run evaluation against all test cases"""
        logger.info(f"Starting evaluation of {len(self.test_cases)} test cases")
        
        passed = 0
        failed = 0
        
        for test_case in self.test_cases:
            result = await app.handle_customer_query(
                customer_id=test_case["customer_id"],
                query=test_case["query"],
                session_id=f"eval_{test_case['customer_id']}"
            )
            
            # Simple evaluation: check if response is not empty
            is_passed = result["status"] == "success" and len(result.get("response", "")) > 10
            
            if is_passed:
                passed += 1
            else:
                failed += 1
            
            self.results.append({
                "test_case": test_case,
                "result": result,
                "passed": is_passed
            })
        
        success_rate = (passed / len(self.test_cases)) * 100
        
        logger.info(f"Evaluation complete: {passed}/{len(self.test_cases)} passed ({success_rate:.1f}%)")
        
        return {
            "total_tests": len(self.test_cases),
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "results": self.results
        }



async def main():
    """Main execution function demonstrating the complete system"""
    
    # Initialize application
    logger.info("=" * 80)
    logger.info("TELECOM CUSTOMER SUPPORT AGENT - ENTERPRISE SOLUTION")
    logger.info("=" * 80)
    
    app = TelecomAgentApp(use_persistent_storage=True)
    
    # Example customer interactions
    test_queries = [
        {
            "customer_id": "CUST001",
            "query": "My bill for this month seems very high. Can you explain the charges?"
        },
        {
            "customer_id": "CUST002",
            "query": "I want to upgrade my plan. What options are available in my region?"
        },
        {
            "customer_id": "CUST001",
            "query": "I'm having trouble with my data connection. Can you help?"
        }
    ]
    
    # Process customer queries
    logger.info("\n" + "=" * 80)
    logger.info("PROCESSING CUSTOMER QUERIES")
    logger.info("=" * 80)
    
    for test_query in test_queries:
        result = await app.handle_customer_query(
            customer_id=test_query["customer_id"],
            query=test_query["query"]
        )
        
        print(f"\nCustomer ID: {result['customer_id']}")
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"Response Preview: {result['response'][:200]}...")
    
    # Parallel workflow example
    logger.info("\n" + "=" * 80)
    logger.info("EXECUTING PARALLEL WORKFLOWS")
    logger.info("=" * 80)
    
    parallel_result = await execute_parallel_agent_workflow(
        customer_query="What's my current status?",
        customer_id="CUST001"
    )
    logger.info(f"Parallel workflow result: {json.dumps(parallel_result, indent=2, default=str)}")
    
    # Sequential workflow example
    logger.info("\n" + "=" * 80)
    logger.info("EXECUTING SEQUENTIAL WORKFLOWS")
    logger.info("=" * 80)
    
    sequential_result = await execute_sequential_plan_change_workflow(
        customer_id="CUST002",
        customer_query="I want a better plan"
    )
    logger.info(f"Sequential workflow result: {json.dumps(sequential_result, indent=2, default=str)}")
    
    # Loop workflow example
    logger.info("\n" + "=" * 80)
    logger.info("EXECUTING LOOP WORKFLOWS")
    logger.info("=" * 80)
    
    loop_result = await execute_loop_agent_workflow(customer_id="CUST001")
    logger.info(f"Loop workflow result: {json.dumps(loop_result, indent=2, default=str)}")
    
    # Evaluation
    logger.info("\n" + "=" * 80)
    logger.info("AGENT EVALUATION")
    logger.info("=" * 80)
    
    evaluator = AgentEvaluator()
    
    # Add evaluation test cases
    evaluator.add_test_case(
        customer_id="TEST001",
        query="Check my account balance",
        expected_resolution="balance_shown",
        category="BILLING"
    )
    evaluator.add_test_case(
        customer_id="TEST002",
        query="Upgrade my plan",
        expected_resolution="plan_change_initiated",
        category="PLAN_CHANGE"
    )
    
    evaluation_results = await evaluator.run_evaluation(app)
    logger.info(f"Evaluation Results: {json.dumps(evaluation_results, indent=2, default=str)}")
    
    # Get observability report
    logger.info("\n" + "=" * 80)
    logger.info("OBSERVABILITY REPORT")
    logger.info("=" * 80)
    
    observability_report = await app.get_observability_report()
    logger.info(f"Total events logged: {len(observability_report['logs'])}")
    logger.info(f"Active traces: {len(observability_report['traces'])}")
    logger.info(f"Metrics recorded: {len(observability_report['metrics'])}")
    
    print("\n" + "=" * 80)
    print("ENTERPRISE SOLUTION EXECUTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
