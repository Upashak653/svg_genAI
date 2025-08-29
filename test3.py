import os
import re
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from dotenv import load_dotenv
from crewai.llm import LLM

# --- Configuration & Environment ---

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY not set in .env")

# Initialize LLM for CrewAI 0.165.1
llm = LLM(model="gpt-4o-mini", api_key=api_key)

INPUT_SVG_PATH = "input.svg"
OUTPUT_SVG_PATH = "output.svg"

# Global storage for passing data between tasks
workflow_data = {}


# --- Utility Functions ---

def read_svg_file(file_path):
    try:
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return None


def write_svg_file(file_path, content):
    with open(file_path, "w") as f:
        f.write(content)
    print(f"✅ Successfully wrote {file_path}")


# --- Tools ---

@tool
def parse_gradient_details_tool(prompt: str) -> str:
    """Parse user prompt for gradient details and store in global workflow_data."""
    
    gradient_config = {
        "type": "linear",
        "direction": "vertical",
        "start_color": "#ff0000",
        "end_color": "#0000ff",
        "target_shape": "rect",
    }

    # Extract colors from prompt
    colors = re.findall(r"#([0-9a-fA-F]{6})", prompt)
    if len(colors) >= 2:
        gradient_config["start_color"] = f"#{colors[0]}"
        gradient_config["end_color"] = f"#{colors[1]}"

    # Determine gradient type
    if "radial" in prompt.lower():
        gradient_config["type"] = "radial"
    
    # Determine direction
    if "vertical" in prompt.lower():
        gradient_config["direction"] = "vertical"
    elif "horizontal" in prompt.lower():
        gradient_config["direction"] = "horizontal"

    # Extract target shape
    if "rectangle" in prompt.lower() or "rect" in prompt.lower():
        gradient_config["target_shape"] = "rect"
    elif "circle" in prompt.lower():
        gradient_config["target_shape"] = "circle"
    elif "ellipse" in prompt.lower():
        gradient_config["target_shape"] = "ellipse"

    # Store in global workflow data
    workflow_data['gradient_config'] = gradient_config
    
    return f"Parsed gradient config: {gradient_config}"


@tool
def svg_modifier_tool(svg_content: str) -> str:
    """Insert gradient into SVG and update fill using stored config."""
    
    config = workflow_data.get('gradient_config', {})
    print(f"--- SVG MODIFIER AGENT ACTION ---")
    print(f"Using config: {config}")

    gradient_type = config.get("type", "linear")
    grad_id = "grad1"

    # Direction attributes
    if gradient_type == "linear":
        if config.get("direction") == "vertical":
            direction_attrs = 'x1="0%" y1="0%" x2="0%" y2="100%"'
        elif config.get("direction") == "horizontal":
            direction_attrs = 'x1="0%" y1="0%" x2="100%" y2="0%"'
        else:
            direction_attrs = 'x1="0%" y1="0%" x2="0%" y2="100%"'
    else:  # radial
        direction_attrs = 'cx="50%" cy="50%" r="50%"'

    # Create gradient definition
    gradient_xml = f"""    <defs>
        <{gradient_type}Gradient id="{grad_id}" {direction_attrs}>
            <stop offset="0%" style="stop-color:{config['start_color']}; stop-opacity:1" />
            <stop offset="100%" style="stop-color:{config['end_color']}; stop-opacity:1" />
        </{gradient_type}Gradient>
    </defs>"""

    # Insert gradient definition
    if "<defs>" in svg_content:
        new_svg_content = re.sub(r"<defs>.*?</defs>", gradient_xml, svg_content, flags=re.DOTALL)
    else:
        new_svg_content = svg_content.replace("<svg", f"<svg").replace(">", f">\n{gradient_xml}", 1)

    # Update the target shape's fill attribute
    target_shape = config.get("target_shape", "rect")
    
    # Replace fill attribute
    pattern = rf'(<{target_shape}[^>]*\s)fill="[^"]*"([^>]*>)'
    if re.search(pattern, new_svg_content):
        updated_svg = re.sub(pattern, rf'\1fill="url(#{grad_id})"\2', new_svg_content)
    else:
        # Add fill if not present
        pattern_no_fill = rf'(<{target_shape}[^>]*?)(/?>)'
        updated_svg = re.sub(pattern_no_fill, rf'\1 fill="url(#{grad_id})"\2', new_svg_content)

    workflow_data['final_svg'] = updated_svg
    return updated_svg


# --- Agents ---
#Agent 1: this agent uses parse_gradient_details_tool for extracting gradient details from user prompts and pass it to the SVG modifier
gradient_parser = Agent(
    role="Gradient Parser",
    goal="Extract gradient details from user prompt",
    backstory="You are an expert at analyzing design prompts and extracting gradient specifications.",
    llm=llm,
    tools=[parse_gradient_details_tool],
    verbose=True,
    allow_delegation=False,
)
#Agent 2: this agent uses svg_modifier_tool for applying the gradient to the SVG and updating the fill attributes.
svg_modifier = Agent(
    role="SVG Modifier", 
    goal="Apply gradient to SVG elements",
    backstory="You are an SVG expert who specializes in adding gradients to SVG elements.",
    llm=llm,
    tools=[svg_modifier_tool],
    verbose=True,
    allow_delegation=False,
)


# --- Tasks ---
# Task 1: Parse gradient details from user prompt 
task_parse = Task(
    description="""
    Analyze this user prompt and extract gradient details: {user_prompt}
    
    Use the parse_gradient_details_tool to identify:
    - Gradient type (linear or radial)
    - Direction (horizontal or vertical) 
    - Start and end colors
    - Target shape to modify
    
    Return the parsed configuration.
    """,
    agent=gradient_parser,
    expected_output="Gradient configuration details",
)
# Task 2: Modify SVG with gradient and gets updated SVG 
task_modify = Task(
    description="""
    Modify the SVG to apply the gradient that was parsed in the previous task.
    
    Input SVG: {svg_content}
    
    Use the svg_modifier_tool to apply the gradient configuration to the SVG.
    Return the complete modified SVG with the gradient applied.
    """,
    agent=svg_modifier,
    expected_output="Complete SVG with gradient applied",
    context=[task_parse],
)


# --- Crew ---
# This crew is responsible for handling the gradient application workflow
crew = Crew(
    agents=[gradient_parser, svg_modifier],
    tasks=[task_parse, task_modify],
    process=Process.sequential,
    verbose=True,
)


# --- Execution ---

def main():
    # Create initial SVG
    initial_svg_content = """<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
 <rect x="50" y="50" width="200" height="100" fill="red"/>
</svg>"""

    write_svg_file(INPUT_SVG_PATH, initial_svg_content)

    user_prompt = "Change the red rectangle to have a vertical gradient from #ff0000 to #0000ff."

    print("\n" + "=" * 50)
    print(f"User Prompt: {user_prompt}")
    print("=" * 50 + "\n")

    try:
        # Execute crew workflow
        result = crew.kickoff(inputs={
            "user_prompt": user_prompt, 
            "svg_content": initial_svg_content
        })

        # For CrewAI 0.165.1, the final output is in result.raw
        raw_output = result.raw
        
        # Extract clean SVG from the output (in case agent adds extra text)
        final_svg = None
        
        # Try to extract SVG from agent response
        if raw_output:
            # Look for SVG content in the response
            svg_match = re.search(r'(<svg[^>]*>.*?</svg>)', raw_output, re.DOTALL)
            if svg_match:
                final_svg = svg_match.group(1)
                print("✅ Extracted SVG from agent response")
            else:
                # Fallback to backup storage
                final_svg = workflow_data.get('final_svg')
                if final_svg:
                    print("✅ Using backup SVG from workflow_data")
        
        if final_svg and final_svg.strip():
            write_svg_file(OUTPUT_SVG_PATH, final_svg)
            
            print("\n" + "=" * 50)
            print("Workflow Complete!")
            print("=" * 50 + "\n")
            print("Modified SVG:")
            print(final_svg)
        else:
            print("❌ No valid SVG content found")
            print(f"Raw agent output: {raw_output}")
            
    except Exception as e:
        print(f"❌ Error executing crew: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()