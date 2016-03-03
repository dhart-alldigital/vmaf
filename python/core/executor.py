__copyright__ = "Copyright 2016, Netflix, Inc."
__license__ = "Apache, Version 2.0"

import multiprocessing
import os
import subprocess
from time import sleep

from tools.misc import make_parent_dirs_if_nonexist, get_dir_without_last_slash
from core.mixin import TypeVersionEnabled
import config


class Executor(TypeVersionEnabled):
    """
    An Executor takes in a list of Assets, and run calculation on them, and
    return a list of corresponding Results. An Executor must specify a unique
    type and version combination (by the TYPE and VERSION attribute), so that
    a Result generated by it can be identified.
    """

    def __init__(self,
                 assets,
                 logger,
                 log_file_dir=config.ROOT + "/workspace/log_file_dir",
                 fifo_mode=True,
                 delete_workdir=True,
                 result_store=None,
                 optional_dict=None,
                 ):

        TypeVersionEnabled.__init__(self)

        self.assets = assets
        self.logger = logger
        self.log_file_dir = log_file_dir
        self.fifo_mode = fifo_mode
        self.delete_workdir = delete_workdir
        self.results = []
        self.result_store = result_store
        self.optional_dict = optional_dict

        self._assert_assets()

    @property
    def executor_id(self):
        return TypeVersionEnabled.get_type_version_string(self)

    def run(self):
        """
        Do all the calculation here.
        :return:
        """
        if self.logger:
            self.logger.info(
                "For each asset, if {type} result has not been generated, run "
                "and generate {type} result...".format(type=self.executor_id))

        self.results = map(self._run_on_asset, self.assets)

    def remove_logs(self):
        """
        Remove all the intermediate log files if no need for inspection.
        :return:
        """
        for asset in self.assets:
            self._remove_log(asset)

    def remove_results(self):
        """
        Remove all relevant Results stored in ResultStore, which is specified
        at the constructor.
        :return:
        """
        for asset in self.assets:
            self._remove_result(asset)

    def _assert_assets(self):

        list_dataset_contentid_assetid = \
            map(lambda asset: (asset.dataset, asset.content_id, asset.asset_id),
                self.assets)
        assert len(list_dataset_contentid_assetid) == \
               len(set(list_dataset_contentid_assetid)), \
            "Triplet of dataset, content_id and asset_id must be unique for each asset."

    @staticmethod
    def _assert_an_asset(asset):

        # 1) for now, quality width/height has to agree with ref/dis width/height
        assert asset.quality_width_height \
               == asset.ref_width_height \
               == asset.dis_width_height
        # 2) ...
        # 3) ...

    def _wait_for_workfiles(self, asset):
        # wait til workfile paths being generated
        # FIXME: use proper mutex (?)
        for i in range(10):
            if os.path.exists(asset.ref_workfile_path) and \
                    os.path.exists(asset.dis_workfile_path):
                break
            sleep(0.1)
        else:
            raise RuntimeError("ref or dis video workfile path is missing.")

    def _prepare_log_file(self, asset):

        log_file_path = self._get_log_file_path(asset)

        # if parent dir doesn't exist, create
        make_parent_dirs_if_nonexist(log_file_path)

        # add runner type and version
        with open(log_file_path, 'wt') as log_file:
            log_file.write("{type_version_str}\n\n".format(
                type_version_str=self.get_cozy_type_version_string()))

    def _assert_paths(self, asset):
        assert os.path.exists(asset.ref_path), \
            "Reference path {} does not exist.".format(asset.ref_path)
        assert os.path.exists(asset.ref_path), \
            "Distorted path {} does not exist.".format(asset.dis_path)

    def _run_on_asset(self, asset):
        # Wraper around the essential function _run_and_generate_log_file, to
        # do housekeeping work including 1) asserts of asset, 2) skip run if
        # log already exist, 3) creating fifo, 4) delete work file and dir

        # asserts
        self._assert_an_asset(asset)

        if self.result_store:
            result = self.result_store.load(asset, self.executor_id)
        else:
            result = None

        if result is not None:
            if self.logger:
                self.logger.info('{id} result exists. Skip {id} run.'.
                                 format(id=self.executor_id))
        else:

            log_file_path = self._get_log_file_path(asset)
            if os.path.exists(log_file_path):
                if self.logger:
                    self.logger.info('{id} log file exists. Skip run and log file'
                                     ' generation.'.format(id=self.executor_id))

            else:

                if self.logger:
                    self.logger.info('{id} result does\'t exist. Perform {id} '
                                     'calculation.'.format(id=self.executor_id))

                # at this stage, it is certain that asset.ref_path and
                # asset.dis_path will be used. must early determine that
                # they exists
                self._assert_paths(asset)

                # remove workfiles if exist (do early here to avoid race condition
                # when ref path and dis path have some overlap)
                self._close_ref_workfile(asset)
                self._close_dis_workfile(asset)

                make_parent_dirs_if_nonexist(asset.ref_workfile_path)
                make_parent_dirs_if_nonexist(asset.dis_workfile_path)

                if self.fifo_mode:
                    ref_p = multiprocessing.Process(target=self._open_ref_workfile,
                                                    args=(asset, True))
                    dis_p = multiprocessing.Process(target=self._open_dis_workfile,
                                                    args=(asset, True))
                    ref_p.start()
                    dis_p.start()
                else:
                    self._open_ref_workfile(asset, fifo_mode=False)
                    self._open_dis_workfile(asset, fifo_mode=False)

                self._wait_for_workfiles(asset)
                self._prepare_log_file(asset)

                self._run_and_generate_log_file(asset)

                if self.delete_workdir:
                    self._close_ref_workfile(asset)
                    self._close_dis_workfile(asset)

                    ref_dir = get_dir_without_last_slash(asset.ref_workfile_path)
                    dis_dir = get_dir_without_last_slash(asset.dis_workfile_path)
                    os.rmdir(ref_dir)
                    try:
                        os.rmdir(dis_dir)
                    except OSError as e:
                        if e.errno == 2: # [Errno 2] No such file or directory
                            # already removed by os.rmdir(ref_dir)
                            pass

            if self.logger:
                self.logger.info("Read {id} log file, get scores...".
                                 format(type=self.executor_id))

            # collect result from each asset's log file
            result = self._read_result(asset)

            # save result
            if self.result_store:
                self.result_store.save(result)

        return result

    def _get_log_file_path(self, asset):
        return "{dir}/{executor_id}/{str}".format(dir=self.log_file_dir,
                                                  executor_id=self.executor_id,
                                                  str=str(asset))

    # ===== workfile =====

    def _open_ref_workfile(self, asset, fifo_mode):
        # For now, only works for YUV format -- all need is to copy from ref
        # file to ref workfile

        src = asset.ref_path
        dst = asset.ref_workfile_path

        # if fifo mode, mkfifo
        if fifo_mode:
            os.mkfifo(dst)

        # open ref file
        self._open_file(src, dst)

    def _open_dis_workfile(self, asset, fifo_mode):
        # For now, only works for YUV format -- all need is to copy from dis
        # file to dis workfile

        src = asset.dis_path
        dst = asset.dis_workfile_path

        # if fifo mode, mkfifo
        if fifo_mode:
            os.mkfifo(dst)

        # open dis file
        self._open_file(src, dst)

    def _open_file(self, src, dst):
        # For now, only works if source is YUV -- all needed is to copy

        # NOTE: & is required for fifo mode !!!!
        cp_cmd = "cp {src} {dst} &". \
            format(src=src, dst=dst)
        if self.logger:
            self.logger.info(cp_cmd)
        subprocess.call(cp_cmd, shell=True)

    @staticmethod
    def _close_ref_workfile(asset):
        path = asset.ref_workfile_path
        if os.path.exists(path):
            os.remove(path)

    @staticmethod
    def _close_dis_workfile(asset):
        path = asset.dis_workfile_path
        if os.path.exists(path):
            os.remove(path)

    def _remove_log(self, asset):
        log_file_path = self._get_log_file_path(asset)
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

    def _remove_result(self, asset):
        if self.result_store:
            self.result_store.delete(asset, self.executor_id)


def run_executors_in_parallel(executor_class,
                              assets,
                              log_file_dir=config.ROOT + "/workspace/log_file_dir",
                              fifo_mode=True,
                              delete_workdir=True,
                              parallelize=True,
                              logger=None,
                              result_store=None,
                              optional_dict=None,
                              ):
    """
    Run multiple Executors in parallel.
    :param executor_class:
    :param assets:
    :param log_file_dir:
    :param fifo_mode:
    :param delete_workdir:
    :param parallelize:
    :param logger:
    :param result_store:
    :param optional_dict:
    :return:
    """

    def run_executor(args):
        executor_class, asset, log_file_dir, fifo_mode, \
        delete_workdir, result_store, optional_dict = args
        executor = executor_class([asset], None, log_file_dir, fifo_mode,
                                  delete_workdir, result_store, optional_dict)
        executor.run()
        return executor

    # pack key arguments to be used as inputs to map function
    list_args = []
    for asset in assets:
        list_args.append(
            [executor_class, asset, log_file_dir, fifo_mode,
             delete_workdir, result_store, optional_dict])

    # map arguments to func
    if parallelize:
        try:
            from pathos.pp_map import pp_map
            executors = pp_map(run_executor, list_args)
        except ImportError:
            # fall back
            msg = "pathos.pp_map cannot be imported for parallel execution, fall back to sequential map()."
            if logger:
                logger.warn(msg)
            else:
                print 'Warning: {}'.format(msg)
            executors = map(run_executor, list_args)
    else:
        executors = map(run_executor, list_args)

    # aggregate results
    results = [executor.results[0] for executor in executors]

    return executors, results
