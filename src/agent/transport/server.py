"""
FastAPI WebSocket server for the agent.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict
import uuid
import logging
import os

from .connection import ConnectionManager
from .messages import ClientMessage, ServerMessage
from ..core.agent import ReactAgent, AgentEvent
from ..llm.factory import LLMFactory
from ..tools.registry import registry as tool_registry
from ..tools.builtin import core_tools
from ..skills.index import skill_index
from ..skills.executor import SkillCommandExecutor
from ..config.settings import settings

logger = logging.getLogger(__name__)


# Global instances
connection_manager = ConnectionManager(
    heartbeat_interval=settings.server.heartbeat_interval
)
agents: Dict[str, ReactAgent] = {}


def load_system_prompt() -> str:
    """Load system prompt from file or return default."""
    try:
        with open("config/prompts/system_prompt.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        return DEFAULT_SYSTEM_PROMPT


DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools and skills.

## How to Use Tools
You have direct tools available that you can call when needed. Simply use them when appropriate.

## How to Use Skills
Skills are powerful capability modules with documentation. To use a skill:
1. Call `list_skills()` to see what's available
2. Call `read_skill("skill_name")` to read the full SKILL.md documentation
3. Use `execute_command("...")` to run skill commands as documented

**Important**: ALWAYS read a skill's documentation before using it. The SKILL.md contains exact command formats and examples.

## Guidelines
- Think step-by-step about complex problems
- Use tools/skills when they would help
- If something fails, explain what happened and try alternatives
- Be concise but thorough"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting agent server...")
    
    # Initialize skill index
    skill_index.set_base_path(settings.skills.base_path)
    if settings.skills.auto_discover:
        skill_index.discover()
    
    # Initialize skill command executor
    command_executor = SkillCommandExecutor(
        base_path=skill_index.base_path,
        allowed_prefixes=settings.skills.allowed_commands,
        timeout=settings.skills.command_timeout
    )
    core_tools.set_command_executor(command_executor)
    
    logger.info(f"Loaded {len(skill_index.list_skills())} skills")
    logger.info(f"Loaded {len(tool_registry.list_names())} tools")
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(
    title="Autonomous Agent",
    description="WebSocket-based conversational agent with tools and skills",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine frontend path (works both in dev and installed mode)
def get_frontend_path() -> Path:
    """Get the frontend directory path."""
    # Try relative to current working directory first (for running from project root)
    cwd_path = Path.cwd() / "frontend"
    if cwd_path.exists():
        return cwd_path
    
    # Try relative to this file (for installed package)
    file_path = Path(__file__).parent.parent.parent.parent / "frontend"
    if file_path.exists():
        return file_path
    
    return cwd_path  # Return cwd path even if it doesn't exist

frontend_path = get_frontend_path()

# Log frontend path for debugging
print(f"Frontend path: {frontend_path} (exists: {frontend_path.exists()})")


def create_agent() -> ReactAgent:
    """Create a new agent instance."""
    api_key = settings.llm.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    
    llm = LLMFactory.from_config({
        "provider": settings.llm.provider,
        "model": settings.llm.model,
        "api_key": api_key,
        "cache": {"enabled": settings.llm.cache.enabled},
        "max_tokens": settings.llm.max_tokens,
        "temperature": settings.llm.temperature,
    })
    
    return ReactAgent(
        llm=llm,
        tool_registry=tool_registry,
        skill_index=skill_index,
        system_prompt=load_system_prompt(),
        max_iterations=settings.agent.max_iterations
    )


@app.get("/")
async def root():
    """Serve the frontend."""
    fp = get_frontend_path()
    frontend_file = fp / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return {"message": "Autonomous Agent API", "docs": "/docs", "frontend_path": str(fp), "exists": fp.exists()}


@app.get("/styles.css")
async def styles():
    """Serve CSS."""
    fp = get_frontend_path()
    css_file = fp / "styles.css"
    if css_file.exists():
        return FileResponse(str(css_file), media_type="text/css")
    return {"error": "styles.css not found"}


@app.get("/app.js")
async def app_js():
    """Serve JavaScript."""
    fp = get_frontend_path()
    js_file = fp / "app.js"
    if js_file.exists():
        return FileResponse(str(js_file), media_type="application/javascript")
    return {"error": "app.js not found"}


@app.websocket("/chat")
async def chat_websocket(websocket: WebSocket):
    """Main WebSocket endpoint for chat."""
    client_id = str(uuid.uuid4())
    
    await connection_manager.connect(websocket, client_id)
    
    # Create agent for this connection
    agent = create_agent()
    agents[client_id] = agent
    
    try:
        # Send connection confirmation
        await connection_manager.send_json(client_id, ServerMessage(
            type="connected",
            data={
                "client_id": client_id,
                "model": f"{settings.llm.provider}/{settings.llm.model}"
            }
        ).to_json_dict())
        
        while True:
            raw_data = await websocket.receive_json()
            
            try:
                message = ClientMessage(**raw_data)
            except Exception as e:
                await connection_manager.send_json(client_id, ServerMessage(
                    type="error",
                    content=f"Invalid message format: {e}"
                ).to_json_dict())
                continue
            
            # Handle different message types
            if message.type == "ping":
                await connection_manager.send_json(client_id, ServerMessage(
                    type="pong"
                ).to_json_dict())
            
            elif message.type == "reset":
                agent.reset()
                await connection_manager.send_json(client_id, ServerMessage(
                    type="status",
                    content="Conversation reset"
                ).to_json_dict())
            
            elif message.type == "switch_model":
                # Hot-swap model
                if message.data and "provider" in message.data and "model" in message.data:
                    try:
                        api_key = message.data.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
                        new_llm = LLMFactory.create(
                            provider=message.data["provider"],
                            model=message.data["model"],
                            api_key=api_key
                        )
                        agent.update_llm(new_llm)
                        await connection_manager.send_json(client_id, ServerMessage(
                            type="model_switched",
                            data={
                                "provider": message.data["provider"],
                                "model": message.data["model"]
                            }
                        ).to_json_dict())
                    except Exception as e:
                        await connection_manager.send_json(client_id, ServerMessage(
                            type="error",
                            content=f"Failed to switch model: {e}"
                        ).to_json_dict())
            
            elif message.type == "chat" and message.content:
                # Process chat message with streaming
                try:
                    async for event in agent.process_stream(message.content):
                        await connection_manager.send_json(client_id, ServerMessage(
                            type=event.type,
                            content=event.data.get("content"),
                            data={k: v for k, v in event.data.items() if k != "content"}
                        ).to_json_dict())
                except Exception as e:
                    logger.exception(f"Agent processing error: {e}")
                    await connection_manager.send_json(client_id, ServerMessage(
                        type="error",
                        content=f"Processing error: {str(e)}"
                    ).to_json_dict())
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.exception(f"WebSocket error for {client_id}: {e}")
    finally:
        connection_manager.disconnect(client_id)
        agents.pop(client_id, None)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "connections": connection_manager.get_connection_count(),
        "skills": len(skill_index.list_skills()),
        "tools": len(tool_registry.list_names())
    }


@app.get("/info")
async def server_info():
    """Server information endpoint."""
    return {
        "version": "0.1.0",
        "llm": {
            "provider": settings.llm.provider,
            "model": settings.llm.model
        },
        "skills": [
            {"name": s.name, "description": s.description}
            for s in skill_index.list_skills()
        ],
        "tools": tool_registry.list_names()
    }
