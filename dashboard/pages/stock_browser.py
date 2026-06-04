"""Page 4 — Stock Browser: normalized multi-symbol chart + fetch action."""

import threading
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html
from dash.exceptions import PreventUpdate

dash.register_page(__name__, path="/stocks", name="Stocks", order=3)

_fetch_lock = threading.Lock()

_COLORS = [
    "#0d6efd", "#fd7e14", "#198754", "#dc3545", "#6f42c1",
    "#20c997", "#d63384", "#0dcaf0", "#ffc107", "#6c757d",
]


def layout(**_):
    from dashboard.db import get_all_symbols, get_last_quote_date

    symbols = get_all_symbols()
    options = [{"label": s, "value": s} for s in symbols]
    defaults = symbols[:3] if len(symbols) >= 3 else symbols

    last_date = get_last_quote_date()

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Symbols (up to 10)", className="fw-bold small"),
                            dcc.Dropdown(
                                id="stk-symbols",
                                options=options,
                                value=defaults,
                                multi=True,
                                placeholder="Select symbols...",
                            ),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            html.Label("Normalize", className="fw-bold small"),
                            dcc.RadioItems(
                                id="stk-normalize",
                                options=[
                                    {"label": " Price ($)", "value": "raw"},
                                    {"label": " Rebased to 100", "value": "norm"},
                                ],
                                value="norm",
                                className="small",
                                inputStyle={"marginRight": "4px"},
                                labelStyle={"marginRight": "12px"},
                            ),
                        ],
                        width=2,
                    ),
                    dbc.Col(
                        [
                            html.Label(" ", className="fw-bold small d-block"),
                            dbc.Button(
                                "Fetch Latest Quotes",
                                id="stk-fetch-btn",
                                color="success",
                                outline=True,
                                size="sm",
                                n_clicks=0,
                            ),
                        ],
                        width=2,
                        className="d-flex flex-column justify-content-end",
                    ),
                ],
                className="mb-2 align-items-end",
            ),
            dbc.Row(
                dbc.Col(
                    dcc.Loading(
                        html.Div(id="stk-fetch-status", className="small text-muted mb-2")
                    )
                )
            ),
            html.P(
                f"Last quote date in DB: {last_date}",
                className="text-muted small mb-2",
                id="stk-last-date",
            ),
            dcc.Loading(dcc.Graph(id="stk-chart", style={"height": "500px"})),
        ]
    )


@callback(
    Output("stk-chart", "figure"),
    Input("stk-symbols", "value"),
    Input("stk-normalize", "value"),
)
def update_stock_chart(symbols, normalize):
    if not symbols:
        raise PreventUpdate

    symbols = symbols[:10]  # cap at 10

    from dashboard.db import get_db

    with get_db() as db:
        df = db.read_quotes(symbols=symbols)

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data for selected symbols", showarrow=False)
        return fig

    wide = df.pivot_table(index="date", columns="symbol", values="close")
    wide = wide.sort_index()

    fig = go.Figure()
    for i, sym in enumerate(symbols):
        if sym not in wide.columns:
            continue
        series = wide[sym].dropna()
        if series.empty:
            continue

        if normalize == "norm":
            y_vals = series / series.iloc[0] * 100
            y_title = "Rebased Value (100 = first date)"
        else:
            y_vals = series
            y_title = "Close Price ($)"

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=y_vals.values,
                name=sym,
                mode="lines",
                line={"color": _COLORS[i % len(_COLORS)], "width": 1.8},
                hovertemplate=f"{sym} %{{x|%Y-%m-%d}}: %{{y:,.2f}}<extra></extra>",
            )
        )

    fig.update_layout(
        xaxis={
            "rangeslider": {"visible": True},
            "type": "date",
        },
        yaxis_title=y_title,
        hovermode="x unified",
        template="plotly_white",
        margin={"l": 60, "r": 20, "t": 20, "b": 80},
        legend={"orientation": "h", "y": 1.02, "x": 0},
    )
    return fig


@callback(
    Output("stk-fetch-status", "children"),
    Input("stk-fetch-btn", "n_clicks"),
    prevent_initial_call=True,
)
def fetch_quotes(_n_clicks):
    if not _fetch_lock.acquire(blocking=False):
        return dbc.Alert("Fetch already in progress — please wait.", color="warning", className="py-1")
    try:
        from alphavantage.quotes import TickerQuotes

        tq = TickerQuotes()
        results = tq.fetch_quotes()
        tq.save_quotes(results)
        return dbc.Alert(
            f"Fetched and saved {len(results)} records at {datetime.now().strftime('%H:%M:%S')}",
            color="success",
            className="py-1",
        )
    except Exception as exc:
        return dbc.Alert(f"Error: {exc}", color="danger", className="py-1")
    finally:
        _fetch_lock.release()
