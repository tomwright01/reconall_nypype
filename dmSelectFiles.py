import os
import logging

from nipype import SelectFiles
import datman.config as dm_cfg
import datman.scanid as dm_scanid

logging.basicConfig(level=logging.WARN,
                    format="[%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(os.path.basename(__file__))


class dmSelectFiles(SelectFiles):
    """
    Adds count checking, based on study config to the niPype SelectFiles class

    Requires the subject_id to be defined as dm_subject_id so study and site
    parameters can be extracted.

    Usage:
        templates = {'T1' : '{dm_subject_id}/{dm_subject_id}*T1*.nii.gz'}
        sf = dmSelectFiles(templates)
        sf.inputs.dm_subject_id = 'SPN01_CMH_0001_01'
    """
    dm_config = None

    def __init__(self, templates, **kwargs):
        self.dm_config = dm_cfg.config()
        super(dmSelectFiles, self).__init__(templates, **kwargs)

    def _list_outputs(self):
        outputs = super(dmSelectFiles, self)._list_outputs()

        # use the datman config file to get expected counts for each type of file
        if 'dm_subject_id' in self._infields:
            try:
                ident = dm_scanid.parse(self.inputs.dm_subject_id)
                study = ident.study
                site = ident.site
                export_info = self.dm_config.get_export_info_object(site,
                                                                    study=study)
            except:
                logger.warning('Invalid datman scanid:{}'
                               .format(self.inputs.dm_subject_id))
                return(outputs)

        for file_type in outputs.keys():
            try:
                expected_count = export_info.get_tag_info(file_type)['Count']
                if isinstance(outputs[file_type], str):
                    found_count = 1
                else:
                    found_count = len(outputs[file_type])
                if found_count > expected_count:
                    msg = ('Found {} {} files, expected {}.'
                           .format(found_count, file_type, expected_count))
                    raise IOError(msg)
            except KeyError:
                logger.debug('Count value for tag:{} not found.'
                             .format(file_type))
                pass

        return(outputs)
