"""LangGraph conversation agent for English speaking practice."""

from typing import Annotated, AsyncGenerator, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from app.agents.prompts import get_system_prompt
from app.services.llm import get_llm_client


class ConversationState(TypedDict):
    """State for the conversation graph."""

    messages: Annotated[list, add_messages]
    mode: str
    level: str
    scenario: str | None


class ConversationAgent:
    """
    LangGraph-based conversation agent for English practice.

    Manages conversation state and generates contextual responses.
    """

    def __init__(self, mode: str = "free_talk", level: str = "B1", scenario: str | None = None):
        """
        Initialize the conversation agent.

        @param mode - Conversation mode (free_talk, corrective, roleplay, guided)
        @param level - CEFR level (A2, B1, B2, C1)
        @param scenario - Optional roleplay scenario
        """
        self.mode = mode
        self.level = level
        self.scenario = scenario
        self.llm = get_llm_client()
        self.graph = self._build_graph()
        self.state: ConversationState = {
            "messages": [],
            "mode": mode,
            "level": level,
            "scenario": scenario,
        }

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph conversation flow."""
        graph = StateGraph(ConversationState)

        # Add nodes
        graph.add_node("respond", self._respond_node)

        # Add edges
        graph.add_edge(START, "respond")
        graph.add_edge("respond", END)

        return graph.compile()

    def _respond_node(self, state: ConversationState) -> dict:
        """Generate a response to the user's message."""
        # Build messages with system prompt
        system_prompt = get_system_prompt(
            mode=state["mode"],
            level=state["level"],
            scenario=state.get("scenario"),
        )

        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        # Generate response
        response = self.llm.invoke(messages)

        return {"messages": [response]}

    async def respond(self, user_text: str) -> str:
        """
        Process user input and generate a response.

        @param user_text - User's spoken text
        @returns Agent's response text
        """
        # Add user message to state
        self.state["messages"].append(HumanMessage(content=user_text))

        # Run the graph
        result = self.graph.invoke(self.state)

        # Update state with new messages
        self.state = result

        # Extract and return the response text
        last_message = result["messages"][-1]
        if isinstance(last_message, AIMessage):
            return last_message.content

        return "I'm sorry, I didn't understand that. Could you please repeat?"

    async def respond_stream(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Process user input and stream the response token by token.

        @param user_text - User's spoken text
        @yields Response text chunks as they're generated
        """
        # Add user message to state
        self.state["messages"].append(HumanMessage(content=user_text))

        # Build messages with system prompt
        system_prompt = get_system_prompt(
            mode=self.state["mode"],
            level=self.state["level"],
            scenario=self.state.get("scenario"),
        )
        messages = [SystemMessage(content=system_prompt)] + self.state["messages"]

        # Stream the response
        full_response = ""
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        # Add full response to state
        self.state["messages"].append(AIMessage(content=full_response))

    def set_mode(self, mode: str):
        """Change the conversation mode."""
        self.mode = mode
        self.state["mode"] = mode

    def set_level(self, level: str):
        """Change the CEFR level."""
        self.level = level
        self.state["level"] = level

    def set_scenario(self, scenario: str | None):
        """Set roleplay scenario."""
        self.scenario = scenario
        self.state["scenario"] = scenario

    def reset(self):
        """Reset conversation history."""
        self.state["messages"] = []

    def get_history(self) -> list[dict]:
        """Get conversation history as simple dicts."""
        history = []
        for msg in self.state["messages"]:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "text": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "text": msg.content})
        return history
