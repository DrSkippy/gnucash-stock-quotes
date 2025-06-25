#!/usr/bin/env -S poetry run python

import argparse
import logging
from logging.config import dictConfig

from alphavantage.quotes import TickerQuotes
from analyzer.gnucash import Gnucash
from analyzer.plots import CorrelationsPlotter
from market_indexes.portfolio import PortfolioAnalyzer

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s %(funcName)s at %(lineno)s: %(message)s',
    }},
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
})

FMT = "%Y-%m-%d"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""**Save Haven Adventure Kit** (SHaK) is a tool for analyzing and plotting stock market data.
        It allows you to compare two securities, create a gnucash quotes file, or analyze market indexes.
        """)
    parser.add_argument("command",
                        choices=['compare', 'gnucash', 'index'],
                        help="Command to execute: 'compare' for comparing securities, 'gnucash' for creating a gnucash quotes file, or 'index' for analyzing market indexes."
                        )
    parser.add_argument('-c', '--compare-securities',
                        action='append',
                        nargs="+",
                        dest='security',
                        help='2 security symbols')
    parser.add_argument('-l', '--list',
                        action='store_true',
                        default=False,
                        help='List available securities in the database')
    parser.add_argument('-i', '--index-name',
                        default=None,
                        help='Name of the index to analyze (e.g., "equal_weight", "constant", "market_cap")')
    parser.add_argument('-s', '--start-date',
                        default=None,
                        help='Start date for the analysis in YYYY-MM-DD format')
    parser.add_argument('-p', '--compare-portfolio',
                        action='append',
                        nargs="+",
                        dest='comp_portfolio',
                        help='Portfolio to compare against the index, e.g., "FFIV 0" for default allocation to FFIV')

    args = vars(parser.parse_args())

    if args['command'] == 'compare':
        if args['list']:
            tq = TickerQuotes()
            tq.print_tickers()

        if len(args['security'][0]) == 2:
            symbols = args['security'][0] if args['security'] is not None else []
            logging.info(f"args={args} symbols={symbols}")
            tq = TickerQuotes()
            dfs = tq.read_quotes(symbols=symbols)
            logging.info(f"data frame has {dfs.symbol.unique()}")

            comp = CorrelationsPlotter(dfs)
            comp.plot_correlation(*symbols)
    elif args['command'] == 'gnucash':
        dfs = TickerQuotes().read_quotes()  # save quotes json
        Gnucash(dfs).process_quotes()  # create gnucash object
    elif args['command'] == 'index':
        analyzer = PortfolioAnalyzer()
        if args['list']:
            tq = TickerQuotes()
            tq.print_tickers()
            analyzer.asset_index.print_indexes()
        if args['index_name']:
            if args['comp_portfolio'] is not None and len(args['comp_portfolio'][0]) == 2:
                cp = {str(args['comp_portfolio'][0][0]): float(args['comp_portfolio'][0][1])}
            else:
                cp = {"FFIV": 0}
            logging.info(f"comparison portfolio={cp}")
            index_name = args['index_name']
            analyzer.log_portfolio_value(index_name)
            # Compare and plot market cap index
            analyzer.analyze_and_plot(
                index_name,
                comparison_portfolio=cp,
                output_path=f"./data/{index_name}_comparison.pdf"
            )
        if args['security'] is not None and len(args['security'][0]) == 2:
            symbols = args['security'][0] if args['security'] is not None else []
            analyzer.correlations_plot(
                symbols=symbols,
                start_date=args['start_date']
            )
