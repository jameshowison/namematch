
import pandas as pd
import numpy as np
import os

from namematch.namematcher import NameMatcher


# Define Name Match configuration
config_dict = {

    # define the data files that will be linked and/or deduplicated
    # -------------------------------------------------------------

    'data_files': {
        'potential_candidates': {
            'filepath' : '../preprocessed_data/potential_candidates.csv',
            'record_id_col' : 'record_id'
        },
        'past_candidates': {
            'filepath' : '../preprocessed_data/past_candidates.csv',
            'record_id_col' : 'candidacy_id'
        }
    },

    # define the variables that should be used in the matching process
    # ----------------------------------------------------------------

    'variables': [
        {
            'name' : 'first_name',
            'compare_type' : 'String',
            'potential_candidates_col' : 'first_name',
            'past_candidates_col' : 'first_name',
            'drop': [''] # don't include records with missing first-name in the match
        },
        {
            'name' : 'last_name',
            'compare_type' : 'String',
            'potential_candidates_col' : 'last_name',
            'past_candidates_col' : 'last_name',
            'drop': [''] # don't include records with missing last-name in the match
        },
        {
            'name' : 'dob',
            'compare_type' : 'Date',
            'potential_candidates_col' : 'dob',
            'past_candidates_col' : 'dob',
            'check' : 'Date - %Y-%m-%d' # optional, check to make sure that all input values
                                        # are in this format; otherwise, set to missing
        },
        {
            'name' : 'age',
            'compare_type' : 'Number',
            'potential_candidates_col' : 'age_in_2025',
            'past_candidates_col' : 'age_in_2025',
        },
        {
            'name' : 'middle_name',
            'compare_type' : 'String',
            'potential_candidates_col' : 'middle_name',
            'past_candidates_col' : 'middle_name'
        },
        {
            'name' : 'gender',
            'compare_type' : 'Category',
            'potential_candidates_col' : 'sex', # notice we refer to the original column name, which differs by dataset
            'past_candidates_col' : 'gender',
            'check' : 'M,F' # optional, check that input values are either M or F; otherwise, set to missing
        },
        {
            'name' : 'race',
            'compare_type' : 'Category',
            'potential_candidates_col' : 'race',
            'past_candidates_col' : 'race'
        },
        {
            'name' : 'marital_status',
            'compare_type' : 'Category',
            'potential_candidates_col' : 'marital_status',
            'past_candidates_col' : 'marital_status'
        },
        {
            # exactly one of the variables defined in the config should have compare_type of "UniqueID";
            # this is the pre-existing unique person-identifier that we identified when checking if our
            # datasets met the requirements of Name Match
            'name' : 'official_candidate_id',
            'compare_type' : 'UniqueID',
            'potential_candidates_col' : '', # the potential candidates dataset does not have this
                                             # column -- therefore the col value is empty ('')
            'past_candidates_col' : 'candidate_id'
        }
    ],

    # set parameter values (optional -- defaults work for most basic matching tasks)
    # ------------------------------------------------------------------------------

    'num_workers': 8,
    'pct_train': .9,
    'allow_clusters_w_multiple_unique_ids': False,
    'missingness_model': None,
    'negate_exact_match_variables': ['middle_name']

}

# Instantiate NameMatcher objet
nm = NameMatcher(
    config=config_dict
)

# Run Name Match
nm.run()

# Once the process completes, the output will be in the output/ directory
