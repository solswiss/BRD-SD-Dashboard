# graph_config.py
VARIABLE_GROUPS = {
    # Combined category views
    'SEIQR': ['Susceptible', 'Infected', 'Quarantine', 'Exposed', 'Recovered'],
    'Antimicrobial Use': ['Cumulative antimicrobial usage', 'Metaphylactic usage', 'Therapeutic usage'],
    'Economic Outcomes': ['Profit', 'Herd Revenue', 'Total Production Loss', 'Healthcare cost'],
}

def build_view_options(schema: dict, doc) -> dict[str, list[str]]:
    """Builds a dictionary mapping selection options to lists of model variables."""
    # Start with predefined categories
    views = VARIABLE_GROUPS.copy()
    x = doc[['Real Name','Units','Type']].loc[doc['Type'] != 'Constant']

    # Add every individual variable dynamically from schema
    for idx, row in x.iterrows():
        real_name = row['Real Name']
        # avoid dupes
        if real_name not in views:
            views[real_name] = [real_name]
    
    return views