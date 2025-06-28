# Product Context

## Why This Project Exists

This is a **Customer Service Agents Demo** that showcases the capabilities of the OpenAI Agents SDK for building intelligent customer service systems. The project demonstrates how multiple AI agents can work together to handle different aspects of airline customer service through intelligent routing and orchestration.

## What Problems It Solves

### Primary Problems:
1. **Complex Customer Service Routing** - Automatically routes customer inquiries to the most appropriate specialist agent
2. **Multi-Agent Orchestration** - Demonstrates how different AI agents can collaborate and hand off conversations seamlessly
3. **Guardrail Implementation** - Shows how to implement safety measures to keep conversations on-topic and prevent misuse
4. **Real-time Agent Visualization** - Provides transparency into the agent decision-making process

### Business Value:
- Reduces customer service response times through intelligent routing
- Ensures customers get specialized help for their specific needs
- Maintains conversation quality through guardrails
- Provides operational visibility into agent behavior

## How It Should Work

### Core Workflow:
1. **Customer Interaction** - User sends a message through the chat interface
2. **Triage Agent** - Initial agent analyzes the request and routes to appropriate specialist
3. **Specialist Agents** - Handle specific tasks (seat booking, flight status, cancellations, FAQ)
4. **Context Preservation** - Maintains customer context (confirmation numbers, flight details) across handoffs
5. **Guardrail Enforcement** - Ensures conversations stay relevant to airline topics

### Agent Types:
- **Triage Agent** - Routes requests to appropriate specialists
- **Seat Booking Agent** - Handles seat changes and displays interactive seat maps
- **Flight Status Agent** - Provides flight information and status updates
- **Cancellation Agent** - Processes flight cancellations
- **FAQ Agent** - Answers common questions about airline policies

### Key Features:
- Real-time agent switching visualization
- Interactive seat map for seat selection
- Guardrails for relevance and jailbreak prevention
- Context preservation across agent handoffs
- Tool execution tracking and visualization

## Target Use Cases

### Demo Flow #1 - Seat Change:
1. Customer requests seat change
2. Triage routes to Seat Booking Agent
3. Agent confirms details and shows seat map
4. Customer selects new seat
5. System updates booking

### Demo Flow #2 - Flight Cancellation:
1. Customer requests cancellation
2. Triage routes to Cancellation Agent
3. Agent confirms flight details
4. Processes cancellation
5. Guardrails prevent off-topic requests

## Success Metrics
- Successful agent routing accuracy
- Conversation completion rates
- Guardrail effectiveness
- User experience quality
- System response times
