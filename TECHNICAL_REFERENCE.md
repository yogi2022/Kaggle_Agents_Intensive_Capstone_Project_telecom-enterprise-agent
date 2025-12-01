# TECHNICAL REFERENCE - DEEP DIVE
# Telecom Enterprise Agent System - Implementation Details

---

## TABLE OF CONTENTS

1. Agent Design Patterns
2. Tool Development Guide
3. Workflow Implementation
4. Session Management Deep Dive
5. Memory Architecture
6. Observability Implementation
7. Scalability Patterns
8. Security Hardening
9. Performance Optimization
10. Troubleshooting Guide

---

## 1. AGENT DESIGN PATTERNS

### 1.1 Specialist Agent Pattern

Every agent in our system follows this pattern:

```python
def create_specialist_agent(
    name: str,
    domain: str,
    required_tools: List[Callable],
    constraints: List[str]
) -> LlmAgent:
    
    return LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
        name=name,
        description=f"{name} - Specialized in {domain}",
        instruction=f"""You are a specialized {domain} agent.
        
        Your responsibilities:
        - Primary: {domain} domain expertise
        - Handle queries in this domain
        - Escalate complex issues
        - Follow regulations: {constraints}
        
        Do NOT:
        - Handle out-of-domain queries
        - Bypass compliance checks
        - Make promises you can't keep
        
        Tools available: {[t.__name__ for t in required_tools]}
        """,
        tools=[FunctionTool(t) for t in required_tools]
    )
```

**Key Principles**:
1. **Single Responsibility**: Each agent has one clear domain
2. **Tool Specificity**: Only add tools agent needs
3. **Clear Instructions**: Explicit about capabilities and constraints
4. **Error Handling**: Graceful degradation
5. **Auditability**: All actions logged

### 1.2 Agent Composition Patterns

#### Hierarchical (Orchestrator Pattern)
```
Orchestrator Agent
├─→ Sub-Agent 1 (Billing)
├─→ Sub-Agent 2 (Plans)
└─→ Sub-Agent 3 (Support)

When to use:
- Complex routing needed
- Multiple specialized domains
- Flexible workflow
- Natural language routing
```

#### Pipeline (Sequential Pattern)
```
Agent 1 → Agent 2 → Agent 3 → Result

When to use:
- Step-by-step process
- Dependent tasks
- Guaranteed order
- Compliance required
```

#### Parallel (Concurrent Pattern)
```
┌→ Agent 1 ─┐
├→ Agent 2 ─┤ Merge
└→ Agent 3 ─┘

When to use:
- Independent tasks
- Speed critical
- Resource optimization
- Responsive UX
```

#### Loop (Iterative Pattern)
```
Start → Agent → Check → Success? 
              ↓       ↓
            Try Again
              (max 3)

When to use:
- Troubleshooting
- Retryable failures
- Progressive solving
- Resilience needed
```

---

## 2. TOOL DEVELOPMENT GUIDE

### 2.1 Tool Categories

#### Type 1: Query Tools (Read-Only)
```python
def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    """
    Retrieve customer information from database.
    
    Safe: No state changes
    Cached: Can be cached for performance
    """
    # Validation
    if not customer_id or len(customer_id) != 8:
        return {"status": "error", "message": "Invalid customer ID format"}
    
    # Logging
    observer.log_event("get_customer_profile", "TOOL_CALL", {"customer_id": customer_id})
    
    # Implementation
    result = db.query("SELECT * FROM customers WHERE id = ?", customer_id)
    
    if result:
        return {"status": "success", "data": result}
    return {"status": "error", "message": "Customer not found"}
```

#### Type 2: Action Tools (Write Operations)
```python
def submit_plan_change_request(
    customer_id: str,
    new_plan: str,
    effective_date: str
) -> Dict[str, Any]:
    """
    Submit a plan change request.
    
    Important: Causes state change
    Returns: Confirmation token
    """
    # Pre-validation
    if not validate_plan_exists(new_plan):
        return {"status": "error", "message": "Plan not found"}
    
    # Log for compliance
    audit_log.write({
        "action": "plan_change_requested",
        "customer": customer_id,
        "plan": new_plan,
        "date": effective_date,
        "timestamp": datetime.now()
    })
    
    # Execute transaction
    try:
        ticket = db.insert("plan_changes", {
            "customer_id": customer_id,
            "new_plan": new_plan,
            "effective_date": effective_date,
            "status": "pending_approval"
        })
        return {"status": "success", "ticket_id": ticket}
    except Exception as e:
        logger.error(f"Plan change failed: {e}")
        return {"status": "error", "message": "Failed to submit request"}
```

#### Type 3: Integration Tools (External APIs)
```python
def check_network_status(customer_id: str) -> Dict[str, Any]:
    """
    Check customer's network status from network management system.
    
    Integration: Calls external API
    Timeout: 5 seconds
    Fallback: Return cached data if timeout
    """
    try:
        response = requests.get(
            f"https://nms.telco.com/status/{customer_id}",
            timeout=5
        )
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
    except requests.Timeout:
        # Return cached data
        cached = cache.get(f"nms_status:{customer_id}")
        if cached:
            return {"status": "cached", "data": cached}
    
    return {"status": "error", "message": "Network status unavailable"}
```

### 2.2 Tool Error Handling

```python
class ToolError(Exception):
    """Base class for tool errors"""
    pass

class ValidationError(ToolError):
    """Input validation failed"""
    pass

class IntegrationError(ToolError):
    """External service unavailable"""
    pass

class PermissionError(ToolError):
    """Customer not authorized"""
    pass

# Usage
def safe_tool_wrapper(func):
    async def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            observer.log_event(func.__name__, "SUCCESS", {})
            return result
        except ValidationError as e:
            return {"status": "error", "message": f"Validation: {e}"}
        except IntegrationError as e:
            return {"status": "error", "message": f"Service unavailable: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            return {"status": "error", "message": "Internal error"}
    return wrapper
```

---

## 3. WORKFLOW IMPLEMENTATION

### 3.1 Parallel Workflow

```python
async def parallel_data_gathering(customer_id: str) -> Dict[str, Any]:
    """
    Gather multiple data sources in parallel.
    
    Benefits: Reduced latency (200ms vs 450ms)
    """
    
    # Create concurrent tasks
    tasks = {
        "profile": asyncio.create_task(get_customer_profile(customer_id)),
        "billing": asyncio.create_task(get_billing_history(customer_id)),
        "service": asyncio.create_task(check_service_status(customer_id))
    }
    
    # Wait for all to complete
    results = {}
    for key, task in tasks.items():
        try:
            results[key] = await asyncio.wait_for(task, timeout=5)
        except asyncio.TimeoutError:
            results[key] = {"status": "timeout", "data": None}
    
    # Aggregate results
    return {
        "status": "success",
        "data": results,
        "timestamp": datetime.now()
    }
```

### 3.2 Sequential Workflow

```python
class SequentialWorkflow:
    def __init__(self, name: str):
        self.name = name
        self.steps = []
    
    async def add_step(self, step_name: str, handler: Callable):
        """Add a sequential step"""
        self.steps.append((step_name, handler))
    
    async def execute(self, context: Dict) -> Dict:
        """Execute all steps in order"""
        
        observer.start_trace(self.name, "sequential_workflow")
        
        for step_name, handler in self.steps:
            start_time = datetime.now()
            
            try:
                # Execute step with context
                result = await handler(context)
                
                if result["status"] != "success":
                    # Abort on failure
                    return {"status": "failed", "failed_at": step_name}
                
                # Pass result to next step
                context.update(result.get("data", {}))
                
                # Log timing
                duration = (datetime.now() - start_time).total_seconds() * 1000
                observer.add_trace_event(self.name, step_name, duration)
                
            except Exception as e:
                logger.error(f"Step {step_name} failed: {e}")
                return {"status": "error", "failed_at": step_name, "error": str(e)}
        
        return {"status": "success", "data": context}
```

### 3.3 Loop Workflow

```python
async def iterative_troubleshooting(customer_id: str) -> Dict[str, Any]:
    """
    Try different solutions until problem resolved.
    """
    
    solutions = [
        ("basic_checks", perform_basic_checks),
        ("restart_services", restart_services),
        ("network_diagnostics", run_diagnostics),
        ("escalate_to_human", escalate)
    ]
    
    max_iterations = 3
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Troubleshooting iteration {iteration}")
        
        solution_name, solution_func = solutions[iteration - 1]
        
        result = await solution_func(customer_id)
        
        if result.get("resolved", False):
            return {
                "status": "resolved",
                "solution": solution_name,
                "iterations": iteration
            }
        
        observer.log_event(
            "troubleshooting",
            "ITERATION",
            {"iteration": iteration, "solution": solution_name}
        )
    
    # Max iterations reached
    return {
        "status": "escalate",
        "reason": "Max iterations reached",
        "iterations": max_iterations
    }
```

---

## 4. SESSION MANAGEMENT DEEP DIVE

### 4.1 Session Lifecycle

```
┌─ Creation (create_session)
│  - Allocate session ID
│  - Initialize storage
│  - Set timestamps
│
├─ Active Phase
│  - Accumulate events
│  - Maintain state
│  - Add messages
│
├─ Context Compaction
│  - Summarize history
│  - Reduce token count
│  - Preserve important info
│
└─ Persistence
   - Save to database
   - Archive old sessions
   - Generate audit logs
```

### 4.2 Session State Management

```python
class SessionState:
    def __init__(self):
        self.customer_info = {}
        self.billing_data = {}
        self.conversation_context = {}
        self.decisions_made = []
    
    def add_customer_info(self, info: Dict):
        """Add customer information to session state"""
        self.customer_info.update(info)
        logger.debug(f"Added customer info: {list(info.keys())}")
    
    def add_decision(self, decision: Dict):
        """Record decision in audit trail"""
        self.decisions_made.append({
            "decision": decision,
            "timestamp": datetime.now(),
            "context": self.conversation_context.copy()
        })
    
    def get_context_for_llm(self) -> str:
        """Format state for LLM context"""
        return f"""
        Customer: {self.customer_info.get('name')}
        Billing Status: {self.billing_data.get('status')}
        Conversation So Far: {self.conversation_context}
        Decisions Made: {len(self.decisions_made)}
        """

# Usage in agent
session_state = SessionState()

# Within agent handling
session_state.add_customer_info(profile_result)
session_state.add_decision({"action": "plan_change", "plan": "Premium-299"})
```

### 4.3 Context Compaction

```python
class ContextCompactor:
    """Reduce context size while preserving important information"""
    
    def __init__(self, max_tokens=2000):
        self.max_tokens = max_tokens
    
    def compact(self, messages: List[Dict]) -> List[Dict]:
        """
        Compact conversation to fit within token limit.
        
        Strategy:
        1. Keep latest 10 messages
        2. Summarize older messages
        3. Preserve decisions
        """
        
        if len(messages) <= 10:
            return messages
        
        # Keep latest messages
        kept_messages = messages[-10:]
        old_messages = messages[:-10]
        
        # Summarize old messages
        summary = self._create_summary(old_messages)
        
        return [summary] + kept_messages
    
    def _create_summary(self, messages: List[Dict]) -> Dict:
        """Create summary of old messages"""
        # In production, use LLM to summarize
        actions = [m.get("action") for m in messages if m.get("action")]
        
        return {
            "role": "summary",
            "content": f"Previous conversation covered: {', '.join(set(actions))}",
            "type": "summary"
        }
```

---

## 5. MEMORY ARCHITECTURE

### 5.1 Memory Types

```python
class MemoryBank:
    def __init__(self):
        self.short_term = {}      # Session-based (5 min TTL)
        self.long_term = {}       # Cross-session (persistent)
        self.episodic = {}        # Event-based (permanent log)
    
    async def store_preference(self, user_id: str, pref: str, value: Any):
        """Store long-term preference"""
        key = f"{user_id}:preference:{pref}"
        self.long_term[key] = {
            "value": value,
            "timestamp": datetime.now(),
            "sources": ["user_input"]
        }
    
    async def retrieve_preferences(self, user_id: str) -> Dict:
        """Retrieve all preferences for user"""
        pattern = f"{user_id}:preference:*"
        return {
            k.split(":")[-1]: v["value"]
            for k, v in self.long_term.items()
            if k.startswith(f"{user_id}:preference:")
        }
    
    async def log_event(self, user_id: str, event: Dict):
        """Log event for compliance/audit"""
        event_id = str(uuid.uuid4())
        self.episodic[event_id] = {
            "user_id": user_id,
            "event": event,
            "timestamp": datetime.now()
        }
```

### 5.2 Memory Retrieval

```python
async def retrieve_relevant_memory(user_id: str, query: str) -> Dict:
    """
    Retrieve memory relevant to current query.
    
    Uses semantic search in production (Vertex AI Memory Bank)
    """
    
    # For demo: keyword-based matching
    keywords = query.lower().split()
    
    relevant_memory = {}
    
    # Search in preferences
    preferences = await memory.retrieve_preferences(user_id)
    for pref_key, pref_value in preferences.items():
        if any(kw in pref_key.lower() for kw in keywords):
            relevant_memory[f"preference_{pref_key}"] = pref_value
    
    # Search in history
    # In production: use semantic embeddings
    
    return relevant_memory
```

---

## 6. OBSERVABILITY IMPLEMENTATION

### 6.1 Structured Logging

```python
class StructuredLogger:
    def __init__(self, component: str):
        self.component = component
    
    def log(self, level: str, action: str, **context):
        """Log with structured context"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": self.component,
            "level": level,
            "action": action,
            **context
        }
        
        # Send to logging system
        print(json.dumps(entry))
        
        # Store for later analysis
        if level == "error":
            error_queue.put(entry)

# Usage
logger = StructuredLogger("BillingAgent")
logger.log(
    "error",
    "query_failed",
    customer_id="CUST001",
    query="get_balance",
    reason="DB timeout"
)
```

### 6.2 Distributed Tracing

```python
class DistributedTracer:
    def __init__(self):
        self.traces = {}
    
    def start_trace(self, trace_id: str, workflow: str):
        """Start a distributed trace"""
        self.traces[trace_id] = {
            "workflow": workflow,
            "start": time.time(),
            "spans": []
        }
    
    def add_span(self, trace_id: str, span_name: str, duration: float, status: str):
        """Add span to trace"""
        self.traces[trace_id]["spans"].append({
            "name": span_name,
            "duration_ms": duration,
            "status": status
        })
    
    def end_trace(self, trace_id: str):
        """End trace and calculate metrics"""
        trace = self.traces[trace_id]
        total_time = time.time() - trace["start"]
        
        return {
            "trace_id": trace_id,
            "workflow": trace["workflow"],
            "total_ms": total_time * 1000,
            "spans": trace["spans"]
        }

# Usage
tracer = DistributedTracer()
tracer.start_trace("trace_123", "handle_query")
# ... do work ...
tracer.add_span("trace_123", "get_profile", 50, "success")
tracer.add_span("trace_123", "check_plans", 100, "success")
result = tracer.end_trace("trace_123")
```

---

## 7. SCALABILITY PATTERNS

### 7.1 Horizontal Scaling

```yaml
# Kubernetes deployment with auto-scaling
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telecom-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: telecom-agent
  template:
    metadata:
      labels:
        app: telecom-agent
    spec:
      containers:
      - name: agent
        image: gcr.io/project/telecom-agent:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: telecom-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: telecom-agent
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 7.2 Queue-Based Architecture

```python
# Use message queue for async processing
import asyncio
from google.cloud import pubsub_v1

class AgentQueue:
    def __init__(self, project_id: str):
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.project_id = project_id
    
    async def enqueue_query(self, customer_id: str, query: str):
        """Add query to queue"""
        topic = f"projects/{self.project_id}/topics/customer_queries"
        
        message_json = json.dumps({
            "customer_id": customer_id,
            "query": query,
            "timestamp": datetime.now().isoformat()
        })
        
        future = self.publisher.publish(
            topic,
            message_json.encode("utf-8")
        )
        
        return future.result()
    
    async def process_from_queue(self):
        """Process queries from queue"""
        subscription = f"projects/{self.project_id}/subscriptions/agent_worker"
        
        async def callback(message):
            data = json.loads(message.data.decode())
            
            # Process query
            result = await app.handle_customer_query(
                customer_id=data["customer_id"],
                query=data["query"]
            )
            
            # Acknowledge message
            message.ack()
        
        # Subscribe and listen
        self.subscriber.subscribe(subscription, callback=callback)
```

---

## 8. SECURITY HARDENING

### 8.1 API Security

```python
from fastapi import FastAPI, Depends, HTTPException, Header
import jwt

app = FastAPI()

# API Key validation
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.environ.get("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=lambda: "global")

@app.post("/api/query")
@limiter.limit("100/minute")
async def handle_query(
    request: QueryRequest,
    api_key: str = Depends(verify_api_key)
):
    """Handle customer query with rate limiting"""
    result = await app.handle_customer_query(
        customer_id=request.customer_id,
        query=request.query
    )
    return result
```

### 8.2 Data Encryption

```python
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())
    
    def encrypt_sensitive_data(self, data: Dict) -> Dict:
        """Encrypt customer-sensitive fields"""
        sensitive_fields = ["phone", "address", "email"]
        
        encrypted = data.copy()
        for field in sensitive_fields:
            if field in encrypted:
                encrypted[field] = self.cipher.encrypt(
                    str(encrypted[field]).encode()
                ).decode()
        
        return encrypted
    
    def decrypt_sensitive_data(self, data: Dict) -> Dict:
        """Decrypt for display"""
        sensitive_fields = ["phone", "address", "email"]
        
        decrypted = data.copy()
        for field in sensitive_fields:
            if field in decrypted:
                decrypted[field] = self.cipher.decrypt(
                    decrypted[field].encode()
                ).decode()
        
        return decrypted
```

---

## 9. PERFORMANCE OPTIMIZATION

### 9.1 Caching Strategy

```python
from functools import lru_cache
import redis

class CacheManager:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379)
    
    def get_customer_profile_cached(self, customer_id: str, ttl=300):
        """Get profile with caching (5 min TTL)"""
        cache_key = f"profile:{customer_id}"
        
        # Check cache
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fetch fresh
        profile = get_customer_profile(customer_id)
        
        # Store in cache
        self.redis.setex(
            cache_key,
            ttl,
            json.dumps(profile)
        )
        
        return profile
    
    def invalidate_cache(self, customer_id: str):
        """Invalidate customer cache on updates"""
        self.redis.delete(f"profile:{customer_id}")
```

### 9.2 Query Optimization

```python
# Use indices for fast queries
class OptimizedQueries:
    # Index on customer_id
    SELECT * FROM customers WHERE id = ?  -- Index: customers(id)
    
    # Composite index for common queries
    SELECT * FROM billing 
    WHERE customer_id = ? AND month = ?  
    -- Index: billing(customer_id, month)
    
    # Use LIMIT for pagination
    SELECT * FROM events
    WHERE customer_id = ?
    ORDER BY timestamp DESC
    LIMIT 20  -- Prevent large result sets
```

---

## 10. TROUBLESHOOTING GUIDE

### Issue 1: High Latency

```
Symptoms: Response time >5 seconds

Diagnosis:
1. Check database query performance
2. Verify external API timeouts
3. Check agent token count
4. Review parallel task performance

Solution:
- Add database indices
- Increase parallel concurrency
- Implement request caching
- Upgrade to faster model
```

### Issue 2: Memory Leaks

```
Symptoms: Memory usage growing over time

Diagnosis:
1. Check session cleanup
2. Verify event accumulation
3. Review trace storage

Solution:
- Implement session garbage collection
- Add memory monitoring
- Rotate logs periodically
```

### Issue 3: Agent Hallucinations

```
Symptoms: Agent giving incorrect information

Solution:
- Reduce agent temperature (0.1-0.3)
- Add information retrieval (RAG)
- Improve tool quality
- Add output validation
```

---

**End of Technical Reference Document**
