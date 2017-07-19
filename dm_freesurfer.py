#!/usr/bin/env python
"""
Run the freesurfer pipeline on a datman study

Requires:
    Note: Instructions below differ slightly if running on scc or local

    Datman - module load /archive/code/datman_env.module
             N.B. these isn't the original datman module as we don't
                  want to force the python environment at this stage
    nipype - source activate some suitable env
             e.g. source /imaging/home/kimel/twright/miniconda3/bin/activate
    freesurfer - module load (F)freesurfer/6.0.0
            N.B. command arguments for freesurfer 6 are not compatible with
                 freesurfer 5. Specifically 5 supports --nu-iter but not --parallel
                 freesurfer 6 supports --parallel but not --nu-iter

Usage:
    dm_freesurfer.py [options] <study>

Arguments:
    <study>     Study name defined on master .yml file

Options:
  --log-to-server       If set, all log messages are sent to the configured
                        logging server.
  --debug               debug logging
"""

import os
import sys
import logging
import logging.handlers

from datman.docopt import docopt
import datman.config as dm_cfg
import datman.scanid as dm_scanid

from nipype.interfaces.freesurfer import ReconAll
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.pipeline.engine import Workflow, Node

from dmSelectFiles import dmSelectFiles
from EnigmaSummaries import EnigmaSummaryTask

logging.basicConfig(level=logging.WARN,
                    format="[%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(os.path.basename(__file__))


# Herein follows some helper functions
def add_server_handler(config):
    server_ip = config.get_key('LOGSERVER')
    server_port = logging.handlers.DEFAULT_TCP_LOGGING_PORT
    server_handler = logging.handlers.SocketHandler(server_ip,
                                                    server_port)
    logger.addHandler(server_handler)


def load_config(study):
    try:
        config = dm_cfg.config(study=study)
    except ValueError:
        logger.error('study {} not defined'.format(study))
        sys.exit(1)
    return config


def check_input_paths(config):
    for k in ['nii', 'freesurfer']:
        if k not in config.site_config['paths']:
            logger.error("paths:{} not defined in site config".format(k))
            sys.exit(1)


def get_nuiter_settings(subject_id):
    """
    Returns the site specific nu_iter settings for the pipeline
    Note as this is run as a function node I'm not sure how to handle logging
    >>> get_nuiter_settings('SPN01_CMH_0001_01')
    4
    >>> get_nuiter_settings('SPN01_MRC_0001_01')
    8
    """
    import datman.config as cfg
    import datman.scanid as scanid

    default_value = '-nuiterations 4'

    config = cfg.config()

    ident = scanid.parse(subject_id)
    site = ident.site

    try:
        study = config.map_xnat_archive_to_project(ident.study)
        config.set_study(study)
    except ValueError:
        # logger.warning('Study:{} not defined in config'.format(study))
        return(default_value)

    try:
        settings = config.get_key('freesurfer')
        nu_iter_settings = settings['nu_iter']
    except KeyError:
        # logger.warning('Freesurfer setting not found')
        return(default_value)

    try:
        if site in nu_iter_settings:
            iter_count = nu_iter_settings[site]
        elif 'DEFAULT' in nu_iter_settings:
            iter_count = nu_iter_settings['DEFAULT']
    except TypeError:
        # incase the nu_iter isn't defined as a dict ()
        iter_count = nu_iter_settings

    return('-nuiterations {}'.format(iter_count))


def get_common_scan_types(config):
    """
    Returns the scan types associated with a study site
    Only returns tags that are valid for all sites.
    Usage:
      >>> cfg = cfg.config(study='PRELAPSE')
      >>> get_scan_types(cfg)
      ['DTI60-1000', 'RST', 'T1', 'T2']

    # TODO:
        Move to datman.config
    """
    sites = config.get_key('Sites').keys()
    site_tags = []
    for site in sites:
        site_tags.append(set(config.get_export_info_object(site).tags))
    common_tags = set.intersection(*site_tags)
    common_tags = list(common_tags)
    common_tags.sort()
    return(common_tags)


def check_folder_exists(folder, create=True):
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder)
        except OSError:
            msg = ('Failed to create output folder:{}'
                   .format(folder))
            sys.exit(msg)


def main():
    arguments = docopt(__doc__)
    study = arguments['<study>']
    use_server = arguments['--log-to-server']
    debug = arguments['--debug']

    config = load_config(study)

    if use_server:
        add_server_handler(config)
    if debug:
        logger.setLevel(logging.DEBUG)
    ## setup some paths
    study_base_dir = config.get_study_base()
    fs_dir = config.get_path('freesurfer')
    data_dir = config.get_path('nii')
    # not sure where to put this. Potentially it could be very large
    # keeping it means existing subjects don't get re-run.
    # it could be deleted but then would need extra code to Determine
    # if subjects have been run.
    working_dir = os.path.join(study_base_dir, 'pipelines/workingdir_reconflow')

    ## These are overrides, for testing
    base_dir = '/external/rprshnas01/tigrlab/'
    fs_dir = os.path.join(base_dir, 'scratch/twright/pipelines/freesurfer', study)

    working_dir = os.path.join(base_dir, 'scratch/twright/pipelines/workingdir_reconflow')

    # freesurfer fails if the subjects dir doesn't exist
    check_folder_exists(fs_dir)
    # get the list of subjects that are not phantoms and have been qc'd
    subject_list = config.get_subject_metadata()
    subject_list = [subject for subject in subject_list
                    if not dm_scanid.is_phantom(subject)]

    # Need to determine if the study has T2 (or FLAIR) scans,
    # do this by looking in the study_config.yml for expected scantypes.
    # Current pipelines add T2 files if they exist on a per-subject basis
    # Nipype expects the each run of the pipeline to be the same across all subjects
    # it is possible to set some parameters on a per-subject basis (see nu-iter setting)
    # but is this desirable?
    scan_types = get_common_scan_types(config)

    if not 'T1' in scan_types:
        msg = 'Study {} does not have T1 scans, aborting.'.format(study)
        sys.exit(msg)

    templates = {'T1': '{dm_subject_id}/{dm_subject_id}_??_T1_??*.nii.gz'}
    if 'T2' in scan_types:
        templates['T2'] = '{dm_subject_id}/{dm_subject_id}_??_T2_??*.nii.gz'
    if 'FLAIR' in scan_types:
        logger.debug('FLAIR processing not yet implemented')
        #templates = {'T2': '{dm_subject_id}/{dm_subject_id}_??_FLAIR _??*.nii.gz'}

    # setup the nipype nodes
    # infosource justs iterates through the list of subjects
    infosource = Node(IdentityInterface(fields=['subject_id']),
                      name="infosource")
    # For testing
    subject_list = ['DTI_CMH_H001_02']
    infosource.iterables = ('subject_id', subject_list)

    # sf finds the files for each subject. The dmSelectFiles class
    # overrides the nipype.SelectFiles adding checks that the numbers
    # of files matches those defined in study_config.yml
    sf = Node(dmSelectFiles(templates),
              name="selectFiles")

    sf.inputs.base_directory = data_dir

    # set_nuiter implements a simple function to set the iteration count
    # on a subject by subject basis
    set_nuiter = Node(Function(input_names=['subject_id'],
                               output_names=['nu_iter'],
                               function=get_nuiter_settings),
                      name='get_nuiter')

    # reconall is the interface for the recon-all freesurfer function
    # currently seem unable to specify multiple directives
    #    (e.g. -qcache and -notal-check)
    reconall = Node(ReconAll(directive='all',
                             parallel=True,
                             subjects_dir=fs_dir),
                    name='recon-all')
    # if this is running on a cluster, we can specify node specific requirements
    #  i.e. reconall runs well with lots of cores.
    reconall.plugin_args = {'qsub_args': '-l nodes=1:ppn=24',
                            'overwrite': True}

    # get_summary extracts the summary information from the output of reconall
    get_summary = Node(EnigmaSummaryTask(),
                       name='Enigma_Summaries')

    ## Create the workflow
    reconflow = Workflow(name='reconflow')
    reconflow.base_dir = working_dir

    # need a different connection pattern and param for the reconall node
    # if T2 files exist
    sf_ra_conx = [('T1', 'T1_files')]

    if 'T2' in scan_types:
        reconall.inputs.use_T2 = True
        sf_ra_conx.append('T2', 'T2_file')

    ## Connect the outputs from each node to the corresponding inputs
    # Basically we link the defined outputs from each node, to the inputs of the next node
    #   Each item in the list is [node1, node2, [(output_node1, input_node2)]]


    # Problem here due to incompatibilities between freesurfer 5 & 6
    # this pattern works for freesurfer 5.3.0 (without the parallel flag for reconall)
    # but failes for 6.0.0, which doesn't support the nuierations flag.
    # reconflow.connect([(infosource, sf, [('subject_id', 'dm_subject_id')]),
    #                    (infosource, set_nuiter, [('subject_id', 'subject_id')]),
    #                    (sf, reconall, sf_ra_conx),
    #                    (set_nuiter, reconall, [('nu_iter', 'flags')])])

    # this is the freesurfer 6 compatible version
    reconflow.connect([(infosource, sf, [('subject_id', 'dm_subject_id')]),
                       (infosource, reconall, [('subject_id', 'subject_id')]),
                       (sf, reconall, sf_ra_conx),
                       (reconall, get_summary, [('subjects_dir', 'subjects_dir'),
                                                ('subject_id', 'subject_id'),
                                                ('subjects_dir', 'output_path')])])

    # need to use a job template to ensure the environment is set correctly
    # on the running nodes.
    # Not sure why the current env isn't being passed
    job_template = os.path.join(os.path.dirname(__file__), 'job_template_scc.sh')

    ## run the actual workflow.
    # the pbsGraph plugin creates jobs for each node on a PBS torque using
    # torque scheduling to keep them in order.
    # Use plugin='SGEGraph' to run on lab cluster (not sure what will happen
    #   to the reconflow node if we don't have any 24 core machines).
    # Don't specify a plugin to run on a single machine
    reconflow.run(plugin='PBSGraph', plugin_args=dict(template=job_template))


if __name__ == '__main__':
    main()
