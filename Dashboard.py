%%capture
%pip install nfl_data_py --upgrade
%pip install dash jupyter-dash

import nfl_data_py as nfl
import pandas as pd
import numpy as npid_df = nfl.import_ids()

id_df = id_df[['pfr_id','name','gsis_id']]

snap_counts_df = nfl.import_snap_counts([2023])

snap_counts_df = snap_counts_df[['pfr_player_id','position','offense_snaps','offense_pct','week']]

weekly_df = nfl.import_weekly_data([2023])

weekly_df = weekly_df[weekly_df['position'].isin(['QB', 'RB', 'WR', 'TE'])]

merged_df = pd.merge(id_df, snap_counts_df, left_on='pfr_id', right_on='pfr_player_id', how='inner')
final_merged_df = pd.merge(merged_df, weekly_df, left_on='gsis_id', right_on='player_id', how='inner')
final_merged_df = final_merged_df.rename(columns={"week_x": "snap_week", "week_y": "weekly_week"})
final_matched_weeks_df = final_merged_df[final_merged_df["snap_week"] == final_merged_df["weekly_week"]]
columns_to_remove = [
    'pfr_id', 'player_display_name', 'pfr_player_id',
    'position_x', 'gsis_id', 'position_group',
    'headshot_url', 'weekly_week', 'player_name'
]
cleaned_df = final_matched_weeks_df.drop(columns=columns_to_remove)
cleaned_df = cleaned_df.reset_index(drop=True)
cleaned_df = cleaned_df[['player_id', 'name'] + [col for col in cleaned_df.columns if col not in ['player_id', 'name']]]
cleaned_df = cleaned_df.rename(columns={"position_y": "position", "snap_week": "week"})
cleaned_df['offense_pct'] = (cleaned_df['offense_pct'] * 100).round(2)
cleaned_df['fp/snap'] = cleaned_df['fantasy_points_ppr'] / cleaned_df['offense_snaps']

from jupyter_dash import JupyterDash
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_table
import pandas as pd
import plotly.express as px

# Initialize the Dash app
app = JupyterDash(__name__)

# Define the layout of the app
app.layout = html.Div([
    html.H1("NFL Player Performance Dashboard"),

    # Dropdown for filtering teams
    html.Label("Select Team:"),
    dcc.Dropdown(id='team-dropdown', options=[{'label': team, 'value': team} for team in cleaned_df['recent_team'].unique()], multi=False, value=None),

    # Dropdown for filtering positions, initially empty
    html.Label("Select Position:"),
    dcc.Dropdown(id='position-dropdown', options=[], multi=False, value=None),

    # Dropdown for filtering players, initially empty
    html.Label("Select Player:"),
    dcc.Dropdown(id='player-dropdown', options=[], multi=False, value=None),

    # Data table to display filtered data
    dash_table.DataTable(
        id='data-table',
        columns=[{"name": i, "id": i} for i in cleaned_df.columns],
        page_size=10,
        style_table={'height': '400px', 'overflowY': 'auto'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
    ),

    # Graph to show offense snaps over weeks
    dcc.Graph(id='offense-snaps-graph')
])

# Callback to update position dropdown based on selected team
@app.callback(
    Output('position-dropdown', 'options'),
    [Input('team-dropdown', 'value')]
)
def set_position_options(selected_team):
    if selected_team is None:
        return []
    filtered_df = cleaned_df[cleaned_df['recent_team'] == selected_team]
    return [{'label': pos, 'value': pos} for pos in filtered_df['position'].unique()]

# Callback to update player dropdown based on selected team and position
@app.callback(
    Output('player-dropdown', 'options'),
    [Input('team-dropdown', 'value'),
     Input('position-dropdown', 'value')]
)
def set_player_options(selected_team, selected_position):
    if selected_team is None or selected_position is None:
        return []
    filtered_df = cleaned_df[(cleaned_df['recent_team'] == selected_team) & (cleaned_df['position'] == selected_position)]
    return [{'label': name, 'value': name} for name in filtered_df['name'].unique()]

# Callback to update data table and graph based on selected team, position, and player
@app.callback(
   [Output('offense-snaps-graph', 'figure')],
    [Input('team-dropdown', 'value'),
     Input('position-dropdown', 'value'),
     Input('player-dropdown', 'value')]
)
def update_dashboard(selected_team, selected_position, selected_player):
    # Start with the full DataFrame and progressively apply filters
    filtered_df = cleaned_df.copy()

    # Apply team filter if a team is selected
    if selected_team:
        filtered_df = filtered_df[filtered_df['recent_team'] == selected_team]

    # Apply position filter if a position is selected
    if selected_position:
        filtered_df = filtered_df[filtered_df['position'] == selected_position]

    # Apply player filter if a player is selected
    if selected_player:
        filtered_df = filtered_df[filtered_df['name'] == selected_player]

    # Check if the DataFrame is still non-empty after filtering
    if filtered_df.empty:
        # Return empty data for the table and an empty figure for the graph
        table_data = []
        fig = {
            'data': [],
            'layout': {
                'title': 'No Data Available'
            }
        }
    else:
        # Convert the filtered DataFrame to dictionary format for the table
        table_data = filtered_df.to_dict('records')

        # Create a graph for offense snaps over weeks
        fig = px.line(filtered_df, x='week', y='offense_snaps', color='name', title="Offense Snaps Over Time")

    return table_data, fig

# Run the app
app.run_server(mode='inline')
