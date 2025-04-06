#!/usr/bin/env python
# Example script to get USDJPY data using yfinance with pinjected
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pinjected import design, instance, injected

# Define currency pair as a constant
@instance
def currency_pair() -> str:
    return "USDJPY=X"

# Create a yfinance ticker instance
@instance
def forex_ticker(currency_pair):
    """Creates a yfinance Ticker object for the given currency pair"""
    return yf.Ticker(currency_pair)

# Function to get historical data with parameters
@injected
def get_historical_data(forex_ticker, /, period: str = "1mo", interval: str = "1d"):
    """
    Fetches historical price data for the forex pair
    
    Args:
        forex_ticker: The yfinance Ticker object (injected)
        period: Time period to fetch (e.g., '1d', '1mo', '1y')
        interval: Data interval (e.g., '1m', '1h', '1d')
    
    Returns:
        DataFrame with historical price data
    """
    return forex_ticker.history(period=period, interval=interval)

# Function to analyze the forex data
@injected
def analyze_forex_data(historical_data, currency_pair, /):
    """Performs basic analysis on the forex data"""
    print(f"Analysis for {currency_pair}:")
    print(f"Latest price: {historical_data['Close'].iloc[-1]:.4f}")
    print(f"Period high: {historical_data['High'].max():.4f}")
    print(f"Period low: {historical_data['Low'].min():.4f}")
    
    # Calculate daily returns
    historical_data['Daily Return'] = historical_data['Close'].pct_change() * 100
    
    # Calculate average daily volatility
    avg_volatility = historical_data['Daily Return'].std()
    print(f"Average daily volatility: {avg_volatility:.2f}%")
    
    return {
        "latest_price": historical_data['Close'].iloc[-1],
        "period_high": historical_data['High'].max(),
        "period_low": historical_data['Low'].min(),
        "avg_volatility": avg_volatility
    }

# Create a design that composes all dependencies
forex_design = design(
    currency_pair=currency_pair,
    forex_ticker=forex_ticker,
    historical_data=get_historical_data(period="6mo", interval="1d"),
    analysis=analyze_forex_data,
)

# Create an object graph and run the analysis
if __name__ == "__main__":
    # Convert the design to a graph and access the analysis
    graph = forex_design.to_graph()
    analysis_result = graph["analysis"]
    
    # Show a message confirming execution
    print("\nAnalysis completed successfully.")