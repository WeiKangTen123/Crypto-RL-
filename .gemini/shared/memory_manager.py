import os
import datetime

# Root directory
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def update_session_memory(agent_name, actions, file_changes, comms="None", open_items="None", outcome="COMPLETED", duration=0):
    """
    Appends a new session memory block to the agent's session_memory.md.
    """
    memory_path = os.path.join(_ROOT, '.gemini', 'skills', agent_name, 'session_memory.md')
    
    # Simple block construction
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    new_block = f"""---

## [{ts}] | Model: Automated-Script | Trigger: Scheduled task | Duration: ~{int(duration)}s

**Actions:** {actions}
**File changes:** {file_changes}
**Communications:** {comms}
**Open items:** {open_items}
**Outcome:** {outcome}
"""

    # Read existing content
    try:
        if os.path.exists(memory_path):
            with open(memory_path, 'r') as f:
                content = f.read()
        else:
            content = "# Session Memory — @" + agent_name + "\n"
            
        # Find where the session blocks start (after the header)
        header_end = content.find("-->") + 3
        
        # Insert new block
        new_content = content[:header_end] + "\n\n" + new_block + content[header_end:]
        
        with open(memory_path, 'w') as f:
            f.write(new_content)
            
    except Exception as e:
        print(f"  [ERROR] Failed to update session memory for {agent_name}: {e}")
