"""Page 3 — Correlation Explorer: price time series + annotated scatter."""

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html
from dash.exceptions import PreventUpdate
from plotly.subplots import make_subplots

dash.register_page(__name__, path="/correlations", name="Correlations", order=2)


def layout(**_):
    from dashboard.db import get_all_symbols

    symbols = get_all_symbols()
    options = [{"label": s, "value": s} for s in symbols]
    first = symbols[0] if len(symbols) > 0 else None
    second = symbols[1] if len(symbols) > 1 else None

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Symbol A", className="fw-bold small"),
                            dcc.Dropdown(
                                id="corr-sym-a",
                                options=options,
                                value=first,
                                clearable=False,
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Label("Symbol B", className="fw-bold small"),
                            dcc.Dropdown(
                                id="corr-sym-b",
                                options=options,
                                value=second,
                                clearable=False,
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Label("Start date", className="fw-bold small"),
                            dcc.Input(
                                id="corr-start-date",
                                type="text",
                                placeholder="YYYY-MM-DD (optional)",
                                debounce=True,
                                className="form-control form-control-sm",
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-3 align-items-end",
            ),
            html.Div(id="corr-r-badge", className="mb-3"),
            dcc.Tabs(
                id="corr-tabs",
                value="time-series",
                children=[
                    dcc.Tab(label="Price Series", value="time-series"),
                    dcc.Tab(label="Scatter / Correlation", value="scatter"),
                ],
                className="mb-3",
            ),
            dcc.Loading(dcc.Graph(id="corr-chart", style={"height": "500px"})),
        ]
    )


@callback(
    Output("corr-chart", "figure"),
    Output("corr-r-badge", "children"),
    Input("corr-sym-a", "value"),
    Input("corr-sym-b", "value"),
    Input("corr-start-date", "value"),
    Input("corr-tabs", "value"),
)
def update_correlations(sym_a, sym_b, start_date, tab):
    if not sym_a or not sym_b:
        raise PreventUpdate

    from dashboard.db import get_db

    start = start_date.strip() if start_date else None

    with get_db() as db:
        df_a = db.read_quotes(start_date=start, symbols=[sym_a])
        df_b = db.read_quotes(start_date=start, symbols=[sym_b])

    if df_a.empty or df_b.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data for selected symbols", showarrow=False)
        return fig, ""

    s_a = df_a.set_index("date")["close"].sort_index().rename(sym_a)
    s_b = df_b.set_index("date")["close"].sort_index().rename(sym_b)
    merged = pd.DataFrame({sym_a: s_a, sym_b: s_b}).dropna()

    pearson_r = merged.corr().iloc[0, 1]
    badge_color = "success" if abs(pearson_r) > 0.7 else ("warning" if abs(pearson_r) > 0.4 else "secondary")
    badge = dbc.Alert(
        f"Pearson r = {pearson_r:.4f}  ({len(merged)} shared trading days)",
        color=badge_color,
        className="py-2 small d-inline-block",
    )

    if tab == "time-series":
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=[sym_a, sym_b],
        )
        fig.add_trace(
            go.Scatter(
                x=s_a.index,
                y=s_a.values,
                name=sym_a,
                mode="lines",
                line={"color": "#0d6efd", "width": 1.5},
                hovertemplate="%{x|%Y-%m-%d}: $%{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=s_b.index,
                y=s_b.values,
                name=sym_b,
                mode="lines",
                line={"color": "#fd7e14", "width": 1.5},
                hovertemplate="%{x|%Y-%m-%d}: $%{y:,.2f}<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="Close ($)", row=1, col=1)
        fig.update_yaxes(title_text="Close ($)", row=2, col=1)
        fig.update_layout(
            template="plotly_white",
            hovermode="x unified",
            margin={"l": 60, "r": 20, "t": 60, "b": 40},
            showlegend=False,
        )
    else:
        # Scatter with date color-gradient
        dates_num = (merged.index - merged.index[0]).days
        fig = go.Figure(
            go.Scatter(
                x=merged[sym_a],
                y=merged[sym_b],
                mode="markers",
                marker={
                    "color": dates_num,
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": "Days since start"},
                    "size": 5,
                    "opacity": 0.7,
                },
                text=merged.index.strftime("%Y-%m-%d"),
                hovertemplate=f"{sym_a}: $%{{x:,.2f}}<br>{sym_b}: $%{{y:,.2f}}<br>%{{text}}<extra></extra>",
            )
        )
        fig.update_layout(
            xaxis_title=f"{sym_a} Close ($)",
            yaxis_title=f"{sym_b} Close ($)",
            template="plotly_white",
            margin={"l": 60, "r": 20, "t": 40, "b": 60},
        )

    return fig, badge
