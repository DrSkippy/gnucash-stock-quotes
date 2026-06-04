"""Page 2 — Index vs Stock Comparison: rebased to 100, rolling correlation subplot."""

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html
from dash.exceptions import PreventUpdate
from plotly.subplots import make_subplots

dash.register_page(__name__, path="/compare", name="Compare", order=1)


def layout(**_):
    from dashboard.db import get_db, get_all_symbols

    with get_db() as db:
        defs = db.read_index_definitions()

    index_options = [
        {"label": idx["NAME"], "value": idx["NAME"]}
        for idx in defs.get("asset_indexes", [])
    ]
    symbol_options = [{"label": s, "value": s} for s in get_all_symbols()]
    first_idx = index_options[0]["value"] if index_options else None
    first_sym = symbol_options[0]["value"] if symbol_options else None

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Index", className="fw-bold small"),
                            dcc.Dropdown(
                                id="cmp-index-dropdown",
                                options=index_options,
                                value=first_idx,
                                clearable=False,
                            ),
                        ],
                        width=5,
                    ),
                    dbc.Col(
                        [
                            html.Label("Comparison Symbol", className="fw-bold small"),
                            dcc.Dropdown(
                                id="cmp-symbol-dropdown",
                                options=symbol_options,
                                value=first_sym,
                                clearable=False,
                            ),
                        ],
                        width=5,
                    ),
                    dbc.Col(
                        [
                            html.Label("Rolling window (days)", className="fw-bold small"),
                            dcc.Slider(
                                id="cmp-window-slider",
                                min=10,
                                max=90,
                                step=5,
                                value=30,
                                marks={10: "10", 30: "30", 60: "60", 90: "90"},
                            ),
                        ],
                        width=2,
                    ),
                ],
                className="mb-3 align-items-end",
            ),
            dcc.Loading(dcc.Graph(id="cmp-chart", style={"height": "600px"})),
        ]
    )


@callback(
    Output("cmp-chart", "figure"),
    Input("cmp-index-dropdown", "value"),
    Input("cmp-symbol-dropdown", "value"),
    Input("cmp-window-slider", "value"),
)
def update_compare(index_name, symbol, window):
    if not index_name or not symbol:
        raise PreventUpdate

    from dashboard.db import get_db, get_index_meta

    with get_db() as db:
        meta = get_index_meta(db, index_name)
        idx_series = db.read_index_history(index_name)
        stock_df = db.read_quotes(symbols=[symbol])

    if idx_series.empty or stock_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Align both series on their shared date range (from index inception onward)
    inception = pd.to_datetime(meta.get("created_date")) if meta.get("created_date") else idx_series.index[0]
    idx_series = idx_series[idx_series.index >= inception]

    stock_series = stock_df.set_index("date")["close"].sort_index()
    stock_series = stock_series[stock_series.index >= inception]

    # Rebase to 100 at first available common date
    common_start = max(
        idx_series.index[0] if not idx_series.empty else inception,
        stock_series.index[0] if not stock_series.empty else inception,
    )
    idx_r = idx_series[idx_series.index >= common_start]
    stk_r = stock_series[stock_series.index >= common_start]
    if idx_r.empty or stk_r.empty:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient overlapping data", showarrow=False)
        return fig

    idx_rebased = idx_r / idx_r.iloc[0] * 100
    stk_rebased = stk_r / stk_r.iloc[0] * 100

    # Rolling correlation on rebased series
    combined = pd.DataFrame({"idx": idx_rebased, "stk": stk_rebased}).dropna()
    rolling_corr = combined["idx"].rolling(window).corr(combined["stk"])

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05,
        subplot_titles=[
            f"Performance (rebased to 100 at {common_start.date()})",
            f"Rolling {window}-day Correlation",
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=idx_rebased.index,
            y=idx_rebased.values,
            name=index_name,
            mode="lines",
            line={"width": 2, "color": "#0d6efd"},
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=stk_rebased.index,
            y=stk_rebased.values,
            name=symbol,
            mode="lines",
            line={"width": 2, "color": "#fd7e14"},
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=rolling_corr.index,
            y=rolling_corr.values,
            name=f"r ({window}d)",
            mode="lines",
            line={"width": 1.5, "color": "#6f42c1"},
            hovertemplate="%{x|%Y-%m-%d}: r=%{y:.3f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    # Reference lines at r=±1 and r=0
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5, row=2, col=1)
    fig.add_hline(y=1, line_dash="dot", line_color="green", opacity=0.3, row=2, col=1)
    fig.add_hline(y=-1, line_dash="dot", line_color="red", opacity=0.3, row=2, col=1)

    fig.update_yaxes(title_text="Rebased Value", row=1, col=1)
    fig.update_yaxes(title_text="Pearson r", range=[-1.1, 1.1], row=2, col=1)
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        margin={"l": 60, "r": 20, "t": 60, "b": 40},
        legend={"orientation": "h", "y": 1.02, "x": 0},
    )
    return fig
