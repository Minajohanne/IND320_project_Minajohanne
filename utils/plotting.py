# Apply the shared styling to a Plotly figure.
def apply_plot_theme(fig):
    fig.update_layout(
        template="plotly_white",
        colorway=[
            "#1676C1",  # Blue
            "#348D73",  # Green
            "#D39A35",  # Warm yellow
            "#183B56",  # Dark blue
        ],
        font=dict(
            color="#183B56",
            size=13,
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        title_font=dict(
            color="#183B56",
            size=18,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    fig.update_xaxes(
        gridcolor="#E2EAF2",
        zerolinecolor="#E2EAF2",
    )

    fig.update_yaxes(
        gridcolor="#E2EAF2",
        zerolinecolor="#E2EAF2",
    )

    return fig