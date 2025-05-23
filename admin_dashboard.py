# admin_dashboard.py
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlalchemy
from datetime import datetime
import dash_bootstrap_components as dbc

# --- Database Connection ---
DATABASE_URL = "postgresql://uc29r4qrkaafp0:pc4f3853eac364c4a8bc0de75002ef99606ca5fdc2b0b1f0e4b5603a33742bf63@c952v5ogavqpah.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7u5skltcktane"
print(f"Attempting to connect to DB: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'RDS'}")
engine = None
try:
    engine = sqlalchemy.create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("SELECT 1"))
        print(f"DB Connection Test Successful. Result: {result.scalar_one()}")
except Exception as e:
    print(f"FATAL: Could not connect to database or execute test query: {e}")

# --- Initialize Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP]) # Using default Bootstrap
# Consider other themes: dbc.themes.FLATLY, dbc.themes.LUX, dbc.themes.ZEPHYR etc.
app.title = "Simulation Performance Dashboard"

# --- Helper: Load Full Data ---
def load_full_simulation_data():
    if not engine:
        print("Engine not initialized, cannot load data.")
        return pd.DataFrame()
    query = """
    SELECT 
        id, simulation_id_str, user_id_str, scenario_key, 
        simulation_started_at, simulation_ended_at,
        llm_overall_score, llm_timeliness_score, llm_contact_strategy_score,
        llm_decision_quality_score, llm_efficiency_score, llm_qualitative_feedback,
        llm_rating_at, user_rating_stars, user_feedback_text, user_rated_at,
        record_created_at, record_updated_at
    FROM simulation_ratings 
    ORDER BY record_created_at DESC;
    """
    try:
        df = pd.read_sql(query, engine)
        if df.empty:
            print("No data returned from simulation_ratings table.")
            return df

        score_cols = ['llm_overall_score', 'llm_timeliness_score', 'llm_contact_strategy_score',
                      'llm_decision_quality_score', 'llm_efficiency_score', 'user_rating_stars']
        for col in score_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                print(f"Warning: Expected score column '{col}' not found in DataFrame from DB.")
        
        if 'record_created_at' in df.columns:
            df['record_created_at'] = pd.to_datetime(df['record_created_at'], errors='coerce')
        else:
            print("Warning: 'record_created_at' column not found. Date filtering will be affected.")
        
        if 'simulation_id_str' in df.columns:
            df['simulation_id_str_short'] = df['simulation_id_str'].apply(lambda x: str(x)[-12:] if pd.notna(x) else None)
        
        return df
    except Exception as e:
        print(f"Error loading full data: {e}")
        return pd.DataFrame()

# --- App Layout ---
app.layout = dbc.Container([
    # 1. Header
    dbc.Row(dbc.Col(html.H1("Simulation Performance Dashboard"), width=12, className="mb-3 mt-4")),
    # html.Hr(className="mb-4"), # Optional horizontal line

    # 2. Filter Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Filters & Controls")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Scenario(s):"),
                            dcc.Dropdown(id='scenario-filter-dropdown', multi=True, placeholder="All Scenarios")
                        ], md=4),
                        dbc.Col([
                            html.Label("Select Date Range:"),
                            dcc.DatePickerRange(
                                id='date-picker-range',
                                min_date_allowed=datetime(2023, 1, 1).date(),
                                max_date_allowed=datetime.now().date(),
                                initial_visible_month=datetime.now().date(),
                                start_date=None, end_date=None,
                                display_format='MM/DD/YYYY'
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Filter by LLM Overall Score:"),
                            dcc.RangeSlider(
                                id='llm-score-slider', min=0, max=10, step=1,
                                marks={i: str(i) for i in range(11)}, value=[0, 10]
                            )
                        ], md=4),
                        # dbc.Col(dbc.Button("Apply Filters", id="apply-filters-button", color="primary", className="mt-3"), md=12, className="text-end")
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),

    # 3. KPIs / Summary Stats
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Simulations"), dbc.CardBody(html.H3(id="kpi-total-sims", children="-", className="text-center"))]), md=3, className="mb-3"),
        dbc.Col(dbc.Card([dbc.CardHeader("Avg. LLM Score"), dbc.CardBody(html.H3(id="kpi-avg-llm-score", children="-", className="text-center"))]), md=3, className="mb-3"),
        dbc.Col(dbc.Card([dbc.CardHeader("Avg. User Rating"), dbc.CardBody(html.H3(id="kpi-avg-user-rating", children="-", className="text-center"))]), md=3, className="mb-3"),
        dbc.Col(dbc.Card([dbc.CardHeader("Filtered Scenarios"), dbc.CardBody(html.H3(id="kpi-active-scenarios", children="-", className="text-center"))]), md=3, className="mb-3"),
    ], className="mb-3"),


    # 4. Tabs for Chart Groups
    dbc.Tabs([
        dbc.Tab(label="LLM Performance Overview", children=[
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("Average LLM Scores per Scenario"),
                    dbc.CardBody(dcc.Graph(id='avg-scores-per-scenario-graph'))
                ]), md=6, className="mb-3"),
                dbc.Col(dbc.Card([
                    dbc.CardHeader("LLM Overall Score Distribution"),
                    dbc.CardBody(dcc.Graph(id='llm-overall-score-distribution-graph'))
                ]), md=6, className="mb-3"),
            ]),
        ], tab_id="tab-llm-overview"),

        dbc.Tab(label="User Feedback Insights", children=[
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("User Star Rating Distribution"),
                    dbc.CardBody(dcc.Graph(id='user-star-rating-distribution-graph'))
                ]), md=6, className="mb-3"),
                dbc.Col(dbc.Card([
                    dbc.CardHeader("LLM Overall Score vs. User Star Rating"),
                    dbc.CardBody(dcc.Graph(id='llm-vs-user-rating-scatter-graph'))
                ]), md=6, className="mb-3"),
            ]),
        ], tab_id="tab-user-feedback"),

        dbc.Tab(label="Performance Trends", children=[
             dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("LLM Score Trend Over Time"),
                    dbc.CardBody(dcc.Graph(id='performance-trend-over-time-graph'))
                ]), md=12, className="mb-3"),
            ]),
        ], tab_id="tab-trends"),

        dbc.Tab(label="Detailed Ratings Data", children=[
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("Detailed Simulation Ratings"),
                    dbc.CardBody(
                        dash_table.DataTable(
                            id='ratings-table',
                            columns=[
                                {"name": "Sim ID (short)", "id": "simulation_id_str_short"},
                                {"name": "Scenario", "id": "scenario_key"},
                                {"name": "Player ID", "id": "user_id_str"},
                                {"name": "LLM Overall", "id": "llm_overall_score"},
                                {"name": "User Stars", "id": "user_rating_stars"},
                            ],
                            page_size=10,
                            style_cell={'textAlign': 'left', 'padding': '5px'},
                            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
                            style_table={'overflowX': 'auto'},
                            filter_action="native", sort_action="native",
                            export_format='csv',
                        )
                    )
                ]), width=12, className="mb-3")
            ])
        ], tab_id="tab-data-table"),
    ], id="content-tabs", active_tab="tab-llm-overview", className="mb-4"),

    dcc.Store(id='filtered-data-store')

], fluid=True, className="p-3") # Add some padding to the main container


# --- Callbacks ---

# Callback to populate scenario dropdown options and update filtered data store
@app.callback(
    [Output('scenario-filter-dropdown', 'options'),
     Output('filtered-data-store', 'data')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('llm-score-slider', 'value')]
    # If using "Apply Filters" button, add: Input('apply-filters-button', 'n_clicks')
    # and State for the other filters.
)
def update_scenario_options_and_filter_data(start_date, end_date, llm_score_range):
    # ctx = dash.callback_context
    # if not ctx.triggered and 'apply-filters-button' in some_config: # Logic for Apply button
    #     return dash.no_update, dash.no_update

    df_full = load_full_simulation_data()
    if df_full.empty:
        return [], pd.DataFrame().to_json(date_format='iso', orient='split')

    df_filtered = df_full.copy()

    if start_date and end_date and 'record_created_at' in df_filtered.columns:
        # Ensure record_created_at is timezone-naive if start/end dates are
        if df_filtered['record_created_at'].dt.tz:
             df_filtered['record_created_at_date'] = df_filtered['record_created_at'].dt.tz_localize(None).dt.date
        else:
            df_filtered['record_created_at_date'] = df_filtered['record_created_at'].dt.date
        try:
            start_date_obj = datetime.strptime(start_date.split('T')[0], '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date.split('T')[0], '%Y-%m-%d').date()
            df_filtered = df_filtered[
                (df_filtered['record_created_at_date'] >= start_date_obj) &
                (df_filtered['record_created_at_date'] <= end_date_obj)
            ]
        except ValueError:
            print(f"Error parsing dates: {start_date}, {end_date}")

    if 'llm_overall_score' in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered['llm_overall_score'] >= llm_score_range[0]) &
            (df_filtered['llm_overall_score'] <= llm_score_range[1])
        ]
    
    scenario_options = [{'label': 'All Scenarios', 'value': 'ALL'}] # Default option
    if 'scenario_key' in df_filtered.columns and not df_filtered.empty:
        unique_scenarios = sorted(df_filtered['scenario_key'].dropna().unique())
        scenario_options.extend([{'label': i, 'value': i} for i in unique_scenarios])
    
    return scenario_options, df_filtered.to_json(date_format='iso', orient='split')

# --- Callbacks for KPIs ---
@app.callback(
    [Output('kpi-total-sims', 'children'),
     Output('kpi-avg-llm-score', 'children'),
     Output('kpi-avg-user-rating', 'children'),
     Output('kpi-active-scenarios', 'children')],
    [Input('filtered-data-store', 'data'),
     Input('scenario-filter-dropdown', 'value')] # Also react to scenario dropdown for active scenarios
)
def update_kpis(jsonified_filtered_data, selected_scenarios):
    no_data_kpis = ("-", "-", "-", "-")
    if not jsonified_filtered_data:
        return no_data_kpis
    
    df = pd.read_json(jsonified_filtered_data, orient='split')
    if df.empty:
        return "0", "-", "-", "0"

    # Further filter by selected scenarios for KPI consistency
    if selected_scenarios and 'ALL' not in selected_scenarios:
        df_kpi = df[df['scenario_key'].isin(selected_scenarios)].copy()
    else:
        df_kpi = df.copy()
    
    if df_kpi.empty and not (selected_scenarios and 'ALL' in selected_scenarios): # if not ALL and result is empty
        return "0", "-", "-", "0"
    elif df_kpi.empty and (selected_scenarios and 'ALL' in selected_scenarios): # if ALL is selected but main df was empty
        df_kpi = df.copy() # revert to full filtered set for 'ALL'

    total_sims = len(df_kpi)
    
    avg_llm_score_val = "-"
    if 'llm_overall_score' in df_kpi.columns and not df_kpi['llm_overall_score'].dropna().empty:
        avg_llm_score_val = f"{df_kpi['llm_overall_score'].dropna().mean():.1f}"

    avg_user_rating_val = "-"
    if 'user_rating_stars' in df_kpi.columns and not df_kpi['user_rating_stars'].dropna().empty:
        avg_user_rating_val = f"{df_kpi['user_rating_stars'].dropna().mean():.1f}"

    active_scenarios_count = "0"
    if 'scenario_key' in df_kpi.columns:
        if selected_scenarios and 'ALL' not in selected_scenarios:
             active_scenarios_count = str(len(selected_scenarios))
        elif not df_kpi['scenario_key'].dropna().empty: # For ALL or no selection from dropdown
            active_scenarios_count = str(df_kpi['scenario_key'].nunique())
        
    return str(total_sims), avg_llm_score_val, avg_user_rating_val, active_scenarios_count

# --- Callbacks for Graphs and Table (Original Logic) ---

# Callback for Average Scores per Scenario
@app.callback(
    Output('avg-scores-per-scenario-graph', 'figure'),
    [Input('filtered-data-store', 'data'),
     Input('scenario-filter-dropdown', 'value')]
)
def update_avg_scores_graph(jsonified_filtered_data, selected_scenarios):
    placeholder_fig = go.Figure().update_layout(title="No data available for average scores graph", template="plotly_white")
    if not jsonified_filtered_data: return placeholder_fig
    
    df_store = pd.read_json(jsonified_filtered_data, orient='split')
    if df_store.empty: return placeholder_fig.update_layout(title="No data after initial filtering")

    if selected_scenarios and 'ALL' not in selected_scenarios:
        df = df_store[df_store['scenario_key'].isin(selected_scenarios)].copy()
    else:
        df = df_store.copy()

    if df.empty or 'scenario_key' not in df.columns:
        return placeholder_fig.update_layout(title="No data for selected scenarios")

    avg_cols = {
        'llm_overall_score': 'mean', 'llm_timeliness_score': 'mean',
        'llm_contact_strategy_score': 'mean', 'llm_decision_quality_score': 'mean',
        'llm_efficiency_score': 'mean', 'simulation_id_str': 'count'
    }
    agg_dict = {k: v for k, v in avg_cols.items() if k in df.columns}
    if not agg_dict or 'scenario_key' not in df.columns:
         return placeholder_fig.update_layout(title="Required columns for aggregation missing")

    df_agg = df.groupby('scenario_key', as_index=False).agg(agg_dict)
    if 'simulation_id_str' in df_agg.columns: # It was count of sim_id_str
        df_agg.rename(columns={'simulation_id_str': 'num_simulations'}, inplace=True)
    
    if df_agg.empty:
         return placeholder_fig.update_layout(title="No aggregated data for average scores")

    melt_value_vars = [col for col in df_agg.columns if col.startswith('llm_') and col.endswith('_score')]
    if not melt_value_vars or 'num_simulations' not in df_agg.columns:
        return placeholder_fig.update_layout(title="No LLM score columns to display")

    df_melted = df_agg.melt(id_vars=['scenario_key', 'num_simulations'],
                            value_vars=melt_value_vars,
                            var_name='score_type', value_name='average_score')
    
    if df_melted.empty:
        return placeholder_fig.update_layout(title="No data after melting for graph")

    df_melted['score_type'] = df_melted['score_type'].str.replace('llm_', '', case=False).str.replace('_score', '').str.title()

    fig = px.bar(df_melted, x="scenario_key", y="average_score",
                 color="score_type", barmode="group",
                 labels={"scenario_key": "Scenario", "average_score": "Avg. Score", "score_type": "Score Category"},
                 text_auto=".1f", template="plotly_white")
    fig.update_layout(legend_title_text='Score Category', title=None) # Title is in CardHeader
    return fig

# Callback for LLM Overall Score Distribution
@app.callback(
    Output('llm-overall-score-distribution-graph', 'figure'),
    [Input('filtered-data-store', 'data'),
     Input('scenario-filter-dropdown', 'value')]
)
def update_llm_score_distribution(jsonified_filtered_data, selected_scenarios):
    placeholder_fig = go.Figure().update_layout(title="No data available", template="plotly_white")
    if not jsonified_filtered_data: return placeholder_fig
    df_store = pd.read_json(jsonified_filtered_data, orient='split')
    if df_store.empty: return placeholder_fig.update_layout(title="No data after filtering")

    if selected_scenarios and 'ALL' not in selected_scenarios:
        df = df_store[df_store['scenario_key'].isin(selected_scenarios)].copy()
    else:
        df = df_store.copy()
    
    if df.empty or 'llm_overall_score' not in df.columns:
        return placeholder_fig.update_layout(title="No 'llm_overall_score' data for selection")

    fig = px.histogram(df, x="llm_overall_score", nbins=10,
                       labels={"llm_overall_score": "LLM Overall Score", "count": "Simulations"},
                       text_auto=True, template="plotly_white")
    fig.update_layout(bargap=0.1, title=None) # Title is in CardHeader
    return fig

# Callback for User Star Rating Distribution
@app.callback(
    Output('user-star-rating-distribution-graph', 'figure'),
    [Input('filtered-data-store', 'data'),
     Input('scenario-filter-dropdown', 'value')]
)
def update_user_star_distribution(jsonified_filtered_data, selected_scenarios):
    placeholder_fig = go.Figure().update_layout(title="No data available", template="plotly_white")
    if not jsonified_filtered_data: return placeholder_fig
    df_store = pd.read_json(jsonified_filtered_data, orient='split')
    if df_store.empty: return placeholder_fig.update_layout(title="No data after filtering")

    if selected_scenarios and 'ALL' not in selected_scenarios:
        df = df_store[df_store['scenario_key'].isin(selected_scenarios)].copy()
    else:
        df = df_store.copy()

    if df.empty or 'user_rating_stars' not in df.columns or df['user_rating_stars'].dropna().empty:
        return placeholder_fig.update_layout(title="No 'user_rating_stars' data for selection")

    rating_counts = df['user_rating_stars'].value_counts().sort_index()
    fig = px.pie(values=rating_counts.values, names=rating_counts.index,
                 labels={'names': 'Stars', 'values': 'Count'}, template="plotly_white")
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(title=None) # Title is in CardHeader
    return fig

# Callback for LLM Score vs User Rating Scatter Plot
@app.callback(
    Output('llm-vs-user-rating-scatter-graph', 'figure'),
    [Input('filtered-data-store', 'data'),
     Input('scenario-filter-dropdown', 'value')]
)
def update_llm_vs_user_scatter(jsonified_filtered_data, selected_scenarios):
    placeholder_fig = go.Figure().update_layout(title="No data available", template="plotly_white")
    if not jsonified_filtered_data: return placeholder_fig
    df_store = pd.read_json(jsonified_filtered_data, orient='split')
    if df_store.empty: return placeholder_fig.update_layout(title="No data after filtering")

    if selected_scenarios and 'ALL' not in selected_scenarios:
        df = df_store[df_store['scenario_key'].isin(selected_scenarios)].copy()
    else:
        df = df_store.copy()

    required_cols = ['llm_overall_score', 'user_rating_stars']
    if not all(col in df.columns for col in required_cols) or df.empty:
        missing = [col for col in required_cols if col not in df.columns]
        return placeholder_fig.update_layout(title=f"Missing columns for scatter: {', '.join(missing)}" if missing else "No data for selection")

    df_plot = df.dropna(subset=required_cols)
    if df_plot.empty:
        return placeholder_fig.update_layout(title="Not enough data points for scatter")

    fig = px.scatter(df_plot, x="user_rating_stars", y="llm_overall_score",
                     color="scenario_key" if "scenario_key" in df_plot.columns else None,
                     trendline="ols",
                     labels={"user_rating_stars": "User Star Rating (1-5)", "llm_overall_score": "LLM Overall Score (0-10)"},
                     template="plotly_white")
    fig.update_layout(title=None) # Title is in CardHeader
    return fig

# Callback for Performance Trend Over Time
@app.callback(
    Output('performance-trend-over-time-graph', 'figure'),
    [Input('filtered-data-store', 'data'),
     Input('scenario-filter-dropdown', 'value')]
)
def update_performance_trend(jsonified_filtered_data, selected_scenarios):
    placeholder_fig = go.Figure().update_layout(title="No data available", template="plotly_white")
    if not jsonified_filtered_data: return placeholder_fig
    df_store = pd.read_json(jsonified_filtered_data, orient='split')
    if df_store.empty: return placeholder_fig.update_layout(title="No data after filtering")

    if selected_scenarios and 'ALL' not in selected_scenarios:
        df = df_store[df_store['scenario_key'].isin(selected_scenarios)].copy()
    else:
        df = df_store.copy()

    if df.empty or 'record_created_at' not in df.columns or 'llm_overall_score' not in df.columns:
        return placeholder_fig.update_layout(title="Not enough data for trend (missing columns)")
    
    df_trend = df.dropna(subset=['record_created_at', 'llm_overall_score'])
    if df_trend.empty:
        return placeholder_fig.update_layout(title="No data points after NaNs removal for trend")
        
    df_trend = df_trend.copy()
    try:
        df_trend.loc[:, 'record_created_at'] = pd.to_datetime(df_trend['record_created_at'], errors='coerce')
        df_trend.dropna(subset=['record_created_at'], inplace=True)
        if df_trend.empty:
            return placeholder_fig.update_layout(title="No valid dates for trend after conversion")
        
        df_trend.loc[:, 'date_period'] = df_trend['record_created_at'].dt.to_period('W').astype(str)
    except Exception as e:
        print(f"Error processing dates for trend: {e}")
        return placeholder_fig.update_layout(title="Error in date processing for trend")
    
    df_agg_trend = df_trend.groupby('date_period')['llm_overall_score'].mean().reset_index()
    df_agg_trend = df_agg_trend.sort_values('date_period')

    if df_agg_trend.empty:
        return placeholder_fig.update_layout(title="No aggregated trend data")

    fig = px.line(df_agg_trend, x="date_period", y="llm_overall_score",
                  markers=True,
                  labels={"date_period": "Week", "llm_overall_score": "Avg. LLM Overall Score"},
                  template="plotly_white")
    fig.update_layout(title=None) # Title is in CardHeader
    return fig

# Callback for DataTable
@app.callback(
    Output('ratings-table', 'data'),
    [Input('filtered-data-store', 'data'),
     Input('scenario-filter-dropdown', 'value')]
)
def update_ratings_table(jsonified_filtered_data, selected_scenarios):
    if not jsonified_filtered_data: return []
    df_store = pd.read_json(jsonified_filtered_data, orient='split')
    if df_store.empty: return []

    if selected_scenarios and 'ALL' not in selected_scenarios:
        df = df_store[df_store['scenario_key'].isin(selected_scenarios)].copy()
    else:
        df = df_store.copy()

    if df.empty: return []
    
    cols_for_table = [
        "simulation_id_str_short", "scenario_key", "user_id_str", 
        "llm_overall_score", "user_rating_stars"
    ]
    df_display = df[[col for col in cols_for_table if col in df.columns]]
    return df_display.to_dict('records')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8055)