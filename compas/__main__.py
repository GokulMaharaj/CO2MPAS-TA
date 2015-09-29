"""
Predict NEDC CO2 emissions from WLTP cycles.

Usage:
    co2mpas [options] [-I <folder>  -O <folder>]
    co2mpas [-f | --force] --create-template <excel-file>
    co2mpas --help
    co2mpas --version

-I <folder> --inp <folder>       Input folder, prompted with GUI if missing.
                                 [default: ./input]
-O <folder> --out <folder>       Input folder, prompted with GUI if missing.
                                 [default: ./output]
--create-template <excel-file>   Create a new input-template excel-file.
-f --force                       Create template even if file already exists.
--plot-workflow                  Show workflow in browser, after run finished.
"""
# [-f | --force]
# -f --force                       Create template even if file already exists.
import sys
import os
import shutil
import pkg_resources
from docopt import docopt

from compas import __version__ as proj_ver


proj_name = 'co2mpas'


def _get_input_template_fpath():
    return pkg_resources.resource_filename(__name__,  # @UndefinedVariable
                                           'input_template.xlsx')


def _create_input_template(fpath, force=False):
    fpath = os.path.abspath(fpath)
    if not fpath.endswith('.xlsx'):
        fpath = '%s.xlsx' % fpath
    if os.path.exists(fpath) and not force:
        exit("File '%s' already exists! Use '-f' to overwrite it." % fpath)
    if os.path.isdir(fpath):
        exit("Expecting a file-name instead of directory '%s'!" % fpath)

    print("Creating co2mpas INPUT template-file '%s'..." % fpath,
          file=sys.stderr)
    shutil.copy(_get_input_template_fpath(), fpath)


def _prompt_folder(folder_name, folder):
    import easygui as eu

    while folder and not os.path.isdir(folder):
        print('Cannot find %s folder: %r' % (folder_name, folder),
              file=sys.stderr)
        folder = eu.diropenbox(msg='Select %s folder' % folder_name,
                               title=proj_name,
                               default=folder)
        if not folder:
            exit('User abort.')
    return folder


def main(*args):
    opts = docopt(__doc__,
                  argv=args or sys.argv[1:],
                  version='%s %s' % (proj_name, proj_ver))

    inp_template = opts['--create-template']
    if inp_template:
        _create_input_template(inp_template, opts['--force'])
        exit()

    input_folder = _prompt_folder(folder_name='INPUT', folder=opts['--inp'])
    input_folder = os.path.abspath(input_folder)

    output_folder = _prompt_folder(folder_name='OUTPUT', folder=opts['--out'])
    output_folder = os.path.abspath(output_folder)

    print("Processing '%s' --> '%s'..." %
          (input_folder, output_folder), file=sys.stderr)

    from compas.functions import process_folder_files
    process_folder_files(input_folder, output_folder,
                         plot_workflow=opts['--plot-workflow'])


if __name__ == '__main__':
    main()
