# svg_genAI

# 🎨 CrewAI SVG Gradient Updater

This project demonstrates a **CrewAI multi-agent workflow** that accepts a **natural language prompt** and updates an SVG file by applying gradients to shapes.  

The system uses **two CrewAI agents**:
- **Gradient Parser Agent** → extracts gradient details (colors, direction, target shape) from user instructions.
- **SVG Modifier Agent** → updates the SVG file with the gradient configuration.

---

## 🚀 Features
- Accepts **natural language prompts** (e.g. *"Change the red rectangle to have a vertical gradient from #ff0000 to #0000ff."*).
- Uses **CrewAI agents** to parse gradient configs and modify the SVG.
- Produces a valid **`output.svg`** that can be opened in any browser.
- Prints a detailed **workflow log**:
  - User prompt  
  - Parsed gradient config  
  - Actions by each agent  
  - Before and after SVG snippets  

---

## 📂 Project Structure
