import argparse, glob, importlib.util, os, subprocess, sys

h5py_spec = importlib.util.find_spec("h5py")
if h5py_spec is not None:
    import h5py


def _get_remote_path(ssh_remote, path):
    if ssh_remote:
        return ':'.join([ssh_remote, path])
    else:
        return path


def _get_completed_list(dest_dir, ssh_remote):
    completed_list_filepath = os.path.join(dest_dir, "completed_list")
    process = subprocess.Popen(["rsync",
                                _get_remote_path(ssh_remote,
                                                 completed_list_filepath),
                                '.'])
    process.wait()

    if os.path.exists("completed_list"):
        with open("completed_list", 'r') as file:
            content = file.read()

        completed_list = []
        for filename in content.split('\n'):
            if filename.endswith(".transcoded"):
                filename = filename[0:-len(".transcoded")]
            completed_list.append(os.path.basename(filename))

        return completed_list
    else:
        return []


def concat(args):
    """ Takes a source directory containing files and append/concatenate them
    into a single destination file

    Files contained in the subdirectory 'queue' of the source directory will be
    concatenated

    A 'completed_list' containing the concatenated file will be created in the
    source directory

    Files with a base name that is contained in the 'completed_list' file of
    the source directory will be ignored

    :param args: parsed arguments
    """
    src_dir = args.src
    dest_dir = os.path.dirname(args.dest)
    queued_files = glob.glob(os.path.join(src_dir, "queue/", '*'))
    queued_files.sort()

    if src_dir and not os.path.exists(src_dir):
        os.makedirs(src_dir)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    with open(args.dest, "ab") as concat_file, \
         open(os.path.join(src_dir, "completed_list"), "a") \
         as completed_list:
        for queued_filepath in queued_files:
            with open(queued_filepath, "rb") as queued_file:
                concat_file.write(queued_file.read())

            completed_list.write(queued_filepath + '\n')
            os.remove(queued_filepath)


def transcode_img(input_path, dest_dir, args):
    uploaded_dir = os.path.join(dest_dir, "upload/")
    queued_dir = os.path.join(dest_dir, "queue/")
    tmp_dir = args.tmp if args.tmp is not None else \
              os.path.dirname(input_path)
    filename = os.path.basename(input_path)

    if uploaded_dir and not os.path.exists(uploaded_dir):
        os.makedirs(uploaded_dir)
    if queued_dir and not os.path.exists(queued_dir):
        os.makedirs(queued_dir)
    if tmp_dir and not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    output_path = os.path.join(tmp_dir, filename + ".transcoded")
    command = args.transcoding_cmd.format(src=input_path, dest=output_path)
    process = subprocess.Popen(command.split())
    process.wait()

    uploaded_path = os.path.join(uploaded_dir, os.path.basename(output_path))
    process = subprocess.Popen(["rsync", "--remove-source-files", output_path,
                                _get_remote_path(args.ssh_remote,
                                                 uploaded_dir)])
    process.wait()

    queued_path = os.path.join(queued_dir, os.path.basename(output_path))
    if args.ssh_remote:
        subprocess.Popen(["ssh", args.ssh_remote,
                          "mv {} {}".format(uploaded_path, queued_path)])
    else:
        os.rename(uploaded_path, queued_path)


def transcode(args):
    """ Takes a list of images and transcodes them into a destination directory

    The suffix ".transcoded" will be appended to the file a base name

    Subdirectories 'upload' and 'queue' will be created in destination
    directory where 'upload' contains the files that are being uploaded and
    'queue' contains the files which are ready to be concatenated

    Files with a base name that is contained in the 'completed_list' file of
    the destination directory will be ignored

    :param args: parsed arguments
    """
    dest_dir = args.dest

    completed_list = _get_completed_list(dest_dir, args.ssh_remote)

    for input_path in args.src.split(','):
        if os.path.basename(input_path) in completed_list:
            continue
        transcode_img(input_path, dest_dir, args)


def extract_hdf5(args):
    """ Takes a source HDF5 file and extracts images from it into a destination
    directory. If the --transcode parameter is set, images will also be
    transcoded

    :param args: parsed arguments
    """
    if not args.transcode:
        args.transcoding_cmd = None
        args.ssh_remote = None
        args.tmp = None

    tmp_dir = args.tmp if args.tmp is not None else None
    extract_dir = tmp_dir if tmp_dir is not None else args.dest

    file_h5 = h5py.File(args.src, "r")
    num_elements = len(file_h5["encoded_images"])

    start = args.start
    end = min(start + args.number, num_elements) if args.number else num_elements

    if tmp_dir and not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    if extract_dir and not os.path.exists(extract_dir):
        os.makedirs(extract_dir)

    extracted_filenames = []

    for i in range(start, end):
        filename = file_h5["filenames"][i][0].decode("utf-8")
        extract_filepath = os.path.join(extract_dir, filename)
        extracted_filenames.append(extract_filepath)

        if os.path.exists(extract_filepath):
            continue

        img_jpeg = bytes(file_h5["encoded_images"][i])

        with open(extract_filepath, "xb") as file:
            file.write(img_jpeg)

    if args.transcode:
        transcode_args = build_transcode_parser() \
            .parse_args(["transcode",
                         ','.join(extracted_filenames),
                         args.dest,
                         args.transcoding_cmd,
                         "--ssh-remote", args.ssh_remote,
                         "--tmp", tmp_dir])

        transcode(transcode_args)


def build_base_parser():
    parser = argparse.ArgumentParser(description="Benzina HEIF Concatenation",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("action", choices=list(ACTIONS.keys()),
                        help="action to execute")
    parser.add_argument('_', metavar="...", nargs=argparse.REMAINDER,
                        help="use -h {} to view the action's arguments"
                             .format('{'+','.join(ACTIONS.keys())+'}'))

    return parser


def build_concat_parser():
    parser = argparse.ArgumentParser(description="Benzina HEIF Concatenation action: "
                                                 "\"concat\"",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("action", metavar="\"concat\"",
                        help="action to execute")
    parser.add_argument("src", metavar="source",
                        help="the source directory containing a 'queue' "
                             "directory of files to concatenate")
    parser.add_argument("dest", metavar="destination",
                        help="the destination concatenated file")

    return parser


def build_transcode_parser():
    parser = argparse.ArgumentParser(description="Benzina HEIF Concatenation action: "
                                                 "\"transcode\"",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("action", metavar="\"transcode\"",
                        help="action to execute")
    parser.add_argument("src", metavar="source",
                        help="the source file or ',' separated files to transcode")
    parser.add_argument("dest", metavar="destination",
                        help="the destination directory for the transcoded file(s)")
    parser.add_argument("transcoding_cmd", metavar="transcoding-cmd",
                        help="transcoding command with the following placeholders: "
                             "{src}, {dest}")
    parser.add_argument("--ssh-remote", metavar="REMOTE",
                        help="optional remote to use to transfer the transcoded "
                             "file to destination")
    parser.add_argument("--tmp", metavar="DIR",
                        help="the directory to use to store temporary file(s)")

    return parser


def build_extract_hdf5_parser():
    parser = argparse.ArgumentParser(description="Benzina HEIF Concatenation action: "
                                                 "\"extract_hdf5\"",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    if extract_hdf5:
        parser.add_argument("action", metavar="\"extract_hdf5\"",
                            help="action to execute")
        parser.add_argument("src", metavar="source",
                            help="the hdf5 file to draw the images to extract and "
                                 "transcode if --transcode is True")
        parser.add_argument("dest", metavar="destination",
                            help="the destination directory of extracted "
                                 "file(s) or transcoded file(s) if --transcode "
                                 "is True")
        parser.add_argument("--start", default=0, type=int,
                            help="the start element index to transcode from source")
        parser.add_argument("--number", default=1000, metavar="NUM", type=int,
                            help="the number of elements to extract from source")

        parser.add_argument("--transcode", default=False, action="store_true",
                            help="follow the extraction with a transcoding")
        parser.add_argument("--transcoding-cmd", metavar="CMD",
                            help="if --transcode is True, transcoding command "
                                 "with the following placeholders: "
                                 "{src}, {dest}")
        parser.add_argument("--ssh-remote", metavar="REMOTE",
                            help="if --transcode is True, optional remote to "
                                 "use to transfer the transcoded file to "
                                 "destination")
        parser.add_argument("--tmp", metavar="DIR",
                            help="if --transcode is True, the directory to "
                                 "store temporary file(s)")

    else:
        parser.add_argument("action", choices="\"extract_hdf5\"",
                            help="Unavailable action as h5py is not accessible")

    return parser


def parse_args(raw_arguments=None):
    argv = sys.argv[1:] if raw_arguments is None else raw_arguments
    is_help_request = "-h" in argv

    if is_help_request:
        if len(argv) == 1:
            build_base_parser().parse_args(argv)
        argv.remove("-h")
        base_args = build_base_parser().parse_args(argv)
        ACTIONS_PARSER.get(base_args.action, None).parse_args(argv + ["-h"])

    base_args = build_base_parser().parse_args(argv)
    return ACTIONS_PARSER.get(base_args.action, None).parse_args(argv)


def main(args):
    ACTIONS.get(args.action, None)(args)


ACTIONS = {"transcode": transcode, "concat": concat, "extract_hdf5": extract_hdf5}
ACTIONS_PARSER = {"concat": build_concat_parser(),
                  "transcode": build_transcode_parser(),
                  "extract_hdf5": build_extract_hdf5_parser(),
                  "_": build_base_parser()}


if __name__ == "__main__":
    main(parse_args())
