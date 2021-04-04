import yaml
import argparse
import logging
import multiprocessing as mp
import numpy as np
import os
import pandas as pd
import pickle

import pyarrow.parquet as pq
import pyarrow as pa

from namematch.base import NamematchBase
from namematch.utils.utils import setup_logging
from namematch.data_structures.parameters import Parameters
from namematch.utils.utils import equip_logger_id, load_models, log_runtime_and_memory, determine_model_to_use, load_yaml

try:
    profile
except:
    from line_profiler import LineProfiler
    profile = LineProfiler()


# globals:
MATCH_COL = 1


class Predict(NamematchBase):
    def __init__(
        self,
        params,
        data_rows_dir,
        model_info_file,
        output_dir,
        output_file=None,
        logger_id=None,
        *args,
        **kwargs
    ):
        super(Predict, self).__init__(params, None, output_file, logger_id, *args, **kwargs)

        self.data_rows_dir = data_rows_dir
        self.model_info_file = model_info_file
        self.output_dir = output_dir
        self.output_file = []

    @equip_logger_id
    @log_runtime_and_memory
    def main__predict(self, **kw):
        '''Read in data-rows and predict (in parallel) for each unlabeled pair. Output
        the pairs above the threshold.

        Args:
            params (Parameters object): contains parameter values
            model_info_file (str): path to output_temp's data-rows dir
            data_rows_dir (str): path to the model info yaml file for a trained model
            output_dir (str): path to output_temp's potential-edges dir
        '''

        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        global logger

        logger_id = kw.get('logger_id')
        if logger_id:
            logger = logging.getLogger(f'namematch_{str(logger_id)}')

        else:
            logger = self.logger

        dr_file_list = [os.path.join(self.data_rows_dir, dr_file) for
                        dr_file in os.listdir(self.data_rows_dir)]

        # remove previous potential_edges files if they exists
        for potential_edges_file in os.listdir(self.output_dir):
            os.remove(os.path.join(self.output_dir, potential_edges_file))

        match_models, model_info = load_models(self.model_info_file)

        self.get_potential_edges_in_parallel(
                dr_file_list,
                match_models,
                model_info,
                self.output_dir,
                self.params)

    @profile
    @equip_logger_id
    @log_runtime_and_memory
    def get_potential_edges(self, dr_file, match_models, model_info,
                output_dir, params, chunksize=1000000, **kw):
        '''Read in data rows in chunks and predict as needed. Write (append)
        the edges above the threshold to the appropriate file.

        Args:
            dr_file (string): path to data file to predict for
            match_models (dict): maps model name (e.g. basic or no-dob) to a fit match model object
            model_info (dict): contains information about threshold
            output_dir (str): directory to place potential edges
            params (Parameters obj):  contains parameter values (i.e. use_uncovered_phats)
            chunksize (int): number of rows to read at a time
        '''
        try:
            thread = dr_file.split('/')[-1].replace('data_rows_', '').replace('.parquet', '')
            output_file = os.path.join(output_dir, f'potential_edges_{thread}.parquet')

            pq_df = pq.ParquetFile(dr_file)
            for i in range(pq_df.num_row_groups):

                df = pq_df.read_row_group(i).to_pandas()
                df = df[df.labeled_data == 0]

                if len(df) == 0:
                    continue

                df['model_to_use'] = determine_model_to_use(df, model_info)

                df = self.predict(match_models, df, 'match')

                df['potential_edge'] = 0
                for model_name in df.model_to_use.unique():
                    threshold = model_info[model_name]['match_thresh']
                    df.loc[(df.model_to_use == model_name) &
                           (df[f'{model_name}_match_phat'] >= threshold), 'potential_edge'] = 1

                if not params.use_uncovered_phats:
                    df.loc[df.covered_pair == 0, 'potential_edge'] = 0

                table = pa.Table.from_pandas(df)

                if i == 0:
                    pqwriter = pq.ParquetWriter(output_file, table.schema)
                    parquet_schema = table.schema

                if not df.empty:
                    pqwriter.write_table(table)

            if pqwriter:
                pqwriter.close()

        except Exception as e:
            os.remove(dr_file)
            logger.error(f"{dr_file} failed.")
            raise e

    def get_potential_edges_in_parallel(self, dr_file_list, match_models, model_info, output_dir, params):
        '''Dispatch the worker threads that will predict for unlabeled pairs in paralle.

        Args:
            dr_file_list (list): paths of output_temp's data-rows files
            match_models (dict): maps model name (e.g. basic or no-dob) to a fit match model object
            model_info (dict): dict with information about how to fit the model
            output_dir
            params (Parameters object): contains parameter values
        '''

        if params.parallelize:

            jobs = [
                mp.Process(
                    target = self.get_potential_edges,
                    args = (
                        dr_file,
                        match_models,
                        model_info,
                        output_dir,
                        params,
                        500000)) for dr_file in dr_file_list]
            for job in jobs:
                job.start()
            for job in jobs:
                t = job.join()
            failure_occurred = sum([job.exitcode != 0 for job in jobs])
            if failure_occurred:
                logger.error("Error occurred in %s worker(s)." % failure_occurred)
                raise Exception("Error occurred in %s worker(s)." % failure_occurred)

        else:

            for dr_file in dr_file_list:
                self.get_potential_edges(dr_file, match_models, model_info,
                        output_dir, params, 500000)

    @classmethod
    def predict(cls, models, df, model_type, oob=False, all_cols=False, all_models=True):
        '''Use the trainined models to predict for pairs of records.

        Args:
            models (dict): maps model name (e.g. basic or no-dob) to a fit match model object
            df (pd.DataFrame): portion of the data-rows table, with a "model_to_use" column appended
            model_type (str): model type (e.g. selection or match)
            oob (bool): if True, use the out-of-bag predictions
            all_cols (bool): if True, keep all columns in the output df; not just the relevant ones
            all_models (bool): if True, predict for each row using all models, not just the "model to use"
        '''

        if all_cols:

            phats = df.copy()

        else:

            cols_to_keep = [
                    'record_id_1', 'record_id_2', 'model_to_use',
                    'covered_pair', 'match_train_eligible', 'exactmatch', 'label']
            cols_to_keep = [col for col in cols_to_keep if col in df.columns]

            phats = df[cols_to_keep].copy()

        for model_name, mod in models.items():

            phat_col = f'{model_name}_{model_type}_phat'

            # initialize phat cols
            phats[phat_col] = np.NaN

            if oob:
                phats[phat_col] = mod.named_steps['clf'].oob_decision_function_[:, MATCH_COL]

            else:
                if all_models:
                    phats[phat_col] = mod.predict_proba(df)[:, MATCH_COL]
                else:
                    to_predict_for = (phats.model_to_use == model_name)
                    phats.loc[to_predict_for, phat_col] = \
                            mod.predict_proba(df[to_predict_for])[:, MATCH_COL]

        return phats

