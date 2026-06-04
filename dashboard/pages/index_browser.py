"""Page 1 — Index Browser: history chart, member weights, recalculate action."""

import threading
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html
from dash.exceptions import PreventUpdate

dash.register_page(__name__, path="/", name="Indexes", order=0)

_recalc_lock = threading.Lock()


def layout(**_):
    from dashboard.db import get_db

    with get_db() as db:
        defs = db.read_index_definitions()

    options = [
        {"label": idx["NAME"], "value": idx["NAME"]}
        for idx in defs.get("asset_indexes", [])
    ]
    first = options[0]["value"] if options else None

    return dbc.Row(
        [
            # ── Sidebar ──────────────────────────────────────────────────────
            dbc.Col(
                [
                    html.H5("Index", className="mb-2"),
                    dcc.Dropdown(
                        id="idx-dropdown",
                        options=options,
                        value=first,
                        clearable=False,
                    ),
                    html.Div(id="idx-info", className="mt-3"),
                    dbc.Button(
                        "Recalculate All Indexes",
                        id="recalc-btn",
                        color="warning",
                        outline=True,
                        className="mt-4 w-100",
                        n_clicks=0,
                    ),
                    dcc.Loading(
                        html.Div(id="recalc-status", className="mt-2 small")
                    ),
                ],
                width=3,
            ),
            # ── Main area ─────────────────────────────────────────────────────
            dbc.Col(
                [
                    dbc.Row(
                        dbc.Col(
                            dcc.DatePickerRange(
                                id="idx-date-range",
                                display_format="YYYY-MM-DD",
                                className="mb-3",
                            )
                        )
                    ),
                    dcc.Loading(dcc.Graph(id="idx-chart", style={"height": "420px"})),
                    html.H6("Portfolio Weights", className="mt-4 mb-2"),
                    dcc.Loading(html.Div(id="idx-weights-table")),
                ],
                width=9,
            ),
        ],
        className="g-3",
    )


@callback(
    Output("idx-chart", "figure"),
    Output("idx-info", "children"),
    Output("idx-weights-table", "children"),
    Input("idx-dropdown", "value"),
    Input("idx-date-range", "start_date"),
    Input("idx-date-range", "end_date"),
)
def update_index_view(index_name, start_date, end_date):
    if not index_name:
        raise PreventUpdate

    from dashboard.db import get_db, get_index_meta

    with get_db() as db:
        meta = get_index_meta(db, index_name)
        defs = db.read_index_definitions()
        series = db.read_index_history(index_name, start_date=start_date, end_date=end_date)
        weights = db.read_index_weights(index_name)

    idx_cfg = next(
        (i for i in defs.get("asset_indexes", []) if i["NAME"] == index_name), {}
    )

    # ── Chart ────────────────────────────────────────────────────────────────
    fig = go.Figure()
    if not series.empty:
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines",
                name=index_name,
                line={"width": 2, "color": "#0d6efd"},
                hovertemplate="%{x|%Y-%m-%d}: $%{y:,.2f}<extra></extra>",
            )
        )
    fig.update_layout(
        title={"text": index_name, "font": {"size": 14}},
        xaxis_title="Date",
        yaxis_title="Value ($)",
        margin={"l": 60, "r": 20, "t": 40, "b": 40},
        hovermode="x unified",
        template="plotly_white",
    )

    # ── Info card ────────────────────────────────────────────────────────────
    members = idx_cfg.get("MEMBERS", [])
    info = dbc.Card(
        dbc.CardBody(
            [
                dbc.Badge(meta.get("type", ""), color="primary", className="mb-2"),
                html.P(
                    f"Inception: {meta.get('created_date', 'N/A')}",
                    className="mb-1 small",
                ),
                html.P(
                    f"Portfolio Value: ${meta.get('portfolio_value', 10_000):,.0f}",
                    className="mb-1 small",
                ),
                html.P(
                    f"{len(members)} members: {', '.join(members)}",
                    className="mb-0 small text-muted",
                ),
            ]
        ),
        className="mt-2",
    )

    # ── Weights table ────────────────────────────────────────────────────────
    if weights:
        rows = [
            html.Tr([html.Td(sym), html.Td(f"{shares:,.6f}")])
            for sym, shares in sorted(weights.items())
        ]
        table = dbc.Table(
            [
                html.Thead(html.Tr([html.Th("Symbol"), html.Th("Shares")])),
                html.Tbody(rows),
            ],
            size="sm",
            bordered=True,
            hover=True,
            className="mt-1",
        )
    else:
        table = dbc.Alert(
            "No weight data. Click Recalculate All Indexes to compute.",
            color="light",
            className="small mt-1",
        )

    return fig, info, table


@callback(
    Output("recalc-status", "children"),
    Input("recalc-btn", "n_clicks"),
    prevent_initial_call=True,
)
def recalculate(_n_clicks):
    if not _recalc_lock.acquire(blocking=False):
        return dbc.Alert("Already running — please wait.", color="warning", className="py-1 small")
    try:
        from market_indexes.portfolio import PortfolioAnalyzer

        PortfolioAnalyzer()  # reads all quotes, recalculates + persists all indexes
        return dbc.Alert(
            f"Done at {datetime.now().strftime('%H:%M:%S')}",
            color="success",
            className="py-1 small",
        )
    except Exception as exc:
        return dbc.Alert(f"Error: {exc}", color="danger", className="py-1 small")
    finally:
        _recalc_lock.release()
