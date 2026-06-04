import os
import sys

# Ensure the project root is importable regardless of how the app is launched
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
import dash_bootstrap_components as dbc
from dash import html

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages"),
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Stock Dashboard",
)
server = app.server  # Gunicorn entry point

_nav = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Indexes", href="/")),
        dbc.NavItem(dbc.NavLink("Compare", href="/compare")),
        dbc.NavItem(dbc.NavLink("Correlations", href="/correlations")),
        dbc.NavItem(dbc.NavLink("Stocks", href="/stocks")),
    ],
    brand="Stock Dashboard",
    brand_href="/",
    color="dark",
    dark=True,
    className="mb-4",
)

app.layout = dbc.Container(
    [_nav, dash.page_container],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
