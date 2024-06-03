import dash
from dash import dcc, Input, Output, State, html, MATCH, ALL, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import base64
import datetime
import io
from pathlib import Path
import os
import glob
import shutil

dash.register_page(__name__, path='/compare-optical', title='Micro-Image (Compare Optical)')

user_upload_dir = 'user_uploads'
analysis_type = 'compare_optical'
data_folder = Path(user_upload_dir)/analysis_type

@dash.callback(
    Output({'type': 'analytics-chart', 'index': MATCH}, 'figure'),
    Input({'type': 'chart-select', 'index': MATCH}, 'value'),
)
def callback_analytics_chart(chart_type):
    list_of_dfs = []
    list_of_filepaths = [fp for fp in sorted(glob.glob(os.path.join(data_folder, '*'))) if '.csv' in fp]
    list_of_filenames = [os.path.basename(fp) for fp in list_of_filepaths]
    for fp in list_of_filepaths:
        list_of_dfs.append(pd.read_csv(fp, index_col=0))
    num_files = len(list_of_filenames)
    #  plotly.express.colors.qualitative.Plotly
    list_of_colors = ['#636EFA',
                      '#EF553B',
                      '#00CC96',
                      '#AB63FA',
                      '#FFA15A',
                      '#19D3F3',
                      '#FF6692',
                      '#B6E880',
                      '#FF97FF',
                      '#FECB52'][:num_files]
    fig = visualize_mydata(chart_type, zip(list_of_filenames, list_of_dfs, list_of_colors))
    return fig

def visualize_mydata(chart_type, iter_fn_df_col):
    fig = go.Figure()

    # plot main diagram of the chart
    if chart_type == 'scatter':
        for fn,df,col in iter_fn_df_col:
            fig.add_trace(go.Scatter(x=df["fano"],
                                     y=df["mean_intensity"],
                                     name=fn,
                                     mode='markers',
                                     marker=dict(color=col)))
        fig.update_layout(legend=dict(yanchor="bottom",y=0.01,xanchor="right",x=0.99),height=650)
        fig.update_layout(yaxis={'title': 'mean intensity'},
                          xaxis={'title': 'var_intensity/mean_intensity'},
                          title='Estimate of homogeneity for optical images')

    else:
        for fn,df,col in iter_fn_df_col:
            fig.add_trace(go.Histogram(x=df[chart_type], name=fn))
        fig.update_layout(yaxis={'title': 'N'}, title=f"Histogram of {chart_type}")

    return fig


def built_in_analysis_filter(idx):
    return html.Div(
        id={
            'type': 'built-in-filter-container',
            'index': idx
        },
        children=[
            dcc.Dropdown(
                options={'scatter': 'Homogeneity (mean vs fano)',
                         'mean_intensity': 'Mean intensity',
                         'eccentricity': 'Eccentricity',
                         'area': 'Area',
                         'solidity': 'Solidity'
                         },
                value='scatter',
                clearable=False,
                id={
                    'type': 'chart-select',
                    'index': idx
                },
                className='filter-dropdown mb-2 mt-3'
            ),
        ]
    )


def new_chart(idx: int, width: int):
    chart = dbc.Col(md=width, className='py-3 px-3', children=
        dbc.Card(children=
            dbc.Row(children=[
                dbc.Col(md=10, className='chart-panel', children=[
                    dbc.Row(children=[
                        dbc.Col(md=9, children=[
                            dbc.Input(
                                className='chart-name-input',
                                placeholder='New Chart',
                                style={'border': 'none'}
                            )
                        ]),
                        dbc.Col(md=3, children=[
                            html.I(
                                className='fa-solid fa-trash-can',
                                title='Remove this chart',
                                id={
                                    'type': 'comparison-remove-chart-button',
                                    'index': idx
                                }
                            )
                        ])
                    ]),
                    dcc.Graph(
                        id={
                            'type': 'analytics-chart',
                            'index': idx
                        },
                        figure={}
                    )
                ]),
                dbc.Col(md=2, className='filter-panel', children=[
                    html.Div(id={
                        'type': 'comparison-filter',
                        'index': idx
                    }, children=[built_in_analysis_filter(idx)])
                ])
            ])
        )
    )

    return chart


@dash.callback(
    Output('comparison-charts-container', 'children'),
    Input('refresh-button-compare-optical', 'n_clicks'),
    Input({'type': 'comparison-add-chart-button', 'width': ALL}, 'n_clicks'),
    Input({'type': 'comparison-remove-chart-button', 'index': ALL}, 'n_clicks'),
    State('comparison-charts-container', 'children'),
    config_prevent_initial_callbacks=True
)
# Because of the ALL pattern matcher, when any one button is being clicked,
# all buttons' (of the same type) n_clicks will be returned as an array
def callback_comparison_charts_container(refresh_btn_n_clicks, add_btn_n_clicks_array, remove_btn_n_clicks_array, current_content):

    ctx = dash.callback_context
    if ctx.triggered_id == 'refresh-button-compare-optical':
        if refresh_btn_n_clicks:
            return []

    elif ctx.triggered_id['type'] == 'comparison-add-chart-button':  # add chart
        width = ctx.triggered_id['width']
        idx = 0
        for i in add_btn_n_clicks_array:
            if i:
                idx = idx + i
        current_content.append(new_chart(idx, width))
    elif ctx.triggered_id['type'] == 'comparison-remove-chart-button':  # remove chart
        for idx, val in enumerate(remove_btn_n_clicks_array):
            if val is not None:  # All buttons will have its n_clicks value equal to None, except the one being clicked
                del current_content[idx]
    return current_content

@dash.callback(
    Output('upload-csv-output','children'),
    Input('upload-csv','contents'),
    Input('upload-csv','filename'),
    Input('upload-csv','last_modified'),
    Input('refresh-button-compare-optical', 'n_clicks'),
    config_prevent_initial_callbacks=True
)
def callback_upload_csv_output(list_of_contents, list_of_names, list_of_dates, refresh_btn_n_clicks):
    ctx = dash.callback_context
    if ctx.triggered_id == 'refresh-button-compare-optical':
        return []
    # create new data folder
    os.makedirs(data_folder, exist_ok=True)
    children = dbc.Row([
        parse_csv(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
    ])
    return children

@dash.callback(
    Output('refresh-button-spinner-compare-optical','children'),
    Input('refresh-button-compare-optical', 'n_clicks')
)
def callback_refresh_button_spinner_compare_optical(n_clicks):
    list_of_filenames = None
    if n_clicks:
        # delete previous input images
        if data_folder.exists():
            list_of_filenames = os.listdir(data_folder)
            shutil.rmtree(data_folder)
        if not list_of_filenames:
            return None
        return [html.Div(f"Previous .csv files deleted: {list_of_filenames}")]


def parse_csv(contents, filename, date):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        # Assume that the user uploaded a CSV file
        df = pd.read_csv(io.StringIO(decoded.decode("utf-8")), index_col=0)
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    df = df[df["area"] >= 8000]
    df.to_csv(Path(data_folder)/filename) # write to working location

    return dbc.Col([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),
        html.H6(f"number of entries: {df.shape[0]}"),
    ], width='auto')

layout = dbc.Col(md=12, className='px-5 py-2', children=[
    html.Div(children=[
        dcc.Upload(
            id='upload-csv',
            children=html.Div(
                className='upload-csv-div',
                children=['Drag and Drop or ', html.A('Select Files', style={'fontWeight': 1000})]),
            className='mt-3',
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
            },
            multiple=True
        ),
        dbc.Spinner(html.Div(id='upload-csv-spinner', style={'textAlign': 'center'}), color='warning'),
        dbc.Card(id='upload-csv-output'),
    ]),
    dbc.Row(id='comparison-charts-container', className='mb-2', children=[
        # new_chart(0, 12)
    ]),
    dbc.Card(
        className='mx-1 border-0',
        children=dbc.Button(
            id={
                'type': 'comparison-add-chart-button',
                'width': 12
            },
            className='w-100',
            children='Add New Chart'
        )
    ),
    html.Br(),
    dbc.Card(
        className='mx-1 border-0',
        children=[
            # n_clicks=1 does an initial refresh
            dbc.Button("Refresh", id="refresh-button-compare-optical", color='danger', n_clicks=1),
            dbc.Spinner(html.Div(
                id="refresh-button-spinner-compare-optical",
                children="Click here to delete all input and output files",
                style={'textAlign': 'center'}
            ), color='warning'),
        ]
    ),
])
