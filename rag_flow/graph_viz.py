from pathlib import Path

from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod

from rag_flow.graph_flow import app_graph


BASE_DIR = Path(__file__).resolve().parent.parent
viz_path = BASE_DIR / "rag_flow" / "graph_viz_test5.png"

display(
    Image(
        app_graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
            output_file_path=viz_path,
        )
    )
)
