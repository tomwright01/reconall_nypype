from nipype.interfaces.base import (
    TraitedSpec,
    CommandLineInputSpec,
    CommandLine,
    Directory,
    File,
    Str
)
# The next 3 classes are wrappers for the shell scripts that extract the summary
# data after recon_all has finished
class EnigmaSummaryInputSpec(CommandLineInputSpec):
    """
    A nipype interface style class wrapping the inputs for
    Enigma_Summaries_nipype_launcher.sh
    """
    subjects_dir = Directory(desc="Freesurfer Subjects Directory",
                             exists=True,
                             mandatory=True,
                             position=1,
                             argstr='%s')
    subject_id = Str(desc="Subject id",
                     mandatory=True,
                     position=2,
                     argstr='%s')
    output_path = Directory(desc="Output directory",
                            exists=True,
                            mandatory=True,
                            position=3,
                            argstr='%s')


class EnigmaSummaryOutputSpec(TraitedSpec):
    """
    A nypype interface class wrapping the outputs for
    Enigma_Summaries_nipype_launcher.sh
    """
    thickness_file = File(desc="Thickness outputs",
                          exists=True)
    surface_file = File(desc="Surface outputs",
                        exists=True)
    subcortical_file = File(desc="Subcortical outputs",
                            exists=True)


class EnigmaSummaryTask(CommandLine):
    """
    Actual wrapper for the Enigma_Summaries_nipype_launcher.sh script
    """
    input_spec = EnigmaSummaryInputSpec
    output_spec = EnigmaSummaryOutputSpec
    cmd = 'Enigma_Summaries_nipype_launcher.sh'

    def __list_outputs(self):
        outputs = self.output_spec().get()
        out_path = os.path.abspath(self.inputs.output_path)
        outputs['thickness_file'] = os.path.join(out_path, 'CorticalMeasuresENIGMA_ThickAvg.csv')
        outputs['surface_file'] = os.path.join(out_path, 'CorticalMeasuresENIGMA_SurfAvg.csv')
        outputs['surface_file'] = os.path.join(out_path, 'LandRvolumes.csv')
        return(outputs)
