from graph_flow import app_graph
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod


display(
    Image(
        app_graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
            output_file_path="graph_viz_test.png",
        )
    )
)
