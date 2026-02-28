import sys
import os

# Add the backend directory to the python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.ai.graph.workflow import app

def main():
    try:
        graph = app.get_graph(xray=True)
        mermaid_graph = graph.draw_mermaid()
        print(mermaid_graph)
        
        # Also try to save as png if possible, though it requires external dependencies
        try:
            png_data = graph.draw_mermaid_png()
            with open("graph_visualization.png", "wb") as f:
                f.write(png_data)
            print("\nGraph saved as graph_visualization.png")
        except Exception as e:
            print(f"\nCould not save PNG (this is expected if graphviz is missing): {e}")

    except Exception as e:
        print(f"Error visualizing graph: {e}")

if __name__ == "__main__":
    main()
